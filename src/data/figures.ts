export interface Figure { group: string; title: string; caption: string; id: string; }

const imgUrl = (id: string) => `https://www.arcgis.com/sharing/rest/content/items/${id}/data`;
export const figureUrl = (fig: Figure) => imgUrl(fig.id);

export const FIGURES: Figure[] = [
  // Síntesis (2)
  { group: "Síntesis", title: "Mapa de priorización parroquial (Fig. 5)", caption: "Mapa de diferenciación territorial del riesgo: 42 parroquias bajo SSP5-8.5 en 2061-2080 (5 clases).", id: "97b6b4fdb0934e878b591f85a574137f" },
  { group: "Síntesis", title: "Exposición agrícola parroquial (Fig. 3)", caption: "Superficie cosechada (ha) de papa, maíz y fréjol por parroquia (MapSPAM 2020 v2r0).", id: "a95a597109224f9d950bbb085d3b4102" },
  // Panel resumen (Fig 4 manuscrito)
  { group: "Panel resumen", title: "SSP5-8.5 · 3 horizontes · 4 cultivos (Fig. 4)", caption: "Panel resumen: IR agroclimático bajo SSP5-8.5 en los tres horizontes 2021-2040, 2041-2060 y 2061-2080.", id: "3cf503cc13564fbc926dd0a3cf493af2" },
  // Por cultivo (4)
  { group: "Por cultivo", title: "Papa · 9 escenarios (3 SSP × 3 horizontes)", caption: "Evolución del IR de la papa bajo los 9 escenarios SSP × horizonte.", id: "a8569185be9a44e79fe0135c265f6cdb" },
  { group: "Por cultivo", title: "Maíz · 9 escenarios", caption: "Evolución del IR del maíz bajo los 9 escenarios SSP × horizonte.", id: "f738f1753a9345adb74ec4bc9fd89f3c" },
  { group: "Por cultivo", title: "Fréjol · 9 escenarios", caption: "Evolución del IR del fréjol — el cultivo más estable.", id: "ad8dadfc5ec649dcb4f6e2d89a936ae8" },
  { group: "Por cultivo", title: "Quinua · 9 escenarios (exploratorio)", caption: "IR de la quinua bajo 9 escenarios (estimación exploratoria provincial, n=15).", id: "4bd346634d074b0f9a02b1f8984f8e33" },
  // Por SSP (3)
  { group: "Por SSP", title: "SSP1-2.6 · 4 cultivos × 3 horizontes", caption: "Trayectoria optimista: mitigación sostenida. IR en los 4 cultivos.", id: "b90f849de7104b889ee74d387d1b58a3" },
  { group: "Por SSP", title: "SSP3-7.0 · 4 cultivos × 3 horizontes", caption: "Trayectoria de rivalidad regional: emisiones altas. IR en los 4 cultivos.", id: "bb75ca9145a44eb5ad2982024ab7a859" },
  { group: "Por SSP", title: "SSP5-8.5 · 4 cultivos × 3 horizontes", caption: "Trayectoria fósil intensiva (peor caso). IR en los 4 cultivos.", id: "957ecf4fa8944cc9a072c9342226732a" },
  // Cambio temporal (12)
  { group: "Cambio temporal", title: "Cambio ΔIR · Papa · SSP1-2.6", caption: "Diferencia IR(2061-2080) − IR(2021-2040) para papa bajo SSP1-2.6.", id: "57ed3c46a273445cb46c2ef23a5ce46f" },
  { group: "Cambio temporal", title: "Cambio ΔIR · Papa · SSP3-7.0", caption: "Cambio temporal papa SSP3-7.0.", id: "518ced40872f400f92572739e7687e75" },
  { group: "Cambio temporal", title: "Cambio ΔIR · Papa · SSP5-8.5", caption: "Cambio temporal papa SSP5-8.5.", id: "db4eadc42f264d4a9ba91b828afdd3ab" },
  { group: "Cambio temporal", title: "Cambio ΔIR · Maíz · SSP1-2.6", caption: "Cambio temporal maíz SSP1-2.6.", id: "9d9b92ba76dd4419ade8e96446bca4e9" },
  { group: "Cambio temporal", title: "Cambio ΔIR · Maíz · SSP3-7.0", caption: "Cambio temporal maíz SSP3-7.0.", id: "5873ba730c6342b6ad88a6ca96d75c35" },
  { group: "Cambio temporal", title: "Cambio ΔIR · Maíz · SSP5-8.5", caption: "Cambio temporal maíz SSP5-8.5.", id: "3ce106ab3f2143d79f9340c801930c47" },
  { group: "Cambio temporal", title: "Cambio ΔIR · Fréjol · SSP1-2.6", caption: "Cambio temporal fréjol SSP1-2.6.", id: "cd84dea8a41b4265a7ca71fe8734222a" },
  { group: "Cambio temporal", title: "Cambio ΔIR · Fréjol · SSP3-7.0", caption: "Cambio temporal fréjol SSP3-7.0.", id: "d3ea3075b9ef47a69982a08af659bb69" },
  { group: "Cambio temporal", title: "Cambio ΔIR · Fréjol · SSP5-8.5", caption: "Cambio temporal fréjol SSP5-8.5.", id: "e21e35a1dcd14aaa9f8267717594b690" },
  { group: "Cambio temporal", title: "Cambio ΔIR · Quinua · SSP1-2.6", caption: "Cambio temporal quinua SSP1-2.6.", id: "057c075647b449d59990a836894cacf6" },
  { group: "Cambio temporal", title: "Cambio ΔIR · Quinua · SSP3-7.0", caption: "Cambio temporal quinua SSP3-7.0.", id: "aea0a396aa894288b44a76f77e1488c3" },
  { group: "Cambio temporal", title: "Cambio ΔIR · Quinua · SSP5-8.5", caption: "Cambio temporal quinua SSP5-8.5.", id: "5f9af60fd2a84efe89830f3dd2c9a110" },
  // Infografías (2)
  { group: "Infografías", title: "Pipeline científico (5 fases)", caption: "Pipeline de 22 scripts de Python en 5 fases metodológicas.", id: "9fac0787346f451687f425849e97634f" },
  { group: "Infografías", title: "Red Bayesiana — DAG de 7 nodos", caption: "Grafo acíclico dirigido de la integración probabilística peligro-exposición-susceptibilidad.", id: "8f493d1d1e2d426f8bcedda2ff739a41" },
];

export const GROUPS = [
  "Síntesis", "Panel resumen", "Por cultivo", "Por SSP", "Cambio temporal", "Infografías"
];
