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

mapa = folium.Map(location=[lat, lon], zoom_start=19)

folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Tiles © Esri",
    name="Satélite",
    max_native_zoom=19,
    max_zoom=22
).add_to(mapa)

nombre_mapa = mapa.get_name()

mapa.get_root().header.add_child(folium.Element("""
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
"""))

mapa.get_root().html.add_child(folium.Element(f"""
<style>
    .folium-map {{ width: 100%; height: 100vh; }}

    #capture-frame {{
        position: fixed;
        width: {CAPTURE_SIZE}px;
        height: {CAPTURE_SIZE}px;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        border: 3px solid #22c55e;
        box-shadow: 0 0 0 9999px rgba(0,0,0,0.15);
        z-index: 999998;
        pointer-events: none;
        border-radius: 4px;
    }}

    #zona-label {{
        position: fixed;
        top: calc(50% - {CAPTURE_SIZE // 2}px - 30px);
        left: 50%;
        transform: translateX(-50%);
        z-index: 999999;
        background: rgba(0,0,0,0.55);
        color: white;
        font-size: 11px;
        font-family: sans-serif;
        padding: 3px 10px;
        border-radius: 20px;
        pointer-events: none;
        letter-spacing: 0.05em;
    }}

    #loading-box {{
        position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
        z-index: 99999999; background: rgba(0,0,0,0.85); color: white;
        padding: 20px 28px; border-radius: 12px; display: none;
        font-family: sans-serif; font-size: 14px; font-weight: 600;
    }}

    #custom-alert {{
        position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
        z-index: 9999999; background: #1f2937; color: white;
        padding: 10px 22px; border-radius: 24px;
        opacity: 0; transition: opacity 0.3s;
        font-family: sans-serif; font-size: 13px; font-weight: 500;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }}
</style>

<div id="capture-frame"></div>
<div id="zona-label">Zona de análisis</div>
<div id="loading-box">⏳ Analizando tejados con IA...</div>
<div id="custom-alert"></div>

<script>
    const ZOOMS_PERMITIDOS = {ZOOMS_PERMITIDOS};
    const CAPTURE_SIZE = {CAPTURE_SIZE};
    const nombreMapa = '{nombre_mapa}';

    function getMap() {{
        return window[nombreMapa];
    }}

    function notificarZoom() {{
        const map = getMap();
        if (!map) return;
        const zoom = map.getZoom();
        const valido = ZOOMS_PERMITIDOS.includes(zoom);
        window.parent.postMessage({{ type: "zoom_update", zoom: zoom, valido: valido }}, "*");
    }}

    function showAlert(msg) {{
        const box = document.getElementById("custom-alert");
        box.innerText = msg;
        box.style.opacity = 1;
        setTimeout(() => {{ box.style.opacity = 0; }}, 2500);
    }}

    function canvasToBlob(canvas) {{
        return new Promise(resolve => canvas.toBlob(blob => resolve(blob), "image/png"));
    }}

    async function ejecutarAnalisis() {{
        const map = getMap();
        if (!map) return;
        const zoom = map.getZoom();
        const loadingBox = document.getElementById("loading-box");

        if (!ZOOMS_PERMITIDOS.includes(zoom)) {{
            showAlert("Ajusta el zoom antes de analizar");
            return;
        }}

        window.parent.postMessage("analizando_inicio", "*");
        loadingBox.style.display = "block";

        try {{
            const mapContainer = document.getElementsByClassName("folium-map")[0];
            const fullCanvas = await html2canvas(mapContainer, {{ useCORS: true, scale: 1 }});

            const startX = Math.floor((fullCanvas.width - CAPTURE_SIZE) / 2);
            const startY = Math.floor((fullCanvas.height - CAPTURE_SIZE) / 2);

            const canvas = document.createElement("canvas");
            canvas.width = CAPTURE_SIZE;
            canvas.height = CAPTURE_SIZE;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(fullCanvas, startX, startY, CAPTURE_SIZE, CAPTURE_SIZE, 0, 0, CAPTURE_SIZE, CAPTURE_SIZE);

            const tl = map.containerPointToLatLng([startX, startY]);
            const tr = map.containerPointToLatLng([startX + CAPTURE_SIZE, startY]);
            const br = map.containerPointToLatLng([startX + CAPTURE_SIZE, startY + CAPTURE_SIZE]);
            const bl = map.containerPointToLatLng([startX, startY + CAPTURE_SIZE]);
            const center = map.getCenter();
            const pc = map.latLngToContainerPoint(center);
            const right = map.containerPointToLatLng([pc.x + 1, pc.y]);
            const down  = map.containerPointToLatLng([pc.x, pc.y + 1]);

            const metadata = {{
                width: CAPTURE_SIZE, height: CAPTURE_SIZE, zoom,
                center: {{ lat: center.lat, lon: center.lng }},
                bbox: {{
                    top_left:     {{ lat: tl.lat, lon: tl.lng }},
                    top_right:    {{ lat: tr.lat, lon: tr.lng }},
                    bottom_right: {{ lat: br.lat, lon: br.lng }},
                    bottom_left:  {{ lat: bl.lat, lon: bl.lng }}
                }},
                meters_per_pixel: {{
                    x: center.distanceTo(right),
                    y: center.distanceTo(down),
                    area_m2_per_pixel: center.distanceTo(right) * center.distanceTo(down)
                }}
            }};

            const imageBlob = await canvasToBlob(canvas);
            const formData = new FormData();
            formData.append("image", imageBlob, "mapa_limpio.png");
            formData.append("metadata", JSON.stringify(metadata));

            const response = await fetch("http://localhost:8001/detect-roofs", {{
                method: "POST", body: formData
            }});
            if (!response.ok) throw new Error("API error: " + response.status);

            const geojson = await response.json();
            window.roofLayer.clearLayers();
            window.roofLayer.addData(geojson);

            const cantidad = geojson.features ? geojson.features.length : 0;
            window.parent.postMessage({{ type: "tejados_resultado", cantidad }}, "*");

            showAlert(cantidad > 0 ? "Tejados detectados: " + cantidad : "No se detectaron tejados");

        }} catch (err) {{
            console.error(err);
            showAlert("Error al analizar la imagen");
            window.parent.postMessage({{ type: "tejados_resultado", cantidad: 0 }}, "*");
        }} finally {{
            loadingBox.style.display = "none";
        }}
    }}

    // ── Escucha mensajes del sidebar ──
    window.addEventListener("message", function(event) {{
        if (event.data === "trigger_analizar") {{
            ejecutarAnalisis();
        }}

        if (event.data?.type === "buscar") {{
            // Geocode directo con Nominatim (sin depender de la API)
            const q = event.data.query;
            fetch("https://nominatim.openstreetmap.org/search?q=" + encodeURIComponent(q) + "&format=json&limit=1", {{
                headers: {{ "User-Agent": "SolarMap/1.0" }}
            }})
            .then(r => r.json())
            .then(data => {{
                if (data && data.length > 0) {{
                    const map = getMap();
                    map.flyTo([parseFloat(data[0].lat), parseFloat(data[0].lon)], 19);
                }} else {{
                    showAlert("Dirección no encontrada");
                    window.parent.postMessage({{ type: "buscar_error" }}, "*");
                }}
            }})
            .catch(() => showAlert("Error al buscar la dirección"));
        }}
    }});

    // ── Init tras carga ──
    window.addEventListener('load', function() {{
        const map = getMap();
        if (!map) return;

        map.zoomControl.setPosition('bottomright');

        // Notifica zoom inicial con pequeño delay para asegurar que React está listo
        setTimeout(() => notificarZoom(), 300);

        // Notifica en cada cambio de zoom
        map.on('zoomend', function() {{
            setTimeout(() => notificarZoom(), 100);
        }});

        // Capa tejados
        window.roofLayer = L.geoJSON(null, {{
            style: () => ({{
                color: "#6d28d9", fillColor: "#a855f7",
                fillOpacity: 0.45, weight: 2
            }}),
            onEachFeature: function(feature, layer) {{
                const p = feature.properties || {{}};
                layer.bindPopup(`
                    <div style="font-family:sans-serif;min-width:180px;">
                        <div style="font-weight:700;margin-bottom:6px;">Tejado ${{p.id || ""}}</div>
                        <div style="font-size:13px;color:#374151;">Área: <strong>${{p.area_m2 || "—"}} m²</strong></div>
                        <div style="font-size:13px;color:#374151;">Orientación: <strong>${{p.orientation_label || "—"}}</strong></div>
                        <div style="font-size:13px;color:#374151;">Ángulo: <strong>${{p.orientation_angle_degrees || "—"}}º</strong></div>
                    </div>
                `);
            }}
        }}).addTo(map);
    }});
</script>
"""))

mapa.save("mapa.html")
print("Mapa listo")