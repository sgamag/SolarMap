import folium
from peticion_direcciones import geocode_osm
import webbrowser
import os

# --- CONFIGURACIÓN ---
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

# --- DEPENDENCIAS ---
mapa.get_root().header.add_child(folium.Element("""
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
"""))

# --- UI + LÓGICA DE SELECCIÓN INVISIBLE ---
mapa.get_root().html.add_child(folium.Element(f"""
<style>
    .folium-map {{ width: 100%; height: 100vh; }}
    #home-btn {{ position: absolute; top: 10px; left: 10px; z-index: 999999; background: #2563eb; color: white; padding: 10px 15px; border-radius: 8px; border: 2px solid white; cursor: pointer; font-weight: bold; font-family: sans-serif; box-shadow: 0 2px 4px rgba(0,0,0,0.3); }}
    #search-container {{ position: absolute; top: 10px; left: 50%; transform: translateX(-50%); z-index: 999999; background: white; padding: 8px; border-radius: 8px; display: flex; gap: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.3); }}
    #capture-btn {{ position: absolute; top: 10px; right: 10px; z-index: 999999; background: #14532d; color: white; padding: 10px 15px; border-radius: 8px; border: 2px solid #4ade80; cursor: pointer; font-weight: bold; font-family: sans-serif; transition: 0.3s; }}
    #capture-frame {{ position: fixed; width: {CAPTURE_SIZE}px; height: {CAPTURE_SIZE}px; top: 50%; left: 50%; transform: translate(-50%, -50%); border: 3px solid #22c55e; box-shadow: 0 0 0 9999px rgba(0,0,0,0.2); z-index: 999998; pointer-events: none; }}
    #loading-box {{ position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 99999999; background: rgba(0, 0, 0, 0.9); color: white; padding: 20px; border-radius: 10px; display: none; font-family: sans-serif; text-align: center; }}
</style>

<div id="home-btn" onclick="volverInicio()">Volver al Inicio</div>
<div id="search-container">
    <input id="search" style="padding:8px; border:1px solid #ccc; border-radius:4px; width:200px;" placeholder="Ej: Madrid..."/>
    <button onclick="buscar()" style="padding:8px 12px; cursor:pointer; font-weight:bold;">Buscar</button>
</div>
<div id="capture-btn">Analizar Zona</div>
<div id="capture-frame"></div>
<div id="loading-box">Analizando zona...</div>

<script>
    const nombreMapa = '{nombre_mapa}';
    
    // Leemos el usuario desde la URL (lo enviará la web de React)
    const urlParams = new URLSearchParams(window.location.search);
    const USUARIO_ACTUAL = urlParams.get('user') || "anonimo";

    function volverInicio() {{ window.location.href = "http://localhost:8081"; }}

    function buscar() {{
        const q = document.getElementById("search").value;
        if(!q) return;
        fetch("http://localhost:8001/geocode?direccion=" + encodeURIComponent(q))
        .then(r => r.json()).then(data => {{ window[nombreMapa].flyTo([data.lat, data.lon], 19); }});
    }}

    // Envío invisible de datos
    window.confirmarTejado = function(lat, lon, area, orientacion) {{
        const loadingBox = document.getElementById("loading-box");
        loadingBox.innerText = "Configurando zona...";
        loadingBox.style.display = "block";

        fetch("http://localhost:8001/seleccionar-tejado", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{
                id_usuario: USUARIO_ACTUAL,
                lat: lat,
                lon: lon,
                area_m2: area,
                orientacion: orientacion
            }})
        }})
        .then(() => {{ window.location.href = "http://localhost:8081/dashboard"; }})
        .catch(err => {{ 
            console.error(err);
            loadingBox.innerText = "Error al guardar";
            setTimeout(() => loadingBox.style.display = "none", 2000);
        }});
    }};

    window.addEventListener('load', function() {{
        const map = window[nombreMapa];
        const btn = document.getElementById("capture-btn");
        const ZOOMS_PERMITIDOS = {ZOOMS_PERMITIDOS};
        const CAPTURE_SIZE = {CAPTURE_SIZE};

        map.zoomControl.setPosition('bottomright');

        function actualizarColorBoton() {{
            const zoomActual = map.getZoom();
            if (!ZOOMS_PERMITIDOS.includes(zoomActual)) {{
                btn.style.background = "#dc2626";
                btn.style.borderColor = "#991b1b";
                btn.innerText = "Zoom inválido";
            }} else {{
                btn.style.background = "#14532d";
                btn.style.borderColor = "#4ade80";
                btn.innerText = "Analizar Zona";
            }}
        }}
        actualizarColorBoton();
        map.on('zoomend', actualizarColorBoton);

        var roofLayer = L.geoJSON(null, {{
            style: {{ color: "#6d28d9", fillColor: "#a855f7", fillOpacity: 0.45, weight: 2 }},
            onEachFeature: function(f, l) {{
                const p = f.properties;
                const centro = l.getBounds().getCenter();
                
                // Popup ultra limpio: Solo el pin y el botón
                l.bindPopup(`
                    <div style="text-align:center; padding: 5px;">
                        <div style="font-size: 32px; margin-bottom: 10px;">📍</div>
                        <button onclick="confirmarTejado(${{centro.lat}}, ${{centro.lng}}, ${{p.area_m2}}, '${{p.orientation_label}}')" 
                                style="background:#2563eb; color:white; border:none; padding:10px 15px; border-radius:5px; cursor:pointer; font-weight:bold; width: 100%;">
                            Seleccionar tejado
                        </button>
                    </div>
                `, {{ closeButton: false }});
            }}
        }}).addTo(map);

        function canvasToBlob(canvas) {{
            return new Promise(function(resolve) {{
                canvas.toBlob(function(blob) {{ resolve(blob); }}, "image/png");
            }});
        }}

        btn.onclick = async function() {{
            const zoom = map.getZoom();
            if (!ZOOMS_PERMITIDOS.includes(zoom)) return alert("Acércate o aléjate para escanear");
            
            document.getElementById("loading-box").style.display = "block";
            btn.style.pointerEvents = "none";
            btn.style.opacity = "0.6";
            
            try {{
                var mapContainer = document.getElementsByClassName("folium-map")[0];
                var fullCanvas = await html2canvas(mapContainer, {{ useCORS: true, scale: 1 }});

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

                if (!response.ok) throw new Error("Error en la API");

                var geojson = await response.json();
                roofLayer.clearLayers();
                roofLayer.addData(geojson);

                if (!geojson.features || geojson.features.length === 0) {{
                    alert("No se detectaron tejados en esta captura");
                }}

            }} catch(e) {{ 
                console.error(e); 
                alert("Error al analizar la imagen");
            }} finally {{ 
                document.getElementById("loading-box").style.display = "none";
                btn.style.pointerEvents = "auto";
                btn.style.opacity = "1";
            }}
        }};
    }});
</script>
"""))

mapa.save("mapa.html")
webbrowser.open("file://" + os.path.abspath("mapa.html"))