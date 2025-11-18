import folium
from peticion_direcciones import geocode_osm

direccion = input("Introduce una dirección: ").strip() or "Universidad Europea de Madrid, Villaviciosa de Odón"
lat, lon = geocode_osm(direccion)

mapa = folium.Map(
    location=[lat, lon],
    zoom_start=32
)


folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Tiles © Esri — Source: Esri, Earthstar Geographics, Maxar, etc.",
    name="Satélite Esri"
).add_to(mapa)


tooltip = 'plaza'

folium.Marker(
    [lat, lon],
    popup=str(direccion),
    tooltip=tooltip
).add_to(mapa)

folium.LayerControl().add_to(mapa)

mapa.save("mapa.html")

print("Mapa guardado como 'mapa.html'. Ábrelo en el navegador.")
