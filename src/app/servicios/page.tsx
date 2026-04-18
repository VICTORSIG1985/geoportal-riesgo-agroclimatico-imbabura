import Link from "next/link";
import { Map, Image as ImgIcon, FileText, Database, Bot, Microscope, BarChart3, Info, ExternalLink } from "lucide-react";
import { SERVICES, SITE } from "@/data/config";
import PageHero from "@/components/PageHero";

export default function Servicios() {
  const services = [
    { href: "/visor", icon: Map, color: "#B2182B", title: "Visor Cartográfico",
      desc: "Visor interactivo con tres capas publicadas (Parroquias Base, Riesgo Long, Priorización Final), filtros dinámicos por cultivo × SSP × horizonte, leyenda, bookmarks territoriales, búsqueda por parroquia y popups con descarga directa de fichas.",
      tech: "ArcGIS Instant App (Sidebar) + 3 Feature Services REST públicos" },
    { href: "/galeria", icon: ImgIcon, color: "#0F4C81", title: "Galería Científica",
      desc: "60 figuras cartográficas organizadas por 6 grupos temáticos: síntesis (2), panel resumen Fig. 4 (1), por cultivo (4), por SSP (3), cambio temporal (12), individuales (36) e infografías (2).",
      tech: "Images hospedadas en ArcGIS Online · acceso público REST" },
    { href: "/fichas", icon: FileText, color: "#228B6E", title: "Fichas Parroquiales (42 PDF)",
      desc: "Una ficha PDF pública por parroquia, con IR medio y máximo bajo los 9 escenarios, cultivo más vulnerable, mensaje de priorización y recomendación operativa para los GADs.",
      tech: "42 items PDF en ArcGIS Online · descarga directa" },
    { href: "/metodologia", icon: Microscope, color: "#6B4E9B", title: "Metodología",
      desc: "Pipeline de 22 scripts Python en 5 fases: preparación climática BASD-CMIP6-PE, 16 índices agroclimáticos, exposición (MapSPAM+ESPAC), Random Forest k=5 con validación espacial, Red Bayesiana 7 nodos.",
      tech: "Random Forest · AUC 0,804-0,871 · Red Bayesiana con pgmpy · 1.512 inferencias" },
    { href: "/resultados", icon: BarChart3, color: "#EF8A62", title: "Resultados Interactivos",
      desc: "Ranking dinámico de 42 parroquias, gráficos interactivos del IR por cultivo/SSP/horizonte, tablas completas (T4-T7 del manuscrito) y exploración parroquial filtrable.",
      tech: "Plotly + tabla + datos en vivo desde Feature Service" },
    { href: "/datos", icon: Database, color: "#333333", title: "Datos Abiertos · APIs",
      desc: "3 Feature Services REST públicos, catálogo de metadatos ISO 19115, descarga en GeoJSON/Shapefile/FGDB, código fuente Python (22 scripts) en GitHub y DOI permanente en Zenodo.",
      tech: "PostgreSQL/PostGIS en ArcGIS Managed Services · OGC REST · licencia CC BY 4.0" },
    { href: "/asistente", icon: Bot, color: "#4F46E5", title: "Asistente IA (RAG)",
      desc: "Consulta en lenguaje natural sobre la metodología, cultivos, escenarios y resultados. Retrieval-Augmented Generation sobre el manuscrito completo (Natural Hazards, 2026).",
      tech: "Vercel AI SDK + Claude API · retrieval sobre texto del manuscrito" },
    { href: "/acerca", icon: Info, color: "#4A5568", title: "Acerca del Geoportal",
      desc: "Autor, institución, manuscrito de referencia, cita sugerida, licencia de uso, agradecimientos y contacto institucional.",
      tech: "ORCID · DOI Zenodo · manuscrito Natural Hazards" },
  ];

  return (
    <>
      <PageHero
        title="Servicios del Geoportal"
        subtitle="Nueve servicios integrados que combinan visualización cartográfica, descarga de datos, consulta científica e inteligencia artificial."
        image="wm_angochagua.jpg"
        overlayColor="rgba(15,76,129,0.35)"
        credit="Imagen: Angochagua (Ibarra) · Wikimedia Commons · CC BY-SA"
      />

      <section className="container-prose py-12 space-y-6">
        {services.map(s => {
          const Icon = s.icon;
          return (
            <div key={s.href} className="card grid md:grid-cols-[auto_1fr_auto] gap-6 items-start">
              <div className="w-16 h-16 rounded-xl flex items-center justify-center text-white flex-shrink-0" style={{ background: s.color }}>
                <Icon size={30}/>
              </div>
              <div className="min-w-0">
                <h3 className="text-2xl mb-2">{s.title}</h3>
                <p className="text-[var(--text-muted)] mb-3 leading-relaxed">{s.desc}</p>
                <div className="text-xs text-[var(--text-muted)] bg-[var(--bg)] inline-block px-3 py-1 rounded-full">
                  <strong>Stack:</strong> {s.tech}
                </div>
              </div>
              <div className="flex flex-col gap-2">
                <Link href={s.href} className="btn-primary">Acceder</Link>
              </div>
            </div>
          );
        })}
      </section>
    </>
  );
}
