import { useSearchParams, useNavigate } from "react-router-dom";
import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import PageLayout from "@/components/PageLayout";
import { Button } from "@/components/ui/button";

// ─── Configuración Power BI ───────────────────────────────────────────────────
const POWERBI_BASE_URL =
  "https://app.powerbi.com/reportEmbed" +
  "?reportId=eb17de9c-61c6-4b26-884d-17a767fcfd71" +
  "&autoAuth=true" +
  "&ctid=032115c7-35fe-4637-b2c3-d0a42906ba7b";

const PBI_TABLE = "fatc_tejados_detectados";
const PBI_FIELD = "id_tejado";

// ─────────────────────────────────────────────────────────────────────────────

function buildEmbedUrl(roofId: string | null): string {
  const url = new URL(POWERBI_BASE_URL);

  if (roofId) {
    // Si id_tejado es NÚMERO en Power BI → quita las comillas simples alrededor de ${roofId}
    const filter = `${PBI_TABLE}/${PBI_FIELD} eq '${roofId}'`;
    url.searchParams.set("filter", filter);
  }

  // Fuerza la página 1 del report

  return url.toString();
}

export default function AnalisisResumen() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [loaded, setLoaded] = useState(false);

  const roofId   = params.get("roof_id");
  const embedUrl = buildEmbedUrl(roofId);

  return (
    <PageLayout>
      {/* Ocupa toda la altura disponible menos la navbar */}
      <div className="relative w-full h-[calc(100vh-4rem)]">

        {/* Loader mientras Power BI inicializa */}
        {!loaded && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-background z-10">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            <span className="text-sm text-muted-foreground">Cargando análisis solar…</span>
          </div>
        )}

        {/* iframe Power BI */}
        <iframe
          title="CMandosPotencial"
          src={embedUrl}
          allowFullScreen
          onLoad={() => setLoaded(true)}
          className={`w-full h-full border-0 transition-opacity duration-500 ${
            loaded ? "opacity-100" : "opacity-0"
          }`}
        />

        {/* ── Botón volver ── abajo izquierda, flotando sobre el iframe */}
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
    </PageLayout>
  );
}