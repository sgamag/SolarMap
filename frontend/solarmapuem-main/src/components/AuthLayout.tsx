import { ReactNode } from "react";
import { Link } from "react-router-dom";
import authImg from "@/assets/auth-side.jpg";
import logo from "@/assets/logo.png";
import PrototypeBanner from "@/components/PrototypeBanner";

export default function AuthLayout({ children, overlayText }: { children: ReactNode; overlayText: string }) {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <PrototypeBanner />
      <div className="flex-1 grid lg:grid-cols-2">
        <div className="relative hidden lg:block">
          <img src={authImg} alt="Paneles solares" className="absolute inset-0 h-full w-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-tr from-primary/80 via-primary/40 to-transparent" />
          <div className="absolute inset-0 flex flex-col justify-between p-10 text-primary-foreground">
            <Link to="/" className="flex items-center gap-2 font-extrabold text-lg">
              <img src={logo} alt="SolarMap" className="h-10 w-10 object-contain" />
              SolarMap
            </Link>
            <h2 className="text-4xl xl:text-5xl font-extrabold leading-tight max-w-md">
              {overlayText}
            </h2>
          </div>
        </div>
        <div className="flex items-center justify-center p-6 md:p-12 bg-background">
          <div className="w-full max-w-md">{children}</div>
        </div>
      </div>
    </div>
  );
}
