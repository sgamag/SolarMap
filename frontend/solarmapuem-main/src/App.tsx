import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/context/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import Index from "./pages/Index.tsx";
import NotFound from "./pages/NotFound.tsx";
import Mapa from "./pages/Mapa.tsx";
import MapaSolar from "./pages/MapaSolar.tsx";
import AnalisisResumen from "./pages/AnalisisResumen.tsx";
import AnalisisProveedores from "./pages/AnalisisProveedores.tsx";
import AnalisisInstaladoras from "./pages/AnalisisInstaladoras.tsx";
import AnalisisDetalle from "./pages/AnalisisDetalle.tsx";
import Login from "./pages/Login.tsx";
import Registro from "./pages/Registro.tsx";
import Recuperar from "./pages/Recuperar.tsx";
import Perfil from "./pages/Perfil.tsx";
import QuienesSomos from "./pages/QuienesSomos.tsx";
import FAQ from "./pages/FAQ.tsx";
import Privacidad from "./pages/Privacidad.tsx";
import Terminos from "./pages/Terminos.tsx";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/" element={<Index />} />
            <Route path="/mapa" element={<MapaSolar />} />
            <Route path="/mapa-antiguo" element={<Mapa />} />
            <Route path="/analisis" element={<ProtectedRoute><AnalisisResumen /></ProtectedRoute>} />
            <Route path="/analisis/resumen" element={<ProtectedRoute><AnalisisResumen /></ProtectedRoute>} />
            <Route path="/analisis/proveedores" element={<ProtectedRoute><AnalisisProveedores /></ProtectedRoute>} />
            <Route path="/analisis/instaladoras" element={<ProtectedRoute><AnalisisInstaladoras /></ProtectedRoute>} />
            <Route path="/analisis/detalle" element={<ProtectedRoute><AnalisisDetalle /></ProtectedRoute>} />
            <Route path="/login" element={<Login />} />
            <Route path="/registro" element={<Registro />} />
            <Route path="/recuperar" element={<Recuperar />} />
            <Route path="/perfil" element={<ProtectedRoute><Perfil /></ProtectedRoute>} />
            <Route path="/quienes-somos" element={<QuienesSomos />} />
            <Route path="/faq" element={<FAQ />} />
            <Route path="/privacidad" element={<Privacidad />} />
            <Route path="/terminos" element={<Terminos />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
