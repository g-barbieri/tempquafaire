from __future__ import annotations

import re


def split_teachers(value: str | None) -> tuple[str, ...]:
    """Return individual teachers from a cell containing one or several names."""
    if not value:
        return ()
    names = [part.strip() for part in re.split(r"[+;|/\n]+", value) if part.strip()]
    return tuple(dict.fromkeys(names))


def teacher_key(value: str) -> str:
    return " ".join(value.casefold().split())


def teacher_keys(value: str | None) -> frozenset[str]:
    return frozenset(teacher_key(name) for name in split_teachers(value))


def teachers_overlap(left: str | None, right: str | None) -> bool:
    return bool(teacher_keys(left) & teacher_keys(right))


def split_rooms(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    rooms = [part.strip() for part in re.split(r"[,;+|\n]+", value) if part.strip()]
    return tuple(dict.fromkeys(rooms))


def room_keys(value: str | None) -> frozenset[str]:
    return frozenset(" ".join(room.casefold().split()) for room in split_rooms(value))


def rooms_overlap(left: str | None, right: str | None) -> bool:
    return bool(room_keys(left) & room_keys(right))
