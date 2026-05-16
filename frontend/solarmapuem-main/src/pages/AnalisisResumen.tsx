import { useSearchParams } from "react-router-dom";
import { useState } from "react";
import PageLayout from "@/components/PageLayout";

// ─── Configuración Power BI ───────────────────────────────────────────────────
const POWERBI_BASE_URL =
  "https://app.powerbi.com/reportEmbed" +
  "?reportId=eb17de9c-61c6-4b26-884d-17a767fcfd71" +
  "&autoAuth=true" +
  "&ctid=032115c7-35fe-4637-b2c3-d0a42906ba7b";

// Nombre EXACTO de tabla y campo en el modelo de Power BI
const PBI_TABLE = "fatc_tejados_detectados";
const PBI_FIELD = "id_tejado";

// ─────────────────────────────────────────────────────────────────────────────

/**
 * Construye la URL de embedding añadiendo el filtro de Power BI si hay roof_id.
 *
 * Sintaxis del filtro:
 *   &filter=NombreTabla/NombreCampo eq 'valor'
 *
 * Si id_tejado es numérico en tu modelo (no texto), quita las comillas simples:
 *   eq ${roofId}   →  en lugar de   eq '${roofId}'
 */
function buildEmbedUrl(roofId: string | null): string {
  const url = new URL(POWERBI_BASE_URL);

  if (roofId) {
    // Cambia a eq ${roofId} (sin comillas) si el campo es numérico en Power BI
    const filter = `${PBI_TABLE}/${PBI_FIELD} eq '${roofId}'`;
    url.searchParams.set("filter", filter);
  }

  return url.toString();
}

export default function AnalisisResumen() {
  const [params] = useSearchParams();
  const [loaded, setLoaded] = useState(false);

  const roofId = params.get("roof_id");
  const embedUrl = buildEmbedUrl(roofId);

  return (
    <PageLayout>
      {/* Ocupa toda la altura disponible menos la navbar */}
      <div className="relative w-full h-[calc(100vh-4rem)]">

        {/* Loader mientras el iframe inicializa */}
        {!loaded && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-background z-10">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            <span className="text-sm text-muted-foreground">Cargando análisis solar…</span>
          </div>
        )}

        <iframe
          title="CMandosPotencial"
          src={embedUrl}
          allowFullScreen
          onLoad={() => setLoaded(true)}
          className={`w-full h-full border-0 transition-opacity duration-500 ${
            loaded ? "opacity-100" : "opacity-0"
          }`}
        />
      </div>
    </PageLayout>
  );
}