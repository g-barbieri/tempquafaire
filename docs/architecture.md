# Architecture

```text
Excel -> import normalisé -> contraintes déduites -> solveur -> validation -> sorties
```

- `importers/` : adapte les fichiers externes ;
- `domain.py` : format stable d'un cours ;
- `constraints.py` et `settings.py` : règles configurables ;
- `analysis.py` : salles et jours de repos déduits ;
- `optimizer.py` : recherche et validation ;
- `output/` : fichiers générés, jamais données source.

Choix actuel : petit projet Python local, sans serveur ni base de données.
