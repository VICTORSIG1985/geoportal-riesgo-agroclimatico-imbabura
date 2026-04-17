import { Microscope, Cpu, Network, CheckCircle2, AlertTriangle } from "lucide-react";
import PipelineDiagram from "@/components/PipelineDiagram";
import DAGDiagram from "@/components/DAGDiagram";
import PageHero from "@/components/PageHero";

export const metadata = {
  title: "Metodología · Geoportal Riesgo Agroclimático Imbabura",
  description: "Pipeline científico de 5 fases (22 scripts Python): BASD-CMIP6-PE + 16 índices agroclimáticos + Random Forest + Red Bayesiana.",
};

export default function MetodologiaPage() {

  const fases = [
    { n: 1, title: "Preparación climática", scripts: "Scripts 00–02",
      desc: "Lectura y alineación del ensemble BASD-CMIP6-PE (10 MCG × 3 SSP × 3 horizontes; Fernandez-Palomino et al. 2024) con corrección de sesgo ISIMIP3BASD v2.5, calibrado contra PISCO y RAIN4PE." },
    { n: 2, title: "Índices agroclimáticos", scripts: "Scripts 03A–03F",
      desc: "16 índices: ET₀ Hargreaves-Samani, P − ET₀, índice de aridez (PNUMA 1992), CDD (ETCCDI), días secos 7d/15d, estrés térmico por cultivo (papa>25°C, fréjol>30°C, quinua>32°C, maíz>35°C)." },
    { n: 3, title: "Exposición agrícola", scripts: "Scripts 04A–04C",
      desc: "Desagregación parroquial de MapSPAM 2020 v2r0 (IFPRI 2024) con exactextract (Baston 2022); error de cierre aritmético 0,0000%. Para quinua: ESPAC 2024 (INEC)." },
    { n: 4, title: "SDM con Random Forest", scripts: "Scripts 05A–06C",
      desc: "Un RF por cultivo (scikit-learn 1.3): n_estimators=500, max_features=√p, min_samples_leaf=5, class_weight=balanced. Validación cruzada espacial k=5 con bloques de 2° de latitud (Roberts et al. 2017). 2.681 registros GBIF filtrados." },
    { n: 5, title: "Integración bayesiana", scripts: "Scripts 07–10",
      desc: "Red Bayesiana con pgmpy v0.1.25; DAG de 7 nodos y 6 aristas. IR = 0·P(Bajo) + 0.5·P(Medio) + 1·P(Alto). 1.512 inferencias (42 × 4 × 3 × 3), sin valores nulos." },
  ];

  const metricas = [
    { cultivo: "Papa", auc: "0,871", tss: "0,603", oob: "0,169", top: "dias_estres_papa_anual (ΔAUC 0,021 ± 0,003)" },
    { cultivo: "Quinua", auc: "0,867", tss: "0,614", oob: "0,179", top: "dias_secos_anual (ΔAUC 0,015)" },
    { cultivo: "Fréjol", auc: "0,859", tss: "0,574", oob: "0,174", top: "dias_secos_anual (ΔAUC 0,020)" },
    { cultivo: "Maíz", auc: "0,804", tss: "0,511", oob: "0,252", top: "dias_secos_anual (ΔAUC 0,049)" },
  ];

  return (
    <>
      <PageHero
        title="Metodología"
        subtitle="Pipeline científico reproducible de 22 scripts Python organizados en 5 fases, integrando datos CMIP6 con corrección de sesgo, modelos de distribución de especies (Random Forest) y una Red Bayesiana de 7 nodos."
        image="wm_cotacachi.jpg"
        overlayColor="rgba(107,78,155,0.82)"
        credit="Imagen: Volcán Cotacachi · Wikimedia Commons · CC BY-SA"
      />

      <section className="container-prose py-12">
        <h2 className="mb-6 flex items-center gap-3"><Cpu className="text-[var(--primary)]"/> Pipeline científico</h2>
        <PipelineDiagram/>
        <p className="text-sm text-[var(--text-muted)] mt-3">
          Organizador gráfico nativo del sitio (SVG/HTML) · 22 scripts Python en 5 fases · Pinto Páez (2026), Script 07.
          Los scripts pueden descargarse por fase en la sección <a href="/datos" className="text-[var(--primary)] font-semibold">Datos Abiertos</a>.
        </p>
      </section>

      <section className="container-prose py-8">
        <h2 className="mb-6 flex items-center gap-3"><Cpu className="text-[var(--primary)]"/> Fases del pipeline</h2>
        <div className="space-y-5">
          {fases.map(f => (
            <div key={f.n} className="card flex gap-6">
              <div className="w-14 h-14 bg-[#6B4E9B] text-white rounded-full flex items-center justify-center text-2xl font-bold flex-shrink-0">
                {f.n}
              </div>
              <div className="min-w-0">
                <div className="text-xs uppercase tracking-wider text-[var(--text-muted)] font-semibold">{f.scripts}</div>
                <h3 className="text-xl mb-2">{f.title}</h3>
                <p className="text-[var(--text-muted)] leading-relaxed">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="container-prose py-10">
        <h2 className="mb-6 flex items-center gap-3"><Network className="text-[var(--primary)]"/> Red Bayesiana — DAG de 7 nodos</h2>
        <div className="card bg-white">
          <DAGDiagram/>
        </div>
        <div className="grid md:grid-cols-2 gap-6 mt-6">
          <div>
            <h3 className="text-lg mb-2">Estructura de la red</h3>
            <ul className="space-y-2 text-sm text-[var(--text-muted)]">
              <li><strong>Nodos raíz:</strong> Peligro_Deficit, Peligro_Termico, Peligro_Sequia, Exposicion, Susceptibilidad_Agroclimática</li>
              <li><strong>Nodo intermedio:</strong> Peligro (regla de daño máximo → Alto si algún subpeligro es Alto)</li>
              <li><strong>Nodo objetivo:</strong> Riesgo (IR ∈ [0, 1])</li>
              <li><strong>IR:</strong> 0 · P(Bajo) + 0,5 · P(Medio) + 1 · P(Alto)</li>
              <li><strong>Estados:</strong> Bajo / Medio / Alto · umbrales Tabla 3 del manuscrito</li>
            </ul>
          </div>
          <div className="p-4 bg-amber-50 border-l-4 border-amber-400 rounded-r text-sm">
            <strong>Nota terminológica:</strong> se adopta <em>Susceptibilidad Agroclimática</em> en lugar de
            <em> Vulnerabilidad</em> porque el nodo representa sensibilidad biofísica (1 − aptitud RF), no la vulnerabilidad
            socioeconómica del IPCC AR6.
          </div>
        </div>
      </section>

      <section className="container-prose py-10">
        <h2 className="mb-6 flex items-center gap-3"><Microscope className="text-[var(--primary)]"/> Desempeño Random Forest</h2>
        <div className="card p-0 overflow-hidden">
          <table className="data">
            <thead>
              <tr>
                <th>Cultivo</th>
                <th>AUC-ROC</th>
                <th>TSS</th>
                <th>OOB Error</th>
                <th>Variable más importante</th>
              </tr>
            </thead>
            <tbody>
              {metricas.map(m => (
                <tr key={m.cultivo}>
                  <td className="font-bold">{m.cultivo}</td>
                  <td>{m.auc}</td>
                  <td>{m.tss}</td>
                  <td>{m.oob}</td>
                  <td className="text-sm font-mono">{m.top}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-sm text-[var(--text-muted)] mt-3">
          Umbrales de aceptación: AUC ≥ 0,75 (Fielding & Bell 1997) · TSS ≥ 0,50 (Allouche et al. 2006) · OOB ≤ 0,30.
          Los 4 modelos cumplen. Validación cruzada espacial k=5 con bloques de 2° de latitud. Fuente: Tabla 4 del manuscrito.
        </p>
      </section>

      <section className="container-prose py-10">
        <h2 className="mb-6 flex items-center gap-3"><CheckCircle2 className="text-[var(--accent-2)]"/> Robustez</h2>
        <div className="grid md:grid-cols-3 gap-5">
          <div className="card border-l-4 border-[var(--accent-2)]">
            <div className="text-3xl font-bold text-[var(--accent-2)]">ρ ≥ 0,91</div>
            <div className="text-sm text-[var(--text-muted)] mt-1">Correlación de Spearman del ranking bajo perturbación ±15 pp de las TPC</div>
          </div>
          <div className="card border-l-4 border-[var(--accent-2)]">
            <div className="text-3xl font-bold text-[var(--accent-2)]">CV &lt; 8%</div>
            <div className="text-sm text-[var(--text-muted)] mt-1">Dispersión intermodelo del ensemble de 10 MCG bajo SSP5-8.5 2061-2080</div>
          </div>
          <div className="card border-l-4 border-[var(--accent-2)]">
            <div className="text-3xl font-bold text-[var(--accent-2)]">1.512 / 1.512</div>
            <div className="text-sm text-[var(--text-muted)] mt-1">Inferencias IR completadas sin valores nulos ni imputaciones</div>
          </div>
        </div>
      </section>

      <section className="container-prose py-10">
        <h2 className="mb-6 flex items-center gap-3"><AlertTriangle className="text-amber-500"/> Limitaciones</h2>
        <ol className="card space-y-3 list-decimal list-inside">
          <li><strong>Resolución ~10 km:</strong> no resuelve microclimas de quebrada; adecuada a mesoescala parroquial.</li>
          <li><strong>MapSPAM es proxy estadística:</strong> razones MapSPAM/ESPAC de 0,69 (papa) a 1,52 (maíz) retenidas sin conciliación.</li>
          <li><strong>Quinua exploratoria:</strong> 18,36 ha ESPAC 2024 distribuidas uniformemente; IR indicativo provincial, no territorial.</li>
          <li><strong>TPC de conocimiento experto:</strong> análisis de sensibilidad confirma estabilidad del ranking (ρ ≥ 0,91).</li>
          <li><strong>Sin validación in situ:</strong> carácter prospectivo del estudio.</li>
          <li><strong>Conservatismo de nicho:</strong> puede sobreestimar pérdidas si se desarrollan variedades más tolerantes.</li>
        </ol>
      </section>
    </>
  );
}
