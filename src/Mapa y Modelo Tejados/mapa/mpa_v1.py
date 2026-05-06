import folium
from peticion_direcciones import geocode_osm

# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------

direccion = "Universidad Europea de Madrid"
ZOOMS_PERMITIDOS = [18, 19]
CAPTURE_SIZE = 256

coords = geocode_osm(direccion)

if coords is None:
    raise SystemExit("No se encontró la dirección inicial.")

lat, lon = coords

mapa = folium.Map(
    location=[lat, lon],
    zoom_start=19
)

folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Tiles © Esri",
    name="Satélite",
    max_native_zoom=19,
    max_zoom=22
).add_to(mapa)

nombre_mapa = mapa.get_name()

# ---------------------------------------------------
# html2canvas
# ---------------------------------------------------

mapa.get_root().header.add_child(folium.Element("""
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
"""))

# ---------------------------------------------------
# UI + CAPTURA + ENVÍO AL MODELO
# ---------------------------------------------------

mapa.get_root().html.add_child(folium.Element(f"""
<style>
.folium-map {{
    width: 100%;
    height: 100vh;
}}

#capture-btn {{
    position: absolute;
    top: 10px;
    right: 150px;
    z-index: 999999;
    background: #14532d;
    color: white;
    padding: 8px 12px;
    border-radius: 6px;
    border: 2px solid #4ade80;
    cursor: pointer;
}}

#capture-frame {{
    position: fixed;
    width: {CAPTURE_SIZE}px;
    height: {CAPTURE_SIZE}px;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    border: 3px solid #22c55e;
    box-shadow: 0 0 0 9999px rgba(0,0,0,0.2);
    z-index: 999998;
    pointer-events: none;
}}

#custom-alert {{
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 9999999;
    background: black;
    color: white;
    padding: 15px;
    border-radius: 8px;
    opacity: 0;
    transition: 0.3s;
}}

#loading-box {{
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 99999999;
    background: rgba(0, 0, 0, 0.85);
    color: white;
    padding: 18px 24px;
    border-radius: 10px;
    display: none;
    font-size: 16px;
}}
</style>

<div id="capture-btn">Obtener Imagen</div>
<div id="capture-frame"></div>
<div id="custom-alert"></div>
<div id="loading-box">Analizando tejados...</div>

<script>
window.addEventListener('load', function() {{

    var map = {nombre_mapa};
    var btn = document.getElementById("capture-btn");
    var loadingBox = document.getElementById("loading-box");

    var ZOOMS_PERMITIDOS = {ZOOMS_PERMITIDOS};
    var CAPTURE_SIZE = {CAPTURE_SIZE};

    var roofLayer = L.geoJSON(null, {{
        style: function(feature) {{
            return {{
                color: "#6d28d9",
                fillColor: "#a855f7",
                fillOpacity: 0.45,
                weight: 2
            }};
        }},
        onEachFeature: function(feature, layer) {{
            var p = feature.properties || {{}};

            var contenido = `
                <b>Tejado detectado ${{p.id || ""}}</b><br>
                Área: ${{p.area_m2 || "No disponible"}} m²<br>
                Orientación: ${{p.orientation_label || "No disponible"}}<br>
                Ángulo: ${{p.orientation_angle_degrees || "No disponible"}}º<br>
                <br>
                <button onclick="alert('Aquí irá el análisis solar del tejado seleccionado')">
                    Ver análisis solar
                </button>
            `;

            layer.bindPopup(contenido);
        }}
    }}).addTo(map);

    function showAlert(msg) {{
        var box = document.getElementById("custom-alert");
        box.innerText = msg;
        box.style.opacity = 1;
        setTimeout(() => box.style.opacity = 0, 2500);
    }}

    function canvasToBlob(canvas) {{
        return new Promise(function(resolve) {{
            canvas.toBlob(function(blob) {{
                resolve(blob);
            }}, "image/png");
        }});
    }}

    btn.onclick = async function() {{

        var zoom = map.getZoom();

        if (!ZOOMS_PERMITIDOS.includes(zoom)) {{

            if (zoom < Math.min(...ZOOMS_PERMITIDOS)) {{
                showAlert("Acércate más (zoom actual: " + zoom + ")");
            }} else {{
                showAlert("Aléjate un poco (zoom actual: " + zoom + ")");
            }}

            return;
        }}

        loadingBox.style.display = "block";
        btn.style.pointerEvents = "none";
        btn.style.opacity = "0.6";

        try {{

            var mapContainer = document.getElementsByClassName("folium-map")[0];

            var fullCanvas = await html2canvas(mapContainer, {{
                useCORS: true,
                scale: 1
            }});

            var startX = Math.floor((fullCanvas.width - CAPTURE_SIZE) / 2);
            var startY = Math.floor((fullCanvas.height - CAPTURE_SIZE) / 2);

            var canvas = document.createElement("canvas");
            canvas.width = CAPTURE_SIZE;
            canvas.height = CAPTURE_SIZE;

            var ctx = canvas.getContext("2d");

            ctx.drawImage(
                fullCanvas,
                startX, startY, CAPTURE_SIZE, CAPTURE_SIZE,
                0, 0, CAPTURE_SIZE, CAPTURE_SIZE
            );

            var tl = map.containerPointToLatLng([startX, startY]);
            var tr = map.containerPointToLatLng([startX + CAPTURE_SIZE, startY]);
            var br = map.containerPointToLatLng([startX + CAPTURE_SIZE, startY + CAPTURE_SIZE]);
            var bl = map.containerPointToLatLng([startX, startY + CAPTURE_SIZE]);

            var center = map.getCenter();

            var pointCenter = map.latLngToContainerPoint(center);
            var right = map.containerPointToLatLng([pointCenter.x + 1, pointCenter.y]);
            var down = map.containerPointToLatLng([pointCenter.x, pointCenter.y + 1]);

            var mppX = center.distanceTo(right);
            var mppY = center.distanceTo(down);

            var metadata = {{
                width: canvas.width,
                height: canvas.height,
                zoom: zoom,
                center: {{ lat: center.lat, lon: center.lng }},
                bbox: {{
                    top_left: {{ lat: tl.lat, lon: tl.lng }},
                    top_right: {{ lat: tr.lat, lon: tr.lng }},
                    bottom_right: {{ lat: br.lat, lon: br.lng }},
                    bottom_left: {{ lat: bl.lat, lon: bl.lng }}
                }},
                meters_per_pixel: {{
                    x: mppX,
                    y: mppY,
                    area_m2_per_pixel: mppX * mppY
                }}
            }};

            var imageBlob = await canvasToBlob(canvas);

            var formData = new FormData();
            formData.append("image", imageBlob, "mapa_limpio.png");
            formData.append("metadata", JSON.stringify(metadata));

            var response = await fetch("http://localhost:8001/detect-roofs", {{
                method: "POST",
                body: formData
            }});

            if (!response.ok) {{
                throw new Error("Error en la API: " + response.status);
            }}

            var geojson = await response.json();

            roofLayer.clearLayers();
            roofLayer.addData(geojson);

            if (!geojson.features || geojson.features.length === 0) {{
                showAlert("No se detectaron tejados en esta captura");
            }} else {{
                showAlert("Tejados detectados: " + geojson.features.length);
            }}

        }} catch (error) {{
            console.error(error);
            showAlert("Error al analizar la imagen");
        }} finally {{
            loadingBox.style.display = "none";
            btn.style.pointerEvents = "auto";
            btn.style.opacity = "1";
        }}
    }};
}});
</script>
"""))

# ---------------------------------------------------
# BÚSQUEDA
# ---------------------------------------------------

mapa.get_root().html.add_child(folium.Element(f"""
<div style="position:absolute;top:10px;left:50px;z-index:999999;background:white;padding:5px;border-radius:5px;">
<input id="search" placeholder="Buscar dirección"/>
<button onclick="buscar()">Buscar</button>
</div>

<script>
function buscar() {{
    var q = document.getElementById("search").value;

    fetch("http://localhost:8001/geocode?direccion=" + encodeURIComponent(q))
    .then(r => r.json())
    .then(data => {{
        var map = {nombre_mapa};
        map.flyTo([data.lat, data.lon], 19);
    }});
}}
</script>
"""))

mapa.save("mapa.html")
print("Mapa listo")

import webbrowser
import os

ruta_html = os.path.abspath("mapa.html")

webbrowser.open("file://" + ruta_html)