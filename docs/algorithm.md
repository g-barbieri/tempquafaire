# Algorithme

Imaginez que chaque cours soit une carte posée sur une grille.

1. Importer les cartes et les semaines `H/A/B`.
2. Déduire jours travaillés et salles observées.
3. Générer des déplacements proches du créneau initial.
4. Écarter les nouvelles infractions dures, sauf quota d'exceptions explicite.
5. Classer le reste : moins de déplacements, moins de distance, moins de trous.
6. Écrire les propositions et les exceptions dans deux fichiers séparés.

Le prototype utilise une recherche limitée par faisceau : simple et rapide pour de petites réparations. Pour déplacer plusieurs matières ensemble, utiliser ensuite **OR-Tools CP-SAT**. Les règles et les poids resteront dans la configuration ; seul le moteur changera.
