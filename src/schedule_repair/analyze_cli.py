from __future__ import annotations

import argparse
from pathlib import Path

from schedule_repair.analysis import deduce_constraints, render_deduced_markdown
from schedule_repair.importers import XlsxScheduleImporter, load_header_aliases


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deduce rooms and teacher days off from XLSX")
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--sheet")
    parser.add_argument("--header-aliases", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    aliases = load_header_aliases(args.header_aliases)
    imported = XlsxScheduleImporter(aliases).import_file(args.workbook, args.sheet)
    if imported.has_errors:
        raise SystemExit("Import errors must be corrected before constraints are deduced")
    result = deduce_constraints(imported.lessons)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        render_deduced_markdown(result, args.workbook.name), encoding="utf-8"
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
