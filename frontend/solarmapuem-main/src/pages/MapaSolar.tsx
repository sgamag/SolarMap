import NavBar from "@/components/NavBar";

export default function MapaSolar() {
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
    title: "Obtener imagen",
    sub: "Cuando la vivienda esté bien colocada dentro del recuadro verde, pulsa “Obtener Imagen”. La aplicación capturará esa zona del mapa para analizarla.",
  },
  {
    n: 4,
    title: "Detectar tejados",
    sub: "El modelo de inteligencia artificial procesará la imagen capturada y marcará en color morado los tejados detectados.",
  },
  {
    n: 5,
    title: "Pinchar sobre tu tejado",
    sub: "Haz clic sobre el tejado morado que quieras analizar. Se abrirá una ventana con información básica como el área y la orientación.",
  },
  {
    n: 6,
    title: "Ver análisis",
    sub: "Dentro de la ventana del tejado seleccionado, pulsa “Ver análisis” para consultar el estudio solar completo de esa superficie.",
  },
];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      <NavBar />

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
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
            <h1
              style={{
                fontSize: "20px",
                fontWeight: "800",
                color: "#111827",
                marginBottom: "6px",
              }}
            >
              Localiza tu tejado
            </h1>

            <p
              style={{
                fontSize: "13px",
                color: "#6b7280",
                lineHeight: "1.6",
              }}
            >
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
                      fontWeight: "700",
                      fontSize: "14px",
                      marginBottom: "4px",
                      color: "#111827",
                    }}
                  >
                    {title}
                  </div>

                  <div
                    style={{
                      fontSize: "12px",
                      color: "#4b5563",
                      lineHeight: "1.5",
                    }}
                  >
                    {sub}
                  </div>
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
            <div style={{ fontWeight: "700", marginBottom: "8px" }}>💡 Cómo usar el mapa</div>

            <ul style={{ paddingLeft: "16px", margin: 0, lineHeight: "2" }}>
              <li>El recuadro verde marca la zona que se analizará.</li>
              <li>El zoom válido es 18 o 19.</li>
              <li>Los tejados detectados aparecerán en morado.</li>
              <li>Haz clic en un tejado para ver su información.</li>
            </ul>
          </div>
        </aside>

        <div style={{ flex: 1, position: "relative" }}>
          <iframe
            src="/mapa.html?v=2"
            title="Mapa Solar"
            style={{ width: "100%", height: "100%", border: "none" }}
          />
        </div>
      </div>
    </div>
  );
}