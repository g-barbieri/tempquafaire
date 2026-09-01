from __future__ import annotations

import argparse
import json
from pathlib import Path

from schedule_repair.importers import XlsxScheduleImporter
from schedule_repair.optimizer import FirstPassOptimizer, render_markdown_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Suggest two-period physics-chemistry repairs")
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--sheet", help="Worksheet name; defaults to the first sheet")
    parser.add_argument("--output", type=Path, required=True, help="Markdown report path")
    parser.add_argument("--json", type=Path, help="Optional machine-readable plan path")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    imported = XlsxScheduleImporter().import_file(args.workbook, args.sheet)
    if imported.has_errors:
        raise SystemExit("The workbook contains blocking import errors; repair them before optimizing")
    optimizer = FirstPassOptimizer(imported.lessons)
    plan = optimizer.optimize()
    validation_issues = optimizer.validate(plan)
    if validation_issues:
        raise SystemExit("Invalid repair plan: " + "; ".join(validation_issues))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = render_markdown_report(plan, args.workbook.name, imported.lessons)
    args.output.write_text(report, encoding="utf-8")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(plan.summary(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
