# Initial constraint catalog

## Hard constraints

Hard constraints define schedules that must be rejected.

| Kind | Meaning | Initial use |
| --- | --- | --- |
| `no_resource_overlap` | A teacher, class/group, or room cannot be used by overlapping lessons. | Always enabled. |
| `consecutive_subject_block` | Matching lessons must occupy a minimum consecutive duration. | Physics-chemistry requires 120 minutes. |
| `subject_room_eligibility` | A subject may only use approved rooms. | Physics-chemistry rooms are derived from the baseline, then can be overridden. |
| `keep_original_room` | A moved lesson must retain its baseline room. | Enabled for the first repair scenario. |
| `lock_lesson` | Selected lessons cannot change time or room. | Available for teacher-approved or immovable lessons. |

Room eligibility and room stability are deliberately separate. A future user may permit a physics lesson to move between approved laboratories while still prohibiting ordinary classrooms. For the initial case, both constraints are hard, so the exact original room remains fixed.

## Soft constraints

Soft constraints are allowed to be violated at a cost. Weights make the trade-off explicit.

| Kind | Meaning | Starter weight |
| --- | --- | ---: |
| `minimize_changes` | Penalize every lesson whose time or room changes. | 100 |
| `preserve_teacher_days_off` | Penalize placing a lesson on a teacher's baseline day off. | 40 |
| `minimize_gaps` | Penalize empty periods between lessons for teachers and classes. | 20 |

The weights are relative rather than percentages. With these starter values, avoiding a moved lesson is five times more important than avoiding one unit of gap penalty. They should become editable in the teacher interface.

## Likely later additions

- teacher availability windows;
- lunch and travel-time rules;
- room capacity and equipment requirements;
- maximum lessons per day;
- preferred morning or afternoon periods;
- spreading a subject across different days;
- synchronizing or separating class groups;
- limiting how many students or teachers a repair affects.

