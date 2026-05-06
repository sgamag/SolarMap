import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Sun, Star, ArrowRight } from "lucide-react";
import PageLayout from "@/components/PageLayout";
import { Button } from "@/components/ui/button";

export const PANELS = [
  { id: "panel_400", name: "Panel Estándar 400W", potencia: 400 },
  { id: "panel_450", name: "Panel Premium 450W", potencia: 450 },
  { id: "panel_350", name: "Panel Compacto 350W", potencia: 350 },
  { id: "panel_500", name: "Panel Alta Eficiencia 500W", potencia: 500 },
];

function Breadcrumb({ step }: { step: 1 | 2 | 3 }) {
  const items = ["Resumen", "Proveedores", "Análisis detallado"];
  return (
    <nav className="text-sm text-muted-foreground flex flex-wrap items-center gap-2">
      {items.map((it, i) => (
        <span key={it} className="flex items-center gap-2">
          <span className={i + 1 === step ? "text-foreground font-bold" : ""}>{it}</span>
          {i < items.length - 1 && <span>→</span>}
        </span>
      ))}
    </nav>
  );
}

export default function AnalisisProveedores() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState(true);

  const address = params.get("address") || "";
  const roofId = params.get("roof_id") || "";

  const selectPanel = (panelId: string) => {
    const qs = new URLSearchParams();
    if (address) qs.set("address", address);
    if (roofId) qs.set("roof_id", roofId);
    qs.set("provider", "solarmap_installer");
    qs.set("panel", panelId);
    navigate(`/analisis/detalle?${qs.toString()}`);
  };

  return (
    <PageLayout>
      <section className="container-page py-10 space-y-8">
        <Breadcrumb step={2} />
        <div>
          <h1 className="text-3xl md:text-4xl font-extrabold text-primary">
            Elige tu proveedor e instalador
          </h1>
          <p className="text-sm text-muted-foreground mt-2">
            Selecciona el proveedor y el modelo de panel para calcular tu instalación.
          </p>
        </div>

        {/* Tarjeta proveedor */}
        <div className="rounded-2xl border border-border bg-card overflow-hidden">
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="w-full text-left p-6 flex items-center gap-5 hover:bg-muted/50 transition-colors"
          >
            <div
              className="h-16 w-16 rounded-2xl flex items-center justify-center shrink-0"
              style={{ backgroundColor: "#E8970A" }}
            >
              <Sun className="h-8 w-8 text-white" />
              <span className="sr-only">SM</span>
            </div>
            <div className="flex-1 min-w-0">
              <h2 className="text-xl font-extrabold text-primary">SolarMap Installer</h2>
              <p className="text-xs text-muted-foreground">
                Proveedor de ejemplo · Datos pendientes de conexión
              </p>
              <div className="flex items-center gap-1 mt-2 text-solar">
                {[1, 2, 3, 4].map((i) => (
                  <Star key={i} className="h-4 w-4 fill-current" />
                ))}
                <Star className="h-4 w-4 text-muted" />
                <span className="text-xs text-muted-foreground ml-2">4/5 (simulada)</span>
              </div>
              <p className="text-sm text-muted-foreground mt-2">
                Instalador certificado de paneles fotovoltaicos. Cobertura en toda la Comunidad de Madrid.
              </p>
            </div>
            <Button variant="coral" size="sm">
              {expanded ? "Ocultar paneles" : "Ver paneles disponibles"}
            </Button>
          </button>

          {expanded && (
            <div className="border-t border-border p-6 space-y-5">
              <div>
                <h3 className="font-bold text-primary mb-2">Sobre este proveedor</h3>
                <p className="text-sm text-muted-foreground">
                  Empresa de instalación fotovoltaica de ejemplo. En una versión futura, aquí
                  aparecerán los datos reales del proveedor: certificaciones, años de experiencia,
                  zona de cobertura y contacto.
                </p>
              </div>

              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {PANELS.map((p) => (
                  <div
                    key={p.id}
                    className="rounded-xl border border-border p-5 flex flex-col gap-3 bg-background hover:border-accent transition-colors"
                  >
                    <div className="font-bold text-primary">{p.name}</div>
                    <dl className="text-sm space-y-1.5">
                      <div className="flex justify-between">
                        <dt className="text-muted-foreground">Potencia</dt>
                        <dd className="font-bold">{p.potencia} W</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-muted-foreground">Precio unitario</dt>
                        <dd className="text-xs text-muted-foreground italic">Pendiente</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-muted-foreground">Área por panel</dt>
                        <dd className="text-xs text-muted-foreground italic">Pendiente</dd>
                      </div>
                    </dl>
                    <Button variant="coral" size="sm" onClick={() => selectPanel(p.id)}>
                      Seleccionar este panel <ArrowRight className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div>
          <button onClick={() => navigate(-1)} className="text-sm text-accent hover:underline">
            ← Volver al resumen
          </button>
        </div>
      </section>
    </PageLayout>
  );
}
