import { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Users } from "lucide-react";
import NavBar from "@/components/NavBar";
import { Button } from "@/components/ui/button";

// ─── Configuracion del informe Power BI ─────────────────────────────────────
const REPORT_ID = "eb17de9c-61c6-4b26-884d-17a767fcfd71";
const TENANT_ID = "032115c7-35fe-4637-b2c3-d0a42906ba7b";
const URL_BASE  = `https://app.powerbi.com/reportEmbed?reportId=${REPORT_ID}&autoAuth=true&ctid=${TENANT_ID}`;

const PBI_TABLE = "Tejado_detectado_BD";
const PBI_FIELD = "id_tejado";

type TejadoActual = {
  id_tejado: number;
  id_zona?: string;
  id_caracteristica?: number;
  area_total_bruta_m2?: number;
  area_util_m2?: number;
  orientacion_principal?: string;
  potencial_final?: number | null;
};

function buildEmbedUrl(idTejado: number | null): string {
  if (!idTejado) return URL_BASE;
  const filter = `${PBI_TABLE}/${PBI_FIELD} eq ${idTejado}`;
  return `${URL_BASE}&filter=${encodeURIComponent(filter)}`;
}

export default function AnalisisResumen() {
  const navigate = useNavigate();
  const [tejado, setTejado] = useState<TejadoActual | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("solarmap.tejado_actual");
      if (raw) setTejado(JSON.parse(raw));
    } catch {
      // ignore
    }
  }, []);

  const embedUrl = useMemo(
    () => buildEmbedUrl(tejado?.id_tejado ?? null),
    [tejado]
  );

  // ── Sin tejado guardado ──
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
              Para ver tu análisis personalizado, primero localiza tu tejado en el mapa,
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

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      <NavBar />

      {/* Banner con info del tejado */}
      <div
        style={{
          background: "linear-gradient(90deg, #fef3c7 0%, #fef9c3 100%)",
          borderBottom: "1px solid #fde68a",
          padding: "12px 24px",
          display: "flex",
          gap: "24px",
          alignItems: "center",
          flexWrap: "wrap",
          fontSize: "13px",
          color: "#92400e",
        }}
      >
        <strong style={{ fontSize: "14px" }}>📊 Análisis del tejado #{tejado.id_tejado}</strong>
        {tejado.orientacion_principal && (
          <span>Orientación: <strong>{tejado.orientacion_principal}</strong></span>
        )}
        {tejado.area_util_m2 != null && (
          <span>Área útil: <strong>{tejado.area_util_m2} m²</strong></span>
        )}
        {tejado.id_zona && (
          <span>Zona: <strong>{tejado.id_zona}</strong></span>
        )}
      </div>

      {/* Contenedor del dashboard a pantalla completa */}
      <div style={{ flex: 1, position: "relative", background: "#f3f4f6" }}>
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

        <iframe
          title="Dashboard Power BI"
          src={embedUrl}
          style={{ width: "100%", height: "100%", border: "none", display: "block" }}
          allowFullScreen
          onLoad={() => setLoaded(true)}
        />

        {/* Botón volver - abajo izquierda */}
        <div style={{ position: "absolute", bottom: "24px", left: "24px", zIndex: 20 }}>
          <Button
            onClick={() => navigate(-1)}
            className="
              bg-[#F5A623] hover:bg-[#e09510]
              text-white font-semibold
              rounded-full
              px-6 py-3
              shadow-lg
              flex items-center gap-2
              transition-colors duration-200
            "
          >
            <ArrowLeft className="h-4 w-4" />
            Volver
          </Button>
        </div>

        {/* Botón contactar instaladoras - abajo derecha */}
        <div style={{ position: "absolute", bottom: "24px", right: "24px", zIndex: 20 }}>
          <Button
            onClick={() => navigate("/analisis/proveedores")}
            className="
              bg-[#F5A623] hover:bg-[#e09510]
              text-white font-semibold
              rounded-full
              px-6 py-3
              shadow-lg
              flex items-center gap-2
              transition-colors duration-200
            "
          >
            <Users className="h-4 w-4" />
            Contactar instaladoras
          </Button>
        </div>
      </div>
    </div>
  );
}
