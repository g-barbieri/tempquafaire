from __future__ import annotations

import argparse
import json
from pathlib import Path

from schedule_repair.importers import XlsxScheduleImporter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import a school timetable from XLSX")
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--sheet", help="Worksheet name; defaults to the first sheet")
    parser.add_argument("--output", type=Path, help="Optional path for normalized JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = XlsxScheduleImporter().import_file(args.workbook, args.sheet)
    payload = {
        "summary": result.summary(),
        "descriptions": result.descriptions,
        "issues": [issue.to_dict() for issue in result.issues],
        "lessons": [lesson.to_dict() for lesson in result.lessons],
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result.summary(), ensure_ascii=False, indent=2))
    return 2 if result.has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
