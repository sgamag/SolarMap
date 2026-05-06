import StaticPage from "@/components/StaticPage";

export default function Terminos() {
  return (
    <StaticPage
      title="Términos y condiciones"
      intro="Condiciones de uso de la plataforma SolarMap. Última actualización: mayo de 2026."
    >
      <div className="space-y-8 text-base leading-relaxed text-muted-foreground">
        <section>
          <h2 className="text-xl font-extrabold text-primary mb-2">1. Naturaleza académica del servicio</h2>
          <p>
            SolarMap es un proyecto académico desarrollado en el marco de la asignatura Proyectos de Big
            Data II de la Universidad Europea de Madrid. La plataforma se ofrece exclusivamente con fines
            docentes, divulgativos e investigadores. No constituye un servicio comercial ni un asesoramiento
            técnico profesional.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-extrabold text-primary mb-2">2. Aceptación de las condiciones</h2>
          <p>
            El acceso y uso de SolarMap implica la aceptación plena de los presentes términos. Si el usuario
            no está de acuerdo con alguno de ellos, deberá abstenerse de utilizar la plataforma.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-extrabold text-primary mb-2">3. Validez de los resultados</h2>
          <p>
            Los índices y estimaciones mostrados son aproximaciones basadas en datos climáticos abiertos
            (ERA5/Copernicus) y en geometrías de tejado obtenidas de fuentes públicas. Los resultados pueden
            presentar errores derivados de la resolución espacial, de las limitaciones del reanálisis y de la
            detección automática. SolarMap no garantiza la exactitud de las estimaciones y no se hace
            responsable de decisiones de inversión, dimensionamiento o instalación tomadas a partir de
            ellas.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-extrabold text-primary mb-2">4. Uso permitido</h2>
          <p>
            Se autoriza el uso personal, académico y de investigación. Está prohibido el uso comercial directo,
            la reventa de los resultados y la realización de ataques o ingeniería inversa sobre la
            infraestructura. Cualquier reutilización debe citar adecuadamente al equipo SolarMap y a las
            fuentes de datos originales.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-extrabold text-primary mb-2">5. Propiedad intelectual</h2>
          <p>
            El código fuente, los textos y las visualizaciones desarrolladas por el equipo se publican bajo
            licencia abierta para fines educativos. Las marcas, logotipos y conjuntos de datos de terceros
            (Copernicus, IGN, OpenStreetMap, Universidad Europea de Madrid) pertenecen a sus respectivos
            titulares y se utilizan respetando sus condiciones.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-extrabold text-primary mb-2">6. Limitación de responsabilidad</h2>
          <p>
            En la máxima medida permitida por la ley, el equipo SolarMap y la Universidad Europea de Madrid
            quedan exentos de responsabilidad por daños directos o indirectos derivados del uso de la
            plataforma, incluidas decisiones técnicas, económicas o regulatorias adoptadas a partir de la
            información mostrada.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-extrabold text-primary mb-2">7. Legislación aplicable</h2>
          <p>
            Estas condiciones se rigen por la legislación española. Cualquier controversia se someterá a los
            juzgados y tribunales de Madrid, salvo que la normativa aplicable disponga otra cosa.
          </p>
        </section>
      </div>
    </StaticPage>
  );
}
