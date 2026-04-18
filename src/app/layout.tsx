import type { Metadata } from "next";
import "./globals.css";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

const SITE_URL = "https://victorsig1985.github.io/geoportal-riesgo-agroclimatico-imbabura";
const OG_IMAGE = `${SITE_URL}/img/imbabura_geoparque_slide1.png`;

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Geoportal Riesgo Agroclimático — Imbabura, Ecuador",
    template: "%s · Geoportal Riesgo Agroclimático Imbabura",
  },
  description: "Portal de acceso al riesgo agroclimático de cultivos andinos en las 42 parroquias de Imbabura bajo escenarios climáticos CMIP6. Integración Random Forest + Red Bayesiana. USGP 2026.",
  authors: [{ name: "Víctor Hugo Pinto Páez" }],
  keywords: ["geoportal", "Imbabura", "riesgo agroclimático", "CMIP6", "Random Forest", "Red Bayesiana", "USGP"],
  robots: { index: true, follow: true },
  openGraph: {
    type: "website",
    locale: "es_EC",
    url: SITE_URL + "/",
    siteName: "Geoportal Riesgo Agroclimático — Imbabura",
    title: "Geoportal Riesgo Agroclimático — Imbabura, Ecuador",
    description: "Evaluación integrada del riesgo agroclimático para cultivos andinos (papa, maíz, fréjol, quinua) en 42 parroquias de Imbabura bajo escenarios CMIP6. Visor cartográfico, fichas parroquiales, datos abiertos y asistente IA.",
    images: [{
      url: OG_IMAGE,
      width: 1920,
      height: 630,
      alt: "Paisaje del Geoparque Mundial UNESCO Imbabura — Lago San Pablo y volcán Imbabura",
    }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Geoportal Riesgo Agroclimático — Imbabura, Ecuador",
    description: "Riesgo agroclimático para cultivos andinos en 42 parroquias de Imbabura bajo CMIP6. Random Forest + Red Bayesiana. USGP.",
    images: [OG_IMAGE],
  },
  other: {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), usb=(), magnetometer=(), gyroscope=(), accelerometer=(), payment=(), geolocation=(self)",
  },
};

// Content Security Policy — balance entre seguridad y funcionalidad de ArcGIS/CartoDB
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
