// Base de conocimiento — Q&A pre-indexadas del manuscrito para el asistente
export interface KBEntry { q: string; a: string; tags: string[]; }

export const KB: KBEntry[] = [
  {
    q: "¿Qué evalúa la investigación?",
    a: "La investigación evalúa el riesgo agroclimático integrado de cuatro cultivos andinos (papa, maíz, fréjol, quinua) en las 42 parroquias de Imbabura, Ecuador. Combina un Modelo de Distribución de Especies entrenado con Random Forest (16 índices agroclimáticos; AUC 0,804-0,871) con una Red Bayesiana de 7 nodos para obtener un Índice de Riesgo compuesto (IR) bajo 9 escenarios climáticos CMIP6 (SSP1-2.6, SSP3-7.0, SSP5-8.5 × 3 horizontes).",
    tags: ["objetivo", "resumen", "pipeline"]
  },
  {
    q: "¿Qué cultivos se analizan?",
    a: "Se analizan cuatro cultivos andinos: papa (Solanum tuberosum), maíz (Zea mays), fréjol (Phaseolus vulgaris) y quinua (Chenopodium quinoa). Cada uno tiene un modelo RF independiente con umbrales fisiológicos específicos (papa >25°C, fréjol >30°C, quinua >32°C, maíz >35°C).",
    tags: ["cultivos", "papa", "maíz", "fréjol", "quinua"]
  },
  {
    q: "¿Cuál es el hallazgo principal?",
    a: "Bajo el escenario SSP5-8.5 al 2061-2080, el IR medio parroquial va de 0,350 en Imbaya a 0,689 en García Moreno — un factor de 1,97×. Esta diferenciación territorial solo es visible a escala parroquial. En 39 de las 42 parroquias, al menos un cultivo acumula ΔIR > 0,10 entre 2021-2040 y 2061-2080.",
    tags: ["resultado", "IR", "priorización"]
  },
  {
    q: "¿Cuáles son las parroquias prioritarias?",
    a: "El Top 10 bajo SSP5-8.5 2061-2080: 1) García Moreno (IR 0,689, 4 cultivos en alto riesgo), 2) Seis de Julio de Cuellaje (0,657), 3) Lita, 4) Selva Alegre, 5) La Carolina, 6) Peñaherrera, 7) Apuela, 8) Vacas Galindo, 9) Ambuquí, 10) Plaza Gutiérrez. Cotacachi concentra 6 de las 10 prioridades (zona de Intag).",
    tags: ["ranking", "top 10", "Cotacachi", "Intag"]
  },
  {
    q: "¿Cómo funciona la Red Bayesiana?",
    a: "La Red Bayesiana tiene 7 nodos y 6 aristas en 3 niveles. Nodos raíz: Peligro_Deficit, Peligro_Termico, Peligro_Sequia, Exposicion, Susceptibilidad_Agroclimática. Nodo intermedio: Peligro (con regla de daño máximo: Alto si algún subpeligro es Alto). Nodo objetivo: Riesgo. El IR se calcula como 0·P(Bajo) + 0,5·P(Medio) + 1·P(Alto). Se implementó con pgmpy v0.1.25.",
    tags: ["metodología", "red bayesiana", "DAG", "IR"]
  },
  {
    q: "¿Qué métricas tienen los modelos Random Forest?",
    a: "Con validación cruzada espacial (k=5, bloques 2° lat): Papa AUC=0,871, TSS=0,603, OOB=0,169. Quinua AUC=0,867, TSS=0,614. Fréjol AUC=0,859, TSS=0,574. Maíz AUC=0,804, TSS=0,511, OOB=0,252. Los 4 modelos superan los umbrales (AUC≥0,75, TSS≥0,50). La variable más importante por cultivo coincide con el mecanismo fisiológico documentado.",
    tags: ["metodología", "random forest", "AUC", "TSS", "desempeño"]
  },
  {
    q: "¿Cuál es el rango de la exposición agrícola?",
    a: "Superficie cosechada total: 10.706,2 ha. Maíz domina con 7.681,4 ha (71,7%), seguido por fréjol 2.316,9 ha (21,6%) y papa 707,9 ha (6,6%). Lita, San Miguel de Ibarra y La Merced de Buenos Aires concentran el 31,1% provincial. Para quinua: ESPAC 2024 reporta 18,36 ha en toda Imbabura, repartidas uniformemente como supuesto de trabajo (estimación exploratoria).",
    tags: ["exposición", "MapSPAM", "hectáreas"]
  },
  {
    q: "¿Qué datos climáticos se usan?",
    a: "BASD-CMIP6-PE (Fernandez-Palomino et al. 2024) con corrección de sesgo ISIMIP3BASD v2.5, usando PISCO y RAIN4PE como referencias observacionales. Cobertura 1981-2100 a 0,1° (~10 km). Ensemble de 10 MCG (CanESM5, IPSL-CM6A-LR, UKESM1-0-LL, CNRM-CM6-1, CNRM-ESM2-1, MIROC6, GFDL-ESM4, MRI-ESM2-0, MPI-ESM1-2-HR, EC-Earth3). 3 SSPs × 3 horizontes.",
    tags: ["datos climáticos", "CMIP6", "BASD"]
  },
  {
    q: "¿Qué limitaciones tiene el estudio?",
    a: "Seis limitaciones: 1) Resolución ~10 km, no resuelve microclimas de quebrada. 2) MapSPAM es proxy estadística, no catastro. 3) Quinua es exploratoria (18,36 ha distribuidas uniformemente). 4) TPC de conocimiento experto (pero ρ Spearman ≥ 0,91 confirma robustez). 5) Sin validación in situ. 6) Conservatismo de nicho — puede sobreestimar pérdidas si se desarrollan variedades más tolerantes.",
    tags: ["limitaciones", "incertidumbre"]
  },
  {
    q: "¿Cómo descargo los datos?",
    a: "Los datos están disponibles públicamente como 3 Feature Services REST en ArcGIS Online USGP-EC: FL_Parroquias_Base_Imbabura_42 (42 polígonos), FL_Riesgo_Parroquial_Long_1512 (1.512 inferencias) y FL_Priorizacion_Final_Imbabura_42 (ranking). Se pueden consumir desde ArcGIS Pro, QGIS, R o Python, o descargar como GeoJSON/Shapefile/FGDB. Código fuente: GitHub VICTORSIG1985/agroclimatic-risk-imbabura. DOI Zenodo: 10.5281/zenodo.19288559.",
    tags: ["datos", "descarga", "GitHub", "Zenodo", "API"]
  },
  {
    q: "¿Por qué la quinua es exploratoria?",
    a: "Porque ESPAC 2024 (INEC) reporta solo 18,36 hectáreas cosechadas de quinua en toda Imbabura. Esta superficie se distribuyó uniformemente entre las 42 parroquias como supuesto de trabajo. Los IR de quinua reflejan variación en peligro y susceptibilidad, pero no diferencias reales de exposición entre parroquias. Además la muestra GBIF es limitada (n=140 registros, 15 parroquias con cobertura). Por eso sus valores son indicativos a escala provincial, no territorial.",
    tags: ["quinua", "limitación", "exposición"]
  },
  {
    q: "¿Qué cultivo es más estable frente al cambio climático?",
    a: "El fréjol es el más estable: ΔIR ≤ +0,5% en todos los escenarios y horizontes. Mantiene IR ~0,44 en todas las combinaciones. Esto es coherente con la resiliencia documentada de leguminosas andinas (Altieri y Nicholls 2017). El fréjol se menciona como cultivo de diversificación adaptativa en 38 de las 42 fichas parroquiales (90,5%).",
    tags: ["fréjol", "resiliencia", "adaptación"]
  },
  {
    q: "¿Qué SSPs se proyectan?",
    a: "Tres Trayectorias Socioeconómicas Compartidas: SSP1-2.6 (mitigación sostenida), SSP3-7.0 (rivalidad regional, emisiones altas), SSP5-8.5 (fósil intensivo, peor caso). En 3 horizontes: 2021-2040, 2041-2060, 2061-2080. Total 9 combinaciones × 42 parroquias × 4 cultivos = 1.512 inferencias.",
    tags: ["escenarios", "SSP", "horizontes"]
  },
  {
    q: "¿Qué licencia tienen los datos?",
    a: "Todos los productos del geoportal (Feature Services, PDFs, figuras, código y metadatos) están publicados bajo licencia Creative Commons Atribución 4.0 Internacional (CC BY 4.0). Uso libre con cita obligatoria: Pinto Páez, V.H. (2026) DOI 10.5281/zenodo.19288559.",
    tags: ["licencia", "cita"]
  },
];
