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
    attr="Tiles © Esri",
    name="Satélite",
    max_native_zoom=19,
    max_zoom=22
).add_to(mapa)


tooltip = 'plaza'

folium.Marker(
    [lat, lon],
    popup=str(direccion),
    tooltip=tooltip,
    icon=folium.Icon(
        color="green",       # 'red', 'blue', 'green', 'purple', 'orange', 'darkred',...
        icon="cloud"   # icono tipo Bootstrap ('cloud', 'info-sign', 'ok', etc.)
    )
).add_to(mapa)



folium.LayerControl().add_to(mapa)

mapa.save("mapa.html")

print("Mapa guardado como 'mapa.html'. Ábrelo en el navegador.")
