# Schedule Repair

Outil local pour modifier un emploi du temps avec le moins de changements possible.

## Installation simple — Windows

1. Installer [Python 3.11 ou plus](https://www.python.org/downloads/).
2. Ouvrir PowerShell dans le dossier.
3. Tester l'exemple anonymisé :

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

Si Windows ne trouve pas Python, le réinstaller en cochant **Add Python to PATH**.

Pour une autre matière : ajouter `-Subject "MATHEMATIQUES"`.

Pour son propre fichier : le copier dans le dossier puis lancer `run.ps1 "mon-emploi-du-temps.xlsx"`.

Les résultats apparaissent dans `output/` :

- `import.json` : données importées et erreurs éventuelles ;
- `deduced_constraints.md` : salles observées et jours sans cours ;
- `suggested_iterations.md` : propositions valides, ou motif de blocage.

Le fichier Excel source n'est jamais modifié.

## Utiliser un autre format Excel

Consulter [docs/import.md](docs/import.md). Les noms de colonnes peuvent être adaptés dans `config/header-aliases.example.json`.

## Modifier les règles

Modifier `config/constraints.example.json`, puis relancer `run.ps1`.

Règles actuelles : [docs/constraints.md](docs/constraints.md).

## Comprendre ou faire évoluer le projet

- Algorithme : [docs/algorithm.md](docs/algorithm.md)
- Exemples de demandes : [docs/constraint-examples.md](docs/constraint-examples.md)
- Demande actuelle : [requests/physics-blocks.md](requests/physics-blocks.md)
- Cas pratique anonymisé : [examples/practical-use-case.md](examples/practical-use-case.md)
- Architecture : [docs/architecture.md](docs/architecture.md)

## État actuel

L'import et l'analyse fonctionnent. L'optimiseur conservateur ne déplace encore que la physique-chimie. Le fichier source comporte déjà des journées sans pause déjeuner ; la sortie est donc correctement marquée **bloquée**.

Étape suivante : solveur global, puis branche `codex/visualizations` pour les vues enseignants et classes.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```
