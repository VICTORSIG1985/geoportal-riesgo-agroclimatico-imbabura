import Link from "next/link";
import { Database, Code, FileJson, Download, ExternalLink, Shield, Map, FileText, Info, FileDown } from "lucide-react";
import { SERVICES, SITE } from "@/data/config";
import PageHero from "@/components/PageHero";
import ExternalLinkGate from "@/components/ExternalLinkGate";
import DataDownloadGate from "@/components/DataDownloadGate";

export const metadata = { title: "Datos Abiertos · Geoportal Imbabura" };

export default function DatosPage() {
  const layers = [SERVICES.flParroquias, SERVICES.flRiesgoLong, SERVICES.flPrioridad];
  return (
    <>
      <PageHero
        title="Datos Abiertos"
        subtitle="Acceso libre y reproducible a las 3 capas de datos REST, al código fuente, al dataset autoritativo y a los metadatos ISO 19115. Licencia CC BY 4.0."
        image="wm_yahuarcocha.jpg"
        overlayColor="rgba(15,76,129,0.4)"
        credit="Imagen: Laguna de Yahuarcocha (Ibarra) — Wikimedia Commons · CC BY-SA"
      />

      <section className="container-prose py-8">
        <div className="card bg-blue-50 border-l-4 border-blue-500">
          <h3 className="text-lg mb-2 flex items-center gap-2"><Info size={18}/> ¿Cómo usar estos datos?</h3>
          <ul className="text-sm text-[var(--text-muted)] space-y-1 list-disc list-inside">
            <li><strong>Para consulta visual:</strong> use nuestro <Link href="/visor" className="text-[var(--primary)] font-semibold">Visor Cartográfico</Link> — mapa interactivo con filtros y popups.</li>
            <li><strong>Para descarga inmediata:</strong> botón <em>Descargar GeoJSON</em> debajo de cada capa.</li>
            <li><strong>Para integrar en tu SIG:</strong> copia la <em>URL del servicio de capas</em> y pégala en ArcGIS Pro, QGIS, R (sf), Python (geopandas, arcgis).</li>
            <li><strong>Para reproducir el análisis:</strong> descarga el código Python por fases (sección Código fuente, abajo).</li>
          </ul>
        </div>
      </section>

      <section className="container-prose py-6">
        <h2 className="mb-6 flex items-center gap-3"><Database className="text-[var(--primary)]"/> Capas de datos geoespaciales públicas</h2>
        <div className="space-y-5">
          {layers.map(L => (
            <div key={L.id} className="card">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 bg-[var(--primary)] text-white rounded-lg flex items-center justify-center flex-shrink-0">
                  <Map size={22}/>
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="text-xl font-bold">{L.title}</h3>
                  <p className="text-sm text-[var(--text-muted)] mt-1">{L.desc}</p>
                  <div className="mt-3 flex items-center gap-4 flex-wrap text-xs text-[var(--text-muted)]">
                    <span><strong>{L.n}</strong> registros</span>
                    <span>Polígonos · WGS84</span>
                    <span>Formatos: JSON · GeoJSON · PBF</span>
                  </div>
                  <div className="text-xs font-mono bg-[var(--bg)] px-3 py-2 rounded mt-3 break-all select-all">
                    {L.url}
                  </div>
                </div>
              </div>
              <div className="mt-4 grid sm:grid-cols-2 lg:grid-cols-5 gap-2">
                <DataDownloadGate
                  sourceUrl={`${L.url}/query?where=1%3D1&outFields=*&f=geojson`}
                  fileName={`${L.title}.geojson`}
                  format="geojson" tipo="geojson"
                  className="btn-primary text-sm justify-center"
                  ariaLabel={`Descargar ${L.title} GeoJSON`}
                >
                  <Download size={14}/> GeoJSON
                </DataDownloadGate>
                <DataDownloadGate
                  sourceUrl={`${L.url}/query?where=1%3D1&outFields=*&f=geojson`}
                  fileName={`${L.title}.csv`}
                  format="csv" tipo="geojson"
                  className="btn-secondary text-sm justify-center"
                  ariaLabel={`Descargar ${L.title} CSV`}
                >
                  <FileDown size={14}/> CSV (Excel)
                </DataDownloadGate>
                <DataDownloadGate
                  sourceUrl={`${L.url}/query?where=1%3D1&outFields=*&f=geojson`}
                  fileName={`${L.title}.md`}
                  format="md" tipo="geojson"
                  mdTitle={`Datos — ${L.title}`}
                  className="btn-secondary text-sm justify-center"
                  ariaLabel={`Descargar ${L.title} Markdown`}
                >
                  <FileDown size={14}/> Markdown
                </DataDownloadGate>
                <DataDownloadGate
                  sourceUrl={`${L.url}?f=json`}
                  fileName={`${L.title}_metadata.json`}
                  format="json" tipo="geojson"
                  className="btn-secondary text-sm justify-center"
                  ariaLabel={`Descargar metadatos ${L.title}`}
                >
                  <FileJson size={14}/> Metadatos
                </DataDownloadGate>
                <Link href="/visor" className="btn-secondary text-sm justify-center">
                  <Map size={14}/> Abrir en visor
                </Link>
              </div>
              <div className="mt-2 text-[11px] text-[var(--text-muted)]">
                🔒 Toda descarga requiere registro conforme <strong>LOPDP Ecuador</strong> (datos tratados con fines estadísticos y de investigación, como acordado con el usuario final).
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="container-prose py-10">
        <h2 className="mb-6 flex items-center gap-3"><Code className="text-[var(--primary)]"/> Código fuente — 22 scripts Python en 5 fases</h2>
        <p className="text-[var(--text-muted)] mb-5">
          Los scripts se publican <strong>por fase metodológica</strong> para trazabilidad científica y replicabilidad.
          Se entregan <strong>sin credenciales ni claves API</strong>; el usuario debe configurar sus propias rutas de entrada/salida.
        </p>
        <Link href="/descargas" className="btn-primary">
          <Download size={16}/> Ver y descargar scripts por fase
        </Link>
      </section>

      <section className="container-prose py-10">
        <h2 className="mb-6 flex items-center gap-3"><FileText className="text-[var(--primary)]"/> Manuscrito y archivo permanente</h2>
        <div className="grid md:grid-cols-2 gap-5">
          <div className="card">
            <h3 className="text-xl mb-2">GitHub del pipeline</h3>
            <p className="text-sm text-[var(--text-muted)] mb-3">
              Repositorio con el código completo, documentación metodológica (21 documentos ISO 19115) y el archivo de
              resultados autoritativo <code>riesgo_parroquial_20260226_172751.csv</code>.
            </p>
            <ExternalLinkGate href={`https://github.com/${SITE.githubUser}/${SITE.githubRepo}`} label="github-pipeline" className="btn-primary">
              <ExternalLink size={16}/> github.com/{SITE.githubUser}/{SITE.githubRepo}
            </ExternalLinkGate>
          </div>
          <div className="card">
            <h3 className="text-xl mb-2">Zenodo — DOI permanente</h3>
            <p className="text-sm text-[var(--text-muted)] mb-3">
              Snapshot versionado citable académicamente. Incluye código, datos derivados, manuscrito y documentación.
            </p>
            <ExternalLinkGate href={`https://doi.org/${SITE.doi}`} label="zenodo-doi" className="inline-flex items-center gap-2 bg-[#1f5fa8] text-white px-5 py-3 rounded-lg font-semibold hover:bg-[#184781]">
              <ExternalLink size={16}/> doi.org/{SITE.doi}
            </ExternalLinkGate>
          </div>
        </div>
      </section>

      <section className="container-prose py-10">
        <h2 className="mb-6 flex items-center gap-3"><Shield className="text-[var(--primary)]"/> Licencia</h2>
        <div className="card bg-gradient-to-br from-[var(--bg)] to-white">
          <div className="flex items-center gap-3 mb-3">
            <img src="https://licensebuttons.net/l/by/4.0/88x31.png" alt="CC BY 4.0" className="w-24"/>
            <div>
              <h3 className="text-xl mb-0">Creative Commons Atribución 4.0 Internacional</h3>
              <div className="text-xs text-[var(--text-muted)]">CC BY 4.0</div>
            </div>
          </div>
          <p className="text-sm text-[var(--text-muted)] mb-3">
            Está permitido copiar, redistribuir, adaptar y transformar el material para cualquier propósito, incluso comercial,
            bajo las siguientes condiciones:
          </p>
          <ul className="text-sm space-y-1 list-disc list-inside">
            <li><strong>Atribución:</strong> citar a Pinto Páez, V. H. (2026) con DOI <a href={`https://doi.org/${SITE.doi}`} target="_blank" rel="noopener">{SITE.doi}</a></li>
            <li>No hay restricciones adicionales que limiten los usos autorizados por la licencia</li>
            <li><strong>Solo lectura:</strong> las capas de datos y el visor son públicos pero <strong>no permiten modificación</strong>; cualquier análisis derivado debe realizarse sobre copias locales.</li>
          </ul>
        </div>
      </section>
    </>
  );
}
