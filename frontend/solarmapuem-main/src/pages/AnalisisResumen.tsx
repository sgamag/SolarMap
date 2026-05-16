import { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { FileDown, Users } from "lucide-react";
import PageLayout from "@/components/PageLayout";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

// ─── Configuración Power BI ───────────────────────────────────────────────────
const REPORT_ID = "eb17de9c-61c6-4b26-884d-17a767fcfd71";
const TENANT_ID = "032115c7-35fe-4637-b2c3-d0a42906ba7b";
const URL_BASE  = `https://app.powerbi.com/reportEmbed?reportId=${REPORT_ID}&autoAuth=true&ctid=${TENANT_ID}`;

const PBI_TABLE = "Tejado_detectado_BD";
const PBI_FIELD = "id_tejado";

// ─── URL base de tu API ───────────────────────────────────────────────────────
const API_BASE = "/api";
// ─────────────────────────────────────────────────────────────────────────────

type TejadoActual = {
  id_tejado: number;
  id_zona?: string;
  area_util_m2?: number;
  orientacion_principal?: string;
};

function buildEmbedUrl(idTejado: number | null): string {
  if (!idTejado) return URL_BASE;
  const filter = `${PBI_TABLE}/${PBI_FIELD} eq ${idTejado}`;
  return `${URL_BASE}&filter=${encodeURIComponent(filter)}`;
}

// Alturas: PrototypeBanner (36) + NavBar (64) + Banner tejado (52)
const BANNER_HEIGHT = "152px";

export default function AnalisisResumen() {
  const navigate = useNavigate();
  const [tejado, setTejado]       = useState<TejadoActual | null>(null);
  const [loaded, setLoaded]       = useState(false);
  const [generando, setGenerando] = useState(false);

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("solarmap.tejado_actual");
      if (raw) setTejado(JSON.parse(raw));
    } catch { /* ignore */ }
  }, []);

  const embedUrl = useMemo(
    () => buildEmbedUrl(tejado?.id_tejado ?? null),
    [tejado]
  );

  const handleGenerarInforme = async () => {
    if (!tejado) return;
    setGenerando(true);
    try {
      const res = await fetch(`${API_BASE}/informe/${tejado.id_tejado}`);
      if (!res.ok) throw new Error(`Error ${res.status}`);
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      a.download = `informe_tejado_${tejado.id_tejado}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Informe descargado correctamente ✓");
    } catch (err) {
      toast.error("No se pudo generar el informe. Inténtalo de nuevo.");
      console.error(err);
    } finally {
      setGenerando(false);
    }
  };

  // ── Sin tejado: pantalla informativa ──
  if (!tejado) {
    return (
      <PageLayout>
        <div className="flex flex-1 items-center justify-center bg-muted/30 p-10">
          <div className="max-w-md rounded-2xl border bg-card p-8 text-center shadow-sm">
            <div className="mb-4 text-5xl">🛰️</div>
            <h2 className="mb-2 text-xl font-bold text-foreground">
              No has analizado ningún tejado todavía
            </h2>
            <p className="mb-6 text-sm leading-relaxed text-muted-foreground">
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
      </PageLayout>
    );
  }

  // ── Dashboard filtrado ──
  return (
    <PageLayout withFooter={false}>

      {/* Banner info tejado */}
      <div className="shrink-0 border-b border-amber-200 bg-gradient-to-r from-amber-100 to-yellow-100 px-6 py-3 flex flex-wrap items-center gap-6 text-sm text-amber-900">
        <strong>📊 Análisis del tejado #{tejado.id_tejado}</strong>
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

      {/* Contenedor iframe */}
      <div className="relative w-full" style={{ height: `calc(100vh - ${BANNER_HEIGHT})` }}>

        {/* Loader */}
        {!loaded && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-background">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            <span className="text-sm text-muted-foreground">Cargando análisis solar…</span>
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

        {/* Botón Contactar Instaladoras — abajo izquierda */}
        <div className="absolute bottom-6 left-6 z-20">
          <Button
            onClick={() => navigate("/analisis/instaladoras")}
            className="bg-[#F5A623] hover:bg-[#e09510] text-white font-semibold rounded-full px-6 py-3 shadow-lg flex items-center gap-2 transition-colors duration-200"
          >
            <Users className="h-4 w-4" />
            Contactar instaladoras
          </Button>
        </div>

        {/* Botón Generar Informe — abajo derecha */}
        <div className="absolute bottom-6 right-6 z-20">
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
    </PageLayout>
  );
}
