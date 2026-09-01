# Architecture

The system is organized around a stable normalized schedule, with input formats and optimization engines kept behind adapters.

```text
XLSX importer ──> normalized lessons ──> validation
                                           │
constraint JSON ──> constraint specs ──────┤
                                           v
                                  candidate move generator
                                           │
                                           v
                                      CP-SAT solver
                                           │
                                           v
                             ranked, explained repair plans
```

## Design boundaries

### Import adapters

An importer translates a school-specific file into `Lesson` records. The current XLSX adapter understands the supplied two-row header and header aliases in French and English. A future school can add aliases or another adapter without changing optimization logic.

### Domain model

The optimizer receives normalized minutes, resource identifiers, and baseline assignments. Every lesson retains its source row and raw values so a suggested move can be explained and eventually written back safely.

### Constraint specifications

Constraints are JSON data with a stable kind, hard/soft severity, weight, and parameters. School-specific names, rooms, teachers, and priorities belong in configuration rather than solver code.

### Optimization adapter

The planned OR-Tools CP-SAT adapter will compile supported constraint kinds into solver expressions. Keeping this adapter separate makes it possible to test constraint interpretation independently and replace or supplement the solver later.

### Repair plans

Solver output should not be an unexplained replacement timetable. Each repair plan will contain its score, changed lessons, old and new assignments, affected resources, and a penalty breakdown. Multiple plans will be generated so the teacher remains the decision-maker.

## Delivery increments

1. Import and validate the baseline workbook.
2. Generate legal candidate time moves around the affected lessons.
3. Implement hard resource and room constraints in CP-SAT.
4. Add soft disruption, day-off, and gap objectives.
5. Produce several distinct ranked repair plans.
6. Add a simple local web interface and Excel export after the repair engine is stable.

