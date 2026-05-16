import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Star, Clock, ShieldCheck, Target } from "lucide-react";
import PageLayout from "@/components/PageLayout";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

// ─── Datos fijos de instaladoras ────────────────────────────────────────────
type Instaladora = {
  id: string;
  nombre: string;
  iniciales: string;
  color: string;
  valoracion: number;
  resenias: number;
  precisionPresupuestaria: number;
  tiempoInstalacion: string;
  garantia: string;
  cobertura: string;
};

const INSTALADORAS: Instaladora[] = [
  {
    id: "solnova",
    nombre: "SolNova Energía",
    iniciales: "SN",
    color: "#f59e0b",
    valoracion: 4.7,
    resenias: 243,
    precisionPresupuestaria: 4,
    tiempoInstalacion: "2 días",
    garantia: "12 años",
    cobertura: "Madrid y alrededores",
  },
  {
    id: "ecotejado",
    nombre: "EcoTejado Solar",
    iniciales: "ET",
    color: "#10b981",
    valoracion: 4.5,
    resenias: 511,
    precisionPresupuestaria: 7,
    tiempoInstalacion: "3 días",
    garantia: "10 años",
    cobertura: "Nacional",
  },
  {
    id: "iberdrola",
    nombre: "Iberdrola Smart Solar",
    iniciales: "IS",
    color: "#3b82f6",
    valoracion: 4.2,
    resenias: 1872,
    precisionPresupuestaria: 2,
    tiempoInstalacion: "5 días",
    garantia: "15 años",
    cobertura: "Nacional",
  },
  {
    id: "voltaria",
    nombre: "Voltaria Iberia",
    iniciales: "VI",
    color: "#8b5cf6",
    valoracion: 4.6,
    resenias: 387,
    precisionPresupuestaria: 5,
    tiempoInstalacion: "4 días",
    garantia: "12 años",
    cobertura: "Madrid, Castilla-La Mancha",
  },
];

function emailValido(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
}

export default function AnalisisInstaladoras() {
  const navigate = useNavigate();
  const [instaladoraSeleccionada, setInstaladoraSeleccionada] = useState<Instaladora | null>(null);
  const [email, setEmail] = useState("");
  const [errorEmail, setErrorEmail] = useState("");
  const [enviado, setEnviado] = useState(false);

  const abrirModal = (instaladora: Instaladora) => {
    setInstaladoraSeleccionada(instaladora);
    setEmail("");
    setErrorEmail("");
    setEnviado(false);
  };

  const cerrarModal = () => {
    setInstaladoraSeleccionada(null);
    setEmail("");
    setErrorEmail("");
    setEnviado(false);
  };

  const enviarContacto = () => {
    setErrorEmail("");
    if (!emailValido(email)) {
      setErrorEmail("Introduce un correo electrónico válido.");
      return;
    }
    setEnviado(true);
  };

  const finalizarYVolver = () => {
    cerrarModal();
    navigate("/mapa");
  };

  return (
    <PageLayout>
      <div className="mx-auto w-full max-w-5xl px-6 py-8">
        <div className="mb-6">
          <button
            onClick={() => navigate(-1)}
            className="mb-4 flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Volver al análisis
          </button>

          <h1 className="text-3xl font-bold text-foreground mb-2">
            Instaladoras compatibles
          </h1>
          <p className="text-muted-foreground">
            Comparativa basada en tu análisis. SolarMap es independiente y no recibe
            comisiones de las instaladoras listadas.
          </p>
        </div>

        <div className="space-y-4">
          {INSTALADORAS.map((inst) => (
            <div
              key={inst.id}
              className="rounded-xl border bg-card p-6 shadow-sm transition-shadow hover:shadow-md"
            >
              <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div className="flex items-start gap-4 flex-1">
                  <div
                    className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl text-white font-bold text-lg"
                    style={{ backgroundColor: inst.color }}
                  >
                    {inst.iniciales}
                  </div>

                  <div className="flex-1">
                    <h2 className="text-xl font-bold text-foreground mb-1">
                      {inst.nombre}
                    </h2>

                    <div className="flex items-center gap-2 mb-3">
                      <div className="flex items-center gap-1">
                        <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                        <span className="font-semibold text-sm">{inst.valoracion}</span>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        ({inst.resenias.toLocaleString("es-ES")} reseñas)
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
                      <div className="flex items-center gap-2">
                        <Target className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <div className="text-xs text-muted-foreground">
                            Precisión presupuestaria
                          </div>
                          <div className="font-semibold">
                            ±{inst.precisionPresupuestaria}%
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <Clock className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <div className="text-xs text-muted-foreground">
                            Instalación
                          </div>
                          <div className="font-semibold">{inst.tiempoInstalacion}</div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <ShieldCheck className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <div className="text-xs text-muted-foreground">Garantía</div>
                          <div className="font-semibold">{inst.garantia}</div>
                        </div>
                      </div>
                    </div>

                    <div className="mt-2 text-xs text-muted-foreground">
                      Cobertura: {inst.cobertura}
                    </div>
                  </div>
                </div>

                <Button
                  onClick={() => abrirModal(inst)}
                  className="
                    bg-[#F5A623] hover:bg-[#e09510]
                    text-white font-semibold
                    rounded-full
                    px-6 py-3
                    shadow-md
                    w-full md:w-auto
                    whitespace-nowrap
                  "
                >
                  Contactar con instaladora
                </Button>
              </div>
            </div>
          ))}
        </div>

        <p className="mt-8 text-xs text-muted-foreground">
          La <strong>precisión presupuestaria</strong> indica la desviación media entre
          el presupuesto inicial ofrecido por la instaladora y la factura final del
          cliente. Datos obtenidos de reseñas públicas verificadas.
        </p>
      </div>

      <Dialog open={!!instaladoraSeleccionada} onOpenChange={(open) => !open && cerrarModal()}>
        <DialogContent className="sm:max-w-md">
          {!enviado ? (
            <>
              <DialogHeader>
                <DialogTitle>Contactar con {instaladoraSeleccionada?.nombre}</DialogTitle>
                <DialogDescription>
                  Introduce tu correo electrónico y la instaladora se pondrá en contacto
                  contigo.
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-3 py-2">
                <div className="space-y-2">
                  <Label htmlFor="email-contacto">Correo electrónico</Label>
                  <Input
                    id="email-contacto"
                    type="email"
                    placeholder="tu@correo.com"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      if (errorEmail) setErrorEmail("");
                    }}
                  />
                  {errorEmail && (
                    <p className="text-sm text-red-600">{errorEmail}</p>
                  )}
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button variant="outline" onClick={cerrarModal}>
                  Cancelar
                </Button>
                <Button
                  onClick={enviarContacto}
                  className="bg-[#F5A623] hover:bg-[#e09510] text-white"
                >
                  Enviar
                </Button>
              </div>
            </>
          ) : (
            <>
              <DialogHeader>
                <DialogTitle>Correo enviado correctamente</DialogTitle>
                <DialogDescription>
                  Tu correo se ha enviado a {instaladoraSeleccionada?.nombre}. Se
                  pondrán en contacto contigo en un plazo de 24 a 48 horas.
                </DialogDescription>
              </DialogHeader>

              <div className="flex justify-end pt-4">
                <Button
                  onClick={finalizarYVolver}
                  className="bg-[#F5A623] hover:bg-[#e09510] text-white"
                >
                  Volver al mapa
                </Button>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </PageLayout>
  );
}
