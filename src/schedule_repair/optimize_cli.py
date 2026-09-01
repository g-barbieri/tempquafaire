from __future__ import annotations

import argparse
import json
from pathlib import Path

from schedule_repair.constraints import load_constraints
from schedule_repair.importers import XlsxScheduleImporter, load_header_aliases
from schedule_repair.optimizer import (
    ConstantHoursOptimizer,
    render_exception_report,
    render_markdown_report,
)
from schedule_repair.settings import settings_from_constraints


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pair physics rows into constant-hours blocks")
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--sheet", help="Worksheet name; defaults to the first sheet")
    parser.add_argument("--header-aliases", type=Path, help="JSON aliases for another export format")
    parser.add_argument("--subject", default="PHYSIQUE-CHIMIE", help="Subject text to regroup")
    parser.add_argument(
        "--constraints",
        type=Path,
        default=Path("config/constraints.example.json"),
        help="Hard and soft constraint configuration",
    )
    parser.add_argument("--output", type=Path, required=True, help="Markdown report path")
    parser.add_argument(
        "--exceptions",
        type=Path,
        help="Separate Markdown report for accepted and resolved hard-constraint exceptions",
    )
    parser.add_argument(
        "--teacher-changes",
        type=Path,
        help="Before/after Markdown timetables for every teacher whose schedule changes",
    )
    parser.add_argument("--json", type=Path, help="Optional machine-readable plan path")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    aliases = load_header_aliases(args.header_aliases)
    imported = XlsxScheduleImporter(aliases).import_file(args.workbook, args.sheet)
    if imported.has_errors:
        raise SystemExit("The workbook contains blocking import errors; repair them before optimizing")
    settings = settings_from_constraints(load_constraints(args.constraints))
    optimizer = ConstantHoursOptimizer(
        imported.lessons, subject_contains=args.subject, settings=settings
    )
    plan = optimizer.optimize()
    validation_issues = optimizer.validate(plan)
    exception_data = optimizer.exception_report(plan)
    exception_path = args.exceptions or args.output.with_name("constraint_exceptions.md")
    exception_path.parent.mkdir(parents=True, exist_ok=True)
    exception_path.write_text(
        render_exception_report(exception_data, args.workbook.name), encoding="utf-8"
    )
    teacher_changes_path = args.teacher_changes or args.output.with_name(
        "teacher_schedule_changes.md"
    )
    teacher_changes_path.parent.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if validation_issues:
        teacher_changes_path.write_text(
            "# Changements par enseignant\n\n"
            "**Statut : bloqué — aucune permutation validable.**\n",
            encoding="utf-8",
        )
        lines = [
            "# Itérations suggérées",
            "",
            "**Statut : bloqué — aucune proposition valide générée.**",
            "",
            "Le fichier source enfreint déjà des contraintes impératives. Il faut d'abord "
            "corriger ces lignes ou autoriser le déplacement contrôlé d'autres matières.",
            "",
            "## Points à corriger",
            "",
        ]
        lines.extend(f"- {issue}" for issue in validation_issues)
        args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
        if args.json:
            args.json.parent.mkdir(parents=True, exist_ok=True)
            args.json.write_text(
                json.dumps(
                    {
                        "status": "blocked",
                        "issues": validation_issues,
                        "exceptions": exception_data,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        print(json.dumps({"status": "blocked", "issue_count": len(validation_issues)}))
        return 3
    teacher_changes_path.write_text(
        optimizer.render_teacher_change_report(plan, args.workbook.name), encoding="utf-8"
    )
    report = render_markdown_report(plan, args.workbook.name)
    args.output.write_text(report, encoding="utf-8")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        payload = plan.to_dict()
        payload["status"] = (
            "valid_with_exceptions"
            if plan.inherited_exception_count or plan.new_exception_count
            else "valid"
        )
        payload["exceptions"] = exception_data
        args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = plan.summary()
    summary["status"] = (
        "valid_with_exceptions"
        if plan.inherited_exception_count or plan.new_exception_count
        else "valid"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
