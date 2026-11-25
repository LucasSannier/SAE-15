#  Projet SAE-15

1) Prérequis et organisations des fichiers
Pour le bon fonctionnement du script, certaines installations et placement de fichier/dossier doivent être respecté :
- Il faut dans un premier cas, pour le fonctionnement du script, il est nécessaire de pip install pandas et folium 
- Le script python utilise des chemins relatifs pour accéder au fichier source, dans ce cas il doit être impérativement au même niveau que les dossiers sources data et ref
-------------------------------------------------------------------------------------------------------------------------------------------

2) Présentation du projet

La SAE 15 est un travail collaboratif sur les traitement de données. Il a pour objectif de traiter, d'analyser et de cartographier un jeu de données réel issu de la base ouverte de l'ANFR (Agence Nationale des Fréquences).

-------------------------------------------------------------------------------------------------------------------------------------------
3) Structure globale et démarche algorithmique

Le code source du projet s'articule autour d'une architecture claire, découpée en plusieurs grandes étapes

A) Chargement et Typage des données brute

Utilisation de la bibliothèque Pandas pour lire les différents fichiers texte au format tabulaire séparé par des points virgules 
dtype=str : Les identifiants uniques des installations (STA_NM_ANFR) et les codes de référence sont forcés en format texte. Cette précaution algorithmique évite la suppression automatique des zéros non significatifs en début de chaîne, garantissant ainsi l'intégrité des futures jointures entre les tables

Les colonnes de coordonnées et de fréquences sont converties en type numériques, avec prise en charge explicite des séparateurs décimaux (virgules) présents dans les fichiers sources.

B) Fusion des tables (Jointure)

Le programme croise la table principale des supports (support) avec les informations des stations, des exploitants (ADM_ID), de la nature des supports (NAT_ID) et des propriétaires (TPO_ID) à l'aide de jointures relationnelles (.merge()).

C) Traitement géospatial et filtrage territorial

Conversion des coordonnées géographiques d'origine (exprimées en Degrés, Minutes, Secondes) vers un format décimal exploitable par les outils de cartographie. Le script gère également l'inversion des signes pour les hémisphères Sud et Ouest.
Le volume global des données est immédiatement réduit en filtrant les installations selon un code INSEE cible (ex : département de la Seine-Maritime - 76). Cette étape en amont allège considérablement la mémoire vive et accélère les calculs.

D) Agrégation, enrichissement et indicateurs 

Utilisation de regroupements (.groupby()) pour calculer des métriques par station : nombre d'antennes, nombre d'émetteurs, et normalisation des bandes de fréquences minimales et maximales en mégahertz (MHz).
Création de variables booléennes et textuelles permettant d'isoler facilement la présence de la 5G et d'identifier les principaux opérateurs (Orange, SFR, Free, Bouygues, SNCF).

E) Génération de la carte intéractive (Folium) 

Initialisation d'une carte centrée sur Rouen,enrichie par un fond de carte tier (Esri World Street Map)

Implémentation d'un regroupement visuel intelligent avec Markercluster pour fluidifié la navigation malgrés la densité des points 
