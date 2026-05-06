import StaticPage from "@/components/StaticPage";

export default function QuienesSomos() {
  return (
    <StaticPage
      title="Sobre SolarMap"
      intro="Proyectos de Big Data · Universidad Europea de Madrid."
    >
      <div className="space-y-8">
        <p className="text-base leading-relaxed text-muted-foreground">
          SolarMap es un proyecto académico desarrollado en el marco de la asignatura
          <strong> Proyectos de Big Data</strong> de la Universidad Europea de Madrid. Su objetivo es
          estimar el potencial solar de tejados urbanos en el área metropolitana de Madrid,
          combinando datos climáticos reales con análisis geoespacial automatizado.
        </p>

        <section>
          <h2 className="text-2xl font-extrabold text-primary mb-3">Qué hacemos</h2>
          <p className="text-base leading-relaxed text-muted-foreground">
            La plataforma integra datos climáticos históricos procedentes del
            <strong> Copernicus Climate Data Store (ERA5)</strong>, información sobre precios de la
            energía de <strong>ESIOS (Red Eléctrica de España)</strong> y detección automática de
            tejados mediante modelos de inteligencia artificial sobre ortofotos. El territorio se
            divide en 36 zonas de 8×8 km que cubren la Comunidad de Madrid, permitiendo calcular el
            potencial solar de cada tejado detectado y estimar el retorno económico de una
            instalación fotovoltaica.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-extrabold text-primary mb-3">Arquitectura</h2>
          <p className="text-base leading-relaxed text-muted-foreground">
            El sistema sigue una arquitectura <strong>Data Lake por capas (Bronze, Silver y Gold)</strong>
            desplegada sobre HDFS con Docker, con un Data Warehouse relacional como capa de consumo
            final alimentado por tres Data Marts: <strong>Climatología</strong>,
            <strong> Interacción Web</strong> y <strong>ROI</strong>.
          </p>
        </section>

        <p className="italic text-sm text-muted-foreground pt-4 border-t border-border">
          Proyecto académico sin fines comerciales · Universidad Europea de Madrid · 2026
        </p>
      </div>
    </StaticPage>
  );
}
