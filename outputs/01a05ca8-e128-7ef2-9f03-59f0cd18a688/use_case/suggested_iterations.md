# Itérations suggérées

Source : `anonymized_schedule_example.xlsx` — lecture seule.

> Aucune heure de cours n'est ajoutée ou supprimée.

## Résultat

- Groupes de physique-chimie : 18
- Groupes obtenant un bloc de deux créneaux : 8
- Groupes sans bloc dans cette itération : 10
- Lignes existantes regroupées : 16
- Lignes d'une heure restant seules : 23
- Lignes déplacées : 14
- Blocs placés sur un jour de repos : 0
- Évolution nette des trous : 3
- Exceptions héritées conservées : 21
- Nouvelles exceptions : 0
- Exceptions initiales corrigées : 0

## Conservation des heures

| Semaine | Minutes initiales | Minutes proposées | Écart |
| :---: | ---: | ---: | ---: |
| A | 1680 | 1680 | +0 |
| B | 1620 | 1620 | +0 |

## Règles appliquées

- Chaque ligne reste présente une fois, avec sa durée et sa fréquence H/A/B.
- Les autres matières restent fixes ; leurs volumes horaires sont donc constants.
- `H` est actif en A et B ; `A` et `B` uniquement pendant leur semaine.
- Deux lignes forment un bloc seulement pendant une semaine où elles sont toutes deux actives.
- Enseignant, classe/groupe et salle d'origine sont conservés.
- Les blocs utilisent des créneaux adjacents dans la plage source 08:00–16:00.
- Les jours de repos et pauses déjeuner sont des règles dures. Les infractions initiales peuvent rester comme exceptions documentées ; les nouvelles utilisent un quota et une pénalité élevée.

## Blocs de deux créneaux proposés

| Classe/groupe | Semaine | Lignes Excel | Salle | Positions actuelles | Bloc proposé | Lignes déplacées | Jour de repos ? |
| --- | :---: | ---: | --- | --- | --- | ---: | :---: |
| <1CIEL1> 1CIEL1P2 | A | 961, 972 | 401 Labo TP 16 pl | A mardi 10:10 + H jeudi 13:50 | lundi 08:00 + 08:55 | 2 | non |
| <1CIEL2> 1CIEL2P2 | A | 969, 960 | 401 Labo TP 16 pl | H jeudi 10:10 + A lundi 16:00 | mercredi 15:05 + 16:00 | 2 | non |
| <1CIEL3PT> 1CIEL3PTP2 | A | 270, 260 | 409 Labo TP 16 pl | H mercredi 10:10 + A lundi 12:55 | mercredi 12:55 + 13:50 | 2 | non |
| <2MTNE1> 2MTNE1P1 | A | 812, 816 | 401 Labo TP 16 pl | H mardi 15:05 + A mercredi 10:10 | mardi 15:05 + 16:00 | 1 | non |
| <2MTNE1> 2MTNE1P2 | B | 819, 827 | 409 Labo TP 16 pl | B jeudi 08:00 + B vendredi 13:50 | mercredi 13:50 + 15:05 | 2 | non |
| <2MTNE2> 2MTNE2P2 | B | 71, 80 | 401 Labo TP 16 pl | B mardi 08:00 + H vendredi 08:55 | vendredi 08:00 + 08:55 | 1 | non |
| <TCIEL1> TCIEL1P2 | A | 268, 264 | 409 Labo TP 16 pl | A mercredi 08:00 + H mardi 08:55 | mercredi 15:05 + 16:00 | 2 | non |
| <TCIEL2> TCIEL2P1 | A | 968, 974 | 401 Labo TP 16 pl | H mercredi 12:00 + A vendredi 11:05 | mercredi 12:55 + 13:50 | 2 | non |

## Groupes sans bloc de deux créneaux

- <1CIEL1> 1CIEL1P1 (rows 958, 962): Un bloc est possible isolément, mais entre en conflit avec les blocs déjà retenus.
- <1CIEL2> 1CIEL2P1 (rows 967, 975): Un bloc est possible isolément, mais entre en conflit avec les blocs déjà retenus.
- <1CIEL3PT> 1CIEL3PTP1 (rows 259, 273): Un bloc est possible isolément, mais entre en conflit avec les blocs déjà retenus.
- <2MTNE2> 2MTNE2P1 (rows 66, 83): Les lignes actives la même semaine utilisent des salles différentes.
- <2MTNE3> 2MTNE3P1 (rows 75, 79): Un bloc est possible isolément, mais entre en conflit avec les blocs déjà retenus.
- <2MTNE3> 2MTNE3P2 (rows 69, 74): Un bloc est possible isolément, mais entre en conflit avec les blocs déjà retenus.
- <TCIEL1> TCIEL1P1 (rows 256, 258): Un bloc est possible isolément, mais entre en conflit avec les blocs déjà retenus.
- <TCIEL2> TCIEL2P2 (rows 965, 970): Un bloc est possible isolément, mais entre en conflit avec les blocs déjà retenus.
- <TCIEL3PT> TCIEL3PTP1 (rows 740, 754): Les lignes actives la même semaine utilisent des salles différentes.
- <TCIEL3PT> TCIEL3PTP2 (rows 733, 751, 755): Les lignes actives la même semaine utilisent des salles différentes.

## Lignes d'une heure restantes

Ces lignes restent présentes une fois, sans changement de durée. Certaines sont nécessaires à cause des alternances A/B ; d'autres ne peuvent pas être regroupées sans déplacer davantage de ressources.

- Ligne 66 : <2MTNE2> 2MTNE2P1, A, lundi 10:10, 401 Labo TP 16 pl.
- Ligne 69 : <2MTNE3> 2MTNE3P2, H, lundi 15:05, 401 Labo TP 16 pl.
- Ligne 74 : <2MTNE3> 2MTNE3P2, A, mardi 12:00, 401 Labo TP 16 pl.
- Ligne 75 : <2MTNE3> 2MTNE3P1, B, mardi 13:50, 401 Labo TP 16 pl.
- Ligne 79 : <2MTNE3> 2MTNE3P1, H, jeudi 12:00, 401 Labo TP 16 pl.
- Ligne 83 : <2MTNE2> 2MTNE2P1, H, vendredi 11:05, 409 Labo TP 16 pl.
- Ligne 256 : <TCIEL1> TCIEL1P1, A, lundi 08:00, 409 Labo TP 16 pl.
- Ligne 258 : <TCIEL1> TCIEL1P1, H, lundi 11:05, 409 Labo TP 16 pl.
- Ligne 259 : <1CIEL3PT> 1CIEL3PTP1, B, lundi 12:00, 409 Labo TP 16 pl.
- Ligne 273 : <1CIEL3PT> 1CIEL3PTP1, H, vendredi 08:55, 409 Labo TP 16 pl.
- Ligne 733 : <TCIEL3PT> TCIEL3PTP2, A, lundi 10:10, 409 Labo TP 16 pl.
- Ligne 740 : <TCIEL3PT> TCIEL3PTP1, H, mardi 11:05, 401 Labo TP 16 pl.
- Ligne 751 : <TCIEL3PT> TCIEL3PTP2, B, vendredi 10:10, 401 Labo TP 16 pl.
- Ligne 754 : <TCIEL3PT> TCIEL3PTP1, B, vendredi 12:00, 409 Labo TP 16 pl.
- Ligne 755 : <TCIEL3PT> TCIEL3PTP2, A, vendredi 12:00, 401 Labo TP 16 pl.
- Ligne 813 : <2MTNE1> 2MTNE1P2, A, mercredi 08:00, 401 Labo TP 16 pl.
- Ligne 817 : <2MTNE1> 2MTNE1P2, B, mercredi 10:10, 401 Labo TP 16 pl.
- Ligne 958 : <1CIEL1> 1CIEL1P1, B, lundi 13:50, 401 Labo TP 16 pl.
- Ligne 962 : <1CIEL1> 1CIEL1P1, H, mardi 12:55, 401 Labo TP 16 pl.
- Ligne 965 : <TCIEL2> TCIEL2P2, B, mardi 16:00, 401 Labo TP 16 pl.
- Ligne 967 : <1CIEL2> 1CIEL2P1, H, mercredi 11:05, 401 Labo TP 16 pl.
- Ligne 970 : <TCIEL2> TCIEL2P2, H, jeudi 11:05, 401 Labo TP 16 pl.
- Ligne 975 : <1CIEL2> 1CIEL2P1, B, vendredi 12:00, 401 Labo TP 16 pl.

## Relancer

```powershell
$env:PYTHONPATH = "src"
python -m schedule_repair.optimize_cli "base edt.xlsx" --output "output/constant_hours_suggestions.md" --json "output/constant_hours_suggestions.json"
```
