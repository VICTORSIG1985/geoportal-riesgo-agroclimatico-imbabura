export const SITE = {
  title: "Geoportal Riesgo Agroclimático",
  institution: "Universidad San Gregorio de Portoviejo",
  program: "Maestría en Prevención y Gestión de Riesgos con mención en Variabilidad Climática y Resiliencia Territorial",
  province: "Imbabura, Ecuador",
  author: "Víctor Hugo Pinto Páez",
  email: "vpintopaez@hotmail.com",
  orcid: "0009-0001-5573-8294",
  githubUser: "VICTORSIG1985",
  githubRepo: "agroclimatic-risk-imbabura",
  doi: "10.5281/zenodo.19288559",
  year: "2026",
  arcgisOrg: "USGP-EC.maps.arcgis.com",
};

export const SERVICES = {
  visorAppId: "7c43881435b04a47b3497706a28385f6",
  visorUrl: "https://www.arcgis.com/apps/instant/sidebar/index.html?appid=7c43881435b04a47b3497706a28385f6",
  webmapId: "43c9ab88a4e641f89fc5601805fdc142",
  webmapUrl: "https://www.arcgis.com/home/webmap/viewer.html?webmap=43c9ab88a4e641f89fc5601805fdc142",
  flParroquias: {
    id: "f69e1a47a0ae4a979a233ae304213cda",
    title: "FL_Parroquias_Base_Imbabura_42",
    url: "https://services.arcgis.com/LNQOp9d1bu5VZNME/arcgis/rest/services/FL_Parroquias_Base_Imbabura_42/FeatureServer/0",
    n: 42,
    desc: "42 polígonos parroquiales con ficha_url"
  },
  flRiesgoLong: {
    id: "53c74133a52f45aeab60eba6fe505b7c",
    title: "FL_Riesgo_Parroquial_Long_1512",
    url: "https://services.arcgis.com/LNQOp9d1bu5VZNME/arcgis/rest/services/FL_Riesgo_Parroquial_Long_1512/FeatureServer/0",
    n: 1512,
    desc: "1.512 inferencias cultivo × SSP × horizonte con IR + probabilidades"
  },
  flPrioridad: {
    id: "eedce1f65b064211a56e112860fcc810",
    title: "FL_Priorizacion_Final_Imbabura_42",
    url: "https://services.arcgis.com/LNQOp9d1bu5VZNME/arcgis/rest/services/FL_Priorizacion_Final_Imbabura_42/FeatureServer/0",
    n: 42,
    desc: "42 parroquias con ranking, IR medio/máximo, exposición por cultivo y prioridad final"
  },
};

export const MENU = [
  { slug: "/", label: "Inicio" },
  { slug: "/servicios", label: "Servicios" },
  { slug: "/visor", label: "Visor Cartográfico" },
  { slug: "/galeria", label: "Galería Científica" },
  { slug: "/fichas", label: "Fichas Parroquiales" },
  { slug: "/metodologia", label: "Metodología" },
  { slug: "/resultados", label: "Resultados" },
  { slug: "/datos", label: "Datos Abiertos" },
  { slug: "/descargas", label: "Descargas" },
  { slug: "/asistente", label: "Asistente IA" },
  { slug: "/acerca", label: "Acerca" },
];

export const PRIORITY_COLORS = {
  "Muy Alta": { hex: "#B2182B", label: "Muy Alta (IR ≥ 0,65)" },
  "Alta":     { hex: "#EF8A62", label: "Alta (IR 0,55 – 0,65)" },
  "Alerta":   { hex: "#FDDBC7", label: "Alerta (IR 0,45 – 0,55)" },
  "Monitoreo":{ hex: "#67A9CF", label: "Monitoreo (IR 0,40 – 0,45)" },
  "Favorable":{ hex: "#2166AC", label: "Favorable (IR < 0,40)" },
};
