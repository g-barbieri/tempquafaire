# Contraintes

Configuration : `config/constraints.example.json`.

## Dures — toujours respectées

- aucun conflit enseignant, classe/groupe ou salle ;
- début entre l'heure minimale et maximale configurée ;
- enseignant(s) et classe/groupe inchangés pour chaque cours ;
- salle d'origine conservée dans le scénario actuel ;
- heures totales constantes par enseignant, classe, matière et semaine ;
- fréquences `H`, `A`, `B` conservées.

## Dures — exception ponctuelle possible

- jours de repos, séparément en semaines A et B ;
- un créneau libre entre 12 h et 14 h pour chaque enseignant et groupe.

Ces exceptions sont visibles dans `constraint_exceptions.md`. Les autres règles dures restent inviolables.

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

Une infraction éligible déjà présente peut rester comme exception héritée. Toute exception est écrite dans `constraint_exceptions.md`.

Dans `exception_policy` :

- `allow_baseline_exceptions` conserve les infractions initiales ;
- `maximum_new_exceptions` fixe le nombre de nouvelles exceptions ponctuelles ;
- `new_exception_penalty` les rend très coûteuses dans le score.

La valeur recommandée pour `maximum_new_exceptions` est `0`. L'augmenter seulement après accord humain.
