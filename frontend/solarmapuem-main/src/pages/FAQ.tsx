import StaticPage from "@/components/StaticPage";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";

const faqs = [
  {
    q: "¿Qué es SolarMap?",
    a: "SolarMap es una plataforma académica de Big Data que estima el potencial solar de tejados urbanos en el área metropolitana de Madrid. Combina datos climáticos históricos de Copernicus ERA5, detección automática de tejados mediante IA sobre ortofotos, y un modelo de simulación económica para estimar el ahorro y retorno de inversión de una instalación fotovoltaica.",
  },
  {
    q: "¿Los datos son reales?",
    a: "Los datos climáticos provienen de fuentes reales: Copernicus ERA5 para radiación solar, temperatura y nubosidad, y ESIOS (Red Eléctrica de España) para precios de la luz. Los tejados detectados provienen de un modelo de IA entrenado sobre ortofotos reales PNOA. Los resultados económicos mostrados actualmente son simulados para fines de demostración, pendientes de conexión al backend.",
  },
  {
    q: "¿Cómo se calcula el potencial solar?",
    a: "El potencial solar de cada tejado se calcula combinando cuatro factores: radiación solar normalizada, penalización por cobertura nubosa, penalización térmica y horas de sol. El resultado es un índice entre 0 y 1. Además, se aplica un factor de orientación que varía de 1,00 para orientación Sur hasta 0,60 para orientación Norte.",
  },
  {
    q: "¿Qué información utiliza el sistema?",
    a: "El sistema utiliza: datos climáticos horarios de ERA5 agregados por zona y mes, geometría de tejados detectados por IA (área bruta, orientación en grados, orientación cardinal), y precios de la luz proyectados a 30 años bajo tres escenarios económicos: pesimista, plano y verde.",
  },
  {
    q: "¿Qué territorio cubre?",
    a: "SolarMap cubre el área metropolitana de Madrid dividida en 36 zonas de 8×8 km aproximadamente, abarcando municipios de la Comunidad de Madrid.",
  },
  {
    q: "¿Cómo se calcula el retorno de inversión?",
    a: "La energía generada anual se estima como: número de paneles × potencia del panel (kW) × horas de sol pico según orientación × 0,80 de rendimiento del sistema. El ahorro anual se calcula multiplicando la energía generada por el precio de la luz predicho por el modelo para cada año y escenario. El tiempo de amortización y el ROI se proyectan a 30 años.",
  },
];

export default function FAQ() {
  return (
    <StaticPage
      title="Preguntas frecuentes"
      intro="Respuestas sobre la metodología, los datos y los límites de SolarMap."
    >
      <Accordion type="single" collapsible className="w-full">
        {faqs.map((f, i) => (
          <AccordionItem key={i} value={`item-${i}`}>
            <AccordionTrigger className="text-left text-base font-bold">{f.q}</AccordionTrigger>
            <AccordionContent className="text-base leading-relaxed text-muted-foreground">
              {f.a}
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </StaticPage>
  );
}
