import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, Bookmark, Square, Compass, Euro, CalendarClock } from "lucide-react";
import PageLayout from "@/components/PageLayout";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

const cards = [
  { icon: Square, label: "m² de tejado útil", title: "Superficie útil" },
  { icon: Compass, label: "orientación principal", title: "Orientación" },
  { icon: Euro, label: "€ de ahorro anual estimado", title: "Ahorro estimado primer año" },
  { icon: CalendarClock, label: "años de amortización estimados", title: "Tiempo de amortización" },
];

export default function AnalisisResumen() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { isAuthenticated, saveAddress, user } = useAuth();
  const address = params.get("address") || "Calle Guazalate, 2 · Villaviciosa de Odón";
  const roofId = params.get("roof_id") || undefined;

  const alreadySaved = !!user?.savedAddresses?.some(
    (a) => a.address === address && a.roofId === roofId
  );

  const handleSave = () => {
    if (!isAuthenticated) {
      toast("Inicia sesión para guardar esta dirección", {
        action: { label: "Iniciar sesión", onClick: () => navigate("/login?next=/mapa") },
      });
      return;
    }
    saveAddress(address, roofId);
    toast.success("Dirección guardada ✓");
  };

  const goToProveedores = () => {
    const qs = new URLSearchParams();
    qs.set("address", address);
    if (roofId) qs.set("roof_id", roofId);
    navigate(`/analisis/proveedores?${qs.toString()}`);
  };

  return (
    <PageLayout>
      <section className="container-page py-10 space-y-8">
        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-3">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-3xl md:text-4xl font-extrabold text-primary">{address}</h1>
              <Button asChild size="sm" variant="outline">
                <Link to="/mapa">
                  <ArrowLeft className="h-4 w-4" /> Cambiar dirección o tejado
                </Link>
              </Button>
            </div>
            <div className="flex items-center gap-3 flex-wrap">
              <span className="bg-solar/20 text-foreground border border-solar/40 text-xs font-semibold px-3 py-1.5 rounded-full">
                Resultado provisional
              </span>
              <Button
                size="sm"
                variant={alreadySaved ? "secondary" : "coral"}
                onClick={handleSave}
                disabled={alreadySaved}
              >
                <Bookmark className="h-4 w-4" />
                {alreadySaved ? "Dirección guardada" : "Guardar dirección"}
              </Button>
            </div>
          </div>
        </div>

        {/* 4 tarjetas */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {cards.map((c) => (
            <div
              key={c.title}
              className="rounded-2xl border border-border bg-card p-6 flex flex-col gap-3 hover:border-accent transition-colors"
            >
              <div className="h-12 w-12 rounded-full bg-accent/10 flex items-center justify-center text-accent">
                <c.icon className="h-6 w-6" />
              </div>
              <div>
                <div className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">
                  {c.title}
                </div>
                <div className="text-2xl font-extrabold text-primary mt-1">Pendiente de conexión</div>
                <div className="text-sm text-muted-foreground mt-1">{c.label}</div>
              </div>
            </div>
          ))}
        </div>

        <p className="text-sm text-muted-foreground max-w-3xl">
          Estimación basada en datos climáticos ERA5 y geometría del tejado. Resultado provisional
          pendiente de conexión al modelo.
        </p>

        <div className="pt-4">
          <Button variant="coral" size="lg" onClick={goToProveedores}>
            Ver proveedores disponibles <ArrowRight className="h-5 w-5" />
          </Button>
        </div>
      </section>
    </PageLayout>
  );
}
