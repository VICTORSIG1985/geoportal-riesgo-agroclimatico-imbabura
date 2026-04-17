// Datos del ranking (SSP5-8.5 · 2061-2080) derivados del análisis. Fuente: FL_Priorizacion_Final_Imbabura_42
export interface RankingRow {
  rank: number; parroquia: string; canton: string;
  ir_medio: number; ir_max: number; n_cult_alto: number;
  prioridad: "Muy Alta"|"Alta"|"Alerta"|"Monitoreo"|"Favorable";
}

// Top 10 explícitos del manuscrito; resto aproximados desde FS
export const TOP10: RankingRow[] = [
  { rank: 1, parroquia: "García Moreno", canton: "Cotacachi", ir_medio: 0.689, ir_max: 0.742, n_cult_alto: 4, prioridad: "Muy Alta" },
  { rank: 2, parroquia: "Seis de Julio de Cuellaje", canton: "Cotacachi", ir_medio: 0.657, ir_max: 0.719, n_cult_alto: 3, prioridad: "Muy Alta" },
  { rank: 3, parroquia: "Lita", canton: "Ibarra", ir_medio: 0.618, ir_max: 0.701, n_cult_alto: 3, prioridad: "Alta" },
  { rank: 4, parroquia: "Selva Alegre", canton: "Otavalo", ir_medio: 0.601, ir_max: 0.678, n_cult_alto: 3, prioridad: "Alta" },
  { rank: 5, parroquia: "La Carolina", canton: "Ibarra", ir_medio: 0.591, ir_max: 0.665, n_cult_alto: 3, prioridad: "Alta" },
  { rank: 6, parroquia: "Peñaherrera", canton: "Cotacachi", ir_medio: 0.578, ir_max: 0.651, n_cult_alto: 2, prioridad: "Alta" },
  { rank: 7, parroquia: "Apuela", canton: "Cotacachi", ir_medio: 0.562, ir_max: 0.639, n_cult_alto: 2, prioridad: "Alta" },
  { rank: 8, parroquia: "Vacas Galindo", canton: "Cotacachi", ir_medio: 0.547, ir_max: 0.628, n_cult_alto: 2, prioridad: "Alerta" },
  { rank: 9, parroquia: "Ambuquí", canton: "Ibarra", ir_medio: 0.532, ir_max: 0.611, n_cult_alto: 2, prioridad: "Alerta" },
  { rank: 10, parroquia: "Plaza Gutiérrez", canton: "Cotacachi", ir_medio: 0.528, ir_max: 0.606, n_cult_alto: 2, prioridad: "Alerta" },
];

// IR medio provincial · Tabla 5 del manuscrito
export const IR_BY_CULTIVO_SSP_HORIZ = {
  papa: {
    "SSP1-2.6": [0.482, 0.502, 0.511],
    "SSP3-7.0": [0.495, 0.543, 0.596],
    "SSP5-8.5": [0.507, 0.558, 0.596],
  },
  maiz: {
    "SSP1-2.6": [0.441, 0.451, 0.463],
    "SSP3-7.0": [0.448, 0.478, 0.502],
    "SSP5-8.5": [0.453, 0.483, 0.514],
  },
  frejol: {
    "SSP1-2.6": [0.434, 0.436, 0.439],
    "SSP3-7.0": [0.439, 0.441, 0.434],
    "SSP5-8.5": [0.436, 0.438, 0.441],
  },
  quinua: {
    "SSP1-2.6": [0.281, 0.298, 0.312],
    "SSP3-7.0": [0.284, 0.348, 0.416],
    "SSP5-8.5": [0.282, 0.358, 0.412],
  },
};

export const HORIZONTES = ["2021-2040", "2041-2060", "2061-2080"];
export const SSPS = ["SSP1-2.6", "SSP3-7.0", "SSP5-8.5"];
export const CULTIVOS = ["papa", "maiz", "frejol", "quinua"];

// Exposición por cultivo (ha) — valores del manuscrito
export const EXPOSICION = {
  maiz: 7681.4,
  frejol: 2316.9,
  papa: 707.9,
  quinua: 18.36,
};

// Pérdida de aptitud bajo SSP5-8.5 · 2061-2080 (%)
export const PERDIDA_APTITUD = {
  quinua: -16.9, papa: -14.8, maiz: -9.6, frejol: -4.4,
};
