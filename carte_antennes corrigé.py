import pandas as pd
import folium
from folium.plugins import MarkerCluster

support = pd.read_csv("data/data/sup_support.txt", sep=";", dtype=str)
station = pd.read_csv("data/data/sup_station.txt", sep=";", dtype=str)
antenne = pd.read_csv("data/data/sup_antenne.txt", sep=";", dtype=str)
emetteur = pd.read_csv("data/data/sup_emetteur.txt", sep=";", dtype=str)
bande = pd.read_csv("data/data/sup_bande.txt", sep=";", dtype={"STA_NM_ANFR": str}, decimal=",")
exploitant = pd.read_csv("ref/ref/sup_exploitant.txt", sep=";", dtype=str)
nature = pd.read_csv("ref/ref/sup_nature.txt", sep=";", dtype=str)
proprietaire = pd.read_csv("ref/ref/sup_proprietaire.txt", sep=";", dtype=str)

df = support.merge(station, on="STA_NM_ANFR")
df = df.merge(exploitant, on="ADM_ID")
df = df.merge(nature, on="NAT_ID")
df = df.merge(proprietaire, on="TPO_ID", how="left")

for col in ["COR_NB_DG_LAT", "COR_NB_MN_LAT", "COR_NB_SC_LAT",
            "COR_NB_DG_LON", "COR_NB_MN_LON", "COR_NB_SC_LON"]:
    df[col] = pd.to_numeric(df[col])

df["lat"] = df["COR_NB_DG_LAT"] + df["COR_NB_MN_LAT"] / 60 + df["COR_NB_SC_LAT"] / 3600
df["lon"] = df["COR_NB_DG_LON"] + df["COR_NB_MN_LON"] / 60 + df["COR_NB_SC_LON"] / 3600
df.loc[df["COR_CD_NS_LAT"] == "S", "lat"] = -df["lat"]
df.loc[df["COR_CD_EW_LON"] == "W", "lon"] = -df["lon"]

df = df[df["COM_CD_INSEE"].str.startswith("76", na=False)]

stations_76 = df["STA_NM_ANFR"]
antenne = antenne[antenne["STA_NM_ANFR"].isin(stations_76)]
emetteur = emetteur[emetteur["STA_NM_ANFR"].isin(stations_76)]
bande = bande[bande["STA_NM_ANFR"].isin(stations_76)].dropna(subset=["BAN_NB_F_DEB"])

nb_antennes = antenne.groupby("STA_NM_ANFR").size().rename("nb_antennes")
nb_emetteurs = emetteur.groupby("STA_NM_ANFR").size().rename("nb_emetteurs")
systemes = emetteur.groupby("STA_NM_ANFR")["EMR_LB_SYSTEME"].agg(
    lambda x: ", ".join(sorted(x.dropna().unique()))).rename("systemes")

bande["facteur"] = bande["BAN_FG_UNITE"].map({"K": 0.001, "M": 1, "G": 1000})
bande["f_deb_mhz"] = bande["BAN_NB_F_DEB"] * bande["facteur"]
bande["f_fin_mhz"] = bande["BAN_NB_F_FIN"] * bande["facteur"]
frequences = bande.groupby("STA_NM_ANFR").agg(f_min=("f_deb_mhz", "min"), f_max=("f_fin_mhz", "max"))

df = df.merge(nb_antennes, on="STA_NM_ANFR", how="left")
df = df.merge(nb_emetteurs, on="STA_NM_ANFR", how="left")
df = df.merge(systemes, on="STA_NM_ANFR", how="left")
df = df.merge(frequences, on="STA_NM_ANFR", how="left")
df["systemes"] = df["systemes"].fillna("Inconnu")
df["a_5g"] = df["systemes"].str.contains("5G")

print(df["ADM_LB_NOM"].value_counts().head(10))
print(df.groupby("ADM_LB_NOM")["nb_antennes"].mean().sort_values(ascending=False).head(10))
print(emetteur["EMR_LB_SYSTEME"].value_counts().head(10))
print("Installations avec 5G :", df["a_5g"].sum(), "sur", len(df))

carte = folium.Map(location=[49.44, 1.10], zoom_start=9)
groupe = MarkerCluster().add_to(carte)

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
    <b>Fréquences :</b> {ligne['f_min']} - {ligne['f_max']} MHz
    """
    couleur = "green" if ligne["a_5g"] else "blue"
    folium.Marker([ligne["lat"], ligne["lon"]], popup=folium.Popup(texte, max_width=300),
                  icon=folium.Icon(color=couleur)).add_to(groupe)

carte.save("carte_antennes.html")
