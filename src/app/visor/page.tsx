import dynamic from "next/dynamic";
const MapViewer = dynamic(() => import("@/components/MapViewer"), { ssr: false });

export const metadata = {
  title: "Visor Cartográfico · Geoportal Riesgo Agroclimático Imbabura",
  description: "Visor cartográfico interactivo MapLibre GL JS consumiendo Feature Services REST del ArcGIS Online de USGP.",
};

export default function VisorPage() {
  return <MapViewer />;
}
