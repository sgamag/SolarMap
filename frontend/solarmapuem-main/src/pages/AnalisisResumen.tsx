import { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { FileDown, Users, Heart } from "lucide-react";
import NavBar from "@/components/NavBar";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";

// ─── Configuración Power BI ───────────────────────────────────────────────────
const REPORT_ID = "eb17de9c-61c6-4b26-884d-17a767fcfd71";
const TENANT_ID = "032115c7-35fe-4637-b2c3-d0a42906ba7b";

// Disimular Power BI: ocultar panel de filtros y pestañas de páginas
const URL_BASE  =
  `https://app.powerbi.com/reportEmbed?reportId=${REPORT_ID}` +
  `&autoAuth=true&ctid=${TENANT_ID}` +
  `&filterPaneEnabled=false&navContentPaneEnabled=false`;

const PBI_TABLE = "Tejado_detectado_BD";
const PBI_FIELD = "id_tejado";

// ─── URL base de la API ───────────────────────────────────────────────────────
const API_BASE = "http://localhost:8002/api";

type TejadoActual = {
  id_tejado: number;
  id_zona?: string;
  area_util_m2?: number;
  orientacion_principal?: string;
  latitud?: number;
  longitud?: number;
};

function buildEmbedUrl(idTejado: number | null): string {
  if (!idTejado) return URL_BASE;
  const filter = `${PBI_TABLE}/${PBI_FIELD} eq ${idTejado}`;
  return `${URL_BASE}&filter=${encodeURIComponent(filter)}`;
}

// Reverse geocoding: a partir de lat/lon obtiene la direccion textual
async function reverseGeocode(lat: number, lon: number): Promise<string> {
  try {
    const url = `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&zoom=18&addressdetails=1`;
    const res = await fetch(url, { headers: { "Accept-Language": "es" } });
    if (!res.ok) throw new Error("Reverse geocoding error");
    const data = await res.json();
    // display_name es la direccion completa, pero a veces es muy larga.
    // Intentamos construir una version mas limpia.
    if (data.address) {
      const a = data.address;
      const parts = [];
      if (a.road)         parts.push(a.road + (a.house_number ? ` ${a.house_number}` : ""));
      if (a.suburb)       parts.push(a.suburb);
      if (a.city || a.town || a.village) parts.push(a.city || a.town || a.village);
      if (parts.length > 0) return parts.join(", ");
    }
    return data.display_name || `Lat ${lat.toFixed(4)}, Lon ${lon.toFixed(4)}`;
  } catch {
    return `Lat ${lat.toFixed(4)}, Lon ${lon.toFixed(4)}`;
  }
}

export default function AnalisisResumen() {
  const navigate = useNavigate();
  const { user, saveAddress } = useAuth();
  const [tejado, setTejado]       = useState<TejadoActual | null>(null);
  const [loaded, setLoaded]       = useState(false);
  const [generando, setGenerando] = useState(false);
  const [esFavorito, setEsFavorito] = useState(false);

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("solarmap.tejado_actual");
      if (raw) {
        const t = JSON.parse(raw);
        setTejado(t);
      }
    } catch { /* ignore */ }
  }, []);

  // Comprueba si este tejado ya esta guardado en favoritos del usuario
  useEffect(() => {
    if (!tejado || !user) return;
    const yaGuardado = (user.savedAddresses ?? []).some(
      (a) => a.roofId === String(tejado.id_tejado)
    );
    setEsFavorito(yaGuardado);
  }, [tejado, user]);

  const embedUrl = useMemo(
    () => buildEmbedUrl(tejado?.id_tejado ?? null),
    [tejado]
  );

  const handleGenerarInforme = async () => {
    if (!tejado) return;
    setGenerando(true);
    try {
      const res = await fetch(`${API_BASE}/informe/${tejado.id_tejado}`);
      if (!res.ok) {
        const errText = await res.text().catch(() => "");
        throw new Error(`Error ${res.status}: ${errText}`);
      }
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      a.download = `informe_tejado_${tejado.id_tejado}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Informe descargado correctamente");
    } catch (err) {
      toast.error("No se pudo generar el informe. Inténtalo de nuevo.");
      console.error("Error generando informe:", err);
    } finally {
      setGenerando(false);
    }
  };

  const handleFavorito = async () => {
    if (!tejado || !user) return;
    if (esFavorito) {
      toast("Este tejado ya está en tus favoritos");
      return;
    }
    // Geocodificacion inversa para obtener la direccion legible
    const lat = tejado.latitud;
    const lon = tejado.longitud;
    let direccion = `Tejado #${tejado.id_tejado}`;
    if (lat !== undefined && lon !== undefined) {
      direccion = await reverseGeocode(lat, lon);
    }
    saveAddress(direccion, String(tejado.id_tejado));
    setEsFavorito(true);
    toast.success("Tejado marcado como favorito");
  };

  // ── Sin tejado: pantalla informativa ──
  if (!tejado) {
    return (
      <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
        <NavBar />
        <div
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "#f9fafb",
            padding: "40px",
          }}
        >
          <div
            style={{
              maxWidth: "440px",
              background: "white",
              border: "1px solid #e5e7eb",
              borderRadius: "16px",
              padding: "32px",
              textAlign: "center",
              boxShadow: "0 4px 14px rgba(0,0,0,0.06)",
            }}
          >
            <div style={{ fontSize: "44px", marginBottom: "16px" }}>🛰️</div>
            <h2 style={{ fontSize: "22px", fontWeight: 800, color: "#111827", marginBottom: "10px" }}>
              No has analizado ningún tejado todavía
            </h2>
            <p style={{ fontSize: "14px", color: "#6b7280", lineHeight: 1.6, marginBottom: "24px" }}>
              Para ver tu análisis personalizado, localiza tu tejado en el mapa,
              selecciónalo y pulsa <strong>Analizar</strong>.
            </p>
            <Button
              onClick={() => navigate("/mapa")}
              className="bg-[#F5A623] hover:bg-[#e09510] text-white font-semibold rounded-full px-6 py-3 shadow-lg"
            >
              Ir al mapa
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // ── Dashboard filtrado ──
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      <NavBar />

      {/* Contenedor del iframe + botones flotantes */}
      <div style={{ flex: 1, position: "relative", background: "#f3f4f6" }}>

        {/* Loader */}
        {!loaded && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              zIndex: 10,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: "12px",
              background: "#ffffff",
            }}
          >
            <div
              style={{
                width: "32px",
                height: "32px",
                border: "4px solid #f59e0b",
                borderTopColor: "transparent",
                borderRadius: "50%",
                animation: "spin 0.8s linear infinite",
              }}
            />
            <span style={{ fontSize: "13px", color: "#6b7280" }}>Cargando análisis solar…</span>
            <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
          </div>
        )}

        {/* iframe Power BI */}
        <iframe
          title="Dashboard Power BI"
          src={embedUrl}
          style={{ width: "100%", height: "100%", border: "none", display: "block" }}
          allowFullScreen
          onLoad={() => setLoaded(true)}
        />

        {/* Botón Corazón "Me gusta" — ARRIBA DERECHA */}
        <div style={{ position: "absolute", top: "16px", right: "16px", zIndex: 20 }}>
          <button
            onClick={handleFavorito}
            title={esFavorito ? "Tejado en favoritos" : "Marcar como favorito"}
            style={{
              width: "44px",
              height: "44px",
              borderRadius: "50%",
              border: "none",
              background: "white",
              boxShadow: "0 4px 12px rgba(0,0,0,0.18)",
              cursor: esFavorito ? "default" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "transform 0.15s",
            }}
            onMouseEnter={(e) => { if (!esFavorito) e.currentTarget.style.transform = "scale(1.08)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.transform = "scale(1)"; }}
          >
            <Heart
              className="h-5 w-5"
              style={{
                color: esFavorito ? "#ef4444" : "#9ca3af",
                fill: esFavorito ? "#ef4444" : "none",
                transition: "color 0.2s, fill 0.2s",
              }}
            />
          </button>
        </div>

        {/* Botón Contactar Instaladoras — ABAJO IZQUIERDA */}
        <div style={{ position: "absolute", bottom: "24px", left: "24px", zIndex: 20 }}>
          <Button
            onClick={() => navigate("/analisis/instaladoras")}
            className="bg-[#F5A623] hover:bg-[#e09510] text-white font-semibold rounded-full px-6 py-3 shadow-lg flex items-center gap-2 transition-colors duration-200"
          >
            <Users className="h-4 w-4" />
            Contactar instaladoras
          </Button>
        </div>

        {/* Botón Generar Informe — ABAJO DERECHA */}
        <div style={{ position: "absolute", bottom: "24px", right: "24px", zIndex: 20 }}>
          <Button
            onClick={handleGenerarInforme}
            disabled={generando}
            className="bg-[#F5A623] hover:bg-[#e09510] text-white font-semibold rounded-full px-6 py-3 shadow-lg flex items-center gap-2 transition-colors duration-200 disabled:opacity-60"
          >
            <FileDown className="h-4 w-4" />
            {generando ? "Generando..." : "Generar informe"}
          </Button>
        </div>

      </div>
    </div>
  );
}
