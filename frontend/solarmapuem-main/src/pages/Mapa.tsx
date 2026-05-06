import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MapContainer, TileLayer, Rectangle, Polygon, Popup, useMap, useMapEvents } from "react-leaflet";
import { Search } from "lucide-react";
import PageLayout from "@/components/PageLayout";
import StepIndicator, { Step } from "@/components/StepIndicator";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  MADRID_CENTER,
  mockTiles,
  mockRoofs,
  potentialColor,
  tileBounds,
} from "@/data/mockData";
import { toast } from "sonner";

function MapTelemetry({ onUpdate }: { onUpdate: (lat: number, lng: number, zoom: number) => void }) {
  const map = useMap();
  useMapEvents({
    moveend: () => {
      const c = map.getCenter();
      onUpdate(c.lat, c.lng, map.getZoom());
    },
    zoomend: () => {
      const c = map.getCenter();
      onUpdate(c.lat, c.lng, map.getZoom());
    },
  });
  return null;
}

export default function Mapa() {
  const navigate = useNavigate();
  const [address, setAddress] = useState("");
  const [activeTile, setActiveTile] = useState<string | null>(null);
  const [coords, setCoords] = useState({ lat: MADRID_CENTER[0], lng: MADRID_CENTER[1], zoom: 11 });
  const [stepIndex, setStepIndex] = useState(0);

  const steps: Step[] = useMemo(
    () => [
      { label: "Buscar dirección", status: stepIndex > 0 ? "completado" : stepIndex === 0 ? "activo" : "pendiente" },
      { label: "Obtener imagen aérea", hint: "Pendiente — conectar PNOA", status: stepIndex > 1 ? "completado" : stepIndex === 1 ? "activo" : "pendiente" },
      { label: "Seleccionar tejado", hint: "Pendiente — conectar modelo de detección", status: stepIndex > 2 ? "completado" : stepIndex === 2 ? "activo" : "pendiente" },
      { label: "Ver análisis", status: stepIndex > 3 ? "completado" : stepIndex === 3 ? "activo" : "pendiente" },
    ],
    [stepIndex]
  );

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!address.trim()) return;
    // TODO: fetch('/api/geocoding?address=...')
    toast(`Geocodificación pendiente · "${address}"`);
    setStepIndex(Math.max(stepIndex, 1));
  };

  const handleObtenerImagen = () => {
    // TODO: fetch('/api/imagery?lat=...&lng=...')
    toast("Obtención de imagen aérea pendiente de conexión PNOA");
    setStepIndex(Math.max(stepIndex, 2));
  };

  return (
    <PageLayout withFooter={false}>
      <div className="flex flex-col lg:flex-row" style={{ height: "calc(100vh - 64px - 36px)" }}>
        {/* SIDEBAR */}
        <aside className="w-full lg:w-[380px] shrink-0 border-r border-border bg-background overflow-y-auto">
          <div className="p-6 space-y-6">
            <div>
              <h1 className="text-2xl font-extrabold text-primary mb-2">Localiza tu tejado</h1>
              <p className="text-sm text-muted-foreground">
                Busca una dirección o explora los tiles del área metropolitana de Madrid.
              </p>
            </div>

            <form onSubmit={handleSearch} className="flex gap-2">
              <Input
                placeholder="Calle, número, ciudad…"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
              />
              <Button type="submit" variant="coral">
                <Search className="h-4 w-4" /> Buscar
              </Button>
            </form>

            <StepIndicator steps={steps} />

            <div className="flex flex-col gap-2">
              <Button variant="coral" onClick={handleObtenerImagen}>
                Obtener imagen
              </Button>
              <Button variant="outline" onClick={() => navigate("/analisis/resumen?address=" + encodeURIComponent("Calle Guazalate, 2 · Villaviciosa de Odón"))}>
                Ver análisis demo
              </Button>
            </div>

            <div className="rounded-xl border border-border bg-background-alt p-4 text-xs space-y-1.5">
              <div className="font-bold text-foreground uppercase tracking-wider mb-2">Telemetría</div>
              <div className="flex justify-between"><span className="text-muted-foreground">Fuente:</span><span className="font-mono">OpenStreetMap</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Centro:</span><span className="font-mono">{coords.lat.toFixed(3)}, {coords.lng.toFixed(3)}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Tile activo:</span><span className="font-mono">{activeTile ?? "—"}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Zoom:</span><span className="font-mono">{coords.zoom}</span></div>
            </div>
          </div>
        </aside>

        {/* MAP */}
        <div className="relative flex-1 min-h-[500px]">
          <MapContainer
            center={MADRID_CENTER}
            zoom={11}
            scrollWheelZoom
            style={{ height: "100%", width: "100%" }}
          >
            <TileLayer
              attribution='&copy; OpenStreetMap &copy; CARTO'
              url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
            />
            <MapTelemetry onUpdate={(lat, lng, zoom) => setCoords({ lat, lng, zoom })} />

            {mockTiles.map((tile) => {
              const color = potentialColor(tile.potential);
              return (
                <Rectangle
                  key={tile.id}
                  bounds={tileBounds(tile)}
                  pathOptions={{
                    color,
                    weight: 1,
                    fillOpacity: activeTile === tile.id ? 0.5 : 0.25,
                  }}
                  eventHandlers={{
                    click: () => setActiveTile(tile.id),
                  }}
                >
                  <Popup>
                    <div className="text-sm">
                      <div className="font-bold mb-1">{tile.id}</div>
                      <div>Potencial mock: <strong>{tile.potential.toFixed(2)}</strong></div>
                      <div className="text-xs text-gray-500 mt-1">// TODO: /api/tiles</div>
                    </div>
                  </Popup>
                </Rectangle>
              );
            })}

            {mockRoofs.map((roof) => (
              <Polygon
                key={roof.id}
                positions={roof.coords}
                pathOptions={{
                  color: potentialColor(roof.potential),
                  fillOpacity: 0.7,
                  weight: 2,
                }}
              >
                <Popup>
                  <div className="text-sm space-y-1 min-w-[180px]">
                    <div className="font-bold">{roof.id}</div>
                    <div>Área: <strong>{roof.area} m²</strong></div>
                    <div>Potencial: <strong>{roof.potential.toFixed(2)}</strong></div>
                    <button
                      className="mt-2 w-full bg-[#E8970A] text-white rounded-md px-3 py-1.5 text-sm font-medium"
                      onClick={() => navigate(`/analisis/resumen?roof_id=${roof.id}&address=${encodeURIComponent("Calle Guazalate, 2 · Villaviciosa de Odón")}`)}
                    >
                      Ver análisis
                    </button>
                  </div>
                </Popup>
              </Polygon>
            ))}
          </MapContainer>

          {/* Coords overlay */}
          <div className="absolute top-4 right-4 z-[400] bg-background/95 backdrop-blur border border-border rounded-lg px-3 py-2 text-xs font-mono shadow-md">
            {coords.lat.toFixed(4)}, {coords.lng.toFixed(4)}
          </div>

          {/* Legend */}
          <div className="absolute bottom-4 left-4 z-[400] bg-background/95 backdrop-blur border border-border rounded-lg p-3 text-xs shadow-md space-y-1.5">
            <div className="font-bold uppercase tracking-wider mb-1.5">Potencial solar</div>
            <div className="flex items-center gap-2"><span className="h-3 w-3 rounded-sm" style={{ backgroundColor: "#2D6FE8" }} /> Bajo (0–0.4)</div>
            <div className="flex items-center gap-2"><span className="h-3 w-3 rounded-sm" style={{ backgroundColor: "#F5B400" }} /> Medio (0.4–0.65)</div>
            <div className="flex items-center gap-2"><span className="h-3 w-3 rounded-sm" style={{ backgroundColor: "#E8970A" }} /> Alto (0.65–1.0)</div>
          </div>

          {/* Sim chip */}
          <div className="absolute bottom-4 right-4 z-[400] bg-primary text-primary-foreground rounded-full px-3 py-1.5 text-xs font-semibold shadow-md">
            Datos simulados
          </div>
        </div>
      </div>
    </PageLayout>
  );
}
