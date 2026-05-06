import { useEffect, useState } from "react";
import { Link, NavLink as RRNavLink, useNavigate } from "react-router-dom";
import { LogOut, User as UserIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import logo from "@/assets/logo.png";

interface NavBarProps {
  transparent?: boolean;
}

export default function NavBar({ transparent = false }: NavBarProps) {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    if (!transparent) return;
    const onScroll = () => setScrolled(window.scrollY > 80);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [transparent]);

  const isOverHero = transparent && !scrolled;

  const initials = user
    ? `${user.nombre?.[0] ?? ""}${user.apellidos?.[0] ?? ""}`.toUpperCase()
    : "";

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `text-sm font-medium transition-colors ${
      isOverHero
        ? `text-white hover:text-solar ${isActive ? "text-solar" : ""}`
        : `hover:text-accent ${isActive ? "text-accent" : "text-foreground"}`
    }`;

  const handleAnalisisClick = (e: React.MouseEvent) => {
    if (!isAuthenticated) {
      e.preventDefault();
      toast("Inicia sesión para ver el análisis");
      navigate("/login?next=/analisis");
    }
  };

  return (
    <header
      className={`${transparent ? "fixed" : "sticky"} top-0 left-0 right-0 z-40 transition-all duration-300 ${
        isOverHero
          ? "bg-transparent border-b border-transparent"
          : "bg-background/95 backdrop-blur border-b border-border shadow-sm"
      }`}
    >
      <div className="container-page flex h-16 items-center justify-between gap-6">
        <Link to="/" className={`flex items-center gap-2 font-extrabold text-lg ${isOverHero ? "text-white" : "text-primary"}`}>
          <img src={logo} alt="SolarMap" className="h-10 w-10 object-contain" />
          <span>SolarMap</span>
        </Link>

        <nav className="hidden md:flex items-center gap-8">
          <RRNavLink to="/" end className={linkClass}>Inicio</RRNavLink>
          <RRNavLink to="/mapa" className={linkClass}>Mapa</RRNavLink>
          <RRNavLink to="/analisis" className={linkClass} onClick={handleAnalisisClick}>
            Análisis
          </RRNavLink>
        </nav>

        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <>
              <Link
                to="/perfil"
                className={`flex items-center gap-2 text-sm font-medium ${
                  isOverHero ? "text-white hover:text-solar" : "text-foreground hover:text-accent"
                }`}
              >
                <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-accent text-accent-foreground text-xs font-bold">
                  {initials || <UserIcon className="h-4 w-4" />}
                </span>
                <span className="hidden sm:inline">Perfil</span>
              </Link>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => { logout(); navigate("/"); }}
                className={isOverHero ? "text-white hover:bg-white/10 hover:text-white" : ""}
              >
                <LogOut className="h-4 w-4" /> Cerrar sesión
              </Button>
            </>
          ) : (
            <Button asChild variant="coral" size="sm">
              <Link to="/login">Iniciar sesión</Link>
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}
