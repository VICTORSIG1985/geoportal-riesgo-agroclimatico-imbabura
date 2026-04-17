import { Database, Code, FileJson, Download, ExternalLink, Shield } from "lucide-react";
import { SERVICES, SITE } from "@/data/config";

export const metadata = { title: "Datos Abiertos · Geoportal Imbabura" };

export default function DatosPage() {
  const layers = [SERVICES.flParroquias, SERVICES.flRiesgoLong, SERVICES.flPrioridad];
  return (
    <>
      <section className="bg-[#333] text-white py-14">
        <div className="container-prose">
          <h1 className="text-white mb-3">Datos Abiertos</h1>
          <p className="text-xl opacity-90 max-w-3xl">
            Acceso libre y reproducible a los 3 Feature Services REST, al código fuente (22 scripts Python), al dataset autoritativo
            y a los metadatos ISO 19115. Licencia CC BY 4.0.
          </p>
        </div>
      </section>

      <section className="container-prose py-12">
        <h2 className="mb-6 flex items-center gap-3"><Database className="text-[var(--primary)]"/> Feature Services REST públicos</h2>
        <div className="space-y-4">
          {layers.map(L => (
            <div key={L.id} className="card">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div className="min-w-0">
                  <h3 className="text-xl font-bold">{L.title}</h3>
                  <p className="text-sm text-[var(--text-muted)] mt-1">{L.desc}</p>
                  <div className="text-xs font-mono bg-[var(--bg)] px-2 py-1 rounded mt-3 break-all">{L.url}</div>
                  <div className="mt-2 text-sm"><strong>{L.n}</strong> registros</div>
                </div>
                <div className="flex flex-col gap-2 flex-shrink-0">
                  <a href={L.url} target="_blank" className="btn-primary text-sm"><ExternalLink size={14}/> REST endpoint</a>
                  <a href={`${L.url}/query?where=1%3D1&outFields=*&f=geojson`} target="_blank" className="btn-secondary text-sm"><Download size={14}/> GeoJSON</a>
                  <a href={`https://www.arcgis.com/home/item.html?id=${L.id}`} target="_blank" className="text-sm text-[var(--primary)] font-semibold underline text-center">Item AGO</a>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="container-prose py-10">
        <h2 className="mb-6 flex items-center gap-3"><Code className="text-[var(--primary)]"/> Código fuente y reproducibilidad</h2>
        <div className="grid md:grid-cols-2 gap-5">
          <div className="card">
            <h3 className="text-xl mb-2">Repositorio GitHub</h3>
            <p className="text-sm text-[var(--text-muted)] mb-3">
              22 scripts Python organizados en 5 fases, documentación metodológica (21 documentos ISO 19115), archivo de resultados
              autoritativo <code>riesgo_parroquial_20260226_172751.csv</code>.
            </p>
            <a href={`https://github.com/${SITE.githubUser}/${SITE.githubRepo}`} target="_blank" className="btn-primary">
              <ExternalLink size={16}/> github.com/{SITE.githubUser}/{SITE.githubRepo}
            </a>
          </div>
          <div className="card">
            <h3 className="text-xl mb-2">Archivo Zenodo (DOI permanente)</h3>
            <p className="text-sm text-[var(--text-muted)] mb-3">
              Snapshot versionado del código, datos y documentación con DOI permanente citable académicamente.
            </p>
            <a href={`https://doi.org/${SITE.doi}`} target="_blank" className="btn-primary bg-[#1f5fa8] hover:bg-[#184781]">
              <ExternalLink size={16}/> doi.org/{SITE.doi}
            </a>
          </div>
        </div>
      </section>

      <section className="container-prose py-10">
        <h2 className="mb-6 flex items-center gap-3"><FileJson className="text-[var(--primary)]"/> Metadatos ISO 19115</h2>
        <div className="card">
          <p className="text-[var(--text-muted)] mb-3">
            El pipeline incluye 21 documentos de metadatos conformes a la norma ISO 19115, asociados uno por uno a los
            productos cartográficos principales. Cada documento describe linaje, resolución espacial, sistema de referencia,
            productor, licencia y restricciones de uso.
          </p>
          <a href={`https://github.com/${SITE.githubUser}/${SITE.githubRepo}/tree/main/05_DOCUMENTACION/metadatos_iso`} target="_blank" className="btn-secondary">
            Ver carpeta metadatos_iso en GitHub
          </a>
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
            <li><strong>Atribución:</strong> citar a Pinto Páez, V.H. (2026) con DOI <a href={`https://doi.org/${SITE.doi}`} target="_blank">{SITE.doi}</a></li>
            <li>No hay restricciones adicionales que limiten los usos autorizados por la licencia</li>
          </ul>
          <a href="https://creativecommons.org/licenses/by/4.0/deed.es" target="_blank" className="text-sm text-[var(--primary)] font-semibold mt-3 inline-block">Texto completo de la licencia →</a>
        </div>
      </section>
    </>
  );
}
