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
# Script de html2canvas
# ---------------------------------------------------
html2canvas_script = """
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
"""
mapa.get_root().header.add_child(folium.Element(html2canvas_script))

nombre_mapa = mapa.get_name()

# ---------------------------------------------------
# BOTÓN DE CAPTURA + ALERTA + LOADING
# ---------------------------------------------------
boton_captura = f"""
<style>
html, body {{
    height: 100%;
    margin: 0;
}}
.folium-map {{
    width: 100%;
    height: 100vh;
}}

#capture-btn {{
    position: absolute;
    top: 10px;
    right: 150px;
    z-index: 999999;
    background: black;
    color: white;
    padding: 8px 12px;
    border-radius: 6px;
    border: 2px solid #333;
    cursor: pointer;
    font-weight: bold;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
}}
#capture-btn:hover {{
    filter: brightness(1.1);
}}

#custom-alert {{
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 9999999;
    background: rgba(0,0,0,0.9);
    color: white;
    padding: 20px 25px;
    border-radius: 10px;
    font-size: 16px;
    text-align: center;
    max-width: 320px;
    opacity: 0;
    transition: opacity 0.4s ease;
}}

#loading-overlay {{
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0,0,0,0.55);
    backdrop-filter: blur(2px);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 9999998;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.25s ease;
}}

.loading-box {{
    background: rgba(20,20,20,0.95);
    padding: 20px 30px;
    border-radius: 12px;
    text-align: center;
    color: white;
    font-size: 18px;
    box-shadow: 0 0 10px rgba(0,0,0,0.6);
}}

.loading-spinner {{
    margin-top: 15px;
    width: 35px;
    height: 35px;
    border: 5px solid #fff;
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 0.9s linear infinite;
}}

@keyframes spin {{
    from {{ transform: rotate(0deg); }}
    to {{ transform: rotate(360deg); }}
}}

@media (max-width: 768px) {{
    #capture-btn {{
        padding: 6px 8px;
        font-size: 12px;
    }}
}}
</style>

<div id="capture-btn"> Obtener Imagen </div>
<div id="custom-alert"></div>

<div id="loading-overlay">
    <div class="loading-box">
        Procesando búsqueda...
        <div class="loading-spinner"></div>
    </div>
</div>

<script>
window.addEventListener('load', function() {{
    var btn = document.getElementById("capture-btn");
    if (!btn) return;

    var map = {nombre_mapa};

    var minZoom = 19;
    var maxZoom = 20;

    window.showAlert = function(msg) {{
        var alertBox = document.getElementById("custom-alert");
        if (!alertBox) return;
        alertBox.innerText = msg;
        alertBox.style.opacity = "1";
        setTimeout(function() {{
            alertBox.style.opacity = "0";
        }}, 2500);
    }}

    window.showLoading = function() {{
        var overlay = document.getElementById("loading-overlay");
        if (!overlay) return;
        overlay.style.opacity = "1";
        overlay.style.pointerEvents = "all";
    }}

    window.hideLoading = function() {{
        var overlay = document.getElementById("loading-overlay");
        if (!overlay) return;
        overlay.style.opacity = "0";
        setTimeout(function() {{
            overlay.style.pointerEvents = "none";
        }}, 300);
    }}

    function updateCaptureButtonColor() {{
        var z = map.getZoom();
        if (z < minZoom) {{
            btn.style.backgroundColor = "#7f1d1d";
            btn.style.borderColor = "#fecaca";
        }} else if (z > maxZoom) {{
            btn.style.backgroundColor = "#92400e";
            btn.style.borderColor = "#fed7aa";
        }} else {{
            btn.style.backgroundColor = "#14532d";
            btn.style.borderColor = "#4ade80";
        }}
    }}

    map.on('zoomend', updateCaptureButtonColor);
    updateCaptureButtonColor();

    btn.onclick = function() {{
        var currentZoom = map.getZoom();

        if (currentZoom < minZoom || currentZoom > maxZoom) {{
            window.showAlert(
                "Zoom no válido (" + currentZoom +
                "). Solo permitido entre " + minZoom + " y " + maxZoom + "."
            );
            return;
        }}

        var mapContainer = document.getElementsByClassName("folium-map")[0];
        if (!mapContainer) {{
            window.showAlert("No se encontró el contenedor del mapa.");
            return;
        }}

        var toHide = document.querySelectorAll(
            '#capture-btn, #search-container, .leaflet-control-layers-toggle, .leaflet-control-zoom, .leaflet-control-attribution, .leaflet-control-scale'
        );

        toHide.forEach(function(el) {{
            el.style.visibility = 'hidden';
        }});

        html2canvas(mapContainer, {{useCORS: true}}).then(function(canvas) {{

            toHide.forEach(function(el) {{
                el.style.visibility = 'visible';
            }});

            // -------------------------------
            // 1. DESCARGAR IMAGEN DEL MAPA
            // -------------------------------
            var imageName = 'mapa_limpio';

            var link = document.createElement('a');
            link.download = imageName + '.png';
            link.href = canvas.toDataURL('image/png');
            link.click();

            // -------------------------------
            // 2. OBTENER METADATOS DEL MAPA
            // -------------------------------
            var center = map.getCenter();
            var bounds = map.getBounds();
            var zoom = map.getZoom();

            var northWest = bounds.getNorthWest();
            var northEast = bounds.getNorthEast();
            var southEast = bounds.getSouthEast();
            var southWest = bounds.getSouthWest();

            // Cálculo de metros por píxel en el centro del mapa
            var centerLatLng = map.getCenter();
            var pointCenter = map.latLngToContainerPoint(centerLatLng);

            var pointRight = L.point(pointCenter.x + 1, pointCenter.y);
            var pointDown = L.point(pointCenter.x, pointCenter.y + 1);

            var latLngRight = map.containerPointToLatLng(pointRight);
            var latLngDown = map.containerPointToLatLng(pointDown);

            var metersPerPixelX = centerLatLng.distanceTo(latLngRight);
            var metersPerPixelY = centerLatLng.distanceTo(latLngDown);

            var metadata = {{
                image_id: imageName,
                width: canvas.width,
                height: canvas.height,
                crs: "EPSG:4326",
                north_up: true,
                zoom: zoom,
                center: {{
                    lat: center.lat,
                    lon: center.lng
                }},
                bbox: {{
                    top_left: {{
                        lat: northWest.lat,
                        lon: northWest.lng
                    }},
                    top_right: {{
                        lat: northEast.lat,
                        lon: northEast.lng
                    }},
                    bottom_right: {{
                        lat: southEast.lat,
                        lon: southEast.lng
                    }},
                    bottom_left: {{
                        lat: southWest.lat,
                        lon: southWest.lng
                    }}
                }},
                meters_per_pixel: {{
                    x: metersPerPixelX,
                    y: metersPerPixelY
                }},
                source: {{
                    map_provider: "Esri World Imagery",
                    capture_date: new Date().toISOString()
                }}
            }};

            // -------------------------------
            // 3. DESCARGAR JSON DE METADATOS
            // -------------------------------
            var metadataBlob = new Blob(
                [JSON.stringify(metadata, null, 4)],
                {{ type: "application/json" }}
            );

            var metadataLink = document.createElement('a');
            metadataLink.download = imageName + '_metadata.json';
            metadataLink.href = URL.createObjectURL(metadataBlob);
            metadataLink.click();

            URL.revokeObjectURL(metadataLink.href);

            window.showAlert("Imagen y metadata descargadas correctamente.");

        }}).catch(function(err) {{

            toHide.forEach(function(el) {{
                el.style.visibility = 'visible';
            }});

            console.error(err);
            window.showAlert("Error al capturar la imagen.");
        }});
    }};
}});
</script>
"""

mapa.get_root().html.add_child(folium.Element(boton_captura))

# ---------------------------------------------------
# BARRA DE BÚSQUEDA + ENTER + LOADING + FLYTO
# ---------------------------------------------------
barra_busqueda = f"""
<style>
#search-container {{
    position: absolute;
    top: 10px;
    left: 575px;
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

@media (max-width: 768px) {{
    #search-container {{
        top: 50px;
        left: 10px;
        max-width: 80vw;
    }}
    #search-input {{
        width: 150px;
        font-size: 12px;
    }}
    #search-btn {{
        padding: 4px 6px;
        font-size: 12px;
    }}
}}
</style>

<div id="search-container">
    <input id="search-input" type="text" placeholder="Buscar dirección..." />
    <button id="search-btn">Buscar</button>
</div>

<script>
window.addEventListener('load', function() {{
    var map = {nombre_mapa};
    var searchMarker = null;

    var btn = document.getElementById("search-btn");
    var input = document.getElementById("search-input");

    if (!btn || !input) {{
        console.error("No se encontró el input o el botón de búsqueda.");
        return;
    }}

    function ejecutarBusqueda() {{
        var query = input.value.trim();

        if (!query) {{
            if (window.showAlert) {{
                window.showAlert("Introduce una dirección.");
            }} else {{
                alert("Introduce una dirección.");
            }}
            return;
        }}

        var url = "http://localhost:8000/geocode?direccion=" + encodeURIComponent(query);

        if (window.showLoading) {{
            window.showLoading();
        }}

        fetch(url)
        .then(function(response) {{
            if (!response.ok) {{
                throw new Error("No se encontró la dirección");
            }}
            return response.json();
        }})
        .then(function(data) {{
            if (window.hideLoading) {{
                window.hideLoading();
            }}

            var lat = data.lat;
            var lon = data.lon;
            var nombre = data.display_name || query;

            if (searchMarker) {{
                map.removeLayer(searchMarker);
            }}

            searchMarker = L.marker([lat, lon]).addTo(map).bindPopup(nombre).openPopup();

            map.flyTo([lat, lon], 19, {{
                animate: true,
                duration: 1.2
            }});
        }})
        .catch(function(error) {{
            console.error(error);

            if (window.hideLoading) {{
                window.hideLoading();
            }}

            if (window.showAlert) {{
                window.showAlert("Error al buscar la dirección");
            }} else {{
                alert("Error al buscar la dirección.");
            }}
        }});
    }}

    btn.addEventListener('click', ejecutarBusqueda);

    input.addEventListener('keydown', function(e) {{
        if (e.key === 'Enter' || e.keyCode === 13) {{
            e.preventDefault();
            ejecutarBusqueda();
        }}
    }});
}});
</script>
"""

mapa.get_root().html.add_child(folium.Element(barra_busqueda))

# ---------------------------------------------------
# GUARDAR MAPA
# ---------------------------------------------------
mapa.save("mapa.html")
print("Mapa guardado como 'mapa.html'")