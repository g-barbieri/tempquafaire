from __future__ import annotations

import unittest

from schedule_repair.domain import Lesson
from schedule_repair.optimizer import (
    ConstantHoursOptimizer,
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


def _lunch_period_rows() -> tuple[Lesson, Lesson]:
    return (
        _lesson(900, 720, teacher="Lunch fixture 1", subject="MATH", class_group="Lunch class 1", room="Lunch room 1"),
        _lesson(901, 775, teacher="Lunch fixture 2", subject="MATH", class_group="Lunch class 2", room="Lunch room 2"),
    )


class WeekAndConflictTests(unittest.TestCase):
    def test_h_uses_both_weeks_but_a_and_b_do_not_overlap(self) -> None:
        self.assertEqual(active_weeks("H"), frozenset({"A", "B"}))
        self.assertFalse(conflicts(_placement("A"), _placement("B")))
        self.assertTrue(conflicts(_placement("H"), _placement("A")))

    def test_parent_class_conflicts_with_subgroups_but_subgroups_are_distinct(self) -> None:
        self.assertTrue(class_groups_conflict("3A", "<3A> 3AP1"))
        self.assertFalse(class_groups_conflict("<3A> 3AP1", "<3A> 3AP2"))

    def test_shared_teacher_or_room_in_multi_resource_cells_conflicts(self) -> None:
        left = Placement(1, "lundi", 0, 1, "H", "Alice + Bob", "3A", "Lab 1, Lab 2")
        same_teacher = Placement(2, "lundi", 0, 1, "H", "Bob", "4B", "R3")
        same_room = Placement(3, "lundi", 0, 1, "H", "Claire", "4C", "Lab 2")

        self.assertTrue(conflicts(left, same_teacher))
        self.assertTrue(conflicts(left, same_room))


class ConstantHoursOptimizerTests(unittest.TestCase):
    def test_pairs_h_and_a_without_changing_week_minutes(self) -> None:
        lessons = (
            _lesson(3, 480, frequency="H"),
            _lesson(4, 610, frequency="A"),
            _lesson(5, 535, teacher="Other", subject="MATH", class_group="4B", room="R2"),
        ) + _lunch_period_rows()
        optimizer = ConstantHoursOptimizer(lessons)
        plan = optimizer.optimize()

        self.assertEqual(len(plan.suggestions), 1)
        self.assertEqual(plan.suggestions[0].block_weeks, ("A",))
        self.assertEqual(plan.original_minutes, {"A": 120, "B": 60})
        self.assertEqual(plan.final_minutes, plan.original_minutes)
        self.assertEqual(optimizer.validate(plan), ())

    def test_different_original_rooms_prevent_a_block(self) -> None:
        lessons = (
            _lesson(3, 480, frequency="H", room="Lab 1"),
            _lesson(4, 610, frequency="A", room="Lab 2"),
            _lesson(5, 535, teacher="Other", subject="MATH", class_group="4B", room="R2"),
        ) + _lunch_period_rows()
        plan = ConstantHoursOptimizer(lessons).optimize()

        self.assertEqual(plan.suggestions, ())
        self.assertIn("different original rooms", plan.groups_without_block[0].reason)

    def test_never_moves_a_teacher_to_a_baseline_day_off(self) -> None:
        lessons = (
            _lesson(3, 480),
            _lesson(4, 610),
            _lesson(5, 535, teacher="Other", subject="MATH", class_group="4B", room="R2", day="mardi"),
        ) + _lunch_period_rows()
        plan = ConstantHoursOptimizer(lessons).optimize()

        self.assertEqual(len(plan.suggestions), 1)
        self.assertEqual(plan.suggestions[0].placements[0].day, "lundi")
        self.assertFalse(plan.suggestions[0].teacher_day_off_used)

    def test_rejects_a_block_that_removes_the_only_lunch_period(self) -> None:
        lessons = (
            _lesson(3, 480),
            _lesson(4, 610),
            _lesson(5, 720, teacher="Teacher A", subject="MATH", class_group="Other class", room="R2"),
            _lesson(6, 775, teacher="Other", subject="MATH", class_group="<3A> 3AP1", room="R3"),
        )
        optimizer = ConstantHoursOptimizer(lessons)
        plan = optimizer.optimize()

        self.assertEqual(optimizer.validate(plan), ())
        proposed_slots = {
            placement.start_slot
            for suggestion in plan.suggestions
            for placement in suggestion.placements
        }
        self.assertFalse(set(optimizer.lunch_slots).issubset(proposed_slots))


def _placement(frequency: str) -> Placement:
    return Placement(1, "lundi", 0, 1, frequency, "Teacher A", "3A", "Lab 1")


if __name__ == "__main__":
    unittest.main()
