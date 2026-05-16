import { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import NavBar from "@/components/NavBar";

// ─── Configuracion del informe Power BI ─────────────────────────────────────
const REPORT_ID = "eb17de9c-61c6-4b26-884d-17a767fcfd71";
const TENANT_ID = "032115c7-35fe-4637-b2c3-d0a42906ba7b";
const URL_BASE  = `https://app.powerbi.com/reportEmbed?reportId=${REPORT_ID}&autoAuth=true&ctid=${TENANT_ID}`;

// Tabla y columna del modelo (case-sensitive!)
const TABLA_TEJADOS = "Tejado_detectado_BD";
const COLUMNA_ID    = "id_tejado";

type TejadoActual = {
  id_tejado: number;
  id_zona?: string;
  id_caracteristica?: number;
  area_total_bruta_m2?: number;
  area_util_m2?: number;
  orientacion_principal?: string;
  potencial_final?: number | null;
};

export default function AnalisisResumen() {
  const navigate = useNavigate();
  const [tejado, setTejado] = useState<TejadoActual | null>(null);

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("solarmap.tejado_actual");
      if (raw) setTejado(JSON.parse(raw));
    } catch {
      // ignore
    }
  }, []);

  // Construir URL final del informe con filtro por id_tejado
  const urlFinal = useMemo(() => {
    if (!tejado?.id_tejado) return URL_BASE;
    // Sintaxis: filter=Tabla/Columna eq VALOR
    const filtro = `${TABLA_TEJADOS}/${COLUMNA_ID} eq ${tejado.id_tejado}`;
    return `${URL_BASE}&filter=${encodeURIComponent(filtro)}`;
  }, [tejado]);

  // ── Sin tejado guardado: pantalla informativa ──
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
            <button
              onClick={() => navigate("/mapa")}
              style={{
                background: "#f59e0b",
                color: "white",
                border: "none",
                borderRadius: "10px",
                padding: "12px 24px",
                fontWeight: 700,
                fontSize: "14px",
                cursor: "pointer",
                fontFamily: "inherit",
              }}
            >
              Ir al mapa
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Render con banner + dashboard filtrado ──
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      <NavBar />

      {/* Banner con info del tejado analizado */}
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

      {/* Power BI embebido por iframe normal */}
      <div style={{ flex: 1, position: "relative", background: "#f3f4f6" }}>
        <iframe
          title="Dashboard Power BI"
          src={urlFinal}
          style={{ width: "100%", height: "100%", border: "none" }}
          allowFullScreen
        />
      </div>
    </div>
  );
}
