from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from schedule_repair.domain import Lesson

DAY_ORDER = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi")


def active_weeks(frequency: str | None) -> frozenset[str]:
    """Return the alternating weeks in which a lesson occupies resources."""
    normalized = (frequency or "H").strip().upper()
    if normalized == "A":
        return frozenset({"A"})
    if normalized == "B":
        return frozenset({"B"})
    return frozenset({"A", "B"})


@dataclass(frozen=True, slots=True)
class Placement:
    source_row: int
    day: str
    start_slot: int
    span_slots: int
    frequency: str
    teacher: str | None
    class_group: str | None
    room: str | None

    @property
    def end_slot(self) -> int:
        return self.start_slot + self.span_slots


@dataclass(frozen=True, slots=True)
class Candidate:
    target: Lesson
    placement: Placement
    score: int
    changed: bool
    teacher_day_off_used: bool
    gap_delta: int

    def to_dict(self, slot_times: tuple[int, ...]) -> dict[str, object]:
        result = {
            "source_row": self.target.source_row,
            "teacher": self.target.teacher,
            "class_group": self.target.class_group,
            "subject": self.target.subject,
            "frequency": self.target.frequency,
            "room": self.target.room,
            "old_day": self.target.day,
            "old_start": _format_minute(self.target.start_minute),
            "new_day": self.placement.day,
            "new_start": _format_minute(slot_times[self.placement.start_slot]),
            "new_duration_minutes": 120,
            "changed": self.changed,
            "teacher_day_off_used": self.teacher_day_off_used,
            "gap_delta": self.gap_delta,
            "score": self.score,
        }
        return result


@dataclass(frozen=True, slots=True)
class BlockedOption:
    target: Lesson
    placement: Placement
    blocker_rows: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class RepairPlan:
    slot_times: tuple[int, ...]
    suggestions: tuple[Candidate, ...]
    unresolved: tuple[Lesson, ...]
    blocked_options: tuple[BlockedOption, ...] = ()
    baseline_gap_units: int = 0
    final_gap_units: int = 0

    def summary(self) -> dict[str, int]:
        return {
            "physics_lessons": len(self.suggestions) + len(self.unresolved),
            "resolved": len(self.suggestions),
            "unresolved": len(self.unresolved),
            "extended_in_place": sum(not item.changed for item in self.suggestions),
            "moved": sum(item.changed for item in self.suggestions),
            "teacher_days_off_used": sum(item.teacher_day_off_used for item in self.suggestions),
            "net_gap_delta": self.final_gap_units - self.baseline_gap_units,
            "score": sum(item.score for item in self.suggestions),
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "summary": self.summary(),
            "time_bounds": {
                "earliest_start": _format_minute(self.slot_times[0]),
                "latest_start": _format_minute(self.slot_times[-1]),
            },
            "suggestions": [item.to_dict(self.slot_times) for item in self.suggestions],
            "unresolved": [self._unresolved_dict(item) for item in self.unresolved],
        }

    def _unresolved_dict(self, item: Lesson) -> dict[str, object]:
        blocked = next(
            (option for option in self.blocked_options if option.target.source_row == item.source_row),
            None,
        )
        result: dict[str, object] = {
            "source_row": item.source_row,
            "teacher": item.teacher,
            "class_group": item.class_group,
            "frequency": item.frequency,
            "room": item.room,
            "day": item.day,
            "start": item.start_time,
        }
        if blocked:
            result["nearest_candidate"] = {
                "day": blocked.placement.day,
                "start": _format_minute(self.slot_times[blocked.placement.start_slot]),
                "blocker_rows": list(blocked.blocker_rows),
            }
        return result


class FirstPassOptimizer:
    """Find conflict-free two-period placements without moving other subjects."""

    def __init__(self, lessons: Iterable[Lesson], subject_contains: str = "PHYSIQUE-CHIMIE") -> None:
        self.lessons = tuple(lessons)
        needle = subject_contains.casefold()
        self.targets = tuple(
            item for item in self.lessons if needle in (item.subject or "").casefold()
        )
        self.slot_times = tuple(
            sorted({item.start_minute for item in self.lessons if item.start_minute is not None})
        )
        self.slot_index = {minute: index for index, minute in enumerate(self.slot_times)}
        self.days = tuple(day for day in DAY_ORDER if any(item.day == day for item in self.lessons))
        self.placements = tuple(self._placement(item) for item in self.lessons)
        target_rows = {item.source_row for item in self.targets}
        self.fixed = tuple(item for item in self.placements if item.source_row not in target_rows)
        self.teacher_days = self._teacher_days()

    def optimize(self, beam_width: int = 250, options_per_state: int = 12) -> RepairPlan:
        options = {target.source_row: self._options(target) for target in self.targets}
        ordered = sorted(self.targets, key=lambda item: (len(options[item.source_row]), item.source_row))
        states: list[tuple[tuple[Candidate, ...], tuple[Lesson, ...], int]] = [((), (), 0)]
        for target in ordered:
            states = self._advance_states(
                states,
                target,
                options[target.source_row],
                beam_width,
                options_per_state,
            )
        chosen, unresolved, _ = min(states, key=_state_key)
        chosen, unresolved = self._stabilize_partial_plan(chosen, unresolved)
        chosen, unresolved = self._fill_from_unchanged_baseline(chosen, unresolved, options)
        blocked_options = tuple(
            self._diagnose_blockers(item, chosen, unresolved) for item in unresolved
        )
        final_placements = (
            self.fixed
            + tuple(item.placement for item in chosen)
            + tuple(self._placement(item) for item in unresolved)
        )
        return RepairPlan(
            slot_times=self.slot_times,
            suggestions=tuple(sorted(chosen, key=lambda item: item.target.source_row)),
            unresolved=tuple(sorted(unresolved, key=lambda item: item.source_row)),
            blocked_options=tuple(sorted(blocked_options, key=lambda item: item.target.source_row)),
            baseline_gap_units=self._all_gap_units(self.placements),
            final_gap_units=self._all_gap_units(final_placements),
        )

    def validate(self, plan: RepairPlan) -> tuple[str, ...]:
        issues = []
        unchanged = tuple(self._placement(item) for item in plan.unresolved)
        for index, suggestion in enumerate(plan.suggestions):
            placement = suggestion.placement
            if placement.start_slot < 0 or placement.end_slot > len(self.slot_times):
                issues.append(f"Row {placement.source_row} exceeds the source time range")
            if placement.room != suggestion.target.room:
                issues.append(f"Row {placement.source_row} changed room")
            if any(conflicts(placement, fixed) for fixed in self.fixed):
                issues.append(f"Row {placement.source_row} conflicts with a fixed lesson")
            if any(conflicts(placement, original) for original in unchanged):
                issues.append(f"Row {placement.source_row} conflicts with an unresolved lesson")
            for other in plan.suggestions[index + 1 :]:
                if conflicts(placement, other.placement):
                    issues.append(
                        f"Rows {placement.source_row} and {other.placement.source_row} conflict"
                    )
        return tuple(issues)

    def _advance_states(
        self,
        states: list[tuple[tuple[Candidate, ...], tuple[Lesson, ...], int]],
        target: Lesson,
        options: tuple[Candidate, ...],
        beam_width: int,
        options_per_state: int,
    ) -> list[tuple[tuple[Candidate, ...], tuple[Lesson, ...], int]]:
        expanded = []
        for chosen, unresolved, score in states:
            legal = [
                item
                for item in options
                if not any(conflicts(item.placement, prior.placement) for prior in chosen)
            ]
            for candidate in legal[:options_per_state]:
                expanded.append((chosen + (candidate,), unresolved, score + candidate.score))
            expanded.append((chosen, unresolved + (target,), score))
        expanded.sort(key=_state_key)
        return expanded[:beam_width]

    def _stabilize_partial_plan(
        self, chosen: tuple[Candidate, ...], unresolved: tuple[Lesson, ...]
    ) -> tuple[tuple[Candidate, ...], tuple[Lesson, ...]]:
        remaining = list(chosen)
        unchanged = list(unresolved)
        while True:
            occupied = tuple(self._placement(item) for item in unchanged)
            invalid = [
                item
                for item in remaining
                if any(conflicts(item.placement, original) for original in occupied)
            ]
            if not invalid:
                break
            invalid_rows = {item.target.source_row for item in invalid}
            remaining = [item for item in remaining if item.target.source_row not in invalid_rows]
            unchanged.extend(item.target for item in invalid)
        return tuple(remaining), tuple(unchanged)

    def _fill_from_unchanged_baseline(
        self,
        chosen: tuple[Candidate, ...],
        unresolved: tuple[Lesson, ...],
        options: dict[int, tuple[Candidate, ...]],
    ) -> tuple[tuple[Candidate, ...], tuple[Lesson, ...]]:
        selected = list(chosen)
        pending = list(unresolved)
        progress = True
        while progress:
            progress = False
            for target in tuple(pending):
                unchanged = tuple(
                    self._placement(item) for item in pending if item.source_row != target.source_row
                )
                occupied = tuple(item.placement for item in selected) + unchanged
                candidate = next(
                    (
                        item
                        for item in options[target.source_row]
                        if not any(conflicts(item.placement, prior) for prior in occupied)
                    ),
                    None,
                )
                if candidate:
                    selected.append(candidate)
                    pending.remove(target)
                    progress = True
        return tuple(selected), tuple(pending)

    def _options(self, target: Lesson) -> tuple[Candidate, ...]:
        if target.start_minute not in self.slot_index or len(self.slot_times) < 2:
            return ()
        candidates = []
        for day in self.days:
            for start_slot in range(len(self.slot_times) - 1):
                placement = self._candidate_placement(target, day, start_slot)
                if any(conflicts(placement, fixed) for fixed in self.fixed):
                    continue
                candidates.append(self._score_candidate(target, placement))
        return tuple(sorted(candidates, key=lambda item: (item.score, item.placement.day, item.placement.start_slot)))

    def _diagnose_blockers(
        self,
        target: Lesson,
        chosen: tuple[Candidate, ...],
        unresolved: tuple[Lesson, ...],
    ) -> BlockedOption:
        occupied = (
            self.fixed
            + tuple(item.placement for item in chosen)
            + tuple(self._placement(item) for item in unresolved if item.source_row != target.source_row)
        )
        alternatives = []
        for day in self.days:
            for start_slot in range(len(self.slot_times) - 1):
                placement = self._candidate_placement(target, day, start_slot)
                blocker_rows = tuple(
                    sorted({item.source_row for item in occupied if conflicts(placement, item)})
                )
                score = self._score_candidate(target, placement).score
                alternatives.append((len(blocker_rows), score, placement, blocker_rows))
        _, _, placement, blocker_rows = min(alternatives, key=lambda item: (item[0], item[1]))
        return BlockedOption(target, placement, blocker_rows)

    def _all_gap_units(self, placements: tuple[Placement, ...]) -> int:
        teachers = {item.teacher for item in placements if item.teacher}
        classes = {item.class_group for item in placements if item.class_group}
        teacher_gaps = sum(_resource_gaps(placements, "teacher", item) for item in teachers)
        class_gaps = sum(_resource_gaps(placements, "class_group", item) for item in classes)
        return teacher_gaps + class_gaps

    def _candidate_placement(self, target: Lesson, day: str, start_slot: int) -> Placement:
        return Placement(
            source_row=target.source_row,
            day=day,
            start_slot=start_slot,
            span_slots=2,
            frequency=target.frequency or "H",
            teacher=target.teacher,
            class_group=target.class_group,
            room=target.room,
        )

    def _score_candidate(self, target: Lesson, placement: Placement) -> Candidate:
        original_slot = self.slot_index[target.start_minute]
        changed = target.day != placement.day or original_slot != placement.start_slot
        day_distance = abs(self.days.index(target.day) - self.days.index(placement.day))
        slot_distance = abs(original_slot - placement.start_slot)
        teacher_days = self.teacher_days.get(target.teacher or "", set())
        day_off_used = placement.day not in teacher_days
        gap_delta = self._gap_delta(target, placement)
        score = int(changed) * 1000 + day_distance * 100 + slot_distance * 25
        score += int(day_off_used) * 400 + gap_delta * 20
        return Candidate(target, placement, score, changed, day_off_used, gap_delta)

    def _gap_delta(self, target: Lesson, candidate: Placement) -> int:
        current = self._placement(target)
        old_placements = self.placements
        without_target = tuple(item for item in old_placements if item.source_row != target.source_row)
        proposed = without_target + (candidate,)
        return sum(
            _resource_gaps(proposed, kind, value) - _resource_gaps(old_placements, kind, value)
            for kind, value in (("teacher", target.teacher), ("class_group", target.class_group))
            if value
        )

    def _placement(self, lesson: Lesson) -> Placement:
        if lesson.start_minute not in self.slot_index:
            raise ValueError(f"Lesson row {lesson.source_row} has an unknown start time")
        return Placement(
            source_row=lesson.source_row,
            day=lesson.day or "",
            start_slot=self.slot_index[lesson.start_minute],
            span_slots=max(1, round((lesson.duration_minutes or 60) / 60)),
            frequency=lesson.frequency or "H",
            teacher=lesson.teacher,
            class_group=lesson.class_group,
            room=lesson.room,
        )

    def _teacher_days(self) -> dict[str, set[str]]:
        result: dict[str, set[str]] = {}
        for lesson in self.lessons:
            if lesson.teacher and lesson.day:
                result.setdefault(lesson.teacher, set()).add(lesson.day)
        return result


def conflicts(left: Placement, right: Placement) -> bool:
    if left.day != right.day:
        return False
    if not active_weeks(left.frequency).intersection(active_weeks(right.frequency)):
        return False
    if left.end_slot <= right.start_slot or right.end_slot <= left.start_slot:
        return False
    same_teacher = _same(left.teacher, right.teacher)
    same_room = _same(left.room, right.room)
    same_students = class_groups_conflict(left.class_group, right.class_group)
    return same_teacher or same_room or same_students


def class_groups_conflict(left: str | None, right: str | None) -> bool:
    if not left or not right:
        return False
    left_parent, left_subgroup = _class_parts(left)
    right_parent, right_subgroup = _class_parts(right)
    if left_parent != right_parent:
        return False
    return left_subgroup is None or right_subgroup is None or left_subgroup == right_subgroup


def render_markdown_report(
    plan: RepairPlan, source_name: str, lessons: Iterable[Lesson] = ()
) -> str:
    summary = plan.summary()
    lines = [
        "# First physics-chemistry timetable repair",
        "",
        f"Source: `{source_name}` (read-only)",
        "",
        "## Result",
        "",
        f"- Physics-chemistry rows considered: {summary['physics_lessons']}",
        f"- Conflict-free two-period suggestions: {summary['resolved']}",
        f"- Extended at the existing start: {summary['extended_in_place']}",
        f"- Repositioned physics rows: {summary['moved']}",
        f"- Unresolved in the conservative first pass: {summary['unresolved']}",
        f"- Suggestions using a teacher's baseline day off: {summary['teacher_days_off_used']}",
        f"- Net change in teacher/class gap units: {summary['net_gap_delta']}",
        "",
        "## Interpretation rules",
        "",
        "- `H` occupies both week A and week B.",
        "- `A` occupies only week A and `B` occupies only week B; A and B may share a slot.",
        "- Two consecutive hours means two adjacent timetable periods.",
        f"- Candidate starts stay within {_format_minute(plan.slot_times[0])}–{_format_minute(plan.slot_times[-1])}, the source timetable range.",
        "- The teacher, class/group, frequency, and exact original room are preserved.",
        "- Teacher days off are inferred from days with no baseline lesson and penalized, not forbidden.",
        "- This first pass does not move lessons from other subjects.",
        "",
        "## Suggested modifications",
        "",
        "| Excel row | Week | Teacher | Class/group | Room | Current | Suggested two-period start | Action | Day off? |",
        "| ---: | :---: | --- | --- | --- | --- | --- | --- | :---: |",
    ]
    for item in plan.suggestions:
        values = item.to_dict(plan.slot_times)
        action = "extend in place" if not item.changed else "reposition physics"
        current = f"{values['old_day']} {values['old_start']}"
        proposed = f"{values['new_day']} {values['new_start']}"
        lines.append(
            f"| {values['source_row']} | {values['frequency']} | {values['teacher']} | "
            f"{values['class_group']} | {values['room']} | {current} | {proposed} | "
            f"{action} | {'yes' if values['teacher_day_off_used'] else 'no'} |"
        )
    lines.extend(_unresolved_section(plan, {item.source_row: item for item in lessons}))
    lines.extend(_method_section())
    return "\n".join(lines) + "\n"


def _unresolved_section(plan: RepairPlan, lessons: dict[int, Lesson]) -> list[str]:
    lines = ["", "## Unresolved rows", ""]
    if not plan.unresolved:
        return lines + ["All target rows received a conflict-free first-pass suggestion."]
    lines.extend([
        "These need a second-stage permutation of one or more blocking lessons (physics or another subject):",
        "",
    ])
    blocked_by_row = {item.target.source_row: item for item in plan.blocked_options}
    for item in plan.unresolved:
        blocked = blocked_by_row.get(item.source_row)
        detail = ""
        if blocked:
            start = _format_minute(plan.slot_times[blocked.placement.start_slot])
            blockers = ", ".join(str(row) for row in blocked.blocker_rows) or "unknown"
            detail = (
                f" Nearest two-period candidate: {blocked.placement.day} {start}; "
                f"blocking Excel row(s): {blockers}."
            )
        lines.append(
            f"- Row {item.source_row}: {item.class_group}, {item.teacher}, "
            f"{item.frequency}, {item.day} {item.start_time}, {item.room}.{detail}"
        )
    blocker_rows = sorted({row for option in plan.blocked_options for row in option.blocker_rows})
    if blocker_rows:
        lines.extend([
            "",
            "### Blocking source rows",
            "",
            "| Excel row | Subject | Week | Teacher | Class/group | Source position |",
            "| ---: | --- | :---: | --- | --- | --- |",
        ])
        for row in blocker_rows:
            lesson = lessons.get(row)
            if lesson:
                lines.append(
                    f"| {row} | {lesson.subject} | {lesson.frequency} | {lesson.teacher} | "
                    f"{lesson.class_group} | {lesson.day} {lesson.start_time} |"
                )
    return lines


def _method_section() -> list[str]:
    return [
        "",
        "## How to run or adjust it",
        "",
        "```powershell",
        '$env:PYTHONPATH = "src"',
        'python -m schedule_repair.optimize_cli "base edt.xlsx" --output "output/first_optimization_suggestions.md" --json "output/first_optimization_suggestions.json"',
        "```",
        "",
        "The JSON output is intended for a future interface or Excel exporter. The Markdown file is for review by teachers.",
        "",
        "## Important assumption to confirm",
        "",
        "This run expands every one-hour physics-chemistry row into two periods while preserving its H/A/B frequency. That increases scheduled physics time. If the intended rule is instead to merge two existing one-hour rows without increasing total teaching time, the optimization model must pair rows before solving.",
    ]


def _resource_gaps(placements: Iterable[Placement], kind: str, value: str) -> int:
    gaps = 0
    for week in ("A", "B"):
        for day in DAY_ORDER:
            occupied: set[int] = set()
            for item in placements:
                resource = getattr(item, kind)
                if item.day == day and _same(resource, value) and week in active_weeks(item.frequency):
                    occupied.update(range(item.start_slot, item.end_slot))
            if occupied:
                gaps += max(occupied) - min(occupied) + 1 - len(occupied)
    return gaps


def _class_parts(label: str) -> tuple[str, str | None]:
    normalized = " ".join(label.casefold().split())
    if normalized.startswith("<") and ">" in normalized:
        parent, subgroup = normalized[1:].split(">", 1)
        return parent.strip(), subgroup.strip() or None
    return normalized, None


def _same(left: str | None, right: str | None) -> bool:
    return bool(left and right and left.casefold().strip() == right.casefold().strip())


def _state_key(state: tuple[tuple[Candidate, ...], tuple[Lesson, ...], int]) -> tuple[int, int]:
    return len(state[1]), state[2]


def _format_minute(value: int | None) -> str | None:
    if value is None:
        return None
    hours, minutes = divmod(value, 60)
    return f"{hours:02d}:{minutes:02d}"
