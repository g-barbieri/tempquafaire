# Cas pratique anonymisé

Classeur : `outputs/01a05ca8-e128-7ef2-9f03-59f0cd18a688/anonymized_schedule_example.xlsx`.

## Anonymisation

- 1 061 cours conservés ;
- 94 enseignants renommés par discipline : `Science Teacher 1`, `Math Teacher 1`, etc. ;
- horaires, semaines, classes, matières et salles inchangés ;
- aucun nom d'origine détecté.

## Lancer le cas

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1 "outputs\01a05ca8-e128-7ef2-9f03-59f0cd18a688\anonymized_schedule_example.xlsx"
```

## Résultat vérifié

- import : 1 061 cours, 0 erreur, 1 avertissement ;
- analyse : salles et jours de repos correctement déduits ;
- optimisation : statut `valid_with_exceptions`, 8 blocs proposés, 21 exceptions héritées et 0 nouvelle exception.
- enseignants concernés : permutations détaillées et emplois du temps avant/après dans `teacher_schedule_changes.md`.

Les exceptions sont détaillées dans `constraint_exceptions.md` ; elles ne sont pas masquées dans la proposition.
