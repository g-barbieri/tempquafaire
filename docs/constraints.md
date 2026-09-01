# Contraintes

Configuration : `config/constraints.example.json`.

## Dures — jamais enfreintes

- aucun conflit enseignant, classe/groupe ou salle ;
- jours de repos conservés, séparément en semaines A et B ;
- un créneau libre entre 12 h et 14 h pour chaque enseignant et groupe ;
- début entre l'heure minimale et maximale configurée ;
- enseignant(s) et classe/groupe inchangés pour chaque cours ;
- salle d'origine conservée dans le scénario actuel ;
- heures totales constantes par enseignant, classe, matière et semaine ;
- fréquences `H`, `A`, `B` conservées.

Les jours de repos peuvent être déduits du fichier ou fournis dans `days_off_by_teacher`. Un cours peut avoir plusieurs enseignants.

Exemple pour saisir les jours manuellement :

```json
"derive_days_off_from_baseline": false,
"days_off_by_teacher": {"DUPONT Alice": {"A": ["mercredi"], "B": ["mercredi"]}}
```

## Souples — à minimiser

- nombre de cours déplacés ;
- distance par rapport au créneau initial ;
- trous dans les journées.

Une sortie qui enfreint une règle dure porte le statut `blocked` et ne contient aucune suggestion validable.
