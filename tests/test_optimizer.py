from __future__ import annotations

import unittest

from schedule_repair.domain import Lesson
from schedule_repair.optimizer import (
    FirstPassOptimizer,
    Placement,
    active_weeks,
    class_groups_conflict,
    conflicts,
)


def _lesson(row: int, start: int, **changes: object) -> Lesson:
    values = {
        "source_row": row,
        "duration_minutes": 60,
        "day": "lundi",
        "start_minute": start,
        "period": None,
        "frequency": "H",
        "possible_slots": None,
        "possible_days": None,
        "teacher": "Teacher A",
        "subject": "PH-CH - PHYSIQUE-CHIMIE",
        "class_group": "<3A> 3AP1",
        "student_count": 15,
        "room": "Lab 1",
        "alternation": None,
        "co_teaching": None,
        "raw": {},
    }
    values.update(changes)
    return Lesson(**values)


class WeekAndConflictTests(unittest.TestCase):
    def test_h_uses_both_weeks_but_a_and_b_do_not_overlap(self) -> None:
        self.assertEqual(active_weeks("H"), frozenset({"A", "B"}))
        self.assertFalse(conflicts(_placement("A"), _placement("B")))
        self.assertTrue(conflicts(_placement("H"), _placement("A")))
        self.assertTrue(conflicts(_placement("H"), _placement("B")))

    def test_parent_class_conflicts_with_subgroups_but_subgroups_are_distinct(self) -> None:
        self.assertTrue(class_groups_conflict("3A", "<3A> 3AP1"))
        self.assertFalse(class_groups_conflict("<3A> 3AP1", "<3A> 3AP2"))
        self.assertTrue(class_groups_conflict("<3A> 3AP1", "<3A> 3AP1"))


class FirstPassOptimizerTests(unittest.TestCase):
    def test_extends_at_current_start_when_next_period_is_free(self) -> None:
        lessons = (
            _lesson(3, 480),
            _lesson(4, 535, teacher="Other", subject="MATH", class_group="4B", room="R2"),
            _lesson(5, 610, teacher="Other", subject="MATH", class_group="4C", room="R3"),
        )
        plan = FirstPassOptimizer(lessons).optimize()

        self.assertEqual(len(plan.suggestions), 1)
        suggestion = plan.suggestions[0]
        self.assertFalse(suggestion.changed)
        self.assertEqual(suggestion.placement.start_slot, 0)
        self.assertEqual(suggestion.placement.span_slots, 2)


def _placement(frequency: str) -> Placement:
    return Placement(1, "lundi", 0, 1, frequency, "Teacher A", "3A", "Lab 1")


if __name__ == "__main__":
    unittest.main()

