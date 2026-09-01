# Schedule Repair

Schedule Repair is the beginning of a reusable tool for teachers who need to make small timetable changes under hard and soft constraints. The existing timetable is the baseline: the future optimizer will search for the least disruptive set of moves rather than rebuild everything.

## Current foundation

- Imports `.xlsx` schedules whose first row describes the columns and whose second row contains the headers.
- Maps the French workbook schema to stable internal field names.
- Allows additional header aliases to be supplied for another school's export.
- Parses durations and day/time values into optimization-friendly minutes.
- Preserves the original Excel row and raw values for traceability.
- Loads configurable hard and soft constraint specifications from JSON.
- Uses only the Python standard library for the import, so setup remains lightweight.

## Run the importer

From the project root:

```powershell
$env:PYTHONPATH = "src"
python -m schedule_repair.cli "base edt.xlsx" --output "output/schedule.json"
```

The command returns exit code `0` when the import has no row-level errors and `2` when rows need attention. The original workbook is never modified.
It prints a compact summary and writes normalized lesson data only when `--output` is supplied.

## Constraint model

Constraints are data, not school-specific `if` statements. See `config/constraints.example.json` and `docs/constraint-catalog.md` for the first configuration:

- hard: teachers, classes, and rooms cannot overlap;
- hard: physics-chemistry must form a two-hour consecutive block;
- hard: physics-chemistry may use only eligible rooms;
- hard: each lesson keeps its original room;
- soft: minimize the number of changed lessons;
- soft: preserve teacher days off found in the baseline;
- soft: minimize gaps for teachers and classes.

Soft weights express trade-offs. A higher weight means the optimizer should sacrifice that preference only when it enables a more important improvement.

## Tests

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
```

## Next milestone

The project now includes a conservative, week-aware first-pass repair search:

```powershell
$env:PYTHONPATH = "src"
python -m schedule_repair.optimize_cli "base edt.xlsx" --output "output/first_optimization_suggestions.md" --json "output/first_optimization_suggestions.json"
```

It treats `H` as active in both alternating weeks and permits `A` and `B` to occupy the same slot. It first finds conflict-free two-period physics-chemistry placements without moving unrelated subjects. The next increment is controlled displacement of blocking lessons, followed by an OR-Tools CP-SAT adapter for global optimization.
