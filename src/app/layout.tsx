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

// Content Security Policy — balance entre seguridad y funcionalidad de ArcGIS/CartoDB
// Nota: 'unsafe-inline' / 'unsafe-eval' son necesarios para MapLibre GL JS y Next.js export.
// Se documenta abiertamente en GEOPORTAL_ENTREGA_FINAL.md como limitación conocida de GH Pages.
const CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://*.arcgis.com https://*.cartocdn.com",
  "style-src 'self' 'unsafe-inline' https://*.cartocdn.com https://fonts.googleapis.com",
  "img-src 'self' data: blob: https://*.arcgis.com https://*.arcgisonline.com https://*.cartocdn.com https://licensebuttons.net https://tile.openstreetmap.org https://*.tile.openstreetmap.org https://upload.wikimedia.org https://commons.wikimedia.org",
  "font-src 'self' data: https://fonts.gstatic.com https://*.cartocdn.com",
  "connect-src 'self' https://*.arcgis.com https://*.arcgisonline.com https://*.cartocdn.com https://api.anthropic.com https://nominatim.openstreetmap.org https://tile.openstreetmap.org https://*.tile.openstreetmap.org",
  "worker-src 'self' blob:",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self' https://*.arcgis.com",
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
