# Schedule Repair

Outil local pour réparer un emploi du temps avec le moins de changements possible.

## 1. Index

### Exemple fourni

- [Présentation du cas pratique](examples/practical-use-case.md)
- [Classeur anonymisé](outputs/01a05ca8-e128-7ef2-9f03-59f0cd18a688/anonymized_schedule_example.xlsx)
- [Demande : blocs de physique-chimie](requests/physics-blocks.md)
- [Contraintes déduites](outputs/01a05ca8-e128-7ef2-9f03-59f0cd18a688/use_case/deduced_constraints.md)
- [Résultat de l'optimisation](outputs/01a05ca8-e128-7ef2-9f03-59f0cd18a688/use_case/suggested_iterations.md)

### Documentation

- [Importer un Excel](docs/import.md)
- [Configurer les contraintes](docs/constraints.md)
- [Comprendre l'algorithme](docs/algorithm.md)
- [Voir d'autres contraintes possibles](docs/constraint-examples.md)
- [Comprendre l'architecture](docs/architecture.md)

## 2. Exemple détaillé

Le cas fourni reprend l'emploi du temps réel avec **94 enseignants anonymisés** et **1 061 cours inchangés**.

| Étape | Fichier |
| --- | --- |
| Données d'entrée | [anonymized_schedule_example.xlsx](outputs/01a05ca8-e128-7ef2-9f03-59f0cd18a688/anonymized_schedule_example.xlsx) |
| Besoin utilisateur | [physics-blocks.md](requests/physics-blocks.md) |
| Règles appliquées | [constraints.example.json](config/constraints.example.json) |
| Données déduites | [deduced_constraints.md](outputs/01a05ca8-e128-7ef2-9f03-59f0cd18a688/use_case/deduced_constraints.md) |
| Résultat | [suggested_iterations.md](outputs/01a05ca8-e128-7ef2-9f03-59f0cd18a688/use_case/suggested_iterations.md) |

L'import réussit. L'optimisation retourne `blocked`, car 21 pauses déjeuner sont déjà absentes. Ce résultat est correct : aucune proposition invalide n'est produite.

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

Pour des en-têtes différents, adapter [config/header-aliases.example.json](config/header-aliases.example.json). Le fichier Excel source n'est jamais modifié.

### Vérification technique

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
```

Prochaine étape recommandée : solveur global, puis visualisations des emplois du temps enseignants et classes.
