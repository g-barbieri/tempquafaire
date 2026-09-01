from __future__ import annotations

from pathlib import Path
import unittest

from schedule_repair.constraints import ConstraintKind, ConstraintSpec, load_constraints
from schedule_repair.settings import settings_from_constraints


class ConstraintTests(unittest.TestCase):
    def test_example_constraints_are_valid_and_cover_initial_need(self) -> None:
        path = Path(__file__).parents[1] / "config" / "constraints.example.json"
        constraints = load_constraints(path)
        kinds = {constraint.kind for constraint in constraints}

        self.assertIn(ConstraintKind.CONSECUTIVE_SUBJECT_BLOCK, kinds)
        self.assertIn(ConstraintKind.SUBJECT_ROOM_ELIGIBILITY, kinds)
        self.assertIn(ConstraintKind.KEEP_ORIGINAL_ROOM, kinds)
        self.assertIn(ConstraintKind.PRESERVE_TEACHER_DAYS_OFF, kinds)
        self.assertIn(ConstraintKind.GUARANTEE_LUNCH_BREAK, kinds)
        self.assertIn(ConstraintKind.TIME_BOUNDS, kinds)
        self.assertIn(ConstraintKind.PRESERVE_ASSIGNMENTS, kinds)
        self.assertIn(ConstraintKind.PRESERVE_RESOURCE_HOURS, kinds)
        self.assertIn(ConstraintKind.EXCEPTION_POLICY, kinds)
        self.assertIn(ConstraintKind.MINIMIZE_GAPS, kinds)
        self.assertIn(ConstraintKind.MINIMIZE_CHANGES, kinds)

        by_kind = {constraint.kind: constraint for constraint in constraints}
        self.assertEqual(by_kind[ConstraintKind.PRESERVE_TEACHER_DAYS_OFF].severity, "hard")
        self.assertEqual(by_kind[ConstraintKind.GUARANTEE_LUNCH_BREAK].severity, "hard")

        settings = settings_from_constraints(constraints)
        self.assertEqual(settings.earliest_start, 480)
        self.assertEqual(settings.latest_start, 960)
        self.assertEqual(settings.lunch_start, 720)
        self.assertEqual(settings.lunch_end, 840)
        self.assertTrue(settings.allow_baseline_hard_exceptions)
        self.assertEqual(settings.maximum_new_hard_exceptions, 0)

    def test_soft_constraint_requires_positive_weight(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive"):
            ConstraintSpec(
                identifier="invalid",
                kind=ConstraintKind.MINIMIZE_CHANGES,
                severity="soft",
                weight=0,
            )


if __name__ == "__main__":
    unittest.main()
