from __future__ import annotations

import re
import posixpath
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from typing import Any
from zipfile import BadZipFile, ZipFile

from schedule_repair.domain import ImportIssue, Lesson, ScheduleImportResult

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

HEADER_ALIASES = {
    "duree": "duration",
    "duration": "duration",
    "jour et heure": "day_time",
    "day and time": "day_time",
    "periodes": "period",
    "period": "period",
    "frequence": "frequency",
    "frequency": "frequency",
    "nb places": "possible_slots",
    "nombre de places": "possible_slots",
    "nb jours": "possible_days",
    "nombre de jours": "possible_days",
    "professeur": "teacher",
    "teacher": "teacher",
    "matiere": "subject",
    "subject": "subject",
    "classe": "class_group",
    "class": "class_group",
    "nb eleves": "student_count",
    "nombre d eleves": "student_count",
    "student count": "student_count",
    "salle": "room",
    "room": "room",
    "alternances": "alternation",
    "alternation": "alternation",
    "co enseignement": "co_teaching",
    "co teaching": "co_teaching",
}

REQUIRED_FIELDS = {"duration", "day_time", "teacher", "subject", "class_group", "room"}


class WorkbookFormatError(ValueError):
    """Raised when an XLSX workbook cannot provide the expected table."""


class XlsxScheduleImporter:
    """Import schedule rows from an XLSX sheet with descriptions then headers."""

    def __init__(self, header_aliases: dict[str, str] | None = None) -> None:
        self._header_aliases = dict(HEADER_ALIASES)
        self._header_aliases.update(
            {_normalize(label): canonical for label, canonical in (header_aliases or {}).items()}
        )

    def import_file(self, path: str | Path, sheet_name: str | None = None) -> ScheduleImportResult:
        source = Path(path)
        try:
            with ZipFile(source) as archive:
                sheet, rows = self._read_sheet(archive, sheet_name)
        except (BadZipFile, KeyError, ET.ParseError) as exc:
            raise WorkbookFormatError(f"Cannot read {source.name} as an XLSX workbook") from exc
        return self._build_result(source, sheet, rows)

    def _read_sheet(self, archive: ZipFile, selected: str | None) -> tuple[str, list[list[Any]]]:
        shared_strings = self._read_shared_strings(archive)
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = self._read_relationships(archive)
        sheets = workbook.find(f"{{{MAIN_NS}}}sheets")
        if sheets is None:
            raise WorkbookFormatError("Workbook has no worksheets")

        entries = list(sheets)
        chosen = next((item for item in entries if item.attrib.get("name") == selected), None)
        if selected and chosen is None:
            raise WorkbookFormatError(f"Worksheet {selected!r} does not exist")
        chosen = chosen or (entries[0] if entries else None)
        if chosen is None:
            raise WorkbookFormatError("Workbook has no worksheets")

        relationship_id = chosen.attrib[f"{{{DOC_REL_NS}}}id"]
        worksheet_path = relationships[relationship_id]
        xml = ET.fromstring(archive.read(worksheet_path))
        return chosen.attrib["name"], self._read_rows(xml, shared_strings)

    def _read_relationships(self, archive: ZipFile) -> dict[str, str]:
        root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relationships: dict[str, str] = {}
        for relationship in root.findall(f"{{{PKG_REL_NS}}}Relationship"):
            target = relationship.attrib["Target"]
            if target.startswith("/"):
                path = target.lstrip("/")
            else:
                path = str(PurePosixPath("xl") / target)
            relationships[relationship.attrib["Id"]] = posixpath.normpath(path)
        return relationships

    def _read_shared_strings(self, archive: ZipFile) -> list[str]:
        if "xl/sharedStrings.xml" not in archive.namelist():
            return []
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        return ["".join(node.itertext()) for node in root.findall(f"{{{MAIN_NS}}}si")]

    def _read_rows(self, worksheet: ET.Element, shared_strings: list[str]) -> list[list[Any]]:
        result: list[list[Any]] = []
        sheet_data = worksheet.find(f"{{{MAIN_NS}}}sheetData")
        if sheet_data is None:
            return result
        for row_node in sheet_data.findall(f"{{{MAIN_NS}}}row"):
            row_number = int(row_node.attrib.get("r", len(result) + 1))
            while len(result) < row_number:
                result.append([])
            values: list[Any] = []
            for cell in row_node.findall(f"{{{MAIN_NS}}}c"):
                column = _column_index(cell.attrib.get("r", "A1"))
                while len(values) <= column:
                    values.append(None)
                values[column] = _cell_value(cell, shared_strings)
            result[row_number - 1] = values
        return result

    def _build_result(self, source: Path, sheet: str, rows: list[list[Any]]) -> ScheduleImportResult:
        if len(rows) < 2:
            raise WorkbookFormatError("Expected descriptions in row 1 and headers in row 2")
        descriptions, headers = rows[0], rows[1]
        mapping, issues = _map_headers(headers, self._header_aliases)
        missing = REQUIRED_FIELDS - set(mapping)
        if missing:
            labels = ", ".join(sorted(missing))
            raise WorkbookFormatError(f"Missing required schedule columns: {labels}")

        metadata = {
            canonical: _optional_text(_at(descriptions, index))
            for canonical, index in mapping.items()
        }
        lessons = []
        for source_row, row in enumerate(rows[2:], start=3):
            if not any(value not in (None, "") for value in row):
                continue
            lesson, row_issues = _to_lesson(source_row, row, mapping)
            lessons.append(lesson)
            issues.extend(row_issues)
        return ScheduleImportResult(
            source_file=str(source.resolve()),
            source_sheet=sheet,
            descriptions=metadata,
            lessons=tuple(lessons),
            issues=tuple(issues),
        )


def _map_headers(
    headers: list[Any], aliases: dict[str, str]
) -> tuple[dict[str, int], list[ImportIssue]]:
    mapping: dict[str, int] = {}
    issues: list[ImportIssue] = []
    for index, value in enumerate(headers):
        label = _optional_text(value)
        if not label:
            continue
        canonical = aliases.get(_normalize(label))
        if canonical is None:
            issues.append(ImportIssue("warning", "unknown_header", f"Ignored column {label!r}", 2))
            continue
        if canonical in mapping:
            raise WorkbookFormatError(f"Duplicate schedule column for {canonical!r}")
        mapping[canonical] = index
    return mapping, issues


def _to_lesson(
    source_row: int, row: list[Any], mapping: dict[str, int]
) -> tuple[Lesson, list[ImportIssue]]:
    values = {name: _at(row, index) for name, index in mapping.items()}
    issues: list[ImportIssue] = []
    duration = _duration_minutes(values.get("duration"))
    if duration is None:
        issues.append(ImportIssue("error", "invalid_duration", "Duration could not be parsed", source_row))
    day, start_minute = _day_and_time(values.get("day_time"))
    if day is None or start_minute is None:
        issues.append(ImportIssue("error", "invalid_day_time", "Day and time could not be parsed", source_row))
    for field_name in ("teacher", "subject", "class_group"):
        if _optional_text(values.get(field_name)) is None:
            issues.append(
                ImportIssue(
                    "error",
                    "missing_resource",
                    f"Required lesson value {field_name!r} is empty",
                    source_row,
                )
            )
    if _optional_text(values.get("room")) is None:
        issues.append(
            ImportIssue(
                "warning",
                "missing_room",
                "Lesson has no room; room constraints will not apply until one is assigned",
                source_row,
            )
        )

    lesson = Lesson(
        source_row=source_row,
        duration_minutes=duration,
        day=day,
        start_minute=start_minute,
        period=_optional_text(values.get("period")),
        frequency=_optional_text(values.get("frequency")),
        possible_slots=_optional_int(values.get("possible_slots")),
        possible_days=_optional_int(values.get("possible_days")),
        teacher=_optional_text(values.get("teacher")),
        subject=_optional_text(values.get("subject")),
        class_group=_optional_text(values.get("class_group")),
        student_count=_optional_int(values.get("student_count")),
        room=_optional_text(values.get("room")),
        alternation=_optional_text(values.get("alternation")),
        co_teaching=_optional_text(values.get("co_teaching")),
        raw={name: value for name, value in values.items()},
    )
    return lesson, issues


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> Any:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        inline = cell.find(f"{{{MAIN_NS}}}is")
        return "".join(inline.itertext()) if inline is not None else ""
    value_node = cell.find(f"{{{MAIN_NS}}}v")
    if value_node is None or value_node.text is None:
        return None
    value = value_node.text
    if cell_type == "s":
        return shared_strings[int(value)]
    if cell_type == "b":
        return value == "1"
    if cell_type in {"str", "e"}:
        return value
    try:
        number = float(value)
        return int(number) if number.is_integer() else number
    except ValueError:
        return value


def _column_index(reference: str) -> int:
    letters = re.match(r"[A-Za-z]+", reference)
    if letters is None:
        return 0
    result = 0
    for character in letters.group(0).upper():
        result = result * 26 + ord(character) - ord("A") + 1
    return result - 1


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(character for character in decomposed if not unicodedata.combining(character))
    return " ".join(re.sub(r"[^a-zA-Z0-9]+", " ", ascii_value).lower().split())


def _duration_minutes(value: Any) -> int | None:
    if isinstance(value, (int, float)):
        return round(value * 1440) if 0 < value < 1 else round(value * 60)
    text = _optional_text(value)
    if text is None:
        return None
    match = re.fullmatch(r"(?:(\d+)\s*h)?\s*(\d{1,2})?", text.lower().replace(":", "h"))
    if match is None or not any(match.groups()):
        return None
    return int(match.group(1) or 0) * 60 + int(match.group(2) or 0)


def _day_and_time(value: Any) -> tuple[str | None, int | None]:
    text = _optional_text(value)
    if text is None:
        return None, None
    match = re.fullmatch(r"(.+?)\s+(\d{1,2})\s*[h:]\s*(\d{2})", text, flags=re.IGNORECASE)
    if match is None:
        return None, None
    hours, minutes = int(match.group(2)), int(match.group(3))
    if hours > 23 or minutes > 59:
        return None, None
    return _normalize(match.group(1)), hours * 60 + minutes


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _at(row: list[Any], index: int) -> Any:
    return row[index] if index < len(row) else None
