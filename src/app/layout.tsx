import type { Metadata } from "next";
import "./globals.css";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "Geoportal Riesgo Agroclimático — Imbabura, Ecuador",
  description: "Portal institucional de acceso al riesgo agroclimático de cultivos andinos en las 42 parroquias de Imbabura bajo escenarios climáticos CMIP6. Integración Random Forest + Red Bayesiana. USGP 2026.",
  authors: [{ name: "Víctor Hugo Pinto Páez" }],
  keywords: ["geoportal", "Imbabura", "riesgo agroclimático", "CMIP6", "Random Forest", "Red Bayesiana", "tesis", "USGP"],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>
        <Header />
        <main>{children}</main>
        <Footer />
      </body>
    </html>
  );
}
