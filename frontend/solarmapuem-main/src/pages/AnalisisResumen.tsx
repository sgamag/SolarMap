import { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import PageLayout from "@/components/PageLayout";
import { Button } from "@/components/ui/button";

// ─── Configuracion del informe Power BI ─────────────────────────────────────
const REPORT_ID = "eb17de9c-61c6-4b26-884d-17a767fcfd71";
const TENANT_ID = "032115c7-35fe-4637-b2c3-d0a42906ba7b";
const URL_BASE  = `https://app.powerbi.com/reportEmbed?reportId=${REPORT_ID}&autoAuth=true&ctid=${TENANT_ID}`;

// Tabla y columna del modelo (case-sensitive!)
const PBI_TABLE = "Tejado_detectado_BD";
const PBI_FIELD = "id_tejado";

// ─────────────────────────────────────────────────────────────────────────────

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
  // Sintaxis Power BI: filter=Tabla/Columna eq VALOR
  // id_tejado es NUMERO en Power BI, sin comillas alrededor del valor
  const filter = `${PBI_TABLE}/${PBI_FIELD} eq ${idTejado}`;
  return `${URL_BASE}&filter=${encodeURIComponent(filter)}`;
}

export default function AnalisisResumen() {
  const navigate = useNavigate();
  const [tejado, setTejado] = useState<TejadoActual | null>(null);
  const [loaded, setLoaded] = useState(false);

  // Lee el tejado actual de sessionStorage (lo deja el mapa al pulsar "Analizar")
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

  // ── Sin tejado guardado: pantalla informativa ──
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
      </PageLayout>
    );
  }

  // ── Render con dashboard filtrado ──
  return (
    <PageLayout>
      <div className="flex flex-col h-full">
        {/* Banner con info del tejado analizado */}
        <div className="border-b border-amber-200 bg-gradient-to-r from-amber-100 to-yellow-100 px-6 py-3 flex flex-wrap items-center gap-6 text-sm text-amber-900">
          <strong className="text-sm">📊 Análisis del tejado #{tejado.id_tejado}</strong>
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

        {/* Contenedor del dashboard */}
        <div className="relative flex-1 bg-muted/20">
          {/* Loader mientras Power BI inicializa */}
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
            style={{ width: "100%", height: "100%", border: "none" }}
            allowFullScreen
            onLoad={() => setLoaded(true)}
          />

          {/* Boton volver flotante */}
          <div className="absolute bottom-6 left-6 z-20">
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
        </div>
      </div>
    </PageLayout>
  );
}
