from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from schedule_repair.importers.xlsx import WorkbookFormatError, XlsxScheduleImporter


def _write_workbook(path: Path, headers: list[str], room: str = "Lab 1") -> None:
    descriptions = ["description"] * len(headers)
    lesson = [
        "1h00",
        "lundi 08h55",
        "",
        "H",
        "1",
        "1",
        "Mme Curie",
        "PHYSIQUE-CHIMIE",
        "3A",
        "28",
        room,
        "H (36/36)",
        "",
    ][: len(headers)]
    rows = [_row_xml(1, descriptions), _row_xml(2, headers), _row_xml(3, lesson)]
    worksheet = _xml_header() + "<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\"><sheetData>" + "".join(rows) + "</sheetData></worksheet>"
    workbook = _xml_header() + '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Schedule" sheetId="1" r:id="rId1"/></sheets></workbook>'
    relationships = _xml_header() + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>'
    with ZipFile(path, "w") as archive:
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", relationships)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)


def _row_xml(number: int, values: list[str]) -> str:
    cells = []
    for index, value in enumerate(values):
        reference = f"{chr(ord('A') + index)}{number}"
        escaped = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        cells.append(f'<c r="{reference}" t="inlineStr"><is><t>{escaped}</t></is></c>')
    return f'<row r="{number}">{"".join(cells)}</row>'


def _xml_header() -> str:
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'


HEADERS = [
    "Durée",
    "Jour et heure",
    "Périodes",
    "Fréquence",
    "Nb. Places",
    "Nb. Jours",
    "Professeur",
    "Matière",
    "Classe",
    "Nb. élèves",
    "Salle",
    "Alternances",
    "Co-Enseignement",
]


class XlsxScheduleImporterTests(unittest.TestCase):
    def test_imports_two_row_header_and_normalizes_lesson(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "schedule.xlsx"
            _write_workbook(path, HEADERS)
            result = XlsxScheduleImporter().import_file(path)

        self.assertEqual(result.source_sheet, "Schedule")
        self.assertEqual(result.summary()["lesson_count"], 1)
        self.assertEqual(result.descriptions["subject"], "description")
        lesson = result.lessons[0]
        self.assertEqual(lesson.duration_minutes, 60)
        self.assertEqual(lesson.day, "lundi")
        self.assertEqual(lesson.start_time, "08:55")
        self.assertEqual(lesson.teacher, "Mme Curie")
        self.assertEqual(lesson.subject, "PHYSIQUE-CHIMIE")
        self.assertEqual(lesson.student_count, 28)
        self.assertEqual(lesson.room, "Lab 1")
        self.assertEqual(result.issues, ())

    def test_rejects_a_workbook_missing_a_required_header(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "schedule.xlsx"
            _write_workbook(path, [header for header in HEADERS if header != "Salle"])
            with self.assertRaisesRegex(WorkbookFormatError, "room"):
                XlsxScheduleImporter().import_file(path)

    def test_missing_room_is_reported_without_blocking_import(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "schedule.xlsx"
            _write_workbook(path, HEADERS, room="")
            result = XlsxScheduleImporter().import_file(path)

        self.assertFalse(result.has_errors)
        self.assertEqual(result.issues[0].code, "missing_room")
        self.assertEqual(result.issues[0].severity, "warning")


if __name__ == "__main__":
    unittest.main()
