# ☀️ SolarMap — Frontend

Interfaz web de SolarMap, plataforma de análisis del potencial solar de tejados urbanos en el área metropolitana de Madrid. Permite a los usuarios localizar su vivienda en el mapa, obtener un análisis del potencial solar de su tejado y simular el retorno de inversión de una instalación fotovoltaica.

🌐 **Producción:** [solarmapuem.lovable.app](https://solarmapuem.lovable.app)

---

## Stack tecnológico

| Tecnología | Uso |
|---|---|
| React 18 + TypeScript | Framework principal |
| Vite | Bundler y servidor de desarrollo |
| Tailwind CSS + shadcn/ui | Estilos y componentes |
| React Router 6 | Navegación SPA |
| React Leaflet | Mapa interactivo con tiles CartoDB |
| Recharts | Gráficos y sparklines |
| React Query | Gestión de estado asíncrono |
| React Hook Form + Zod | Formularios con validación |
| Lucide React | Iconografía |

---

## Instalación

### Requisitos

- Node.js 18 o superior

### Pasos

```bash
git clone https://github.com/TU_USUARIO/solarmapuem.git
cd solarmapuem
npm install
npm run dev
```

Disponible en `http://localhost:5173`

### Otros comandos

```bash
npm run build     # Compilar para producción
npm run preview   # Previsualizar build de producción
npm run lint      # Ejecutar ESLint
npm run test      # Ejecutar tests con Vitest
```

---

## Estructura del proyecto

```
src/
├── assets/          # Imágenes
├── components/      # Componentes reutilizables
│   ├── ui/          # Componentes base (shadcn/ui)
│   ├── NavBar.tsx
│   ├── Footer.tsx
│   ├── DataCard.tsx
│   ├── PotentialBar.tsx
│   ├── SparklineChart.tsx
│   ├── VariableTable.tsx
│   └── StepIndicator.tsx
├── context/
│   └── AuthContext.tsx   # Contexto global de autenticación
├── data/
│   └── mockData.ts       # Datos centralizados
├── pages/               # Una carpeta por ruta
└── App.tsx              # Routing principal
```

---

## Páginas

| Ruta | Descripción | Acceso |
|---|---|---|
| `/` | Home con hero, características y CTA | Público |
| `/mapa` | Mapa interactivo con tiles ERA5 y tejados detectados | Público |
| `/analisis` | Dashboard de análisis solar y simulación ROI | 🔒 Sesión |
| `/login` | Inicio de sesión | Público |
| `/registro` | Creación de cuenta | Público |
| `/recuperar` | Recuperación de contraseña | Público |
| `/perfil` | Datos del usuario y direcciones guardadas | 🔒 Sesión |
| `/quienes-somos` | Información del equipo y proyecto | Público |
| `/faq` | Preguntas frecuentes | Público |
| `/privacidad` | Política de privacidad | Público |
| `/terminos` | Términos y condiciones | Público |

---

## Funcionalidades principales

- **Mapa interactivo** con 36 tiles de 8×8 km sobre la Comunidad de Madrid coloreados por potencial solar y polígonos de tejados detectados clickeables
- **Flujo de análisis** en tres pasos: resumen simple → selección de proveedor y panel → análisis detallado con ROI por escenario
- **Simulación económica** con tres escenarios (pesimista, plano y verde) proyectados a 30 años
- **Dashboard Power BI** embebido en la sección de análisis
- **Direcciones favoritas** guardadas en el perfil del usuario
- **Generación de informes** en PDF con los resultados del análisis
- **Autenticación** con rutas protegidas

---

*Universidad Europea de Madrid · Big Data II · 2025–2026*
