import pandas as pd
import folium                               #Importation des modules nécessaires à notre code
from folium.plugins import MarkerCluster


#Lecture des fichiers en format .csv avec ; comme séparateur 
#dtype=str,on lit tout en text,c'est indispensable pour STA_NM_ANFR
#(ex : "0162290002") : en nombre, le 0 du début disparaîtrait et les
# jointures entre les tables ne fonctionneraient plus.
support = pd.read_csv("data/data/sup_support.txt", sep=";", dtype=str)
station = pd.read_csv("data/data/sup_station.txt", sep=";", dtype=str)
antenne = pd.read_csv("data/data/sup_antenne.txt", sep=";", dtype=str)
emetteur = pd.read_csv("data/data/sup_emetteur.txt", sep=";", dtype=str)
#Dans le fichier sup_bande,les fréquences s'écrive avec une virgule 
#decimal="," permet à pandas de les lire directement comme des nombres 
#On force seulement STA_NM_ANFR à etre en texte,les fréquences restent numériques
bande = pd.read_csv("data/data/sup_bande.txt", sep=";", dtype={"STA_NM_ANFR": str}, decimal=",") 
exploitant = pd.read_csv("ref/ref/sup_exploitant.txt", sep=";", dtype=str)
nature = pd.read_csv("ref/ref/sup_nature.txt", sep=";", dtype=str)
proprietaire = pd.read_csv("ref/ref/sup_proprietaire.txt", sep=";", dtype=str)


#On relie avec l'identifiants de l'installation
df = support.merge(station, on="STA_NM_ANFR")
#exploitant : ADM_ID -> nom de l'exploitant (ORANGE, SFR...)
df = df.merge(exploitant, on="ADM_ID")
#nature : NAT_ID -> type de support (Pylône, Mât, Immeuble...)
df = df.merge(nature, on="NAT_ID")
# propriétaire : TPO_ID -> propriétaire du support
# how="left" : on garde le support même si le propriétaire n'est pas renseigné
df = df.merge(proprietaire, on="TPO_ID", how="left")

# Folium a besoin de coordonnées décimales (ex : 49.44).
# Les colonnes sont lues en texte, on les convertit d'abord en nombres.
for col in ["COR_NB_DG_LAT", "COR_NB_MN_LAT", "COR_NB_SC_LAT",  
            "COR_NB_DG_LON", "COR_NB_MN_LON", "COR_NB_SC_LON"]:
    df[col] = pd.to_numeric(df[col]) #Prend chaque valeur textuelle et la transforme en nombre 

#Conversion des degres,minutes,seconde en décimaux 
df["lat"] = df["COR_NB_DG_LAT"] + df["COR_NB_MN_LAT"] / 60 + df["COR_NB_SC_LAT"] / 3600
df["lon"] = df["COR_NB_DG_LON"] + df["COR_NB_MN_LON"] / 60 + df["COR_NB_SC_LON"] / 3600
#La gestion des hémisphères Sud et Ouest
#df.loc sert à cibler des lignes précises,pour modifier leurs valeurs 
df.loc[df["COR_CD_NS_LAT"] == "S", "lat"] = -df["lat"]
df.loc[df["COR_CD_EW_LON"] == "W", "lon"] = -df["lon"]

#filtrage pour un département 
#df["COM_CD_INSEE"],cible la colonne qui contient le code INSEE de la commune où se trouve l'installation
#.startswith permet de filtrer avec les textes commançant par 76
#na=False lui indique que si la case est vide, il doit considérer que la réponse est "Faux" et simplement ignorer la ligne au lieu de bloquer le programme.
df = df[df["COM_CD_INSEE"].str.startswith("76", na=False)]

#  Filtrage : on ne garde que les lignes des installations du département.
# isin() teste si la valeur est dans la liste. Les millions de lignes de départ sont réduites à quelques milliers, ce qui accélère tout ce qui suit.
stations_76 = df["STA_NM_ANFR"]
antenne = antenne[antenne["STA_NM_ANFR"].isin(stations_76)]
emetteur = emetteur[emetteur["STA_NM_ANFR"].isin(stations_76)]

# On enlève aussi les bandes dont la fréquence n'est pas renseignée
bande = bande[bande["STA_NM_ANFR"].isin(stations_76)].dropna(subset=["BAN_NB_F_DEB"])
# Nombre d'antennes et d'émetteurs par installation (.size() compte les lignes)
nb_antennes = antenne.groupby("STA_NM_ANFR").size().rename("nb_antennes")
nb_emetteurs = emetteur.groupby("STA_NM_ANFR").size().rename("nb_emetteurs")
# Concaténer la liste des technologies/systèmes (ex: "LTE 800, 5G NR 3500") sans doublons et triés par ordre alphabétique
systemes = emetteur.groupby("STA_NM_ANFR")["EMR_LB_SYSTEME"].agg(
    lambda x: ", ".join(sorted(x.dropna().unique()))).rename("systemes")
# Conversion de toutes les unités de fréquences en MHz (facteur : K=0.001, M=1, G=1000)
bande["facteur"] = bande["BAN_FG_UNITE"].map({"K": 0.001, "M": 1, "G": 1000})
bande["f_deb_mhz"] = bande["BAN_NB_F_DEB"] * bande["facteur"]
bande["f_fin_mhz"] = bande["BAN_NB_F_FIN"] * bande["facteur"]
# Calcul des fréquences minimales et maximales par station
frequences = bande.groupby("STA_NM_ANFR").agg(f_min=("f_deb_mhz", "min"), f_max=("f_fin_mhz", "max"))

#Fusion des résultats agrégés dans le tableau principal df
df = df.merge(nb_antennes, on="STA_NM_ANFR", how="left")
df = df.merge(nb_emetteurs, on="STA_NM_ANFR", how="left")
df = df.merge(systemes, on="STA_NM_ANFR", how="left")
df = df.merge(frequences, on="STA_NM_ANFR", how="left")
#Remplacement des valeurs manquantes de systèmes par "Inconnu"
df["systemes"] = df["systemes"].fillna("Inconnu")
# Création d'une colonne booléenne (True/False) indiquant la présence ou non de la 5G
df["a_5g"] = df["systemes"].str.contains("5G")

#Affichage console
print(df["ADM_LB_NOM"].value_counts().head(10))
print(df.groupby("ADM_LB_NOM")["nb_antennes"].mean().sort_values(ascending=False).head(10))
print(emetteur["EMR_LB_SYSTEME"].value_counts().head(10))
print("Installations avec 5G :", df["a_5g"].sum(), "sur", len(df))

# Initialisation de la carte centrée sur Rouen (latitude, longitude) avec un niveau de zoom initial de 9
carte = folium.Map(location=[49.44, 1.10], zoom_start=9)
# Utilisation de MarkerCluster pour regrouper visuellement les marqueurs proches et garder une carte fluide
groupe = MarkerCluster().add_to(carte)


folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
    attr="Tiles © Esri",
    name="Esri World Street Map"
).add_to(carte)
# Parcours ligne par ligne du DataFrame pour insérer chaque antenne sur la carte
for _, ligne in df.iterrows():
    # Construction du contenu HTML affiché au clic sur un marqueur
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
    # Attribution d'une couleur : Vert si le site diffuse de la 5G, Bleu sinon
    couleur = "green" if ligne["a_5g"] else "blue"
    # Ajout du marqueur dans le cluster de la carte
    folium.Marker([ligne["lat"], ligne["lon"]], popup=folium.Popup(texte, max_width=300),
                  icon=folium.Icon(color=couleur)).add_to(groupe)
# Sauvegarde de la carte finale au format HTML (à ouvrir dans un navigateur web)
carte.save("carte_antennes.html")
