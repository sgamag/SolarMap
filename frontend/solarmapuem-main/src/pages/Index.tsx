import { Link } from "react-router-dom";
import PageLayout from "@/components/PageLayout";
import { Button } from "@/components/ui/button";

const HERO_IMG = "https://images.unsplash.com/photo-1509391366360-2e959784a276?auto=format&fit=crop&w=1920&q=85";
const SEC1_IMG = "https://images.unsplash.com/photo-1532601224476-15c79f2f7a51?auto=format&fit=crop&w=1920&q=85";
const SEC2_IMG = "https://images.unsplash.com/photo-1518156677180-95a2893f3e9f?auto=format&fit=crop&w=1920&q=85";
const SEC3_IMG = "https://images.unsplash.com/photo-1466611653911-95081537e5b7?auto=format&fit=crop&w=1920&q=85";

interface FullSectionProps {
  image: string;
  overlay?: number;
  align?: "left" | "right" | "center";
  eyebrow: string;
  eyebrowColor: string;
  title: string;
  description: string;
  cta: { label: string; to: string; variant: "outline-white" | "coral" };
  fallbackBg?: string;
}

function FullSection({
  image,
  overlay = 0.45,
  align = "left",
  eyebrow,
  eyebrowColor,
  title,
  description,
  cta,
  fallbackBg = "#0F1A2E",
}: FullSectionProps) {
  const alignClasses =
    align === "left"
      ? "items-start text-left pl-6 md:pl-16 lg:pl-24 pr-6"
      : align === "right"
        ? "items-end text-right pr-6 md:pr-16 lg:pr-24 pl-6"
        : "items-center text-center px-6";

  return (
    <section
      className="relative w-full min-h-[70vh] flex flex-col justify-center"
      style={{ backgroundColor: fallbackBg }}
    >
      <img
        src={image}
        alt=""
        loading="lazy"
        className="absolute inset-0 w-full h-full object-cover"
        onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
      />
      <div className="absolute inset-0" style={{ backgroundColor: `rgba(0,0,0,${overlay})` }} />
      <div className={`relative z-10 flex flex-col gap-5 max-w-2xl py-24 ${alignClasses} ${align === "right" ? "ml-auto" : align === "center" ? "mx-auto" : ""}`}>
        <span className={`text-xs font-bold tracking-[0.2em] uppercase ${eyebrowColor}`}>{eyebrow}</span>
        <h2 className="text-white text-4xl md:text-5xl lg:text-[52px] font-bold leading-[1.1]">{title}</h2>
        <p className="text-white/90 text-base md:text-lg leading-relaxed max-w-xl">{description}</p>
        <div>
          {cta.variant === "coral" ? (
            <Button asChild variant="coral" size="lg">
              <Link to={cta.to}>{cta.label}</Link>
            </Button>
          ) : (
            <Button
              asChild
              size="sm"
              className="bg-transparent border border-white text-white hover:bg-white hover:text-primary"
            >
              <Link to={cta.to}>{cta.label}</Link>
            </Button>
          )}
        </div>
      </div>
    </section>
  );
}

export default function Index() {
  return (
    <PageLayout transparentNav>
      {/* HERO */}
      <section className="relative w-screen h-screen min-h-[640px] flex items-center justify-center overflow-hidden" style={{ backgroundColor: "#0F1A2E" }}>
        <img
          src={HERO_IMG}
          alt="Paneles solares al amanecer"
          className="absolute inset-0 w-full h-full object-cover"
          onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
        />
        <div className="absolute inset-0" style={{ backgroundColor: "rgba(0,0,0,0.50)" }} />

        <div className="relative z-10 flex flex-col items-center text-center px-6 max-w-3xl">
          <span className="inline-block bg-white/15 backdrop-blur-sm border border-white/20 text-white text-xs font-semibold px-4 py-1.5 rounded-full mb-6">
            Prototipo visual · Datos pendientes de conexión
          </span>
          <h1 className="text-white font-bold leading-none tracking-tight" style={{ fontSize: "clamp(3rem, 8vw, 80px)", letterSpacing: "-0.02em" }}>
            SolarMap
          </h1>
          <p className="text-white font-normal mt-5" style={{ fontSize: "clamp(1.25rem, 3vw, 28px)" }}>
            Transformando datos urbanos en potencial solar
          </p>
          <p className="text-white/85 mt-5 max-w-[560px]" style={{ fontSize: "18px", lineHeight: 1.6 }}>
            Analizamos datos climáticos y geoespaciales para estimar el potencial solar de tejados urbanos en Madrid.
          </p>
          <div className="flex flex-wrap gap-3 justify-center mt-8">
            <Button asChild size="lg" className="bg-accent text-accent-foreground hover:bg-accent/90">
              <Link to="/mapa">Explorar mapa</Link>
            </Button>
            <Button asChild size="lg" className="bg-transparent border border-white text-white hover:bg-white hover:text-primary">
              <Link to="/analisis">Ver análisis demo</Link>
            </Button>
          </div>
          <div className="flex flex-wrap gap-x-8 gap-y-2 justify-center mt-8 text-white/90 text-sm font-medium">
            <span>✓ Sin compromiso</span>
            <span>✓ Datos abiertos ERA5</span>
            <span>✓ Proyecto académico</span>
          </div>
        </div>
      </section>

      <FullSection
        image={SEC1_IMG}
        overlay={0.45}
        align="left"
        eyebrow="Datos climáticos"
        eyebrowColor="text-accent"
        title="25 años de datos del cielo de Madrid"
        description="Radiación solar, temperatura y nubosidad horaria descargada desde Copernicus ERA5. Variables reales: ssrd_kWhm2, t2m_C, tcc."
        cta={{ label: "Saber más", to: "/quienes-somos", variant: "outline-white" }}
        fallbackBg="#1a2332"
      />

      <FullSection
        image={SEC2_IMG}
        overlay={0.5}
        align="right"
        eyebrow="Análisis geoespacial"
        eyebrowColor="text-solar"
        title="36 zonas. Cada tejado, analizado."
        description="Cuadrícula de 8×8 km sobre el área metropolitana de Madrid. Detección automática de tejados sobre ortofotos PNOA."
        cta={{ label: "Ver el mapa", to: "/mapa", variant: "outline-white" }}
        fallbackBg="#0F1A2E"
      />

      <FullSection
        image={SEC3_IMG}
        overlay={0.45}
        align="center"
        eyebrow="Resultados visuales"
        eyebrowColor="text-trust"
        title="Del dato al mapa, en segundos."
        description="Mapas interactivos, tablas de variables y un índice de potencial solar de 0 a 1 para cada tejado del área metropolitana."
        cta={{ label: "Ver análisis demo", to: "/analisis", variant: "coral" }}
        fallbackBg="#1a2332"
      />

      {/* CLOSING */}
      <section className="w-full min-h-[50vh] flex flex-col items-center justify-center text-center px-6 py-24" style={{ backgroundColor: "#0F1A2E" }}>
        <h2 className="text-white font-bold leading-tight max-w-4xl" style={{ fontSize: "clamp(2rem, 5vw, 56px)" }}>
          De los datos climáticos a decisiones energéticas más claras.
        </h2>
        <p className="text-white/80 mt-6 max-w-2xl" style={{ fontSize: "18px", lineHeight: 1.6 }}>
          SolarMap es un proyecto académico de Big Data desarrollado en la Universidad Europea de Madrid.
        </p>
        <Button asChild size="lg" variant="coral" className="mt-8">
          <Link to="/mapa">Explorar el mapa</Link>
        </Button>
      </section>
    </PageLayout>
  );
}
