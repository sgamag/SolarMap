import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AuthLayout from "@/components/AuthLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

export default function Registro() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    nombre: "",
    apellidos: "",
    email: "",
    password: "",
    confirm: "",
    fechaNacimiento: "",
    codigoPostal: "",
  });

  const set = (k: string, v: string) => setForm({ ...form, [k]: v });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form.password !== form.confirm) {
      toast.error("Las contraseñas no coinciden");
      return;
    }
    await register({
      nombre: form.nombre,
      apellidos: form.apellidos,
      email: form.email,
      password: form.password,
      fechaNacimiento: form.fechaNacimiento,
      codigoPostal: form.codigoPostal,
    });
    toast.success("Cuenta creada (simulada)");
    navigate("/");
  };

  return (
    <AuthLayout overlayText="Tu tejado puede contar otra historia.">
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-extrabold text-primary mb-1">Crear cuenta</h1>
          <p className="text-sm text-muted-foreground">Únete a SolarMap.</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="nombre">Nombre</Label>
              <Input id="nombre" required value={form.nombre} onChange={(e) => set("nombre", e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="apellidos">Apellidos</Label>
              <Input id="apellidos" required value={form.apellidos} onChange={(e) => set("apellidos", e.target.value)} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="email">Correo electrónico</Label>
            <Input id="email" type="email" required value={form.email} onChange={(e) => set("email", e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="password">Contraseña</Label>
              <Input id="password" type="password" required value={form.password} onChange={(e) => set("password", e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="confirm">Confirmar</Label>
              <Input id="confirm" type="password" required value={form.confirm} onChange={(e) => set("confirm", e.target.value)} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="fechaNacimiento">Fecha de nacimiento</Label>
              <Input
                id="fechaNacimiento"
                type="date"
                required
                value={form.fechaNacimiento}
                onChange={(e) => set("fechaNacimiento", e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="codigoPostal">Código postal</Label>
              <Input
                id="codigoPostal"
                inputMode="numeric"
                pattern="\d{5}"
                maxLength={5}
                required
                value={form.codigoPostal}
                onChange={(e) => set("codigoPostal", e.target.value)}
              />
            </div>
          </div>
          <Button type="submit" variant="coral" className="w-full" size="lg">
            Crear cuenta
          </Button>
          <div className="text-sm text-center">
            <Link to="/login" className="text-accent hover:underline font-medium">¿Ya tienes cuenta? Inicia sesión</Link>
          </div>
        </form>
      </div>
    </AuthLayout>
  );
}
