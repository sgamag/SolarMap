import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import NavBar from "@/components/NavBar";

type Step = "buscar" | "zoom" | "analizar" | "resultado";
const ORDEN: Step[] = ["buscar", "zoom", "analizar", "resultado"];

export default function MapaSolar() {
  const navigate = useNavigate();
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const [direccion, setDireccion] = useState("");
  const [zoomValido, setZoomValido] = useState(false);
  const [analizando, setAnalizando] = useState(false);
  const [tejadosDetectados, setTejadosDetectados] = useState(false);
  const [stepActivo, setStepActivo] = useState<Step>("buscar");

  // Recibe mensajes del iframe
  useEffect(() => {
    const handler = (event: MessageEvent) => {
      // Actualización de zoom
      if (event.data?.type === "zoom_update") {
        const valido: boolean = event.data.valido;
        setZoomValido(valido);
        // Avanza al paso de analizar si el zoom es válido y ya se buscó dirección
        setStepActivo(prev => {
          if (valido && (prev === "zoom" || prev === "buscar")) return "analizar";
          if (!valido && prev === "analizar") return "zoom";
          return prev;
        });
      }
      // Inicio del análisis
      if (event.data === "analizando_inicio") {
        setAnalizando(true);
      }
      // Resultado del análisis
      if (event.data?.type === "tejados_resultado") {
        setAnalizando(false);
        if (event.data.cantidad > 0) {
          setTejadosDetectados(true);
          setStepActivo("resultado");
        }
      }
    };
    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, []);

  const handleBuscar = () => {
    if (!direccion.trim()) return;
    iframeRef.current?.contentWindow?.postMessage({ type: "buscar", query: direccion }, "*");
    setStepActivo("zoom");
  };

  const handleAnalizar = () => {
    if (!zoomValido || analizando) return;
    iframeRef.current?.contentWindow?.postMessage("trigger_analizar", "*");
  };

  const esCompletado = (id: Step) =>
    ORDEN.indexOf(id) < ORDEN.indexOf(stepActivo);

  const steps: { id: Step; n: number; title: string; sub: string }[] = [
    { id: "buscar",    n: 1, title: "Buscar dirección",  sub: "Introduce una dirección para centrar el mapa" },
    { id: "zoom",      n: 2, title: "Ajustar zoom",       sub: zoomValido ? "Zoom correcto ✓" : "Acerca o aleja el mapa hasta que el indicador sea verde" },
    { id: "analizar",  n: 3, title: "Analizar tejados",   sub: analizando ? "Analizando..." : "Pulsa el botón para detectar tejados con IA" },
    { id: "resultado", n: 4, title: "Ver análisis",       sub: "Selecciona un tejado detectado en el mapa" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      <NavBar />

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>

        {/* ── SIDEBAR ── */}
        <aside style={{
          width: "360px", minWidth: "360px",
          background: "#ffffff", borderRight: "1px solid #e5e7eb",
          display: "flex", flexDirection: "column",
          padding: "28px 24px", overflowY: "auto",
        }}>

          <div style={{ marginBottom: "24px" }}>
            <h1 style={{ fontSize: "20px", fontWeight: "800", color: "#111827", marginBottom: "6px" }}>
              Localiza tu tejado
            </h1>
            <p style={{ fontSize: "13px", color: "#6b7280", lineHeight: "1.6" }}>
              Sigue los pasos para detectar y analizar el potencial solar de tu tejado.
            </p>
          </div>

          {/* Pasos */}
          <div style={{ display: "flex", flexDirection: "column" }}>
            {steps.map(({ id, n, title, sub }, i) => {
              const activo = stepActivo === id;
              const completado = esCompletado(id);
              const pendiente = !activo && !completado;

              return (
                <div key={id} style={{ display: "flex", gap: "14px" }}>

                  {/* Círculo + línea */}
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                    <div style={{
                      minWidth: "28px", height: "28px", borderRadius: "50%",
                      background: completado ? "#f59e0b" : activo ? "#111827" : "#e5e7eb",
                      color: completado || activo ? "white" : "#9ca3af",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontWeight: "bold", fontSize: "13px",
                      transition: "all 0.3s",
                    }}>
                      {completado ? "✓" : n}
                    </div>
                    {i < steps.length - 1 && (
                      <div style={{
                        width: "2px", flex: 1, minHeight: "20px",
                        background: completado ? "#f59e0b" : "#e5e7eb",
                        margin: "4px 0", transition: "background 0.3s",
                      }} />
                    )}
                  </div>

                  {/* Contenido */}
                  <div style={{ paddingBottom: i < steps.length - 1 ? "20px" : "0", flex: 1 }}>
                    <div style={{
                      fontWeight: "700", fontSize: "14px", marginBottom: "4px",
                      color: activo ? "#111827" : completado ? "#f59e0b" : "#9ca3af",
                      transition: "color 0.3s",
                    }}>
                      {title}
                    </div>
                    <div style={{ fontSize: "12px", color: pendiente ? "#9ca3af" : "#4b5563", lineHeight: "1.5" }}>
                      {sub}
                    </div>

                    {/* Paso 1: buscador */}
                    {id === "buscar" && activo && (
                      <div style={{ display: "flex", gap: "8px", marginTop: "12px" }}>
                        <input
                          value={direccion}
                          onChange={e => setDireccion(e.target.value)}
                          onKeyDown={e => e.key === "Enter" && handleBuscar()}
                          placeholder="Ej: Calle Mayor, Madrid..."
                          style={{
                            flex: 1, padding: "9px 12px",
                            border: "1px solid #d1d5db", borderRadius: "8px",
                            fontSize: "13px", outline: "none", fontFamily: "inherit",
                          }}
                        />
                        <button onClick={handleBuscar} style={{
                          background: "#111827", color: "white", border: "none",
                          borderRadius: "8px", padding: "9px 14px",
                          fontWeight: "600", fontSize: "13px",
                          cursor: "pointer", fontFamily: "inherit",
                        }}>
                          Buscar
                        </button>
                      </div>
                    )}

                    {/* Paso 2: indicador zoom */}
                    {id === "zoom" && !pendiente && (
                      <div style={{
                        marginTop: "10px",
                        display: "inline-flex", alignItems: "center", gap: "6px",
                        background: zoomValido ? "#dcfce7" : "#fef9c3",
                        border: `1px solid ${zoomValido ? "#86efac" : "#fde68a"}`,
                        borderRadius: "20px", padding: "5px 12px",
                        fontSize: "12px", fontWeight: "600",
                        color: zoomValido ? "#166534" : "#92400e",
                        transition: "all 0.3s",
                      }}>
                        <span style={{
                          width: "8px", height: "8px", borderRadius: "50%",
                          background: zoomValido ? "#22c55e" : "#f59e0b",
                          display: "inline-block",
                        }} />
                        {zoomValido ? "Zoom válido — listo para analizar" : "Ajusta el zoom del mapa"}
                      </div>
                    )}

                    {/* Paso 3: botón analizar */}
                    {id === "analizar" && activo && (
                      <button
                        onClick={handleAnalizar}
                        disabled={!zoomValido || analizando}
                        style={{
                          marginTop: "12px", width: "100%",
                          background: zoomValido && !analizando ? "#14532d" : "#e5e7eb",
                          color: zoomValido && !analizando ? "white" : "#9ca3af",
                          border: zoomValido && !analizando ? "2px solid #4ade80" : "2px solid transparent",
                          borderRadius: "10px", padding: "12px 20px",
                          fontWeight: "700", fontSize: "14px",
                          cursor: zoomValido && !analizando ? "pointer" : "not-allowed",
                          transition: "all 0.3s", fontFamily: "inherit",
                        }}
                      >
                        {analizando ? "Analizando..." : "Analizar Zona"}
                      </button>
                    )}

                    {/* Paso 4: botón análisis solar */}
                    {id === "resultado" && tejadosDetectados && (
                      <button
                        onClick={() => navigate("/analisis/resumen")}
                        style={{
                          marginTop: "12px", width: "100%",
                          background: "#f59e0b", color: "white",
                          border: "none", borderRadius: "10px",
                          padding: "12px 20px", fontWeight: "700", fontSize: "14px",
                          cursor: "pointer", fontFamily: "inherit",
                          boxShadow: "0 2px 8px rgba(245,158,11,0.35)",
                          transition: "background 0.2s",
                        }}
                        onMouseEnter={e => (e.currentTarget.style.background = "#d97706")}
                        onMouseLeave={e => (e.currentTarget.style.background = "#f59e0b")}
                      >
                        Análisis Solar
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Espaciador */}
          <div style={{ flex: 1 }} />

          {/* Cómo usar */}
          <div style={{
            marginTop: "24px", background: "#fefce8",
            border: "1px solid #fde68a", borderRadius: "10px",
            padding: "14px", fontSize: "12px", color: "#92400e",
          }}>
            <div style={{ fontWeight: "700", marginBottom: "8px" }}>💡 Cómo usar el mapa</div>
            <ul style={{ paddingLeft: "16px", margin: 0, lineHeight: "2" }}>
              <li>El indicador se pone <strong style={{ color: "#14532d" }}>verde</strong> cuando el zoom es válido</li>
              <li>Pulsa <strong>Analizar Zona</strong> para detectar tejados</li>
              <li>Haz clic en un tejado para ver su info</li>
            </ul>
          </div>

        </aside>

        {/* ── MAPA ── */}
        <div style={{ flex: 1, position: "relative" }}>
          <iframe
            ref={iframeRef}
            src="/mapa.html"
            title="Mapa Solar"
            style={{ width: "100%", height: "100%", border: "none" }}
          />
        </div>

      </div>
    </div>
  );
}