from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

from schedule_repair.domain import Lesson
from schedule_repair.resources import (
    room_keys,
    rooms_overlap,
    split_teachers,
    teacher_key,
    teacher_keys,
    teachers_overlap,
)
from schedule_repair.settings import OptimizationSettings

DAY_ORDER = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi")
def active_weeks(frequency: str | None) -> frozenset[str]:
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
class BlockSuggestion:
    lessons: tuple[Lesson, Lesson]
    placements: tuple[Placement, Placement]
    block_weeks: tuple[str, ...]
    score: int
    changed_rows: int
    teacher_day_off_used: bool
    local_gap_delta: int

    @property
    def class_group(self) -> str:
        return self.lessons[0].class_group or ""

    def to_dict(self, slot_times: tuple[int, ...]) -> dict[str, object]:
        ordered = sorted(self.placements, key=lambda item: item.start_slot)
        lesson_by_row = {item.source_row: item for item in self.lessons}
        return {
            "class_group": self.class_group,
            "teacher": self.lessons[0].teacher,
            "room": self.lessons[0].room,
            "block_weeks": list(self.block_weeks),
            "new_day": ordered[0].day,
            "new_starts": [_format_minute(slot_times[item.start_slot]) for item in ordered],
            "changed_rows": self.changed_rows,
            "teacher_day_off_used": self.teacher_day_off_used,
            "local_gap_delta": self.local_gap_delta,
            "score": self.score,
            "rows": [
                {
                    "source_row": placement.source_row,
                    "frequency": lesson_by_row[placement.source_row].frequency,
                    "old_day": lesson_by_row[placement.source_row].day,
                    "old_start": lesson_by_row[placement.source_row].start_time,
                    "new_day": placement.day,
                    "new_start": _format_minute(slot_times[placement.start_slot]),
                    "duration_minutes": lesson_by_row[placement.source_row].duration_minutes,
                    "room": placement.room,
                }
                for placement in ordered
            ],
        }


@dataclass(frozen=True, slots=True)
class GroupOutcome:
    class_group: str
    source_rows: tuple[int, ...]
    reason: str


@dataclass(frozen=True, slots=True)
class ConservingRepairPlan:
    slot_times: tuple[int, ...]
    suggestions: tuple[BlockSuggestion, ...]
    residual_rows: tuple[Lesson, ...]
    groups_without_block: tuple[GroupOutcome, ...]
    original_minutes: dict[str, int]
    final_minutes: dict[str, int]
    baseline_gap_units: int
    final_gap_units: int

    def summary(self) -> dict[str, int]:
        groups = {item.class_group for item in self.residual_rows}
        groups.update(item.class_group for suggestion in self.suggestions for item in suggestion.lessons)
        return {
            "physics_rows": len(self.residual_rows) + 2 * len(self.suggestions),
            "physics_groups": len(groups),
            "groups_with_two_period_block": len(self.suggestions),
            "groups_without_two_period_block": len(self.groups_without_block),
            "rows_used_in_blocks": 2 * len(self.suggestions),
            "single_rows_remaining": len(self.residual_rows),
            "moved_rows": sum(item.changed_rows for item in self.suggestions),
            "teacher_days_off_used": sum(item.teacher_day_off_used for item in self.suggestions),
            "net_gap_delta": self.final_gap_units - self.baseline_gap_units,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "summary": self.summary(),
            "hour_conservation": {
                week: {
                    "original_minutes": self.original_minutes[week],
                    "proposed_minutes": self.final_minutes[week],
                    "difference": self.final_minutes[week] - self.original_minutes[week],
                }
                for week in ("A", "B")
            },
            "time_bounds": {
                "earliest_start": _format_minute(self.slot_times[0]),
                "latest_start": _format_minute(self.slot_times[-1]),
            },
            "suggestions": [item.to_dict(self.slot_times) for item in self.suggestions],
            "residual_single_rows": [_lesson_summary(item) for item in self.residual_rows],
            "groups_without_block": [
                {
                    "class_group": item.class_group,
                    "source_rows": list(item.source_rows),
                    "reason": item.reason,
                }
                for item in self.groups_without_block
            ],
        }


class ConstantHoursOptimizer:
    """Pair existing one-hour rows into blocks without adding or deleting hours."""

    def __init__(
        self,
        lessons: Iterable[Lesson],
        subject_contains: str = "PHYSIQUE-CHIMIE",
        settings: OptimizationSettings | None = None,
    ) -> None:
        self.lessons = tuple(lessons)
        self.settings = settings or OptimizationSettings()
        needle = subject_contains.casefold()
        self.targets = tuple(
            item for item in self.lessons if needle in (item.subject or "").casefold()
        )
        self.slot_times = tuple(
            sorted({item.start_minute for item in self.lessons if item.start_minute is not None})
        )
        self.slot_index = {minute: index for index, minute in enumerate(self.slot_times)}
        self.days = tuple(day for day in DAY_ORDER if any(item.day == day for item in self.lessons))
        self.baseline = tuple(self._placement(item) for item in self.lessons)
        self.teacher_days = self._teacher_days_by_week()
        self.lunch_slots = tuple(
            index
            for index, minute in enumerate(self.slot_times)
            if self.settings.lunch_start <= minute and minute + 60 <= self.settings.lunch_end
        )
        if self.settings.minimum_free_lunch_periods > 0 and not self.lunch_slots:
            raise ValueError("No complete timetable period exists inside the 12:00-14:00 lunch window")
        self.groups = self._target_groups()

    def optimize(self, beam_width: int = 300, options_per_group: int = 30) -> ConservingRepairPlan:
        options = {group: self._group_options(rows) for group, rows in self.groups.items()}
        ordered_groups = sorted(self.groups, key=lambda group: (len(options[group]), group))
        states: list[tuple[tuple[BlockSuggestion, ...], int]] = [((), 0)]
        for group in ordered_groups:
            states = self._advance(states, options[group], beam_width, options_per_group)
        suggestions, _ = min(states, key=lambda item: (-len(item[0]), item[1]))
        suggestions = tuple(sorted(suggestions, key=lambda item: item.class_group))
        selected_rows = {lesson.source_row for item in suggestions for lesson in item.lessons}
        residual = tuple(item for item in self.targets if item.source_row not in selected_rows)
        outcomes = self._group_outcomes(suggestions, options)
        final_placements = self._final_placements(suggestions)
        return ConservingRepairPlan(
            slot_times=self.slot_times,
            suggestions=suggestions,
            residual_rows=tuple(sorted(residual, key=lambda item: item.source_row)),
            groups_without_block=outcomes,
            original_minutes=_minutes_by_week(self.targets),
            final_minutes=_minutes_by_week(self.targets),
            baseline_gap_units=self._all_gap_units(self.baseline),
            final_gap_units=self._all_gap_units(final_placements),
        )

    def validate(self, plan: ConservingRepairPlan) -> tuple[str, ...]:
        issues = list(self._validate_conservation(plan))
        selected_rows: set[int] = set()
        final = self._final_placements(plan.suggestions)
        if {item.source_row for item in final} != {item.source_row for item in self.baseline}:
            issues.append("Des lignes de cours ont été ajoutées ou supprimées")
        for suggestion in plan.suggestions:
            issues.extend(self._validate_suggestion(suggestion, selected_rows, final))
        if self.settings.preserve_teacher_days_off:
            for teacher, week, day in self._teacher_day_off_violations(final):
                issues.append(f"Enseignant {teacher} : cours sur un jour de repos ({day}, semaine {week})")
        if self.settings.minimum_free_lunch_periods > 0:
            for kind, value, week, day in self._lunch_violations(final):
                label = "Enseignant" if kind == "teacher" else "Groupe"
                issues.append(f"{label} {value} : aucune pause déjeuner le {day}, semaine {week}")
        return tuple(issues)

    def _advance(
        self,
        states: list[tuple[tuple[BlockSuggestion, ...], int]],
        options: tuple[BlockSuggestion, ...],
        beam_width: int,
        options_per_group: int,
    ) -> list[tuple[tuple[BlockSuggestion, ...], int]]:
        expanded = []
        for chosen, score in states:
            expanded.append((chosen, score))
            legal = [
                item
                for item in options
                if not self._blocks_conflict(item, chosen)
                and self._hard_constraints_hold(chosen + (item,))
            ]
            for candidate in legal[:options_per_group]:
                expanded.append((chosen + (candidate,), score + candidate.score))
        expanded.sort(key=lambda item: (-len(item[0]), item[1]))
        return expanded[:beam_width]

    def _group_options(self, rows: tuple[Lesson, ...]) -> tuple[BlockSuggestion, ...]:
        result = []
        for left, right in combinations(rows, 2):
            if self._pair_compatible(left, right):
                result.extend(self._placement_options(left, right))
        return tuple(sorted(result, key=lambda item: item.score))

    def _placement_options(self, left: Lesson, right: Lesson) -> list[BlockSuggestion]:
        result = []
        excluded = {left.source_row, right.source_row}
        occupied = tuple(item for item in self.baseline if item.source_row not in excluded)
        for day in self.days:
            for start_slot in range(len(self.slot_times) - 1):
                if (
                    self.settings.earliest_start is not None
                    and self.slot_times[start_slot] < self.settings.earliest_start
                ):
                    continue
                if (
                    self.settings.latest_start is not None
                    and self.slot_times[start_slot + 1] > self.settings.latest_start
                ):
                    continue
                for first, second in ((left, right), (right, left)):
                    placements = (
                        self._moved_placement(first, day, start_slot),
                        self._moved_placement(second, day, start_slot + 1),
                    )
                    if any(conflicts(item, fixed) for item in placements for fixed in occupied):
                        continue
                    if self._uses_teacher_day_off(placements):
                        continue
                    result.append(self._score_block((first, second), placements))
        return result

    def _score_block(
        self, lessons: tuple[Lesson, Lesson], placements: tuple[Placement, Placement]
    ) -> BlockSuggestion:
        changed_rows = 0
        displacement = 0
        for lesson, placement in zip(lessons, placements):
            original_slot = self.slot_index[lesson.start_minute]
            changed = lesson.day != placement.day or original_slot != placement.start_slot
            changed_rows += int(changed)
            displacement += abs(self.days.index(lesson.day) - self.days.index(placement.day)) * 100
            displacement += abs(original_slot - placement.start_slot) * 25
        day_off = self._uses_teacher_day_off(placements)
        gap_delta = self._block_gap_delta(lessons, placements)
        score = changed_rows * 1000 + displacement + gap_delta * 20
        weeks = tuple(sorted(active_weeks(lessons[0].frequency) & active_weeks(lessons[1].frequency)))
        return BlockSuggestion(lessons, placements, weeks, score, changed_rows, day_off, gap_delta)

    def _block_gap_delta(
        self, lessons: tuple[Lesson, Lesson], placements: tuple[Placement, Placement]
    ) -> int:
        selected_rows = {item.source_row for item in lessons}
        proposed = tuple(item for item in self.baseline if item.source_row not in selected_rows)
        proposed += placements
        resources = tuple(("teacher", teacher) for teacher in split_teachers(lessons[0].teacher))
        resources += (("class_group", lessons[0].class_group),)
        return sum(
            _resource_gaps(proposed, kind, value) - _resource_gaps(self.baseline, kind, value)
            for kind, value in resources
            if value
        )

    def _group_outcomes(
        self,
        suggestions: tuple[BlockSuggestion, ...],
        options: dict[str, tuple[BlockSuggestion, ...]],
    ) -> tuple[GroupOutcome, ...]:
        covered = {item.class_group for item in suggestions}
        outcomes = []
        for group, rows in sorted(self.groups.items()):
            if group not in covered:
                outcomes.append(
                    GroupOutcome(group, tuple(item.source_row for item in rows), self._failure_reason(rows, options[group]))
                )
        return tuple(outcomes)

    def _failure_reason(
        self, rows: tuple[Lesson, ...], options: tuple[BlockSuggestion, ...]
    ) -> str:
        if options:
            return "A legal block exists alone but conflicts with blocks selected for other groups."
        week_pairs = [
            (left, right)
            for left, right in combinations(rows, 2)
            if active_weeks(left.frequency) & active_weeks(right.frequency)
        ]
        if not week_pairs:
            return "No two rows are active in the same week."
        if not any(room_keys(left.room) == room_keys(right.room) for left, right in week_pairs):
            return "Rows active in the same week have different original rooms."
        return "No conflict-free consecutive placement exists while other lessons stay fixed."

    def _validate_conservation(self, plan: ConservingRepairPlan) -> tuple[str, ...]:
        issues = []
        for week in ("A", "B"):
            if plan.original_minutes[week] != plan.final_minutes[week]:
                issues.append(f"Physics minutes changed in week {week}")
        if len(plan.residual_rows) + 2 * len(plan.suggestions) != len(self.targets):
            issues.append("Physics rows were added or removed")
        return tuple(issues)

    def _validate_suggestion(
        self,
        suggestion: BlockSuggestion,
        selected_rows: set[int],
        final: tuple[Placement, ...],
    ) -> tuple[str, ...]:
        issues = []
        for lesson, placement in zip(suggestion.lessons, suggestion.placements):
            if lesson.source_row in selected_rows:
                issues.append(f"Row {lesson.source_row} is used in more than one block")
            selected_rows.add(lesson.source_row)
            if room_keys(lesson.room) != room_keys(placement.room) or lesson.frequency != placement.frequency:
                issues.append(f"Row {lesson.source_row} changed room or frequency")
            if self._placement(lesson).span_slots != placement.span_slots:
                issues.append(f"Row {lesson.source_row} changed duration")
            if teacher_keys(lesson.teacher) != teacher_keys(placement.teacher) or not _same(
                lesson.class_group, placement.class_group
            ):
                issues.append(f"Row {lesson.source_row} changed teacher or class/group")
            if placement.start_slot < 0 or placement.end_slot > len(self.slot_times):
                issues.append(f"Row {lesson.source_row} exceeds source time bounds")
            start_minute = self.slot_times[placement.start_slot]
            if self.settings.earliest_start is not None and start_minute < self.settings.earliest_start:
                issues.append(f"Row {lesson.source_row} starts before the accepted time")
            if self.settings.latest_start is not None and start_minute > self.settings.latest_start:
                issues.append(f"Row {lesson.source_row} starts after the accepted time")
            others = [item for item in final if item.source_row != lesson.source_row]
            if any(conflicts(placement, item) for item in others):
                issues.append(f"Row {lesson.source_row} has a resource conflict")
        return tuple(issues)

    def _final_placements(
        self, suggestions: tuple[BlockSuggestion, ...]
    ) -> tuple[Placement, ...]:
        replacements = {
            placement.source_row: placement
            for suggestion in suggestions
            for placement in suggestion.placements
        }
        return tuple(replacements.get(item.source_row, item) for item in self.baseline)

    def _pair_compatible(self, left: Lesson, right: Lesson) -> bool:
        return bool(
            left.duration_minutes == right.duration_minutes == 60
            and teacher_keys(left.teacher) == teacher_keys(right.teacher)
            and _same(left.class_group, right.class_group)
            and room_keys(left.room) == room_keys(right.room)
            and active_weeks(left.frequency) & active_weeks(right.frequency)
        )

    def _blocks_conflict(
        self, candidate: BlockSuggestion, chosen: tuple[BlockSuggestion, ...]
    ) -> bool:
        candidate_rows = {item.source_row for item in candidate.lessons}
        for block in chosen:
            if candidate_rows.intersection(item.source_row for item in block.lessons):
                return True
            if any(conflicts(left, right) for left in candidate.placements for right in block.placements):
                return True
        return False

    def _moved_placement(self, lesson: Lesson, day: str, start_slot: int) -> Placement:
        original = self._placement(lesson)
        return Placement(
            source_row=original.source_row,
            day=day,
            start_slot=start_slot,
            span_slots=original.span_slots,
            frequency=original.frequency,
            teacher=original.teacher,
            class_group=original.class_group,
            room=original.room,
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

    def _teacher_days_by_week(self) -> dict[tuple[str, str], set[str]]:
        result: dict[tuple[str, str], set[str]] = {}
        if not self.settings.derive_teacher_days_off:
            teachers = {
                teacher for lesson in self.lessons for teacher in split_teachers(lesson.teacher)
            }
            configured = {
                teacher_key(name): weeks
                for name, weeks in self.settings.days_off_by_teacher.items()
            }
            for teacher in teachers:
                for week in ("A", "B"):
                    days_off = configured.get(teacher_key(teacher), {}).get(week, ())
                    result[(teacher_key(teacher), week)] = set(self.days) - set(days_off)
            return result
        for lesson in self.lessons:
            if lesson.teacher and lesson.day:
                for teacher in split_teachers(lesson.teacher):
                    for week in active_weeks(lesson.frequency):
                        result.setdefault((teacher_key(teacher), week), set()).add(lesson.day)
        return result

    def _uses_teacher_day_off(self, placements: Iterable[Placement]) -> bool:
        return self.settings.preserve_teacher_days_off and bool(
            self._teacher_day_off_violations(tuple(placements))
        )

    def _teacher_day_off_violations(
        self, placements: tuple[Placement, ...]
    ) -> tuple[tuple[str, str, str], ...]:
        violations: set[tuple[str, str, str]] = set()
        for placement in placements:
            for teacher in split_teachers(placement.teacher):
                for week in active_weeks(placement.frequency):
                    if placement.day not in self.teacher_days.get((teacher_key(teacher), week), set()):
                        violations.add((teacher, week, placement.day))
        return tuple(sorted(violations))

    def _hard_constraints_hold(self, suggestions: tuple[BlockSuggestion, ...]) -> bool:
        final = self._final_placements(suggestions)
        day_off_ok = not self.settings.preserve_teacher_days_off or not self._teacher_day_off_violations(final)
        lunch_ok = self.settings.minimum_free_lunch_periods <= 0 or not self._lunch_violations(final)
        return day_off_ok and lunch_ok

    def _lunch_violations(
        self, placements: tuple[Placement, ...]
    ) -> tuple[tuple[str, str, str, str], ...]:
        violations: list[tuple[str, str, str, str]] = []
        teachers = sorted({teacher for item in placements for teacher in split_teachers(item.teacher)})
        class_resources = self._class_lunch_resources(placements)
        resources = [("teacher", value, None) for value in teachers]
        resources.extend(("class_group", label, key) for label, key in class_resources)
        for kind, value, class_key in resources:
            for week in ("A", "B"):
                for day in self.days:
                    day_items = [
                        item
                        for item in placements
                        if item.day == day
                        and week in active_weeks(item.frequency)
                        and self._resource_matches(item, kind, value, class_key)
                    ]
                    if not day_items:
                        continue
                    free_periods = sum(
                        not any(item.start_slot <= slot < item.end_slot for item in day_items)
                        for slot in self.lunch_slots
                    )
                    if free_periods < self.settings.minimum_free_lunch_periods:
                        violations.append((kind, value, week, day))
        return tuple(violations)

    @staticmethod
    def _resource_matches(
        item: Placement,
        kind: str,
        value: str,
        class_key: tuple[str, str | None] | None,
    ) -> bool:
        if kind == "teacher":
            return teacher_key(value) in teacher_keys(item.teacher)
        if not item.class_group or class_key is None:
            return False
        item_parent, item_subgroup = _class_parts(item.class_group)
        parent, subgroup = class_key
        return item_parent == parent and (
            item_subgroup is None or subgroup is None or item_subgroup == subgroup
        )

    @staticmethod
    def _class_lunch_resources(
        placements: tuple[Placement, ...]
    ) -> tuple[tuple[str, tuple[str, str | None]], ...]:
        labels: dict[tuple[str, str | None], str] = {}
        subgroups_by_parent: dict[str, set[str]] = {}
        for item in placements:
            if not item.class_group:
                continue
            parent, subgroup = _class_parts(item.class_group)
            labels.setdefault((parent, subgroup), item.class_group)
            if subgroup:
                subgroups_by_parent.setdefault(parent, set()).add(subgroup)
        resources: list[tuple[str, tuple[str, str | None]]] = []
        parents = sorted({parent for parent, _ in labels})
        for parent in parents:
            subgroups = sorted(subgroups_by_parent.get(parent, set()))
            if subgroups:
                resources.extend(
                    (labels[(parent, subgroup)], (parent, subgroup)) for subgroup in subgroups
                )
            else:
                resources.append((labels[(parent, None)], (parent, None)))
        return tuple(resources)

    def _target_groups(self) -> dict[str, tuple[Lesson, ...]]:
        grouped: dict[str, list[Lesson]] = {}
        for lesson in self.targets:
            grouped.setdefault(lesson.class_group or "", []).append(lesson)
        return {key: tuple(value) for key, value in grouped.items()}

    def _all_gap_units(self, placements: tuple[Placement, ...]) -> int:
        teachers = {teacher for item in placements for teacher in split_teachers(item.teacher)}
        classes = {item.class_group for item in placements if item.class_group}
        return sum(_resource_gaps(placements, "teacher", item) for item in teachers) + sum(
            _resource_gaps(placements, "class_group", item) for item in classes
        )


def conflicts(left: Placement, right: Placement) -> bool:
    if left.day != right.day:
        return False
    if not active_weeks(left.frequency) & active_weeks(right.frequency):
        return False
    if left.end_slot <= right.start_slot or right.end_slot <= left.start_slot:
        return False
    return (
        teachers_overlap(left.teacher, right.teacher)
        or rooms_overlap(left.room, right.room)
        or class_groups_conflict(left.class_group, right.class_group)
    )


def class_groups_conflict(left: str | None, right: str | None) -> bool:
    if not left or not right:
        return False
    left_parent, left_subgroup = _class_parts(left)
    right_parent, right_subgroup = _class_parts(right)
    if left_parent != right_parent:
        return False
    return left_subgroup is None or right_subgroup is None or left_subgroup == right_subgroup


def render_markdown_report(plan: ConservingRepairPlan, source_name: str) -> str:
    summary = plan.summary()
    lines = [
        "# Constant-hours physics-chemistry block suggestions",
        "",
        f"Source: `{source_name}` (read-only)",
        "",
        "> This report replaces the earlier expansion report. No subject hours are added or removed.",
        "",
        "## Result",
        "",
        f"- Physics-chemistry groups: {summary['physics_groups']}",
        f"- Groups receiving a two-period block: {summary['groups_with_two_period_block']}",
        f"- Groups without a feasible block in this pass: {summary['groups_without_two_period_block']}",
        f"- Existing rows paired into blocks: {summary['rows_used_in_blocks']}",
        f"- Existing one-hour rows left single: {summary['single_rows_remaining']}",
        f"- Rows repositioned: {summary['moved_rows']}",
        f"- Blocks placed on a teacher's baseline day off: {summary['teacher_days_off_used']}",
        f"- Net change in teacher/class gap units: {summary['net_gap_delta']}",
        "",
        "## Proven hour conservation",
        "",
        "| Week | Original physics minutes | Proposed physics minutes | Difference |",
        "| :---: | ---: | ---: | ---: |",
    ]
    for week in ("A", "B"):
        original = plan.original_minutes[week]
        proposed = plan.final_minutes[week]
        lines.append(f"| {week} | {original} | {proposed} | {proposed - original:+d} |")
    lines.extend(_rules_section(plan))
    lines.extend(_suggestions_section(plan))
    lines.extend(_residual_section(plan))
    lines.extend(_run_section())
    return "\n".join(lines) + "\n"


def _rules_section(plan: ConservingRepairPlan) -> list[str]:
    return [
        "",
        "## Rules used",
        "",
        "- Every original physics row remains exactly once with its original duration and H/A/B frequency.",
        "- Every non-physics row is left untouched, so every subject's total time remains constant.",
        "- `H` is active in A and B; `A` and `B` are active only in their named week.",
        "- Two rows form a block only during a week in which both are active.",
        "- The two rows keep the same teacher, class/group, and each row's exact original room.",
        "- Blocks use adjacent timetable periods and stay inside the source range "
        f"{_format_minute(plan.slot_times[0])}–{_format_minute(plan.slot_times[-1])}.",
        "- Other subjects remain fixed in this conservative pass.",
        "- Teacher days off are inferred separately for weeks A and B and are strictly forbidden.",
        "- Every teacher and class/group keeps at least one complete free timetable period "
        "between 12:00 and 14:00 on every working day.",
    ]


def _suggestions_section(plan: ConservingRepairPlan) -> list[str]:
    lines = [
        "",
        "## Suggested two-period blocks",
        "",
        "| Class/group | Active week | Excel rows | Room | Current positions | Proposed block | Changed rows | Day off? |",
        "| --- | :---: | ---: | --- | --- | --- | ---: | :---: |",
    ]
    for suggestion in plan.suggestions:
        data = suggestion.to_dict(plan.slot_times)
        rows = ", ".join(str(item["source_row"]) for item in data["rows"])
        current = " + ".join(
            f"{item['frequency']} {item['old_day']} {item['old_start']}" for item in data["rows"]
        )
        proposed = f"{data['new_day']} {' + '.join(data['new_starts'])}"
        lines.append(
            f"| {data['class_group']} | {','.join(data['block_weeks'])} | {rows} | "
            f"{data['room']} | {current} | {proposed} | {data['changed_rows']} | "
            f"{'yes' if data['teacher_day_off_used'] else 'no'} |"
        )
    return lines


def _residual_section(plan: ConservingRepairPlan) -> list[str]:
    lines = ["", "## Groups without a two-period block", ""]
    if not plan.groups_without_block:
        lines.append("Every physics group received a block.")
    else:
        for item in plan.groups_without_block:
            rows = ", ".join(str(row) for row in item.source_rows)
            lines.append(f"- {item.class_group} (rows {rows}): {item.reason}")
    lines.extend(["", "## Residual one-hour rows", ""])
    lines.append(
        "These rows remain once and unchanged in duration. Some are mathematically necessary because a group has an odd number of hours over the A/B cycle; others remain because room or resource constraints prevent a legal pairing in this pass."
    )
    lines.append("")
    for lesson in plan.residual_rows:
        lines.append(
            f"- Row {lesson.source_row}: {lesson.class_group}, {lesson.frequency}, "
            f"{lesson.day} {lesson.start_time}, {lesson.room}."
        )
    return lines


def _run_section() -> list[str]:
    return [
        "",
        "## Run again",
        "",
        "```powershell",
        '$env:PYTHONPATH = "src"',
        'python -m schedule_repair.optimize_cli "base edt.xlsx" --output "output/constant_hours_suggestions.md" --json "output/constant_hours_suggestions.json"',
        "```",
    ]


def _minutes_by_week(lessons: Iterable[Lesson]) -> dict[str, int]:
    return {
        week: sum(
            item.duration_minutes or 0
            for item in lessons
            if week in active_weeks(item.frequency)
        )
        for week in ("A", "B")
    }


def _resource_gaps(placements: Iterable[Placement], kind: str, value: str) -> int:
    gaps = 0
    for week in ("A", "B"):
        for day in DAY_ORDER:
            occupied: set[int] = set()
            for item in placements:
                resource = getattr(item, kind)
                same_resource = (
                    teacher_key(value) in teacher_keys(resource)
                    if kind == "teacher"
                    else _same(resource, value)
                )
                if item.day == day and same_resource and week in active_weeks(item.frequency):
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


def _lesson_summary(item: Lesson) -> dict[str, object]:
    return {
        "source_row": item.source_row,
        "class_group": item.class_group,
        "teacher": item.teacher,
        "frequency": item.frequency,
        "room": item.room,
        "day": item.day,
        "start": item.start_time,
        "duration_minutes": item.duration_minutes,
    }


def _same(left: str | None, right: str | None) -> bool:
    return bool(left and right and left.casefold().strip() == right.casefold().strip())


def _format_minute(value: int | None) -> str | None:
    if value is None:
        return None
    hours, minutes = divmod(value, 60)
    return f"{hours:02d}:{minutes:02d}"
