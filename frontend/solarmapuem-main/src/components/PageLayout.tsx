import { ReactNode } from "react";
import NavBar from "./NavBar";
import Footer from "./Footer";

interface PageLayoutProps {
  children: ReactNode;
  withFooter?: boolean;
  transparentNav?: boolean;
}

export default function PageLayout({ children, withFooter = true, transparentNav = false }: PageLayoutProps) {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <NavBar transparent={transparentNav} />
      <main className="flex-1">{children}</main>
      {withFooter && <Footer />}
    </div>
  );
}
