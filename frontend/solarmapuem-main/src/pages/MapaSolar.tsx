export default function MapaSolar() {
  return (
    <div style={{ width: "100%", height: "100vh", position: "relative" }}>

      {/* BOTÓN VOLVER */}
      <a
        href="/"
        style={{
          position: "absolute",
          top: "20px",
          left: "20px",
          zIndex: 999999,
          background: "#111827",
          color: "white",
          padding: "10px 16px",
          borderRadius: "10px",
          textDecoration: "none",
          fontWeight: "bold",
          boxShadow: "0 4px 10px rgba(0,0,0,0.3)"
        }}
      >
        ← Inicio
      </a>

      {/* MAPA */}
      <iframe
        src="/mapa.html"
        title="Mapa Solar"
        style={{
          width: "100%",
          height: "100%",
          border: "none"
        }}
      />
    </div>
  );
}