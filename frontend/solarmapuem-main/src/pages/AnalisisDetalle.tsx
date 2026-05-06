import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Download } from "lucide-react";
import PageLayout from "@/components/PageLayout";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import SparklineChart from "@/components/SparklineChart";
import { mockSparklines } from "@/data/mockData";
import { PANELS } from "./AnalisisProveedores";

const PENDING = "Pendiente de conexión";

const roofRows = [
  { key: "area_util_m2", label: "Área útil del tejado" },
  { key: "orientacion_grados", label: "Orientación en grados" },
  { key: "orientacion_cardinal", label: "Orientación cardinal (N/NE/E/SE/S/SW/W/NW)" },
  { key: "numero_paneles", label: "Número de paneles estimados" },
  { key: "potencia_total_kw", label: "Potencia total instalada (kW)" },
  { key: "energia_generada_anual_kwh", label: "Energía generada al año (kWh)" },
];

const roiRows = [
  { key: "coste_instalacion", label: "Coste total estimado (€)" },
  { key: "ahorro_primer_año_euros", label: "Ahorro primer año (€)" },
  { key: "tiempo_amortizacion_años", label: "Tiempo de amortización (años)" },
  { key: "roi_medio_anual", label: "ROI medio anual (%)" },
];

const components = [
  { name: "rad_norm", label: "Radiación normalizada", series: mockSparklines.rad_norm, color: "#E8970A" },
  { name: "pen_nube", label: "Penalización por nubes", series: mockSparklines.pen_nube, color: "#2D6FE8" },
  { name: "pen_temp", label: "Penalización por temperatura", series: mockSparklines.pen_temp, color: "#2E8B57" },
  { name: "horas_norm", label: "Horas de sol normalizadas", series: mockSparklines.horas_norm, color: "#F5B400" },
];

function Breadcrumb() {
  const items = [
    { label: "Resumen", active: false },
    { label: "Proveedores", active: false },
    { label: "Análisis detallado", active: true },
  ];
  return (
    <nav className="text-sm text-muted-foreground flex flex-wrap items-center gap-2">
      {items.map((it, i) => (
        <span key={it.label} className="flex items-center gap-2">
          <span className={it.active ? "text-foreground font-bold" : ""}>{it.label}</span>
          {i < items.length - 1 && <span>→</span>}
        </span>
      ))}
    </nav>
  );
}

export default function AnalisisDetalle() {
  const [params] = useSearchParams();
  const [open, setOpen] = useState(false);
  const address = params.get("address") || "Calle Guazalate, 2 · Villaviciosa de Odón";
  const panelId = params.get("panel") || "panel_400";
  const panel = PANELS.find((p) => p.id === panelId) ?? PANELS[0];

  return (
    <PageLayout>
      <section className="container-page py-10 space-y-8">
        <Breadcrumb />

        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl md:text-4xl font-extrabold text-primary">
              {address}
            </h1>
            <p className="text-base text-muted-foreground mt-1">Panel seleccionado: <strong>{panel.name}</strong></p>
          </div>
          <span className="bg-solar/20 text-foreground border border-solar/40 text-xs font-semibold px-3 py-1.5 rounded-full">
            Resultado provisional
          </span>
        </div>

        {/* Sección 1 */}
        <div>
          <h2 className="text-xl font-bold text-primary mb-4">Datos del tejado y la instalación</h2>
          <div className="grid sm:grid-cols-2 gap-3 rounded-2xl border border-border bg-card p-2">
            {roofRows.map((r) => (
              <div key={r.key} className="flex justify-between gap-4 px-4 py-3 border-b last:border-b-0 sm:border-b-0 border-border">
                <div className="text-sm">
                  <div className="font-mono text-xs text-muted-foreground">{r.key}</div>
                  <div className="font-medium text-foreground">{r.label}</div>
                </div>
                <div className="text-sm text-muted-foreground italic shrink-0 self-center">{PENDING}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Sección 2 — escenarios */}
        <div>
          <h2 className="text-xl font-bold text-primary mb-4">Retorno de inversión por escenario</h2>
          <Tabs defaultValue="pesimista" className="w-full">
            <TabsList className="grid w-full max-w-md grid-cols-3">
              <TabsTrigger value="pesimista">Pesimista</TabsTrigger>
              <TabsTrigger value="plano">Plano</TabsTrigger>
              <TabsTrigger value="verde">Verde</TabsTrigger>
            </TabsList>
            {(["pesimista", "plano", "verde"] as const).map((s) => (
              <TabsContent key={s} value={s} className="mt-4">
                <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  {roiRows.map((r) => (
                    <div key={r.key} className="rounded-xl border border-border bg-card p-5">
                      <div className="font-mono text-xs text-muted-foreground">{r.key}</div>
                      <div className="font-bold text-foreground text-sm mt-1">{r.label}</div>
                      <div className="text-base text-muted-foreground italic mt-3">{PENDING}</div>
                    </div>
                  ))}
                </div>
              </TabsContent>
            ))}
          </Tabs>
        </div>

        {/* Sección 3 — sparklines */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-primary">Componentes del modelo</h2>
            <span className="text-xs font-semibold bg-muted text-muted-foreground px-2.5 py-1 rounded-full">
              Datos simulados
            </span>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {components.map((c) => (
              <div key={c.name} className="rounded-xl border border-border bg-card p-5 space-y-3">
                <div>
                  <div className="font-mono text-xs text-muted-foreground">{c.name}</div>
                  <div className="font-bold text-foreground text-sm">{c.label}</div>
                </div>
                <SparklineChart data={c.series} color={c.color} width={200} height={56} />
                <div className="text-xs text-muted-foreground">Serie mensual mock</div>
              </div>
            ))}
          </div>
        </div>

        {/* Sección 4 */}
        <div className="rounded-xl border-2 border-dashed border-solar/60 bg-solar/10 p-5 text-sm text-foreground">
          <strong className="font-bold">Aviso:</strong> Resultados mostrados con datos ficticios.
          Variables reales del modelo, valores pendientes de conexión al backend.
        </div>

        <div className="pt-2">
          <Button variant="coral" size="lg" onClick={() => setOpen(true)}>
            <Download className="h-5 w-5" /> Generar informe PDF
          </Button>
        </div>
      </section>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Generación de informe pendiente</DialogTitle>
            <DialogDescription>
              Generación de informe pendiente de implementación. En una versión futura descargará un
              PDF con todos los datos del análisis.
            </DialogDescription>
          </DialogHeader>
        </DialogContent>
      </Dialog>
    </PageLayout>
  );
}
