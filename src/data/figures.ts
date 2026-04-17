// Rutas LOCALES de las 60 figuras (servidas desde /public/img/figures/).
// Migramos desde URLs AGO para evitar redirects 302 y limitaciones de CSP.

import { asset } from "@/lib/assets";

export interface Figure { group: string; title: string; caption: string; file: string; }

export const figureUrl = (fig: Figure) => asset(`/img/figures/${fig.file}`);

export const FIGURES: Figure[] = [
  // Síntesis (2)
  { group: "Síntesis", title: "Mapa de priorización parroquial (Fig. 5)",
    caption: "Mapa de diferenciación territorial del riesgo: 42 parroquias bajo SSP5-8.5 en 2061-2080 (5 clases).",
    file: "SINTESIS_priorizacion_parroquias.png" },
  { group: "Síntesis", title: "Exposición agrícola parroquial (Fig. 3)",
    caption: "Superficie cosechada (ha) de papa, maíz y fréjol por parroquia (MapSPAM 2020 v2r0).",
    file: "EXPOSICION_superficie_parroquial.png" },

  // Panel resumen (Fig 4)
  { group: "Panel resumen", title: "SSP5-8.5 · 3 horizontes · 4 cultivos (Fig. 4)",
    caption: "Panel resumen: IR agroclimático bajo SSP5-8.5 en los tres horizontes 2021-2040, 2041-2060 y 2061-2080.",
    file: "PANEL_RESUMEN_4cultivos_SSP585_2061-2080.png" },

  // Por cultivo (4)
  { group: "Por cultivo", title: "Papa · 9 escenarios (3 SSP × 3 horizontes)",
    caption: "Evolución del IR de la papa bajo los 9 escenarios SSP × horizonte.",
    file: "PANEL_IR_papa_9escenarios.png" },
  { group: "Por cultivo", title: "Maíz · 9 escenarios",
    caption: "Evolución del IR del maíz bajo los 9 escenarios SSP × horizonte.",
    file: "PANEL_IR_maiz_9escenarios.png" },
  { group: "Por cultivo", title: "Fréjol · 9 escenarios",
    caption: "Evolución del IR del fréjol — el cultivo más estable.",
    file: "PANEL_IR_frejol_9escenarios.png" },
  { group: "Por cultivo", title: "Quinua · 9 escenarios (exploratorio)",
    caption: "IR de la quinua bajo 9 escenarios (estimación exploratoria provincial, n=15).",
    file: "PANEL_IR_quinua_9escenarios.png" },

  // Por SSP (3)
  { group: "Por SSP", title: "SSP1-2.6 · 4 cultivos × 3 horizontes",
    caption: "Trayectoria optimista: mitigación sostenida. IR en los 4 cultivos.",
    file: "PANEL_IR_ssp126_4cultivos.png" },
  { group: "Por SSP", title: "SSP3-7.0 · 4 cultivos × 3 horizontes",
    caption: "Trayectoria de rivalidad regional: emisiones altas. IR en los 4 cultivos.",
    file: "PANEL_IR_ssp370_4cultivos.png" },
  { group: "Por SSP", title: "SSP5-8.5 · 4 cultivos × 3 horizontes",
    caption: "Trayectoria fósil intensiva (peor caso). IR en los 4 cultivos.",
    file: "PANEL_IR_ssp585_4cultivos.png" },

  // Cambio temporal (12)
  { group: "Cambio temporal", title: "Cambio ΔIR · Papa · SSP1-2.6",
    caption: "Diferencia IR(2061-2080) − IR(2021-2040) para papa bajo SSP1-2.6.",
    file: "CAMBIO_papa_ssp126.png" },
  { group: "Cambio temporal", title: "Cambio ΔIR · Papa · SSP3-7.0",
    caption: "Cambio temporal papa SSP3-7.0.", file: "CAMBIO_papa_ssp370.png" },
  { group: "Cambio temporal", title: "Cambio ΔIR · Papa · SSP5-8.5",
    caption: "Cambio temporal papa SSP5-8.5.", file: "CAMBIO_papa_ssp585.png" },
  { group: "Cambio temporal", title: "Cambio ΔIR · Maíz · SSP1-2.6",
    caption: "Cambio temporal maíz SSP1-2.6.", file: "CAMBIO_maiz_ssp126.png" },
  { group: "Cambio temporal", title: "Cambio ΔIR · Maíz · SSP3-7.0",
    caption: "Cambio temporal maíz SSP3-7.0.", file: "CAMBIO_maiz_ssp370.png" },
  { group: "Cambio temporal", title: "Cambio ΔIR · Maíz · SSP5-8.5",
    caption: "Cambio temporal maíz SSP5-8.5.", file: "CAMBIO_maiz_ssp585.png" },
  { group: "Cambio temporal", title: "Cambio ΔIR · Fréjol · SSP1-2.6",
    caption: "Cambio temporal fréjol SSP1-2.6.", file: "CAMBIO_frejol_ssp126.png" },
  { group: "Cambio temporal", title: "Cambio ΔIR · Fréjol · SSP3-7.0",
    caption: "Cambio temporal fréjol SSP3-7.0.", file: "CAMBIO_frejol_ssp370.png" },
  { group: "Cambio temporal", title: "Cambio ΔIR · Fréjol · SSP5-8.5",
    caption: "Cambio temporal fréjol SSP5-8.5.", file: "CAMBIO_frejol_ssp585.png" },
  { group: "Cambio temporal", title: "Cambio ΔIR · Quinua · SSP1-2.6",
    caption: "Cambio temporal quinua SSP1-2.6.", file: "CAMBIO_quinua_ssp126.png" },
  { group: "Cambio temporal", title: "Cambio ΔIR · Quinua · SSP3-7.0",
    caption: "Cambio temporal quinua SSP3-7.0.", file: "CAMBIO_quinua_ssp370.png" },
  { group: "Cambio temporal", title: "Cambio ΔIR · Quinua · SSP5-8.5",
    caption: "Cambio temporal quinua SSP5-8.5.", file: "CAMBIO_quinua_ssp585.png" },

  // Individuales 36 (IR por cultivo × SSP × horizonte)
  ...(() => {
    const cultivos: { key: string; label: string }[] = [
      { key: "papa", label: "Papa" }, { key: "maiz", label: "Maíz" },
      { key: "frejol", label: "Fréjol" }, { key: "quinua", label: "Quinua" },
    ];
    const ssps = [["ssp126","SSP1-2.6"],["ssp370","SSP3-7.0"],["ssp585","SSP5-8.5"]];
    const horizontes = [["2021_2040","2021–2040"],["2041_2060","2041–2060"],["2061_2080","2061–2080"]];
    const out: Figure[] = [];
    for (const c of cultivos) for (const [s, sl] of ssps) for (const [h, hl] of horizontes) {
      out.push({
        group: "Individuales",
        title: `IR · ${c.label} · ${sl} · ${hl}`,
        caption: `Mapa individual del Índice de Riesgo para ${c.label.toLowerCase()} bajo ${sl} en el horizonte ${hl}.`,
        file: `IR_${c.key}_${s}_${h}.png`,
      });
    }
    return out;
  })(),

  // Infografías (2)
  { group: "Infografías", title: "Pipeline científico (5 fases)",
    caption: "Pipeline de 22 scripts de Python en 5 fases metodológicas.",
    file: "infografia_pipeline_5fases.png" },
  { group: "Infografías", title: "Red Bayesiana — DAG de 7 nodos",
    caption: "Grafo acíclico dirigido de la integración probabilística peligro-exposición-susceptibilidad.",
    file: "diagrama_dag_red_bayesiana.png" },
];

export const GROUPS = [
  "Síntesis", "Panel resumen", "Por cultivo", "Por SSP", "Cambio temporal", "Individuales", "Infografías"
];
