import folium

m = folium.Map(
    location=[48.8566, 2.3522],
    zoom_start=12,
    tiles=None
)

folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
    attr="Tiles © Esri",
    name="Esri World Street Map"
).add_to(m)

# Ajouter un marqueur
folium.Marker(
    [48.8566, 2.3522],
    popup="Paris"
).add_to(m)

m.save("carte.html")