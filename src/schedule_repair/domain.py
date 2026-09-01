from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class ImportIssue:
    severity: Literal["warning", "error"]
    code: str
    message: str
    source_row: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Lesson:
    source_row: int
    duration_minutes: int | None
    day: str | None
    start_minute: int | None
    period: str | None
    frequency: str | None
    possible_slots: int | None
    possible_days: int | None
    teacher: str | None
    subject: str | None
    class_group: str | None
    student_count: int | None
    room: str | None
    alternation: str | None
    co_teaching: str | None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def start_time(self) -> str | None:
        if self.start_minute is None:
            return None
        hours, minutes = divmod(self.start_minute, 60)
        return f"{hours:02d}:{minutes:02d}"

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["start_time"] = self.start_time
        return result


@dataclass(frozen=True, slots=True)
class ScheduleImportResult:
    source_file: str
    source_sheet: str
    descriptions: dict[str, str | None]
    lessons: tuple[Lesson, ...]
    issues: tuple[ImportIssue, ...]

    @property
    def has_errors(self) -> bool:
        return any(issue.severity == "error" for issue in self.issues)

    def summary(self) -> dict[str, Any]:
        teachers = {lesson.teacher for lesson in self.lessons if lesson.teacher}
        classes = {lesson.class_group for lesson in self.lessons if lesson.class_group}
        rooms = {lesson.room for lesson in self.lessons if lesson.room}
        subjects = {lesson.subject for lesson in self.lessons if lesson.subject}
        return {
            "source_file": self.source_file,
            "source_sheet": self.source_sheet,
            "lesson_count": len(self.lessons),
            "teacher_count": len(teachers),
            "class_count": len(classes),
            "room_count": len(rooms),
            "subject_count": len(subjects),
            "warning_count": sum(i.severity == "warning" for i in self.issues),
            "error_count": sum(i.severity == "error" for i in self.issues),
        }

