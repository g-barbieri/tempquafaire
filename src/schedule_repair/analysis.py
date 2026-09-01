from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from schedule_repair.domain import Lesson
from schedule_repair.optimizer import DAY_ORDER, active_weeks
from schedule_repair.resources import split_rooms, split_teachers


@dataclass(frozen=True, slots=True)
class DeducedConstraints:
    rooms_by_subject: dict[str, tuple[str, ...]]
    days_off_by_teacher: dict[str, dict[str, tuple[str, ...]]]
    earliest_start: str
    latest_start: str


def deduce_constraints(lessons: Iterable[Lesson]) -> DeducedConstraints:
    rows = tuple(lessons)
    rooms: dict[str, set[str]] = defaultdict(set)
    teacher_days: dict[tuple[str, str], set[str]] = defaultdict(set)
    teachers: set[str] = set()
    for lesson in rows:
        if lesson.subject and lesson.room:
            rooms[lesson.subject].update(split_rooms(lesson.room))
        for teacher in split_teachers(lesson.teacher):
            teachers.add(teacher)
            if lesson.day:
                for week in active_weeks(lesson.frequency):
                    teacher_days[(teacher, week)].add(lesson.day)
    available_days = tuple(day for day in DAY_ORDER if any(row.day == day for row in rows))
    days_off = {
        teacher: {
            week: tuple(day for day in available_days if day not in teacher_days[(teacher, week)])
            for week in ("A", "B")
        }
        for teacher in sorted(teachers)
    }
    starts = sorted(row.start_minute for row in rows if row.start_minute is not None)
    return DeducedConstraints(
        rooms_by_subject={key: tuple(sorted(value)) for key, value in sorted(rooms.items())},
        days_off_by_teacher=days_off,
        earliest_start=_format_minute(starts[0]),
        latest_start=_format_minute(starts[-1]),
    )


def render_deduced_markdown(data: DeducedConstraints, source_name: str) -> str:
    lines = [
        "# Contraintes déduites",
        "",
        f"Source : `{source_name}`.",
        "",
        f"Plage observée : **{data.earliest_start}–{data.latest_start}**.",
        "",
        "## Salles observées par matière",
        "",
        "| Matière | Salles |",
        "| --- | --- |",
    ]
    lines.extend(
        f"| {subject} | {', '.join(rooms)} |" for subject, rooms in data.rooms_by_subject.items()
    )
    lines.extend([
        "",
        "## Jours sans cours par enseignant",
        "",
        "| Enseignant | Semaine A | Semaine B |",
        "| --- | --- | --- |",
    ])
    for teacher, weeks in data.days_off_by_teacher.items():
        lines.append(
            f"| {teacher} | {', '.join(weeks['A']) or 'aucun'} | "
            f"{', '.join(weeks['B']) or 'aucun'} |"
        )
    lines.extend([
        "",
        "> Ces valeurs sont des déductions du fichier, à vérifier avant optimisation.",
    ])
    return "\n".join(lines) + "\n"


def _format_minute(value: int) -> str:
    hours, minutes = divmod(value, 60)
    return f"{hours:02d}:{minutes:02d}"
