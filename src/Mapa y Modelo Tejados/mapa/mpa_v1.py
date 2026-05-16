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

    #search-container {{
        position: absolute; top: 10px; left: 50%;
        transform: translateX(-50%);
        z-index: 999999;
        background: white; padding: 8px;
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.25);
        display: flex; gap: 8px; align-items: center;
    }}
    #search-container input {{
        padding: 8px 12px; border: 1px solid #d1d5db;
        border-radius: 6px; width: 220px;
        font-family: sans-serif; font-size: 14px;
        outline: none;
    }}
    #search-container button {{
        padding: 8px 14px; cursor: pointer;
        background: #f3f4f6; border: 1px solid #d1d5db;
        border-radius: 6px; font-family: sans-serif;
        font-weight: 600; font-size: 14px;
    }}
    #search-container button:hover {{ background: #e5e7eb; }}

    #capture-btn {{
        position: absolute; top: 10px; right: 10px;
        z-index: 999999;
        background: #14532d; color: white;
        padding: 10px 18px; border-radius: 10px;
        border: 2px solid #4ade80;
        cursor: pointer; font-family: sans-serif;
        font-weight: 700; font-size: 14px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.25);
        transition: background-color 0.3s, border-color 0.3s;
    }}

    #capture-frame {{
        position: fixed;
        width: {CAPTURE_SIZE}px;
        height: {CAPTURE_SIZE}px;
        top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        border: 3px solid #22c55e;
        box-shadow: 0 0 0 9999px rgba(0,0,0,0.15);
        z-index: 999998;
        pointer-events: none;
        border-radius: 4px;
    }}

    #loading-box {{
        position: fixed; top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        z-index: 99999999;
        background: rgba(0,0,0,0.85); color: white;
        padding: 20px 28px; border-radius: 12px;
        display: none;
        font-family: sans-serif; font-size: 14px; font-weight: 600;
    }}

    #custom-alert {{
        position: fixed; bottom: 24px; left: 50%;
        transform: translateX(-50%);
        z-index: 9999999;
        background: #1f2937; color: white;
        padding: 10px 22px; border-radius: 24px;
        opacity: 0; transition: opacity 0.3s;
        font-family: sans-serif; font-size: 13px; font-weight: 500;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }}
</style>

<div id="search-container">
    <input id="search" placeholder="Ej: Madrid..." />
    <button onclick="buscarDireccion()">Buscar</button>
</div>

<button id="capture-btn" onclick="ejecutarAnalisis()">Analizar Zona</button>

<div id="capture-frame"></div>
<div id="loading-box">Analizando tejados con IA...</div>
<div id="custom-alert"></div>

<script>
    const ZOOMS_PERMITIDOS = {ZOOMS_PERMITIDOS};
    const CAPTURE_SIZE = {CAPTURE_SIZE};
    const nombreMapa = '{nombre_mapa}';

    function getMap() {{
        return window[nombreMapa];
    }}

    function showAlert(msg) {{
        const box = document.getElementById("custom-alert");
        box.innerText = msg;
        box.style.opacity = 1;
        setTimeout(() => {{ box.style.opacity = 0; }}, 2500);
    }}

    function canvasToBlob(canvas) {{
        return new Promise(resolve => canvas.toBlob(b => resolve(b), "image/png"));
    }}

    // ============================================================
    // COLOR SEGUN LA ETIQUETA DE ORIENTACION
    // ============================================================
    // Asignamos un "score solar" a cada etiqueta y lo convertimos a color HSL
    // (0 = rojo intenso, 1 = verde brillante).
    function colorPorOrientacion(label, angulo) {{
        const scores = {{
            "Sur":         1.00,
            "Sureste":     0.85,
            "Suroeste":    0.85,
            "Norte-Sur":   0.75,   // una vertiente al sur, otra al norte
            "Este-Oeste":  0.55,   // dos vertientes laterales
            "Este":        0.50,
            "Oeste":       0.50,
            "Norte":       0.00
        }};

        let score = scores[label];

        // Si la etiqueta no esta mapeada, intentamos por angulo
        if (score === undefined && angulo !== null && angulo !== undefined) {{
            const diffSur = Math.abs(((angulo - 180 + 540) % 360) - 180);
            score = 1 - (diffSur / 180);
        }}

        // Fallback final
        if (score === undefined) score = 0.5;

        const hue = Math.round(score * 120);   // 0 = rojo, 120 = verde
        return `hsl(${{hue}}, 75%, 45%)`;
    }}

    // ============================================================
    // BUSCADOR
    // ============================================================
    function buscarDireccion() {{
        const input = document.getElementById("search");
        const q = input.value.trim();
        if (!q) return;
        fetch("https://nominatim.openstreetmap.org/search?q=" + encodeURIComponent(q) + "&format=json&limit=1")
            .then(r => r.json())
            .then(data => {{
                if (data && data.length > 0) {{
                    const map = getMap();
                    map.flyTo([parseFloat(data[0].lat), parseFloat(data[0].lon)], 19);
                }} else {{
                    showAlert("Dirección no encontrada");
                }}
            }})
            .catch(() => showAlert("Error al buscar la dirección"));
    }}

    document.addEventListener("DOMContentLoaded", function() {{
        const input = document.getElementById("search");
        if (input) {{
            input.addEventListener("keydown", function(e) {{
                if (e.key === "Enter") {{
                    e.preventDefault();
                    buscarDireccion();
                }}
            }});
        }}
    }});

    // ============================================================
    // GUARDAR TEJADO EN BD
    // ============================================================
    async function analizarYGuardarTejado(props) {{
        let user = null;
        try {{
            const raw = window.parent.localStorage.getItem("solarmap.user");
            if (raw) user = JSON.parse(raw);
        }} catch (e) {{
            console.error("No se pudo leer el usuario:", e);
        }}

        if (!user || !user.id_usuario) {{
            showAlert("Debes iniciar sesión para analizar un tejado");
            setTimeout(() => {{ window.parent.location.href = "/login"; }}, 1500);
            return;
        }}

        const loadingBox = document.getElementById("loading-box");
        loadingBox.innerText = "Guardando análisis...";
        loadingBox.style.display = "block";

        try {{
            const payload = {{
                id_usuario: user.id_usuario,
                lat: props.lat,
                lon: props.lon,
                area_m2: props.area_m2,
                orientation_angle_degrees: props.orientation_angle_degrees,
                orientation_label: props.orientation_label
            }};

            const response = await fetch("http://localhost:8002/api/tejados/guardar", {{
                method: "POST",
                headers: {{ "Content-Type": "application/json" }},
                body: JSON.stringify(payload)
            }});

            if (!response.ok) {{
                const err = await response.json().catch(() => ({{}}));
                throw new Error(err.detail || "Error al guardar el tejado");
            }}

            const data = await response.json();

            try {{
                window.parent.sessionStorage.setItem("solarmap.tejado_actual", JSON.stringify(data));
            }} catch (e) {{
                console.error("No se pudo guardar en sessionStorage:", e);
            }}

            showAlert("Tejado guardado correctamente");
            setTimeout(() => {{ window.parent.location.href = "/analisis/resumen"; }}, 800);

        }} catch (err) {{
            console.error(err);
            showAlert("Error: " + err.message);
        }} finally {{
            loadingBox.style.display = "none";
            loadingBox.innerText = "Analizando tejados con IA...";
        }}
    }}

    window.analizarTejado = function(propsJsonEncoded) {{
        try {{
            const props = JSON.parse(decodeURIComponent(propsJsonEncoded));
            analizarYGuardarTejado(props);
        }} catch (e) {{
            console.error("Error parseando props:", e);
            showAlert("Error al procesar el tejado");
        }}
    }};

    // ============================================================
    // ANALIZAR ZONA
    // ============================================================
    function actualizarColorBoton() {{
        const map = getMap();
        if (!map) return;
        const btn = document.getElementById("capture-btn");
        const zoom = map.getZoom();
        if (!ZOOMS_PERMITIDOS.includes(zoom)) {{
            btn.style.background = "#dc2626";
            btn.style.borderColor = "#991b1b";
            btn.innerText = "Zoom inválido";
        }} else {{
            btn.style.background = "#14532d";
            btn.style.borderColor = "#4ade80";
            btn.innerText = "Analizar Zona";
        }}
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
                width: CAPTURE_SIZE, height: CAPTURE_SIZE, zoom: zoom,
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
            showAlert(cantidad > 0 ? "Tejados detectados: " + cantidad : "No se detectaron tejados");

        }} catch (err) {{
            console.error(err);
            showAlert("Error al analizar la imagen");
        }} finally {{
            loadingBox.style.display = "none";
        }}
    }}

    // ============================================================
    // INIT
    // ============================================================
    window.addEventListener('load', function() {{
        const map = getMap();
        if (!map) return;

        map.zoomControl.setPosition('bottomright');
        actualizarColorBoton();
        map.on('zoomend', actualizarColorBoton);

        window.roofLayer = L.geoJSON(null, {{
            style: function(feature) {{
                const p = feature.properties || {{}};
                const color = colorPorOrientacion(p.orientation_label, p.orientation_angle_degrees);
                return {{
                    color: color,
                    fillColor: color,
                    fillOpacity: 0.55,
                    weight: 2
                }};
            }},
            onEachFeature: function(feature, layer) {{
                const p = feature.properties || {{}};
                let lat = null, lon = null;
                try {{
                    const bounds = layer.getBounds();
                    const center = bounds.getCenter();
                    lat = center.lat;
                    lon = center.lng;
                }} catch (e) {{}}

                const propsParaGuardar = {{
                    lat: lat,
                    lon: lon,
                    area_m2: p.area_m2 || 0,
                    orientation_angle_degrees: p.orientation_angle_degrees || null,
                    orientation_label: p.orientation_label || null
                }};

                const propsEncoded = encodeURIComponent(JSON.stringify(propsParaGuardar));

                const contenido = `
                    <div style="font-family:sans-serif;min-width:180px;text-align:center;">
                        <div style="font-weight:700;font-size:15px;margin-bottom:10px;color:#111827;">
                            Tejado seleccionado
                        </div>
                        <button onclick="window.analizarTejado('${{propsEncoded}}')"
                            style="background:#f59e0b;color:white;border:none;padding:8px 16px;
                                   border-radius:8px;cursor:pointer;font-weight:700;font-size:13px;
                                   font-family:sans-serif;width:100%;">
                            Analizar
                        </button>
                    </div>
                `;
                layer.bindPopup(contenido);
            }}
        }}).addTo(map);
    }});
</script>
"""))

mapa.save("mapa.html")
print("Mapa listo")