"""
SAÉ 15 - Carte interactive des supports d'antennes (données ANFR)

Étapes du script :
    1. Charger les 8 fichiers avec pandas
    2. Fusionner les tables principales (support, station, exploitant, nature, propriétaire)
    3. Convertir les coordonnées GPS (degrés/minutes/secondes -> degrés décimaux)
    4. Filtrer sur un département
    5. Traiter les gros fichiers (antennes, émetteurs, bandes) : filtrer puis agréger
    6. Afficher quelques statistiques
    7. Créer la carte Folium

Le script doit être dans le dossier "SAE 15", à côté des dossiers "data" et "ref".
Installation : pip install pandas folium
"""

import pandas as pd
import folium
from folium.plugins import MarkerCluster

# ----------------------------------------------------------------------
# 1. CHARGEMENT DES DONNÉES
# ----------------------------------------------------------------------
# Les fichiers sont des CSV avec ";" comme séparateur.
# dtype=str : on lit tout en texte. C'est indispensable pour STA_NM_ANFR
# (ex : "0162290002") : en nombre, le 0 du début disparaîtrait et les
# jointures entre les tables ne fonctionneraient plus.
support = pd.read_csv("data/data/sup_support.txt", sep=";", dtype=str)
station = pd.read_csv("data/data/sup_station.txt", sep=";", dtype=str)
antenne = pd.read_csv("data/data/sup_antenne.txt", sep=";", dtype=str)
emetteur = pd.read_csv("data/data/sup_emetteur.txt", sep=";", dtype=str)

# Dans sup_bande, les fréquences s'écrivent avec une virgule (ex : 150,4).
# decimal="," permet à pandas de les lire directement comme des nombres.
# On force seulement STA_NM_ANFR en texte, les fréquences restent numériques.
bande = pd.read_csv("data/data/sup_bande.txt", sep=";", dtype={"STA_NM_ANFR": str}, decimal=",")

# Tables de référence : elles donnent le libellé correspondant à un identifiant
exploitant = pd.read_csv("ref/ref/sup_exploitant.txt", sep=";", dtype=str)
nature = pd.read_csv("ref/ref/sup_nature.txt", sep=";", dtype=str)
proprietaire = pd.read_csv("ref/ref/sup_proprietaire.txt", sep=";", dtype=str)

# ----------------------------------------------------------------------
# 2. FUSION DES TABLES (équivalent d'un JOIN en SQL)
# ----------------------------------------------------------------------
# support + station : on relie avec l'identifiant de l'installation
df = support.merge(station, on="STA_NM_ANFR")

# + exploitant : ADM_ID -> nom de l'exploitant (ORANGE, SFR...)
df = df.merge(exploitant, on="ADM_ID")

# + nature : NAT_ID -> type de support (Pylône, Mât, Immeuble...)
df = df.merge(nature, on="NAT_ID")

# + propriétaire : TPO_ID -> propriétaire du support
# how="left" : on garde le support même si le propriétaire n'est pas renseigné
df = df.merge(proprietaire, on="TPO_ID", how="left")

# ----------------------------------------------------------------------
# 3. COORDONNÉES : degrés/minutes/secondes -> degrés décimaux
# ----------------------------------------------------------------------
# Folium a besoin de coordonnées décimales (ex : 49.44).
# Les colonnes sont lues en texte, on les convertit d'abord en nombres.
for col in ["COR_NB_DG_LAT", "COR_NB_MN_LAT", "COR_NB_SC_LAT",
            "COR_NB_DG_LON", "COR_NB_MN_LON", "COR_NB_SC_LON"]:
    df[col] = pd.to_numeric(df[col])

# Formule : décimal = degrés + minutes/60 + secondes/3600
df["lat"] = df["COR_NB_DG_LAT"] + df["COR_NB_MN_LAT"] / 60 + df["COR_NB_SC_LAT"] / 3600
df["lon"] = df["COR_NB_DG_LON"] + df["COR_NB_MN_LON"] / 60 + df["COR_NB_SC_LON"] / 3600

# Hémisphère Sud (S) et Ouest (W) : les valeurs deviennent négatives
df.loc[df["COR_CD_NS_LAT"] == "S", "lat"] = -df["lat"]
df.loc[df["COR_CD_EW_LON"] == "W", "lon"] = -df["lon"]

# ----------------------------------------------------------------------
# 4. FILTRAGE SUR UN DÉPARTEMENT
# ----------------------------------------------------------------------
# Le code INSEE d'une commune commence par le numéro du département.
# "76" = Seine-Maritime (Rouen). Change cette valeur pour une autre zone.
df = df[df["COM_CD_INSEE"].str.startswith("76", na=False)]

# ----------------------------------------------------------------------
# 5. TRAITEMENT DES GROS FICHIERS (antennes, émetteurs, bandes)
# ----------------------------------------------------------------------
# a) Filtrage : on ne garde que les lignes des installations du département.
# isin() teste si la valeur est dans la liste. Les millions de lignes de
# départ sont réduites à quelques milliers, ce qui accélère tout ce qui suit.
stations_76 = df["STA_NM_ANFR"]
antenne = antenne[antenne["STA_NM_ANFR"].isin(stations_76)]
emetteur = emetteur[emetteur["STA_NM_ANFR"].isin(stations_76)]

# On enlève aussi les bandes dont la fréquence n'est pas renseignée
bande = bande[bande["STA_NM_ANFR"].isin(stations_76)].dropna(subset=["BAN_NB_F_DEB"])

# b) Agrégation : groupby regroupe les lignes par installation.
# Dans ces fichiers, une installation a plusieurs lignes (une par antenne,
# émetteur ou bande). On veut UNE ligne par installation avant de fusionner,
# sinon le tableau principal serait multiplié.

# Nombre d'antennes et d'émetteurs par installation (.size() compte les lignes)
nb_antennes = antenne.groupby("STA_NM_ANFR").size().rename("nb_antennes")
nb_emetteurs = emetteur.groupby("STA_NM_ANFR").size().rename("nb_emetteurs")

# Liste des systèmes de l'installation (ex : "LTE 800, LTE 1800, 5G NR 3500")
# unique() enlève les doublons, sorted() trie, ", ".join() colle en un texte
systemes = emetteur.groupby("STA_NM_ANFR")["EMR_LB_SYSTEME"].agg(
    lambda x: ", ".join(sorted(x.dropna().unique()))).rename("systemes")

# Fréquences : l'unité varie (K = kHz, M = MHz, G = GHz).
# On convertit tout en MHz avec un facteur de conversion (map remplace
# chaque lettre par sa valeur dans le dictionnaire)
bande["facteur"] = bande["BAN_FG_UNITE"].map({"K": 0.001, "M": 1, "G": 1000})
bande["f_deb_mhz"] = bande["BAN_NB_F_DEB"] * bande["facteur"]
bande["f_fin_mhz"] = bande["BAN_NB_F_FIN"] * bande["facteur"]

# Pour chaque installation : fréquence minimale et maximale
frequences = bande.groupby("STA_NM_ANFR").agg(f_min=("f_deb_mhz", "min"), f_max=("f_fin_mhz", "max"))

# c) On ajoute ces résultats au tableau principal (une ligne par installation,
# donc le nombre de lignes de df ne change pas)
df = df.merge(nb_antennes, on="STA_NM_ANFR", how="left")
df = df.merge(nb_emetteurs, on="STA_NM_ANFR", how="left")
df = df.merge(systemes, on="STA_NM_ANFR", how="left")
df = df.merge(frequences, on="STA_NM_ANFR", how="left")

# Si aucun émetteur n'est connu, on met "Inconnu" à la place de NaN
df["systemes"] = df["systemes"].fillna("Inconnu")

# Nouvelle colonne True/False : l'installation a-t-elle de la 5G ?
df["a_5g"] = df["systemes"].str.contains("5G")

# ----------------------------------------------------------------------
# 6. STATISTIQUES (affichées dans la console)
# ----------------------------------------------------------------------
# Nombre d'installations par exploitant (les 10 premiers)
print(df["ADM_LB_NOM"].value_counts().head(10))

# Nombre moyen d'antennes par installation, par exploitant
print(df.groupby("ADM_LB_NOM")["nb_antennes"].mean().sort_values(ascending=False).head(10))

# Systèmes les plus fréquents parmi les émetteurs du département
print(emetteur["EMR_LB_SYSTEME"].value_counts().head(10))

# a_5g contient des True/False : sum() compte les True
print("Installations avec 5G :", df["a_5g"].sum(), "sur", len(df))

# ----------------------------------------------------------------------
# 7. CARTE FOLIUM
# ----------------------------------------------------------------------
# Carte centrée sur Rouen (latitude, longitude), zoom de départ = 9
carte = folium.Map(location=[49.44, 1.10], zoom_start=9)

# MarkerCluster regroupe les points proches pour garder une carte fluide
groupe = MarkerCluster().add_to(carte)

# On parcourt le tableau ligne par ligne : un marqueur par ligne
for _, ligne in df.iterrows():
    # Texte affiché au clic sur le marqueur (le HTML est autorisé)
    texte = f"""
    <b>Exploitant :</b> {ligne['ADM_LB_NOM']}<br>
    <b>Propriétaire :</b> {ligne['TPO_LB']}<br>
    <b>Nature :</b> {ligne['NAT_LB_NOM']}<br>
    <b>Hauteur :</b> {ligne['SUP_NM_HAUT']} m<br>
    <b>Adresse :</b> {ligne['ADR_LB_LIEU']} {ligne['ADR_NM_CP']}<br>
    <b>Antennes :</b> {ligne['nb_antennes']}<br>
    <b>Émetteurs :</b> {ligne['nb_emetteurs']}<br>
    <b>Systèmes :</b> {ligne['systemes']}<br>
    <b>Fréquences :</b> {ligne['f_min']} - {ligne['f_max']} MHz
    """

    # Vert si l'installation a de la 5G, bleu sinon
    couleur = "green" if ligne["a_5g"] else "blue"

    folium.Marker([ligne["lat"], ligne["lon"]],
                  popup=folium.Popup(texte, max_width=300),
                  icon=folium.Icon(color=couleur)).add_to(groupe)

# Sauvegarde en fichier HTML : à ouvrir dans un navigateur
carte.save("carte_antennes.html")
