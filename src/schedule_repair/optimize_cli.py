from __future__ import annotations

import argparse
import json
from pathlib import Path

from schedule_repair.constraints import load_constraints
from schedule_repair.importers import XlsxScheduleImporter, load_header_aliases
from schedule_repair.optimizer import ConstantHoursOptimizer, render_markdown_report
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
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if validation_issues:
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
                    {"status": "blocked", "issues": validation_issues},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        print(json.dumps({"status": "blocked", "issue_count": len(validation_issues)}))
        return 3
    report = render_markdown_report(plan, args.workbook.name)
    args.output.write_text(report, encoding="utf-8")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(plan.summary(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
