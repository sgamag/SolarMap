import folium
from peticion_direcciones import geocode_osm

# Dirección inicial para centrar el mapa
direccion = "Universidad Europea de Madrid"
coords = geocode_osm(direccion)

if coords is None:
    raise SystemExit("No se encontró la dirección inicial.")

lat, lon = coords

mapa = folium.Map(
    location=[lat, lon],
    zoom_start=19
)

# Capa satélite
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Tiles © Esri",
    name="Satélite",
    max_native_zoom=19,
    max_zoom=22
).add_to(mapa)

folium.LayerControl().add_to(mapa)

# ---------------------------------------------------
# 📷 BOTÓN DE CAPTURA (html2canvas)
# ---------------------------------------------------
html2canvas_script = """
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
"""
mapa.get_root().header.add_child(folium.Element(html2canvas_script))

capture_button = """
<style>
#capture-btn {
    position: absolute;
    top: 10px;
    left: 1225px;
    z-index: 999999;
    background: black;
    padding: 8px 12px;
    border-radius: 6px;
    border: 2px solid #333;
    cursor: pointer;
    font-weight: bold;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
}
#capture-btn:hover {
    background: #f0f0f0;
}
</style>

<div id="capture-btn"> Obtener Imágen </div>

<script>
window.addEventListener('load', function() {
    var btn = document.getElementById("capture-btn");
    if (!btn) return;

    btn.onclick = function() {
        var mapContainer = document.getElementsByClassName("folium-map")[0];
        if (!mapContainer) {
            alert("No se encontró el contenedor del mapa.");
            return;
        }

        html2canvas(mapContainer, {useCORS: true}).then(function(canvas) {
            var link = document.createElement('a');
            link.download = 'mapa_captura.png';
            link.href = canvas.toDataURL();
            link.click();
        });
    };
});
</script>
"""
mapa.get_root().html.add_child(folium.Element(capture_button))

map_js_name = mapa.get_name()

search_bar = f"""
<style>
#search-container {{
    position: absolute;
    top: 10px;  /* Debajo del botón de captura */
    left: 612px;
    z-index: 999999;
    background: white;
    padding: 6px;
    border-radius: 6px;
    border: 1px solid #333;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
    display: flex;
    gap: 4px;
}}
#search-input {{
    width: 220px;
    padding: 4px;
    border: 1px solid #aaa;
    border-radius: 4px;
}}
#search-btn {{
    padding: 4px 8px;
    border-radius: 4px;
    border: 1px solid #333;
    background: #eeeeee;
    cursor: pointer;
}}
#search-btn:hover {{
    background: #dddddd;
}}
</style>

<div id="search-container">
    <input id="search-input" type="text" placeholder="Buscar dirección..." />
    <button id="search-btn">Buscar</button>
</div>

<script>
window.addEventListener('load', function() {{
    // Usamos directamente el mapa que ha creado Folium
    var map = {map_js_name};
    var searchMarker = null;

    var btn = document.getElementById("search-btn");
    var input = document.getElementById("search-input");

    if (!btn || !input) {{
        console.error("No se encontró el input o el botón de búsqueda.");
        return;
    }}

    btn.addEventListener('click', function() {{
        var query = input.value;
        if (!query) {{
            alert("Introduce una dirección.");
            return;
        }}

        var url = "http://localhost:8000/geocode?direccion=" + encodeURIComponent(query);

        fetch(url)
        .then(function(response) {{
            if (!response.ok) {{
                throw new Error("No se encontró la dirección");
            }}
            return response.json();
        }})
        .then(function(data) {{
            var lat = data.lat;
            var lon = data.lon;
            var nombre = data.display_name || query;

            if (searchMarker) {{
                map.removeLayer(searchMarker);
            }}

            searchMarker = L.marker([lat, lon]).addTo(map).bindPopup(nombre).openPopup();
            map.setView([lat, lon], 19);
        }})
        .catch(function(error) {{
            console.error(error);
            alert("Error al buscar la dirección.");
        }});
    }});
}});
</script>
"""

mapa.get_root().html.add_child(folium.Element(search_bar))

# ---------------------------------------------------

mapa.save("mapa.html")
print("Mapa guardado como 'mapa.html'. Ábrelo en el navegador.")
