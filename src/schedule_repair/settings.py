from __future__ import annotations

from dataclasses import dataclass, field

from schedule_repair.constraints import ConstraintKind, ConstraintSpec


@dataclass(frozen=True, slots=True)
class OptimizationSettings:
    earliest_start: int | None = None
    latest_start: int | None = None
    lunch_start: int = 12 * 60
    lunch_end: int = 14 * 60
    minimum_free_lunch_periods: int = 1
    preserve_teacher_days_off: bool = True
    derive_teacher_days_off: bool = True
    days_off_by_teacher: dict[str, dict[str, tuple[str, ...]]] = field(default_factory=dict)


def settings_from_constraints(constraints: tuple[ConstraintSpec, ...]) -> OptimizationSettings:
    values: dict[str, object] = {}
    for constraint in constraints:
        if constraint.severity != "hard":
            continue
        parameters = constraint.parameters
        if constraint.kind == ConstraintKind.TIME_BOUNDS:
            values["earliest_start"] = _minute(parameters.get("earliest_start"))
            values["latest_start"] = _minute(parameters.get("latest_start"))
        elif constraint.kind == ConstraintKind.GUARANTEE_LUNCH_BREAK:
            values["lunch_start"] = _minute(parameters.get("window_start"), 12 * 60)
            values["lunch_end"] = _minute(parameters.get("window_end"), 14 * 60)
            values["minimum_free_lunch_periods"] = int(parameters.get("minimum_free_periods", 1))
        elif constraint.kind == ConstraintKind.PRESERVE_TEACHER_DAYS_OFF:
            values["preserve_teacher_days_off"] = True
            values["derive_teacher_days_off"] = bool(
                parameters.get("derive_days_off_from_baseline", True)
            )
            raw = parameters.get("days_off_by_teacher", {})
            values["days_off_by_teacher"] = {
                str(teacher): {
                    week: tuple(str(day) for day in weeks.get(week, []))
                    for week in ("A", "B")
                }
                for teacher, weeks in raw.items()
            }
    return OptimizationSettings(**values)


def _minute(value: object, default: int | None = None) -> int | None:
    if value is None:
        return default
    hours, minutes = str(value).split(":", 1)
    return int(hours) * 60 + int(minutes)
