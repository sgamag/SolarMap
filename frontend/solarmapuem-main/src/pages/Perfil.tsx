import { useNavigate } from "react-router-dom";
import { User, Mail, Calendar, MapPin, Trash2, ArrowRight } from "lucide-react";
import PageLayout from "@/components/PageLayout";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

const HEADER_IMG =
  "https://images.unsplash.com/photo-1605276374104-dee2a0ed3cd6?auto=format&fit=crop&w=1920&q=85";

export default function Perfil() {
  const { user, logout, removeAddress } = useAuth();
  const navigate = useNavigate();

  if (!user) return null;

  const initials = `${user.nombre?.[0] ?? ""}${user.apellidos?.[0] ?? ""}`.toUpperCase();

  const fields = [
    { icon: User, label: "Nombre", value: user.nombre },
    { icon: User, label: "Apellidos", value: user.apellidos },
    { icon: Mail, label: "Correo electrónico", value: user.email },
    { icon: Calendar, label: "Fecha de nacimiento", value: user.fechaNacimiento },
    { icon: MapPin, label: "Código postal", value: user.codigoPostal },
  ];

  const addresses = user.savedAddresses ?? [];

  return (
    <PageLayout transparentNav>
      <section
        className="relative w-full h-[40vh] min-h-[340px] flex items-center justify-center"
        style={{ backgroundColor: "#0F1A2E" }}
      >
        <img
          src={HEADER_IMG}
          alt=""
          className="absolute inset-0 w-full h-full object-cover"
          onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
        />
        <div className="absolute inset-0" style={{ backgroundColor: "rgba(0,0,0,0.55)" }} />
        <div className="relative z-10 flex flex-col items-center text-center px-6 pt-12">
          <div
            className="h-24 w-24 rounded-full flex items-center justify-center text-2xl font-bold text-white mb-4"
            style={{ backgroundColor: "#E8970A" }}
          >
            {initials || "U"}
          </div>
          <h1 className="text-white font-bold" style={{ fontSize: "32px" }}>
            {user.nombre} {user.apellidos}
          </h1>
          <p className="text-white/80 mt-1" style={{ fontSize: "16px" }}>{user.email}</p>
          <span className="mt-4 inline-block border border-white/60 text-white text-xs font-semibold px-3 py-1.5 rounded-full">
            Cuenta demo · Autenticación pendiente
          </span>
        </div>
      </section>

      <section className="w-full py-16 px-6" style={{ backgroundColor: "#FAFAF7" }}>
        <div className="mx-auto bg-white" style={{ maxWidth: "640px", borderRadius: "16px", boxShadow: "0 4px 24px rgba(15,26,46,0.08)" }}>
          <div className="px-6 py-4 border-b border-border">
            <h2 className="text-lg font-bold text-primary">Datos personales</h2>
          </div>
          <div className="divide-y divide-border">
            {fields.map((f) => (
              <div key={f.label} className="flex items-start gap-4 px-6 py-5">
                <div className="h-10 w-10 rounded-full bg-muted flex items-center justify-center text-muted-foreground shrink-0">
                  <f.icon className="h-5 w-5" />
                </div>
                <div className="flex flex-col">
                  <span className="text-[12px] uppercase tracking-wider text-muted-foreground font-medium">
                    {f.label}
                  </span>
                  <span className="text-foreground font-bold mt-0.5" style={{ fontSize: "16px" }}>
                    {f.value || "—"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Mis direcciones */}
        <div className="mx-auto mt-8 bg-white" style={{ maxWidth: "640px", borderRadius: "16px", boxShadow: "0 4px 24px rgba(15,26,46,0.08)" }}>
          <div className="px-6 py-4 border-b border-border">
            <h2 className="text-lg font-bold text-primary">Mis direcciones guardadas</h2>
          </div>
          <div className="p-6">
            {addresses.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Aún no has guardado ninguna dirección. Búscala en el mapa y pulsa <strong>Guardar dirección</strong>.
              </p>
            ) : (
              <ul className="space-y-3">
                {addresses.map((a) => (
                  <li
                    key={a.id}
                    className="flex items-center justify-between gap-3 border border-border rounded-xl p-4 hover:border-accent transition-colors"
                  >
                    <div className="flex items-start gap-3 min-w-0">
                      <MapPin className="h-5 w-5 text-accent shrink-0 mt-0.5" />
                      <div className="min-w-0">
                        <div className="font-bold text-foreground truncate">{a.address}</div>
                        <div className="text-xs text-muted-foreground">
                          Guardada el {new Date(a.savedAt).toLocaleDateString()}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Button
                        size="sm"
                        variant="coral"
                        onClick={() =>
                          navigate(
                            `/analisis/resumen?address=${encodeURIComponent(a.address)}${a.roofId ? `&roof_id=${a.roofId}` : ""}`
                          )
                        }
                      >
                        Analizar <ArrowRight className="h-4 w-4" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() => { removeAddress(a.id); toast("Dirección eliminada"); }}
                        aria-label="Eliminar"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="mx-auto mt-6 flex flex-wrap justify-center gap-3" style={{ maxWidth: "640px" }}>
          <Button variant="coral" onClick={() => { logout(); navigate("/"); }}>
            Cerrar sesión
          </Button>
        </div>
      </section>
    </PageLayout>
  );
}
