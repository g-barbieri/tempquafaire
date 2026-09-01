from __future__ import annotations

from pathlib import Path
import unittest

from schedule_repair.constraints import ConstraintKind, ConstraintSpec, load_constraints


class ConstraintTests(unittest.TestCase):
    def test_example_constraints_are_valid_and_cover_initial_need(self) -> None:
        path = Path(__file__).parents[1] / "config" / "constraints.example.json"
        constraints = load_constraints(path)
        kinds = {constraint.kind for constraint in constraints}

        self.assertIn(ConstraintKind.CONSECUTIVE_SUBJECT_BLOCK, kinds)
        self.assertIn(ConstraintKind.SUBJECT_ROOM_ELIGIBILITY, kinds)
        self.assertIn(ConstraintKind.KEEP_ORIGINAL_ROOM, kinds)
        self.assertIn(ConstraintKind.PRESERVE_TEACHER_DAYS_OFF, kinds)
        self.assertIn(ConstraintKind.MINIMIZE_GAPS, kinds)
        self.assertIn(ConstraintKind.MINIMIZE_CHANGES, kinds)

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
