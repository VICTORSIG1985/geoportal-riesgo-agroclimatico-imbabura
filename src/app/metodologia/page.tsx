import { Microscope, Cpu, Network, CheckCircle2, AlertTriangle, Info } from "lucide-react";
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

  // Tabla principal — fuente: metricas_rf_20260428_202552.csv (Script 06 v1.2.0)
  const metricas = [
    { cultivo: "Papa",   auc: "0,871", aucSig: "0,071", tss: "0,667", tssSig: "0,139", kappa: "0,630", oob: "0,186", top: "dias_estres_papa_anual (ΔAUC 0,021 ± 0,003)" },
    { cultivo: "Quinua", auc: "0,867", aucSig: "0,056", tss: "0,625", tssSig: "0,094", kappa: "0,608", oob: "0,208", top: "dias_secos_anual (ΔAUC 0,015)" },
    { cultivo: "Fréjol", auc: "0,859", aucSig: "0,040", tss: "0,583", tssSig: "0,069", kappa: "0,580", oob: "0,186", top: "dias_secos_anual (ΔAUC 0,020)" },
    { cultivo: "Maíz",   auc: "0,804", aucSig: "0,067", tss: "0,525", tssSig: "0,128", kappa: "0,478", oob: "0,252", top: "dias_secos_anual (ΔAUC 0,049)" },
  ];

  // Tabla de blindaje — fuente: metricas_rf_20260428_202552.csv (Script 06 v1.2.0)
  const blindaje = [
    { cultivo: "Papa",   aucPr: "0,755", mcc: "0,657", mccSig: "0,115", f1: "0,801", f1Sig: "0,050", brier: "0,137" },
    { cultivo: "Quinua", aucPr: "0,816", mcc: "0,640", mccSig: "0,059", f1: "0,814", f1Sig: "0,053", brier: "0,145" },
    { cultivo: "Fréjol", aucPr: "0,750", mcc: "0,580", mccSig: "0,097", f1: "0,738", f1Sig: "0,099", brier: "0,147" },
    { cultivo: "Maíz",   aucPr: "0,637", mcc: "0,509", mccSig: "0,107", f1: "0,708", f1Sig: "0,035", brier: "0,173" },
  ];

  // Matrices de confusión — fuente: metricas_rf_20260428_202552.csv (Script 06 v1.2.0)
  const confusion = [
    { cultivo: "Papa (n=902)",   tp: "342", tn: "390", fp: "150", fn: "20",  sens: "0,945", spec: "0,722" },
    { cultivo: "Quinua (n=245)", tp: "107", tn: "89",  fp: "44",  fn: "5",   sens: "0,955", spec: "0,669" },
    { cultivo: "Fréjol (n=957)", tp: "266", tn: "502", fp: "99",  fn: "90",  sens: "0,747", spec: "0,835" },
    { cultivo: "Maíz (n=2.062)", tp: "668", tn: "843", fp: "456", fn: "95",  sens: "0,876", spec: "0,649" },
  ];

  const tooltips: Record<string, string> = {
    "AUC-ROC": "Área bajo la curva ROC. Mide la capacidad del modelo para distinguir presencias de pseudo-ausencias independientemente del umbral de clasificación. Valores > 0,75 = bueno; > 0,80 = muy bueno (Fielding y Bell 1997).",
    "TSS": "True Skill Statistic = Sensibilidad + Especificidad − 1. Estándar en modelos de distribución de especies. Umbral mínimo ≥ 0,50 (Allouche et al. 2006). El umbral de clasificación usado maximiza el TSS sobre las predicciones de los 5 pliegues espaciales.",
    "Kappa": "Kappa de Cohen: acuerdo ajustado por azar entre predicciones y observaciones.",
    "OOB Error": "Error estimado sobre muestras fuera de bolsa. No requiere conjunto de prueba separado. Estimación interna del modelo final entrenado con todos los datos.",
    "AUC-PR": "Precisión promedio. Más informativa que AUC-ROC cuando las ausencias son pseudo-ausencias generadas por muestreo de fondo (Saito y Rehmsmeier 2015). Valores más conservadores pero más honestos.",
    "MCC": "Coeficiente de correlación de Matthews. Pondera las cuatro celdas de la matriz de confusión (TP, TN, FP, FN). Considerado la métrica más robusta para clasificación binaria (Chicco y Jurman 2020). Rango: −1 a +1.",
    "F1": "Media armónica de precisión y recall. Estándar en aprendizaje automático. Complementa al TSS desde la perspectiva de ML.",
    "Brier": "Calibración de las probabilidades. Mide qué tan bien calibradas están las probabilidades producidas por el Random Forest. Rango: 0 (perfecto) a 1. Brier < 0,20 en todos los cultivos confirma que las probabilidades son confiables antes de su ingreso a la Red Bayesiana.",
    "Sensibilidad": "Porcentaje de presencias reales que el modelo clasifica correctamente: TP / (TP + FN). Alta sensibilidad significa que el modelo raramente pierde un sitio apto real.",
    "Especificidad": "Porcentaje de ausencias reales que el modelo clasifica correctamente: TN / (TN + FP).",
  };

  return (
    <>
      <PageHero
        title="Metodología"
        subtitle="Pipeline científico reproducible de 22 scripts Python organizados en 5 fases, integrando datos CMIP6 con corrección de sesgo, modelos de distribución de especies (Random Forest) y una Red Bayesiana de 7 nodos."
        image="wm_cotacachi.jpg"
        overlayColor="rgba(107,78,155,0.38)"
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

      {/* ===== DESEMPEÑO RANDOM FOREST ===== */}
      <section className="container-prose py-10">
        <h2 className="mb-6 flex items-center gap-3"><Microscope className="text-[var(--primary)]"/> Desempeño Random Forest</h2>

        {/* Tabla principal */}
        <div className="card p-0 overflow-hidden">
          <table className="data">
            <thead>
              <tr>
                <th>Cultivo</th>
                <th title={tooltips["AUC-ROC"]}>AUC-ROC (σ) <Info className="inline w-3 h-3 opacity-50"/></th>
                <th title={tooltips["TSS"]}>TSS (σ) <Info className="inline w-3 h-3 opacity-50"/></th>
                <th title={tooltips["Kappa"]}>Kappa <Info className="inline w-3 h-3 opacity-50"/></th>
                <th title={tooltips["OOB Error"]}>OOB Error <Info className="inline w-3 h-3 opacity-50"/></th>
                <th>Variable más importante</th>
              </tr>
            </thead>
            <tbody>
              {metricas.map(m => (
                <tr key={m.cultivo}>
                  <td className="font-bold">{m.cultivo}</td>
                  <td>{m.auc} <span className="text-xs text-[var(--text-muted)]">(±{m.aucSig})</span></td>
                  <td>{m.tss} <span className="text-xs text-[var(--text-muted)]">(±{m.tssSig})</span></td>
                  <td>{m.kappa}</td>
                  <td>{m.oob}</td>
                  <td className="text-sm font-mono">{m.top}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-sm text-[var(--text-muted)] mt-3">
          σ = desviación estándar entre pliegues · Umbrales de aceptación: AUC ≥ 0,75 (Fielding &amp; Bell 1997) · TSS ≥ 0,50 (Allouche et al. 2006) · OOB ≤ 0,30.
          Los 4 modelos cumplen. Validación cruzada espacial k=5 con bloques de 2° de latitud. Fuente: metricas_rf_20260428_202552.csv (Script 06 v1.2.0 · Tabla 4 del manuscrito).
        </p>

        {/* Blindaje métrico — sección expandible */}
        <details className="mt-6 card p-0 overflow-hidden group">
          <summary className="flex items-center justify-between px-5 py-4 cursor-pointer select-none bg-slate-50 hover:bg-slate-100 transition-colors font-semibold text-[var(--primary)]">
            <span className="flex items-center gap-2">
              <Microscope className="w-4 h-4"/>
              Detalles técnicos — blindaje métrico (AUC-PR, MCC, F1, Brier Score)
            </span>
            <span className="text-xs font-normal text-[var(--text-muted)]">click para expandir</span>
          </summary>

          <div className="px-5 py-5 space-y-6">
            <p className="text-sm text-[var(--text-muted)]">
              Métricas adicionales calculadas por el Script 06 v1.2.0 para blindar la credibilidad del modelo
              frente a revisores científicos. Reportadas en la Tabla 4 y Online Resource 1 del manuscrito (Natural Hazards, en revisión).
            </p>

            {/* Tabla de blindaje */}
            <div>
              <h4 className="font-semibold mb-2 text-sm uppercase tracking-wider text-[var(--text-muted)]">Métricas de blindaje</h4>
              <div className="overflow-x-auto">
                <table className="data w-full text-sm">
                  <thead>
                    <tr>
                      <th>Cultivo</th>
                      <th title={tooltips["AUC-PR"]}>AUC-PR <Info className="inline w-3 h-3 opacity-50"/></th>
                      <th title={tooltips["MCC"]}>MCC (σ) <Info className="inline w-3 h-3 opacity-50"/></th>
                      <th title={tooltips["F1"]}>F1 (σ) <Info className="inline w-3 h-3 opacity-50"/></th>
                      <th title={tooltips["Brier"]}>Brier Score <Info className="inline w-3 h-3 opacity-50"/></th>
                    </tr>
                  </thead>
                  <tbody>
                    {blindaje.map(b => (
                      <tr key={b.cultivo}>
                        <td className="font-bold">{b.cultivo}</td>
                        <td>{b.aucPr}</td>
                        <td>{b.mcc} <span className="text-xs text-[var(--text-muted)]">(±{b.mccSig})</span></td>
                        <td>{b.f1} <span className="text-xs text-[var(--text-muted)]">(±{b.f1Sig})</span></td>
                        <td>{b.brier}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-[var(--text-muted)] mt-2">
                Brier Score &lt; 0,20 en todos los cultivos confirma que las probabilidades del RF están bien calibradas
                antes de su ingreso a la Red Bayesiana. Fuente: metricas_rf_20260428_202552.csv.
              </p>
            </div>

            {/* Nota VIF */}
            <div className="p-4 bg-blue-50 border-l-4 border-blue-300 rounded-r text-sm text-[var(--text-muted)]">
              <strong>Multicolinealidad (VIF):</strong> El diagnóstico mostró dependencia lineal perfecta entre ET₀ media diaria
              y ET₀ anual, y entre déficit hídrico diario y anual. Esto es esperado: las versiones diaria y anual de la misma variable
              son linealmente dependientes por construcción. Random Forest es robusto a este tipo de multicolinealidad
              y los 16 predictores se retuvieron. La importancia por permutación se usa como diagnóstico descriptivo,
              no para inferencia causal.
            </div>

            {/* Matrices de confusión */}
            <div>
              <h4 className="font-semibold mb-2 text-sm uppercase tracking-wider text-[var(--text-muted)]">Matrices de confusión</h4>
              <div className="overflow-x-auto">
                <table className="data w-full text-sm">
                  <thead>
                    <tr>
                      <th>Cultivo</th>
                      <th title="Verdaderos positivos">TP</th>
                      <th title="Verdaderos negativos">TN</th>
                      <th title="Falsos positivos">FP</th>
                      <th title="Falsos negativos">FN</th>
                      <th title={tooltips["Sensibilidad"]}>Sensibilidad <Info className="inline w-3 h-3 opacity-50"/></th>
                      <th title={tooltips["Especificidad"]}>Especificidad <Info className="inline w-3 h-3 opacity-50"/></th>
                    </tr>
                  </thead>
                  <tbody>
                    {confusion.map(c => (
                      <tr key={c.cultivo}>
                        <td className="font-bold">{c.cultivo}</td>
                        <td>{c.tp}</td>
                        <td>{c.tn}</td>
                        <td>{c.fp}</td>
                        <td>{c.fn}</td>
                        <td>{c.sens}</td>
                        <td>{c.spec}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Glosario de métricas */}
            <div>
              <h4 className="font-semibold mb-3 text-sm uppercase tracking-wider text-[var(--text-muted)]">Glosario de métricas</h4>
              <dl className="grid md:grid-cols-2 gap-x-8 gap-y-3 text-sm">
                {Object.entries(tooltips).map(([k, v]) => (
                  <div key={k}>
                    <dt className="font-semibold text-[var(--primary)]">{k}</dt>
                    <dd className="text-[var(--text-muted)] leading-snug">{v}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </div>
        </details>
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
