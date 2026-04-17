import { SITE } from "@/data/config";
import { User, Book, Award, Mail, ExternalLink } from "lucide-react";
import Avatar from "@/components/Avatar";
import { asset } from "@/lib/assets";
import PageHero from "@/components/PageHero";
import ExternalLinkGate from "@/components/ExternalLinkGate";

export const metadata = { title: "Acerca del Geoportal · Pinto Páez 2026" };

export default function AcercaPage() {
  return (
    <>
      <PageHero
        title="Acerca del Geoportal"
        subtitle="Marco institucional, autor, cita sugerida, manuscrito de referencia y contacto."
        image="geoparque_Mapa_Geoparques.jpg"
        overlayColor="rgba(10,53,88,0.45)"
        credit="Imagen: Geoparques Mundiales UNESCO · geoparque.imbabura.gob.ec"
      />

      <section className="container-prose py-12 grid md:grid-cols-3 gap-6">
        <div className="card md:col-span-2">
          <div className="flex items-center gap-4 mb-4">
            <Avatar src={asset("/img/autor_vhpp.jpg")} name="Víctor Hugo Pinto Páez" size={96}/>
            <div>
              <h2 className="text-2xl mb-0">{SITE.author}</h2>
              <div className="text-sm text-[var(--text-muted)]">Maestrando · USGP {SITE.year}</div>
            </div>
          </div>
          <p className="text-[var(--text-muted)] leading-relaxed">
            {SITE.institution} — {SITE.program}.
          </p>
          <div className="mt-4 space-y-2 text-sm">
            <div><Mail size={14} className="inline mr-2"/>Email: <a href={`mailto:${SITE.email}`}>{SITE.email}</a></div>
            <div><Award size={14} className="inline mr-2"/>ORCID: <a href={`https://orcid.org/${SITE.orcid}`} target="_blank">{SITE.orcid}</a></div>
            <div><User size={14} className="inline mr-2"/>GitHub: <a href={`https://github.com/${SITE.githubUser}`} target="_blank">{SITE.githubUser}</a></div>
          </div>
        </div>
        <div className="card bg-gradient-to-br from-[var(--primary)] to-[var(--primary-dark)] text-white">
          <Award size={28} className="mb-3"/>
          <h3 className="text-white text-xl mb-2">DOI Permanente</h3>
          <div className="text-2xl font-bold font-mono">{SITE.doi}</div>
          <ExternalLinkGate href={`https://doi.org/${SITE.doi}`} label="zenodo-acerca" className="inline-flex items-center gap-2 bg-white text-[var(--primary)] px-5 py-3 rounded-lg font-semibold mt-4 hover:bg-gray-100">
            <ExternalLink size={16}/> Abrir en Zenodo
          </ExternalLinkGate>
        </div>
      </section>

      <section className="container-prose py-10">
        <h2 className="mb-4 flex items-center gap-2"><Book/> Manuscrito de referencia</h2>
        <div className="card">
          <div className="text-xs uppercase tracking-wider text-[var(--text-muted)] font-semibold">Sometido a revisión por pares</div>
          <h3 className="text-xl mt-1 mb-3">
            Riesgo agroclimático bajo escenarios CMIP6 mediante Random Forest y Redes Bayesianas a escala parroquial en la
            provincia de Imbabura, Ecuador
          </h3>
          <p className="text-sm text-[var(--text-muted)] mb-3">
            <strong>Pinto Páez, V.H.</strong> ({SITE.year}). Manuscrito sometido a <strong>Natural Hazards</strong> (Springer Nature, ISSN 0921-030X).
          </p>
          <p className="text-sm text-[var(--text-muted)] leading-relaxed">
            El trabajo evalúa el riesgo agroclimático de cuatro cultivos andinos (papa, maíz, fréjol, quinua) en las 42 parroquias
            de Imbabura combinando Modelos de Distribución de Especies entrenados con Random Forest (16 índices agroclimáticos; AUC
            0,804–0,871) y una Red Bayesiana de 7 nodos para obtener un Índice de Riesgo compuesto (IR). Datos climáticos:
            BASD-CMIP6-PE (Fernandez-Palomino et al. 2024) con corrección de sesgo.
          </p>
        </div>
      </section>

      <section className="container-prose py-10">
        <h2 className="mb-4">Cita sugerida</h2>
        <div className="card bg-[var(--bg)] border-l-4 border-[var(--primary)]">
          <p className="font-serif text-[var(--text)] text-[15px] leading-relaxed">
            Pinto Páez, V. H. (2026). <em>Geoportal riesgo agroclimático — Imbabura, Ecuador</em> [Geoportal]. Zenodo. https://doi.org/{SITE.doi}
          </p>
        </div>
      </section>

      <section className="container-prose py-10">
        <h2 className="mb-4">Agradecimientos</h2>
        <div className="card">
          <p className="text-[var(--text-muted)] leading-relaxed">
            Un agradecimiento especial al tutor de la investigación,{" "}
            <strong>MSc. Fernando Mauricio Pavón Cevallos</strong>{" "}
            (<a href="mailto:fernando.pavon@ruminahui.gob.ec">fernando.pavon@ruminahui.gob.ec</a>),
            por su guía y supervisión en el desarrollo de este trabajo.
            <br/><br/>
            A la <strong>USGP</strong> por el marco académico e institucional; al equipo docente por la orientación metodológica;
            y a las instituciones proveedoras de datos públicos: <strong>BASD-CMIP6-PE</strong> (Fernandez-Palomino et al. 2024),
            <strong>GBIF</strong>, <strong>MapSPAM v2r0</strong> (IFPRI 2024), <strong>ESPAC 2024</strong> (INEC),
            <strong>CONALI/INEC</strong>. El autor revisó todas las decisiones metodológicas, validó los resultados y asume
            responsabilidad exclusiva del trabajo publicado.
          </p>
        </div>
      </section>

      <section className="container-prose py-10">
        <h2 className="mb-4">Stack técnico del geoportal</h2>
        <div className="card">
          <div className="grid md:grid-cols-2 gap-4 text-sm">
            <div>
              <h4 className="font-bold text-[var(--primary)] mb-2">Frontend</h4>
              <ul className="space-y-1 list-disc list-inside text-[var(--text-muted)]">
                <li>Next.js 14 (React App Router)</li>
                <li>TypeScript + Tailwind CSS</li>
                <li>MapLibre GL JS (visor cartográfico)</li>
                <li>Plotly.js (gráficos interactivos)</li>
                <li>Lucide React (iconografía)</li>
              </ul>
            </div>
            <div>
              <h4 className="font-bold text-[var(--primary)] mb-2">Datos y servicios</h4>
              <ul className="space-y-1 list-disc list-inside text-[var(--text-muted)]">
                <li>ArcGIS Online USGP ({SITE.arcgisOrg})</li>
                <li>3 Feature Services REST públicos</li>
                <li>42 PDFs + 60 Images públicos</li>
                <li>Web Map oficial con 6 bookmarks</li>
                <li>Pipeline reproducible Python (Zenodo + GitHub)</li>
              </ul>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
