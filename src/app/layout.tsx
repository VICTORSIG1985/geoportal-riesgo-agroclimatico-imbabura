import type { Metadata } from "next";
import "./globals.css";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "Geoportal Riesgo Agroclimático — Imbabura, Ecuador",
  description: "Portal institucional de acceso al riesgo agroclimático de cultivos andinos en las 42 parroquias de Imbabura bajo escenarios climáticos CMIP6. Integración Random Forest + Red Bayesiana. USGP 2026.",
  authors: [{ name: "Víctor Hugo Pinto Páez" }],
  keywords: ["geoportal", "Imbabura", "riesgo agroclimático", "CMIP6", "Random Forest", "Red Bayesiana", "tesis", "USGP"],
  robots: { index: true, follow: true },
  other: {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
  },
};

// Política de seguridad de contenido (CSP) — restringe orígenes de scripts, estilos, imágenes y fetches
const CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://basemaps.cartocdn.com",
  "style-src 'self' 'unsafe-inline' https://basemaps.cartocdn.com https://fonts.googleapis.com",
  "img-src 'self' data: blob: https://www.arcgis.com https://services.arcgis.com https://services.arcgisonline.com https://basemaps.cartocdn.com https://licensebuttons.net https://tiles.arcgis.com https://tile.openstreetmap.org https://*.tile.openstreetmap.org https://upload.wikimedia.org",
  "font-src 'self' data: https://fonts.gstatic.com",
  "connect-src 'self' https://www.arcgis.com https://services.arcgis.com https://*.arcgis.com https://api.anthropic.com https://nominatim.openstreetmap.org https://basemaps.cartocdn.com https://tiles.arcgis.com https://*.tile.openstreetmap.org",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self' https://services.arcgis.com",
  "object-src 'none'",
  "upgrade-insecure-requests",
].join("; ");

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <head>
        <meta httpEquiv="Content-Security-Policy" content={CSP}/>
        <meta name="referrer" content="strict-origin-when-cross-origin"/>
      </head>
      <body>
        <Header />
        <main>{children}</main>
        <Footer />
      </body>
    </html>
  );
}
