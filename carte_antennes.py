import pandas as pd
import folium
from folium.plugins import MarkerCluster

support = pd.read_csv("sup_support.txt", sep=";", dtype=str)
station = pd.read_csv("sup_station.txt", sep=";", dtype=str)
exploitant = pd.read_csv("sup_exploitant.txt", sep=";", dtype=str)
nature = pd.read_csv("sup_nature.txt", sep=";", dtype=str)

df = support.merge(station, on="STA_NM_ANFR")
df = df.merge(exploitant, on="ADM_ID")
df = df.merge(nature, on="NAT_ID")

for col in ["COR_NB_DG_LAT", "COR_NB_MN_LAT", "COR_NB_SC_LAT",
            "COR_NB_DG_LON", "COR_NB_MN_LON", "COR_NB_SC_LON"]:
    df[col] = pd.to_numeric(df[col])

df["lat"] = df["COR_NB_DG_LAT"] + df["COR_NB_MN_LAT"] / 60 + df["COR_NB_SC_LAT"] / 3600
df["lon"] = df["COR_NB_DG_LON"] + df["COR_NB_MN_LON"] / 60 + df["COR_NB_SC_LON"] / 3600

df.loc[df["COR_CD_NS_LAT"] == "S", "lat"] = -df["lat"]
df.loc[df["COR_CD_EW_LON"] == "W", "lon"] = -df["lon"]

df = df[df["COM_CD_INSEE"].str.startswith("76", na=False)]

carte = folium.Map(location=[49.44, 1.10], zoom_start=9)
groupe = MarkerCluster().add_to(carte)

for _, ligne in df.iterrows():
    texte = f"""
    <b>Exploitant :</b> {ligne['ADM_LB_NOM']}<br>
    <b>Nature :</b> {ligne['NAT_LB_NOM']}<br>
    <b>Hauteur :</b> {ligne['SUP_NM_HAUT']} m<br>
    <b>Adresse :</b> {ligne['ADR_LB_LIEU']} {ligne['ADR_NM_CP']}
    """
    folium.Marker([ligne["lat"], ligne["lon"]], popup=texte).add_to(groupe)

carte.save("carte_antennes.html")
