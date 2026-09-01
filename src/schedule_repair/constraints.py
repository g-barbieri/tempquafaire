from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal


class ConstraintKind(StrEnum):
    NO_RESOURCE_OVERLAP = "no_resource_overlap"
    CONSECUTIVE_SUBJECT_BLOCK = "consecutive_subject_block"
    SUBJECT_ROOM_ELIGIBILITY = "subject_room_eligibility"
    KEEP_ORIGINAL_ROOM = "keep_original_room"
    PRESERVE_TEACHER_DAYS_OFF = "preserve_teacher_days_off"
    GUARANTEE_LUNCH_BREAK = "guarantee_lunch_break"
    TIME_BOUNDS = "time_bounds"
    PRESERVE_ASSIGNMENTS = "preserve_assignments"
    PRESERVE_RESOURCE_HOURS = "preserve_resource_hours"
    EXCEPTION_POLICY = "exception_policy"
    MINIMIZE_GAPS = "minimize_gaps"
    MINIMIZE_CHANGES = "minimize_changes"
    LOCK_LESSON = "lock_lesson"


@dataclass(frozen=True, slots=True)
class ConstraintSpec:
    identifier: str
    kind: ConstraintKind
    severity: Literal["hard", "soft"]
    weight: int = 1
    parameters: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.identifier.strip():
            raise ValueError("Constraint identifier cannot be empty")
        if self.severity not in {"hard", "soft"}:
            raise ValueError("Constraint severity must be 'hard' or 'soft'")
        if self.severity == "soft" and self.weight <= 0:
            raise ValueError("Soft constraint weight must be positive")


def load_constraints(path: str | Path) -> tuple[ConstraintSpec, ...]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Constraint configuration must be a JSON list")
    constraints = tuple(_from_dict(item) for item in payload)
    identifiers = [item.identifier for item in constraints]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Constraint identifiers must be unique")
    return constraints


def _from_dict(payload: Any) -> ConstraintSpec:
    if not isinstance(payload, dict):
        raise ValueError("Each constraint must be a JSON object")
    return ConstraintSpec(
        identifier=str(payload["id"]),
        kind=ConstraintKind(payload["kind"]),
        severity=payload["severity"],
        weight=int(payload.get("weight", 1)),
        parameters=dict(payload.get("parameters", {})),
    )
