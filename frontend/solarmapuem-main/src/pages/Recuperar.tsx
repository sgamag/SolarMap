import { useState } from "react";
import { Link } from "react-router-dom";
import AuthLayout from "@/components/AuthLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";

export default function Recuperar() {
  const [email, setEmail] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: fetch('/api/auth/recover')
    toast("Funcionalidad pendiente de implementación");
  };

  return (
    <AuthLayout overlayText="Recupera el acceso, no la energía perdida.">
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-extrabold text-primary mb-1">Recuperar contraseña</h1>
          <p className="text-sm text-muted-foreground">
            Te enviaremos un enlace para restablecer tu contraseña.
          </p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="email">Correo electrónico</Label>
            <Input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <Button type="submit" variant="coral" className="w-full" size="lg">
            Enviar enlace de recuperación
          </Button>
          <p className="text-xs text-muted-foreground text-center">Funcionalidad pendiente de implementación</p>
          <div className="text-sm text-center">
            <Link to="/login" className="text-accent hover:underline font-medium">Volver al inicio de sesión</Link>
          </div>
        </form>
      </div>
    </AuthLayout>
  );
}
