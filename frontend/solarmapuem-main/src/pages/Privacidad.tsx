import StaticPage from "@/components/StaticPage";

export default function Privacidad() {
  return (
    <StaticPage
      title="Política de privacidad"
      intro="Última actualización: mayo de 2026. SolarMap es un proyecto académico sin fines comerciales."
    >
      <div className="space-y-8 text-base leading-relaxed text-muted-foreground">
        <section>
          <h2 className="text-xl font-extrabold text-primary mb-2">1. Responsable del tratamiento</h2>
          <p>
            El responsable de la presente plataforma es el equipo académico SolarMap, vinculado a la
            asignatura Proyectos de Big Data II de la Universidad Europea de Madrid. SolarMap no opera
            como entidad comercial y no realiza tratamientos de datos con finalidad de lucro.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-extrabold text-primary mb-2">2. Datos que recogemos</h2>
          <p>
            En la versión actual (prototipo académico) no se recogen datos personales en servidor. Los
            formularios de registro, inicio de sesión y recuperación de contraseña son simulados y los
            datos introducidos se almacenan exclusivamente en el almacenamiento local del navegador del
            usuario (<code>localStorage</code>), sin transmisión a terceros.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-extrabold text-primary mb-2">3. Datos climáticos y cartográficos</h2>
          <p>
            SolarMap utiliza datos públicos y abiertos: reanálisis ERA5 del programa Copernicus de la Unión
            Europea, ortofotos PNOA del Instituto Geográfico Nacional y geometrías edificatorias de
            OpenStreetMap. Ninguno de estos conjuntos contiene información personal identificable.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-extrabold text-primary mb-2">4. Cookies y tecnologías similares</h2>
          <p>
            La plataforma no utiliza cookies de seguimiento ni herramientas de análisis publicitario. Únicamente
            se emplean mecanismos técnicos imprescindibles para mantener la sesión simulada del usuario.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-extrabold text-primary mb-2">5. Derechos del usuario</h2>
          <p>
            Conforme al Reglamento (UE) 2016/679 (RGPD) y a la Ley Orgánica 3/2018 de Protección de Datos,
            cualquier usuario podrá ejercer los derechos de acceso, rectificación, supresión, oposición,
            limitación y portabilidad escribiendo a <strong>solarmap@uem.es</strong>. Dado que la versión
            actual no almacena datos personales en servidor, el ejercicio de estos derechos se limita a la
            información local del propio navegador, que el usuario puede borrar en cualquier momento.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-extrabold text-primary mb-2">6. Cambios futuros</h2>
          <p>
            Cuando el proyecto evolucione hacia un servicio con backend persistente, se actualizará esta
            política para reflejar las bases jurídicas, plazos de conservación y encargados de tratamiento
            que correspondan. Cualquier cambio relevante se comunicará en esta misma página.
          </p>
        </section>
      </div>
    </StaticPage>
  );
}
