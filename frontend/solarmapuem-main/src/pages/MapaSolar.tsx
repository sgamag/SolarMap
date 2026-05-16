import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import NavBar from "@/components/NavBar";
import { useAuth } from "@/context/AuthContext";

export default function MapaSolar() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    if (!isAuthenticated) {
      navigate("/login?next=/mapa");
    }
  }, [isAuthenticated, navigate]);

  if (!isAuthenticated) {
    return null;
  }

  const pasos = [
    {
      n: 1,
      title: "Buscar dirección",
      sub: "Escribe la dirección de la vivienda en el buscador que aparece dentro del mapa y pulsa “Buscar”. El mapa se centrará automáticamente en esa ubicación.",
    },
    {
      n: 2,
      title: "Hacer zoom sobre tu vivienda",
      sub: "Acerca o aleja el mapa hasta que la vivienda quede dentro del recuadro verde. Para que funcione correctamente, el zoom debe ser 18 o 19.",
    },
    {
      n: 3,
      title: "Analizar zona",
      sub: "Cuando la vivienda esté bien colocada dentro del recuadro verde, pulsa “Analizar Zona”. El modelo procesará la imagen capturada.",
    },
    {
      n: 4,
      title: "Detectar tejados",
      sub: "El modelo marcará los tejados detectados con un gradiente de color: verde si están orientados al sur (mejor) y rojo si miran al norte.",
    },
    {
      n: 5,
      title: "Pinchar sobre tu tejado",
      sub: "Haz clic sobre el tejado que quieras analizar. Se abrirá una ventana con el mensaje “Tejado seleccionado” y un botón “Analizar”.",
    },
    {
      n: 6,
      title: "Ver análisis",
      sub: "Al pulsar “Analizar”, el tejado se guardará en tu cuenta y accederás al dashboard con el estudio solar completo.",
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      <NavBar />

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* SIDEBAR IZQUIERDO */}
        <aside
          style={{
            width: "360px",
            minWidth: "360px",
            background: "#ffffff",
            borderRight: "1px solid #e5e7eb",
            display: "flex",
            flexDirection: "column",
            padding: "28px 24px",
            overflowY: "auto",
          }}
        >
          <div style={{ marginBottom: "24px" }}>
            <h1 style={{ fontSize: "20px", fontWeight: 800, color: "#111827", marginBottom: "6px" }}>
              Localiza tu tejado
            </h1>
            <p style={{ fontSize: "13px", color: "#6b7280", lineHeight: 1.6 }}>
              Sigue estos pasos para detectar tu tejado y consultar su potencial solar.
            </p>
          </div>

          <div style={{ display: "flex", flexDirection: "column" }}>
            {pasos.map(({ n, title, sub }, i) => (
              <div key={n} style={{ display: "flex", gap: "14px" }}>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                  <div
                    style={{
                      minWidth: "28px",
                      height: "28px",
                      borderRadius: "50%",
                      background: "#f59e0b",
                      color: "white",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontWeight: "bold",
                      fontSize: "13px",
                    }}
                  >
                    {n}
                  </div>
                  {i < pasos.length - 1 && (
                    <div
                      style={{
                        width: "2px",
                        flex: 1,
                        minHeight: "22px",
                        background: "#fde68a",
                        margin: "4px 0",
                      }}
                    />
                  )}
                </div>

                <div style={{ paddingBottom: i < pasos.length - 1 ? "20px" : "0", flex: 1 }}>
                  <div
                    style={{
                      fontWeight: 700,
                      fontSize: "14px",
                      marginBottom: "4px",
                      color: "#111827",
                    }}
                  >
                    {title}
                  </div>
                  <div style={{ fontSize: "12px", color: "#4b5563", lineHeight: 1.5 }}>{sub}</div>
                </div>
              </div>
            ))}
          </div>

          <div style={{ flex: 1 }} />

          <div
            style={{
              marginTop: "24px",
              background: "#fefce8",
              border: "1px solid #fde68a",
              borderRadius: "10px",
              padding: "14px",
              fontSize: "12px",
              color: "#92400e",
            }}
          >
            <div style={{ fontWeight: 700, marginBottom: "8px" }}>💡 Cómo usar el mapa</div>
            <ul style={{ paddingLeft: "16px", margin: 0, lineHeight: 2 }}>
              <li>El recuadro verde marca la zona que se analizará.</li>
              <li>El zoom válido es 18 o 19.</li>
              <li>Los tejados se colorean por orientación (verde=sur, rojo=norte).</li>
              <li>Haz clic en un tejado para seleccionarlo.</li>
            </ul>
          </div>
        </aside>

        {/* MAPA A LA DERECHA */}
        <div style={{ flex: 1, position: "relative" }}>
          <iframe
            src="/mapa.html"
            title="Mapa Solar"
            style={{
              width: "100%",
              height: "100%",
              border: "none",
              display: "block",
            }}
          />
        </div>
      </div>
    </div>
  );
}
