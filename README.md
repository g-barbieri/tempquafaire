# Schedule Repair

Outil local pour réparer un emploi du temps avec le moins de changements possible.

## 1. Index

### Exemple fourni

- [Présentation du cas pratique](examples/practical-use-case.md)
- [Classeur anonymisé](outputs/01a05ca8-e128-7ef2-9f03-59f0cd18a688/anonymized_schedule_example.xlsx)
- [Demande : blocs de physique-chimie](requests/physics-blocks.md)
- [Contraintes déduites](outputs/01a05ca8-e128-7ef2-9f03-59f0cd18a688/use_case/deduced_constraints.md)
- [Résultat de l'optimisation](outputs/01a05ca8-e128-7ef2-9f03-59f0cd18a688/use_case/suggested_iterations.md)
- [Emplois du temps avant/après des enseignants](outputs/01a05ca8-e128-7ef2-9f03-59f0cd18a688/use_case/teacher_schedule_changes.md)
- [Exceptions aux contraintes](outputs/01a05ca8-e128-7ef2-9f03-59f0cd18a688/use_case/constraint_exceptions.md)

### Documentation

- [Importer un Excel](docs/import.md)
- [Configurer les contraintes](docs/constraints.md)
- [Comprendre l'algorithme](docs/algorithm.md)
- [Voir d'autres contraintes possibles](docs/constraint-examples.md)
- [Comprendre l'architecture](docs/architecture.md)

## 2. Exemple détaillé

Le cas fourni reprend l'emploi du temps réel avec **94 enseignants anonymisés** et **1 061 cours inchangés**.

| Étape | Fichier | Contenu |
| --- | --- | --- |
| Données d'entrée | [anonymized_schedule_example.xlsx](outputs/01a05ca8-e128-7ef2-9f03-59f0cd18a688/anonymized_schedule_example.xlsx) | Les 1 061 cours, avec horaires, semaines, classes, salles et enseignants anonymisés. |
| Besoin utilisateur | [physics-blocks.md](requests/physics-blocks.md) | L'objectif de créer des blocs de deux heures de physique-chimie avec peu de permutations. |
| Règles appliquées | [constraints.example.json](config/constraints.example.json) | Les contraintes dures, les préférences souples et leurs paramètres. |
| Données déduites | [deduced_constraints.md](outputs/01a05ca8-e128-7ef2-9f03-59f0cd18a688/use_case/deduced_constraints.md) | Les salles observées par matière, les jours sans cours et la plage horaire. |
| Résultat | [suggested_iterations.md](outputs/01a05ca8-e128-7ef2-9f03-59f0cd18a688/use_case/suggested_iterations.md) | Les permutations proposées, les groupes non résolus et les contrôles de conservation. |
| Enseignants concernés | [teacher_schedule_changes.md](outputs/01a05ca8-e128-7ef2-9f03-59f0cd18a688/use_case/teacher_schedule_changes.md) | Pour chaque enseignant modifié : liste des permutations et emploi du temps complet avant/après en semaines A et B. |
| Exceptions | [constraint_exceptions.md](outputs/01a05ca8-e128-7ef2-9f03-59f0cd18a688/use_case/constraint_exceptions.md) | Les règles dures non respectées, leur origine et les exceptions corrigées. |

L'import réussit. L'optimisation retourne `valid_with_exceptions` : 8 blocs sont proposés, les 21 exceptions déjà présentes sont documentées et aucune nouvelle exception n'est créée.

Pour reproduire le cas sous Windows :

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

## 3. Guide pour une future itération

1. Installer [Python 3.11 ou plus](https://www.python.org/downloads/) avec **Add Python to PATH**.
2. Copier le nouvel Excel dans le projet.
3. Vérifier son format avec [docs/import.md](docs/import.md).
4. Copier puis adapter [requests/physics-blocks.md](requests/physics-blocks.md).
5. Modifier si nécessaire [config/constraints.example.json](config/constraints.example.json).
6. Lancer :

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1 "mon-emploi-du-temps.xlsx" -Subject "PHYSIQUE-CHIMIE"
```

7. Lire dans `output/` :

   - `import.json` : erreurs d'import ;
   - `deduced_constraints.md` : salles et jours sans cours ;
   - `suggested_iterations.md` : propositions ou motif de blocage.
   - `teacher_schedule_changes.md` : permutations et emplois du temps avant/après pour chaque enseignant concerné ;
   - `constraint_exceptions.md` : exceptions héritées, nouvelles ou corrigées.

Les exceptions ponctuelles autorisées concernent le déjeuner et les jours de repos. Les conflits et les volumes horaires restent toujours bloquants.

Pour des en-têtes différents, adapter [config/header-aliases.example.json](config/header-aliases.example.json). Le fichier Excel source n'est jamais modifié.

### Vérification technique

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
```

Prochaine étape recommandée : solveur global, puis visualisations des emplois du temps des classes.
