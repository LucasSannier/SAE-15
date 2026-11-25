import pandas as pd
import folium                                   # Import of the modules
from folium.plugins import MarkerCluster, FeatureGroupSubGroup


#Joining files in csv format with ; as separator
# dtype=str, everything is read as text, which in required for STA_NM_ANFR.
# (e.g : "0162290002") : in numbers, the first 0 would disappear
# and attached files between tables would stop working properly.
support = pd.read_csv("data/data/sup_support.txt", sep=";", dtype=str)
station = pd.read_csv("data/data/sup_station.txt", sep=";", dtype=str)
antenne = pd.read_csv("data/data/sup_antenne.txt", sep=";", dtype=str)
emetteur = pd.read_csv("data/data/sup_emetteur.txt", sep=";", dtype=str)

# Within the file sup_bande, the frequencies are written with a coma.
# decimal="," allows pandas to directly read those as numbers.
# Ony STA_NM_ANFR is forced into text, other frequencies remain numerical.
bande = pd.read_csv("data/data/sup_bande.txt", sep=";", dtype={"STA_NM_ANFR": str}, decimal=",") 
exploitant = pd.read_csv("ref/ref/sup_exploitant.txt", sep=";", dtype=str)
nature = pd.read_csv("ref/ref/sup_nature.txt", sep=";", dtype=str)
proprietaire = pd.read_csv("ref/ref/sup_proprietaire.txt", sep=";", dtype=str)

#Files are linked with installation IDs.
# operator : AMD_ID -> name of the operator (ORANGE, SFR...).
# nature : NAT_IT -> support type (Pylon, Mast, Building...).
# proprietaire : TPO_ID -> the support owner.
# how="left" : the support is kept even though the owner is not listed.
df = support.merge(station, on="STA_NM_ANFR")
df = df.merge(exploitant, on="ADM_ID")
df = df.merge(nature, on="NAT_ID")
df = df.merge(proprietaire, on="TPO_ID", how="left")

# Folium works on decimal coordinates (e.g : 49.44).
# Columns are read as text, we first convert them in numbers.
for col in ["COR_NB_DG_LAT", "COR_NB_MN_LAT", "COR_NB_SC_LAT",  
            "COR_NB_DG_LON", "COR_NB_MN_LON", "COR_NB_SC_LON"]:
    df[col] = pd.to_numeric(df[col]) 

# Conversion of degrees, minutes, seconds into decimals.
df["lat"] = df["COR_NB_DG_LAT"] + df["COR_NB_MN_LAT"] / 60 + df["COR_NB_SC_LAT"] / 3600
df["lon"] = df["COR_NB_DG_LON"] + df["COR_NB_MN_LON"] / 60 + df["COR_NB_SC_LON"] / 3600

# Handling of South and West hemispheres.
# df.loc is used to target specific lines, to then change its values.
df.loc[df["COR_CD_NS_LAT"] == "S", "lat"] = -df["lat"]
df.loc[df["COR_CD_EW_LON"] == "W", "lon"] = -df["lon"]

# The user inputs the department's number of which they want to see the installations.
num_dep = input("choisissez le numéro d'un département pour afficher les antennes :")
df = df[df["COM_CD_INSEE"].str.startswith(num_dep, na=False)]

# Filtration ; Only the lines of the installations' municipality are kept.
# isin() ; tests to check if the value is in the list. The millions of lines of codes with which we started are now reduced to a few thousands, which will greatly speed up everything following.
stations_dep = df["STA_NM_ANFR"]
antenne = antenne[antenne["STA_NM_ANFR"].isin(stations_dep)]
emetteur = emetteur[emetteur["STA_NM_ANFR"].isin(stations_dep)]

# The bands which are not registered are severed.
bande = bande[bande["STA_NM_ANFR"].isin(stations_dep)].dropna(subset=["BAN_NB_F_DEB"])

# The number of antennas and public transmitters by installation (.size() counts lines).
nb_antennes = antenne.groupby("STA_NM_ANFR").size().rename("nb_antennes")
nb_emetteurs = emetteur.groupby("STA_NM_ANFR").size().rename("nb_emetteurs")

# Concatenates the list of technologies/systems (i.e: "LTE 800, 5G NR 3500") without doubles and sorted alphabetically.
systemes = emetteur.groupby("STA_NM_ANFR")["EMR_LB_SYSTEME"].agg(
    lambda x: ", ".join(sorted(x.dropna().unique()))).rename("systemes")

# Conversion of all frequency units to MHz (factor : K=0.001, M=1, G=1000).
bande["facteur"] = bande["BAN_FG_UNITE"].map({"K": 0.001, "M": 1, "G": 1000})
bande["f_deb_mhz"] = bande["BAN_NB_F_DEB"] * bande["facteur"]
bande["f_fin_mhz"] = bande["BAN_NB_F_FIN"] * bande["facteur"]

# Calculation of minimal and maximal frequencies by station.
frequences = bande.groupby("STA_NM_ANFR").agg(f_min=("f_deb_mhz", "min"), f_max=("f_fin_mhz", "max"))

# Merging of results are concatenated in the main list.
df = df.merge(nb_antennes, on="STA_NM_ANFR", how="left")
df = df.merge(nb_emetteurs, on="STA_NM_ANFR", how="left")
df = df.merge(systemes, on="STA_NM_ANFR", how="left")
df = df.merge(frequences, on="STA_NM_ANFR", how="left")

# Replaces missing values by "Inconnu" (Unknown).
df["systemes"] = df["systemes"].fillna("Inconnu")

# Fetches the data of each operator and stocks the operator's name in ordor to name them.
df["a_5g"] = df["systemes"].str.contains("5G")
df["orange"] = df["ADM_LB_NOM"].str.contains("ORANGE")
df["sfr"] = df["ADM_LB_NOM"].str.contains("SFR")
df["free"] = df["ADM_LB_NOM"].str.contains("FREE")
df["bouygues"] = df["ADM_LB_NOM"].str.contains("BOUYGUES")
df["sncf"] = df["ADM_LB_NOM"].str.contains("SNCF")

print(df["ADM_LB_NOM"].value_counts().head(10))
print(df.groupby("ADM_LB_NOM")["nb_antennes"].mean().sort_values(ascending=False).head(10))
print(emetteur["EMR_LB_SYSTEME"].value_counts().head(10))

# Calculation and comparison of the sum of sites of each operator to the total number of sites.
print("Installations à Orange :", df["orange"].sum(), "sur", len(df))
print("Installations à SFR :", df["sfr"].sum(), "sur", len(df))
print("Installations à FREE :", df["free"].sum(), "sur", len(df))
print("Installations à Bouygues :", df["bouygues"].sum(), "sur", len(df))
print("Installations à SNCF :", df["sncf"].sum(), "sur", len(df))

# Initialisation of the map centered on Rouen (longitude, latitude), with an initial zoom level of 9.
carte = folium.Map(
    location=[49.44, 1.10],
    zoom_start=9,
    tiles=None
)

# Background of the tiles.
# tiles: variable containing the link to World_Street_Map, a public and free-to-use map.
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
    attr="Tiles © Esri",
    name="Esri World Street Map",
    control=False
).add_to(carte)

# Creates clusters of points when zooming out.
cluster = MarkerCluster(
    options={
        "maxClusterRadius": 15,
        "disableClusteringAtZoom": 11
    },
    control=False
).add_to(carte)

# Creates a group for each operator, which will make it able to check/uncheck specific operators (and not all of them at the same time).
exploitants = {
    nom: FeatureGroupSubGroup(cluster, nom).add_to(carte)
    for nom in ["Orange", "SFR", "Free", "Bouygues", "SNCF", "Autres"]
}

# Line by line track of DataFrame to insert each antenna on the map.
for _, ligne in df.iterrows():

    texte = f"""
    <b>Exploitant :</b> {ligne['ADM_LB_NOM']}<br>
    <b>Propriétaire :</b> {ligne['TPO_LB']}<br>
    <b>Nature :</b> {ligne['NAT_LB_NOM']}<br>
    <b>Hauteur :</b> {ligne['SUP_NM_HAUT']} m<br>
    <b>Adresse :</b> {ligne['ADR_LB_LIEU']} {ligne['ADR_NM_CP']}<br>
    <b>Antennes :</b> {ligne['nb_antennes']}<br>
    <b>Émetteurs :</b> {ligne['nb_emetteurs']}<br>
    <b>Systèmes :</b> {ligne['systemes']}<br>
    <b>Fréquences :</b> {ligne['f_min']} - {ligne['f_max']} MHz<br>
    <b>Contient de la 5G :</b> {ligne['a_5g']}
    """

    # The following if-elif-else statements give each operator their color on the map.
    if ligne['orange']:
        couleur = "orange"
        exploitant = "Orange"

    elif ligne['sfr']:
        couleur = "red"
        exploitant = "SFR"

    elif ligne['free']:
        couleur = "#645B5B"
        exploitant = "Free"

    elif ligne['bouygues']:
        couleur = "#FFEE00"
        exploitant = "Bouygues"

    elif ligne['sncf']:
        couleur = "#100E75"
        exploitant = "SNCF"

    else:
        couleur = "#006110"
        exploitant = "Autres"

    # Adds every marker in the map's cluster.
    folium.Marker(
        [ligne["lat"], ligne["lon"]],
        popup=folium.Popup(texte, max_width=300),
        icon=folium.Icon(color=couleur)
    ).add_to(exploitants[exploitant])

# Displays the visual checklist of the operators.
folium.LayerControl(
    collapsed=False
).add_to(carte)

# Saves the final render of the map in HTML format (needs to be opened with a web browser, preferably Firefox).
carte.save("carte_antennes.html")
