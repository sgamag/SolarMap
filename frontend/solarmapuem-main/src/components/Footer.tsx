import { Link } from "react-router-dom";
import logo from "@/assets/logo.png";

const links = [
  { to: "/quienes-somos", label: "Quiénes somos" },
  { to: "/faq", label: "FAQ" },
  { to: "/privacidad", label: "Política de privacidad" },
  { to: "/terminos", label: "Términos y condiciones" },
];

export default function Footer() {
  return (
    <footer className="mt-20" style={{ backgroundColor: "#F5F3EE" }}>
      <div className="container-page py-12 grid gap-8 md:grid-cols-2 items-start">
        <div>
          <div className="flex items-center gap-3 mb-3">
            <img src={logo} alt="SolarMap" className="h-10 w-10 object-contain" />
            <h3 className="text-xl font-extrabold text-primary">SolarMap</h3>
          </div>
          <p className="text-sm text-muted-foreground max-w-md">
            Plataforma académica para estimar el potencial solar urbano de Madrid mediante datos
            climáticos abiertos y análisis geoespacial.
          </p>
          <p className="mt-4 text-xs text-muted-foreground">
            © 2026 SolarMap · Proyecto académico · Universidad Europea de Madrid
          </p>
        </div>

        <div className="md:text-right">
          <ul className="flex flex-wrap md:justify-end gap-x-6 gap-y-2 text-sm text-foreground">
            {links.map((l) => (
              <li key={l.to}>
                <Link to={l.to} className="hover:text-accent transition-colors">{l.label}</Link>
              </li>
            ))}
            <li>
              <a href="mailto:solarmap@uem.es" className="hover:text-accent transition-colors">
                Contacto · solarmap@uem.es
              </a>
            </li>
          </ul>
        </div>
      </div>
    </footer>
  );
}
