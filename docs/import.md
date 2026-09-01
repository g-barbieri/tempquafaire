# Import de l'emploi du temps

## Format attendu

- fichier `.xlsx` ;
- ligne 1 : description libre des colonnes ;
- ligne 2 : en-têtes ;
- une ligne par cours à partir de la ligne 3.

## Colonnes

| Obligatoire | Exemples |
| --- | --- |
| Durée | `1h`, `0h55` |
| Jour et heure | `lundi 08h00` |
| Professeur | `DUPONT Alice` |
| Matière | `PHYSIQUE-CHIMIE` |
| Classe | `2MTNE1` ou `<2MTNE1> 2MTNE1P1` |
| Salle | `401 Labo TP` |

Facultatif : période, fréquence, effectif, alternance, co-enseignement.

Une salle vide produit un avertissement. Une durée, date, matière, classe ou enseignant invalide bloque l'optimisation. Les colonnes inconnues sont ignorées avec un avertissement.

Fréquences : `H` = toutes les semaines, `A` = semaine A, `B` = semaine B.

Plusieurs enseignants : les séparer par `+`, `;`, `/` ou `|`.

## Adapter les en-têtes

Copier `config/header-aliases.example.json`, modifier les libellés de gauche, puis ajouter :

```powershell
--header-aliases config/mon-format.json
```

Noms internes : `duration`, `day_time`, `teacher`, `subject`, `class_group`, `room`, `period`, `frequency`, `student_count`, `alternation`, `co_teaching`.
