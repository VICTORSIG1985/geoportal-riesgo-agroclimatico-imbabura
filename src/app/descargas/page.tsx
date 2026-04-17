import Link from "next/link";
import scripts from "@/data/scripts.json";
import { Download, FileCode, Shield, Info, ExternalLink } from "lucide-react";
import { assetEncoded } from "@/lib/assets";
import RegisterGateLink from "@/components/RegisterGateLink";
import PageHero from "@/components/PageHero";
import ExternalLinkGate from "@/components/ExternalLinkGate";

export const metadata = { title: "Descargas de scripts por fase · Geoportal Imbabura" };

type Script = { name: string; size_kb: number };

function phaseOf(name: string): string {
  const m = name.match(/SCRIPT\s+(\d+)/);
  if (!m) return "Otro";
  const n = parseInt(m[1]);
  if (n <= 2) return "1 · Preparación climática";
  if (n === 3) return "2 · Índices agroclimáticos";
  if (n === 4) return "3 · Exposición agrícola";
  if (n === 5 || n === 6) return "4 · SDM Random Forest";
  return "5 · Integración bayesiana";
}

const PHASES = [
  { id: "1 · Preparación climática", color: "#2166AC",
    desc: "Descarga del ensemble BASD-CMIP6-PE (10 MCG × 3 SSP × 3 horizontes) con corrección de sesgo ISIMIP3BASD v2.5. Recorte espacial a Imbabura." },
  { id: "2 · Índices agroclimáticos", color: "#67A9CF",
    desc: "16 índices: ET₀ Hargreaves-Samani, P − ET₀, estrés térmico por cultivo, CDD (7/15 d), heladas, agregación temporal." },
  { id: "3 · Exposición agrícola", color: "#228B6E",
    desc: "Adquisición multi-fuente (MapSPAM 2020 v2r0 + ESPAC 2024) y desagregación parroquial con exactextract." },
  { id: "4 · SDM Random Forest", color: "#EF8A62",
    desc: "Limpieza de ocurrencias GBIF, generación de pseudo-ausencias, entrenamiento Random Forest (scikit-learn) con validación cruzada espacial k=5, SHAP, proyección a 9 escenarios y agregación parroquial." },
  { id: "5 · Integración bayesiana", color: "#B2182B",
    desc: "Red Bayesiana de 7 nodos (pgmpy), 1.512 inferencias IR, generación de 42 fichas técnicas y validación ISO 19115." },
  { id: "Otro", color: "#666",
    desc: "Scripts de soporte o auxiliares." },
];

export default function DescargasPage() {
  const byPhase: Record<string, Script[]> = {};
  for (const s of scripts as Script[]) {
    const p = phaseOf(s.name);
    (byPhase[p] ||= []).push(s);
  }

  return (
    <>
      <PageHero
        title="Descargas — Código fuente por fase"
        subtitle="22 scripts Python del pipeline científico, publicados para trazabilidad y replicabilidad. Adapte las rutas de entrada y podrá reproducir el estudio."
        image="wm_mojanda.jpg"
        overlayColor="rgba(31,95,168,0.4)"
        credit="Imagen: Lagunas de Mojanda (Otavalo) — Wikimedia Commons · CC BY-SA"
      />

      <section className="container-prose py-8">
        <div className="card bg-amber-50 border-l-4 border-amber-400">
          <h3 className="text-lg mb-2 flex items-center gap-2"><Shield size={18}/> Seguridad y trazabilidad científica</h3>
          <ul className="text-sm text-[var(--text-muted)] space-y-1 list-disc list-inside">
            <li>Los scripts han sido <strong>sanitizados</strong>: se removieron credenciales (API keys, tokens, service accounts) y rutas absolutas locales, reemplazadas por marcadores <code>&lt;REDACTED_*&gt;</code> y <code>&lt;RUTA_LOCAL&gt;</code>.</li>
            <li>Antes de ejecutar, configure <strong>sus propias</strong> rutas de entrada/salida y credenciales de servicios externos (GEE, GBIF, etc.).</li>
            <li>La publicación es para <strong>trazabilidad científica</strong>: quien replique el estudio puede verificar cada paso computacional.</li>
            <li>Licencia <strong>CC BY 4.0</strong> — cita: Pinto Páez, V. H. (2026). DOI <a href="https://doi.org/10.5281/zenodo.19288559" target="_blank" rel="noopener">10.5281/zenodo.19288559</a>.</li>
          </ul>
        </div>
      </section>

      <section className="container-prose py-6">
        {PHASES.map(ph => {
          const items = byPhase[ph.id] || [];
          if (items.length === 0) return null;
          return (
            <div key={ph.id} className="mb-10">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-3 h-10 rounded" style={{ background: ph.color }}></div>
                <div>
                  <h2 className="mb-0 text-2xl">{ph.id}</h2>
                  <div className="text-sm text-[var(--text-muted)]">{items.length} script{items.length !== 1 ? "s" : ""}</div>
                </div>
              </div>
              <p className="text-sm text-[var(--text-muted)] mb-4">{ph.desc}</p>
              <div className="grid md:grid-cols-2 gap-3">
                {items.map(s => (
                  <div key={s.name} className="card p-4 flex items-start gap-3">
                    <div className="w-10 h-10 rounded bg-[var(--bg)] flex items-center justify-center text-[var(--primary)] flex-shrink-0">
                      <FileCode size={18}/>
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-semibold break-words">{s.name}</div>
                      <div className="text-xs text-[var(--text-muted)]">{s.size_kb} KB · Python · sanitizado</div>
                    </div>
                    <RegisterGateLink
                      href={assetEncoded(`/scripts/${s.name}`)}
                      fileName={s.name}
                      tipo="script"
                      className="btn-primary text-sm flex-shrink-0"
                      ariaLabel={`Descargar ${s.name}`}
                    >
                      <Download size={14}/>
                    </RegisterGateLink>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </section>

      <section className="container-prose py-10">
        <div className="card bg-gradient-to-br from-[var(--primary)] to-[var(--primary-dark)] text-white">
          <h3 className="text-white text-2xl mb-3 flex items-center gap-2"><Info/> Replicabilidad completa</h3>
          <p className="opacity-90 mb-4">
            Para replicar el estudio completo (incluyendo datos intermedios), consulte el archivo Zenodo con DOI permanente:
          </p>
          <div className="flex flex-wrap gap-3">
            <ExternalLinkGate href="https://doi.org/10.5281/zenodo.19288559" className="inline-flex items-center gap-2 bg-white text-[var(--primary)] px-5 py-3 rounded-lg font-semibold hover:bg-gray-100 shadow">
              <ExternalLink size={16}/> Zenodo DOI 10.5281/zenodo.19288559
            </ExternalLinkGate>
            <Link href="/datos" className="inline-flex items-center gap-2 bg-white/15 border-2 border-white text-white px-5 py-3 rounded-lg font-semibold hover:bg-white hover:text-[var(--primary)]">
              Volver a Datos Abiertos
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
