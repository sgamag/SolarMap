import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import AuthLayout from "@/components/AuthLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: fetch('/api/auth/login')
    await login(email, password);
    toast.success("Sesión iniciada (simulada)");
    navigate(params.get("next") || "/");
  };

  return (
    <AuthLayout overlayText="El sol no caduca, tu factura sí.">
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-extrabold text-primary mb-1">Bienvenido de vuelta</h1>
          <p className="text-sm text-muted-foreground">Accede a tu panel de SolarMap.</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="email">Correo electrónico</Label>
            <Input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="password">Contraseña</Label>
            <Input id="password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          <Button type="submit" variant="coral" className="w-full" size="lg">
            Iniciar sesión
          </Button>
          <div className="flex items-center justify-between text-sm">
            <Link to="/registro" className="text-accent hover:underline font-medium">¿No tienes cuenta? Regístrate</Link>
            <Link to="/recuperar" className="text-muted-foreground hover:underline">¿Olvidaste tu contraseña?</Link>
          </div>
          <p className="text-xs text-muted-foreground text-center pt-2">
            Autenticación pendiente de implementación
          </p>
        </form>
      </div>
    </AuthLayout>
  );
}
