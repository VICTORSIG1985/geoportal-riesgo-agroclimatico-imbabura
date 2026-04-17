"""
Script publicado como parte del Geoportal Riesgo Agroclimático — Imbabura, Ecuador
Pinto Páez, V. H. (2026). https://doi.org/10.5281/zenodo.19288559
Licencia: CC BY 4.0

NOTA: este archivo fue sanitizado para publicación pública.
- Credenciales (API keys, tokens, service accounts) removidas → <REDACTED_*>
- Rutas absolutas locales sustituidas por <RUTA_LOCAL>
Antes de ejecutar, configure sus propias rutas de entrada/salida y credenciales.

Archivo original: SCRIPT 09 GENERACIÓN DE FICHAS TÉCNICAS PARROQUIALES.py
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
SCRIPT 09: GENERACIÓN DE FICHAS TÉCNICAS PARROQUIALES
===============================================================================

Tesis:        Riesgo agroclimático de cultivos andinos bajo escenarios CMIP6
              en la provincia de Imbabura: modelamiento de distribución de
              especies para la gestión territorial

Autor:        Víctor Hugo Pinto Páez
Universidad:  San Gregorio de Portoviejo
Maestría:     Prevención y Gestión de Riesgos – Mención en Variabilidad
              Climática y Resiliencia Territorial

Versión:      1.0.0
Fecha:        2026-03

===============================================================================
PROPÓSITO
===============================================================================

Generar 42 fichas técnicas individuales (una por parroquia de Imbabura)
en formato PDF, destinadas a tomadores de decisiones de los GADs
parroquiales y cantonales. Cada ficha sintetiza:

  - Identificación territorial (cantón, área, ubicación)
  - Índice de Riesgo (IR) para los 4 cultivos bajo 3 SSPs × 3 horizontes
  - Superficie cultivada (componente de Exposición, Script 04C)
  - Ranking de priorización provincial
  - Mapa de ubicación de la parroquia dentro de Imbabura
  - Recomendaciones específicas basadas en los hallazgos

===============================================================================
ENTRADAS
===============================================================================

  ARCHIVO                                  SCRIPT   CONTENIDO
  ──────────────────────────────────────── ──────── ──────────────────────────
  riesgo_parroquial_*.csv                  07       IR × parroquia/cultivo/SSP
  exposicion_resumen_*.csv                 04C      ha por cultivo/parroquia
  ranking_priorizacion_*.csv               08       Ranking provincial
  Imbabura_Parroquia.gpkg                  CONALI   Límites 42 parroquias

===============================================================================
NORMAS DE CALIDAD
===============================================================================

  - ISO 19115:2014 — Metadatos geográficos
  - Fichas en formato PDF (una por parroquia)
  - Nomenclatura: FICHA_{CANTON}_{PARROQUIA}.pdf
  - Trazabilidad completa con reporte de auditoría

DEPENDENCIAS:
  pip install matplotlib geopandas pandas numpy --break-system-packages

EJECUCIÓN:
  %runfile 'D:/POSGRADOS/TESIS/03_SCRIPTS/python/SCRIPT_09_FICHAS_PARROQUIALES.py'

===============================================================================
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
from datetime import datetime
import time
import warnings
import unicodedata
import re

warnings.filterwarnings("ignore")

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

BASE_TESIS = Path(r"<RUTA_LOCAL>")
BASE_PREV = BASE_TESIS / "Prevención_de_Riesgos"

BN_DIR = BASE_PREV / "04_RESULTADOS" / "fase4_modelamiento" / "red_bayesiana"
EXPO_DIR = BASE_TESIS / "04_RESULTADOS" / "exposicion_agricola"
SINT_DIR = (BASE_TESIS / "04_RESULTADOS" / "fase5_productos" /
            "mapas_riesgo" / "sintesis")
PARROQUIAS_PATH = BASE_TESIS / "Imbabura_Parroquia.gpkg"

OUTPUT_DIR = (BASE_TESIS / "04_RESULTADOS" / "fase5_productos" /
              "fichas_parroquiales")
REPORTS_DIR = BASE_TESIS / "05_DOCUMENTACION" / "reportes_auditoria"

for d in [OUTPUT_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

VERSION = "1.2.0"
TS = datetime.now().strftime("%Y%m%d_%H%M%S")

CULTIVOS_KEYS = ["papa", "maiz", "frejol", "quinua"]
CULTIVOS = {
    "papa":   {"nombre": "Papa", "sci": "S. tuberosum", "tc": 25},
    "maiz":   {"nombre": "Maíz", "sci": "Z. mays", "tc": 35},
    "frejol": {"nombre": "Fréjol", "sci": "P. vulgaris", "tc": 30},
    "quinua": {"nombre": "Quinua", "sci": "C. quinoa", "tc": 32},
}

SSPS = ["ssp126", "ssp370", "ssp585"]
SSP_LBL = {"ssp126": "SSP1-2.6", "ssp370": "SSP3-7.0", "ssp585": "SSP5-8.5"}
HORIZONTES = ["2021-2040", "2041-2060", "2061-2080"]

IR_BINS = [0.0, 0.25, 0.40, 0.55, 0.70, 1.0]
IR_LABELS = ["Muy Bajo", "Bajo", "Medio", "Alto", "Muy Alto"]
IR_COLORS = ["#2166AC", "#67A9CF", "#FDDBC7", "#EF8A62", "#B2182B"]
CULT_COLORS = {"papa": "#8B4513", "maiz": "#DAA520",
               "frejol": "#228B22", "quinua": "#7B68EE"}


def buscar_csv(d, p):
    cs = sorted(d.glob(p))
    if not cs:
        raise FileNotFoundError(f"'{p}' no en {d}")
    return cs[-1]


def clasificar_ir(ir):
    for i in range(len(IR_BINS) - 1):
        if ir <= IR_BINS[i + 1]:
            return IR_LABELS[i], IR_COLORS[i]
    return IR_LABELS[-1], IR_COLORS[-1]


def nombre_archivo(canton, parroquia):
    def limpiar(t):
        t = unicodedata.normalize("NFKD", t).encode("ASCII", "ignore").decode()
        t = re.sub(r"[^A-Za-z0-9]+", "_", t)
        return t.strip("_").upper()
    return f"FICHA_{limpiar(canton)}_{limpiar(parroquia)}"


def generar_recomendaciones(ir_datos, expo_datos):
    recos = []
    peor = ir_datos[
        (ir_datos["ssp"] == "ssp585") & (ir_datos["horizonte"] == "2061-2080")
    ]
    if len(peor) > 0:
        row_max = peor.loc[peor["indice_riesgo"].idxmax()]
        ir_max = row_max["indice_riesgo"]
        cn = CULTIVOS[row_max["cultivo"]]["nombre"]
        if ir_max >= 0.70:
            recos.append(
                f"PRIORIDAD ALTA: {cn} alcanza riesgo Muy Alto "
                f"(IR={ir_max:.2f}). Evaluar variedades tolerantes "
                f"al calor o transición a cultivos alternativos.")
        elif ir_max >= 0.55:
            recos.append(
                f"ATENCIÓN: {cn} presenta riesgo Alto (IR={ir_max:.2f}). "
                f"Implementar monitoreo agroclimático y adaptación.")
        elif ir_max >= 0.40:
            recos.append(
                f"MONITOREO: {cn} en riesgo Medio (IR={ir_max:.2f}). "
                f"Vigilar calendarios de siembra y disponibilidad hídrica.")
        else:
            recos.append(
                f"FAVORABLE: Todos los cultivos con riesgo Bajo a Muy Bajo "
                f"(IR máx={ir_max:.2f}).")

    for cult in CULTIVOS_KEYS:
        dc = ir_datos[ir_datos["cultivo"] == cult]
        vi = dc[(dc["ssp"] == "ssp585") & (dc["horizonte"] == "2021-2040")]
        vf = dc[(dc["ssp"] == "ssp585") & (dc["horizonte"] == "2061-2080")]
        if len(vi) > 0 and len(vf) > 0:
            delta = vf["indice_riesgo"].values[0] - vi["indice_riesgo"].values[0]
            if delta > 0.10:
                recos.append(
                    f"ALERTA {CULTIVOS[cult]['nombre']}: incremento "
                    f"{delta:+.3f} entre 2021-2040 y 2061-2080 (SSP5-8.5).")

    if expo_datos is not None and not expo_datos.empty:
        total = sum(expo_datos.get(c, pd.Series([0])).fillna(0).values[0]
                    for c in ["papa", "maiz", "frejol"]
                    if c in expo_datos.columns)
        if total > 500:
            recos.append(
                f"EXPOSICIÓN ALTA: {total:.0f} ha cultivadas. "
                f"Diversificación productiva recomendada.")

    fr = peor[peor["cultivo"] == "frejol"] if len(peor) > 0 else pd.DataFrame()
    if len(fr) > 0 and fr["indice_riesgo"].values[0] < 0.45:
        recos.append(
            "OPORTUNIDAD: Fréjol mantiene riesgo bajo en todos los "
            "escenarios. Considerar como cultivo de diversificación.")

    return recos if recos else ["Sin alertas específicas."]


def partir_texto(texto, max_chars=95):
    """Parte texto en líneas de máximo max_chars caracteres."""
    palabras = texto.split()
    lineas = []
    actual = ""
    for p in palabras:
        if len(actual + " " + p) > max_chars:
            lineas.append(actual.strip())
            actual = p
        else:
            actual += " " + p
    if actual.strip():
        lineas.append(actual.strip())
    return lineas


# =============================================================================
# GENERADOR DE FICHA
# =============================================================================

def generar_ficha(parr_nombre, canton_nombre, area_km2, ranking,
                   ir_datos, expo_datos, gdf_parr, gdf_hl, outdir):

    fig = plt.figure(figsize=(8.5, 11), dpi=150)
    fig.patch.set_facecolor("white")

    # ═══════════════════════════════════════════════════════════
    # ZONA 1: ENCABEZADO (y: 0.94 – 0.98)
    # ═══════════════════════════════════════════════════════════
    fig.text(0.50, 0.978, "FICHA TÉCNICA DE RIESGO AGROCLIMÁTICO",
             fontsize=15, fontweight="bold", ha="center", va="top",
             color="#1F4E79")
    fig.text(0.50, 0.958,
             f"Parroquia {parr_nombre}  \u2014  Cantón {canton_nombre}",
             fontsize=12, fontweight="bold", ha="center", va="top",
             color="#2E75B6")
    fig.text(0.50, 0.943,
             "Riesgo agroclimático de cultivos andinos bajo escenarios "
             "CMIP6 en Imbabura",
             fontsize=7, ha="center", va="top", color="0.5", style="italic")
    fig.add_artist(plt.Line2D([0.04, 0.96], [0.928, 0.928],
                               transform=fig.transFigure,
                               color="#1F4E79", linewidth=1.5))

    # ═══════════════════════════════════════════════════════════
    # ZONA 2: INFO + MAPA (izq) + TABLA IR (der) (y: 0.60 – 0.93)
    # ═══════════════════════════════════════════════════════════

    # --- Info (izq arriba) ---
    info = [("Provincia:", "Imbabura"),
            ("Cantón:", canton_nombre),
            ("Parroquia:", parr_nombre),
            ("Superficie:", f"{area_km2:.1f} km\u00b2"),
            ("Ranking:", f"#{ranking} de 42 parroquias")]

    y_i = 0.925
    for lbl, val in info:
        fig.text(0.05, y_i, lbl, fontsize=8, fontweight="bold",
                 va="top", color="0.3")
        fig.text(0.19, y_i, val, fontsize=8, va="top")
        y_i -= 0.016

    # --- Mapa de ubicación (izq abajo) ---
    # Posición: debajo del texto de info, con margen
    ax_map = fig.add_axes([0.04, 0.62, 0.28, 0.20])
    gdf_parr.plot(ax=ax_map, color="#E0E0E0", edgecolor="0.6", linewidth=0.3)
    gdf_hl.plot(ax=ax_map, color="#B2182B", edgecolor="black", linewidth=1.2)
    ax_map.set_title("Ubicación en Imbabura", fontsize=7, fontweight="bold",
                      pad=2, color="0.3")
    ax_map.set_axis_off()

    # --- Tabla IR (derecha) ---
    ax_t = fig.add_axes([0.36, 0.60, 0.60, 0.33])
    ax_t.set_xlim(0, 12)
    ax_t.set_ylim(0, 12)
    ax_t.set_axis_off()

    # Título tabla (parte superior del axes, bien separado de headers)
    ax_t.text(6, 11.8,
              "Índice de Riesgo (IR) por Cultivo y Escenario",
              fontsize=9, fontweight="bold", ha="center", va="top",
              color="#1F4E79")

    # Encabezados columna (separados del título)
    cx = [2.0, 4.8, 6.8, 8.8, 10.8]
    ch = ["Escenario", "Papa", "Maíz", "Fréjol", "Quinua"]
    for x, h in zip(cx, ch):
        ax_t.text(x, 10.7, h, fontsize=6.5, fontweight="bold", ha="center",
                  va="center", color="white",
                  bbox=dict(boxstyle="round,pad=0.25", fc="#1F4E79",
                            ec="none"))

    # Filas de datos (9 filas, separadas de headers)
    y_r = 9.7
    row_spacing = 0.88
    for ssp in SSPS:
        for hor in HORIZONTES:
            lbl = f"{SSP_LBL[ssp]}  {hor}"
            ax_t.text(cx[0], y_r, lbl, fontsize=5, ha="center", va="center")

            for ci, cult in enumerate(CULTIVOS_KEYS):
                d = ir_datos[
                    (ir_datos["cultivo"] == cult) &
                    (ir_datos["ssp"] == ssp) &
                    (ir_datos["horizonte"] == hor)
                ]
                if len(d) > 0:
                    iv = d["indice_riesgo"].values[0]
                    _, clr = clasificar_ir(iv)
                    ax_t.text(cx[ci + 1], y_r, f"{iv:.3f}",
                              fontsize=6, ha="center", va="center",
                              fontweight="bold",
                              bbox=dict(boxstyle="round,pad=0.2",
                                        fc=clr, ec="0.5", lw=0.3,
                                        alpha=0.85))
                else:
                    ax_t.text(cx[ci + 1], y_r, "\u2014", fontsize=6,
                              ha="center", va="center", color="0.5")
            y_r -= row_spacing

    # Separador Z2-Z3
    fig.add_artist(plt.Line2D([0.04, 0.96], [0.59, 0.59],
                               transform=fig.transFigure,
                               color="#D0D0D0", linewidth=0.5))

    # ═══════════════════════════════════════════════════════════
    # ZONA 3: EXPOSICIÓN AGRÍCOLA (y: 0.43 – 0.58)
    # ═══════════════════════════════════════════════════════════
    fig.text(0.50, 0.575,
             "Exposición Agrícola \u2014 Superficie Cultivada",
             fontsize=10, fontweight="bold", ha="center", va="top",
             color="#1F4E79")

    ax_bar = fig.add_axes([0.08, 0.44, 0.48, 0.11])

    cult_names = ["Papa", "Maíz", "Fréjol"]
    cult_cols = ["papa", "maiz", "frejol"]
    bar_colors = ["#8B4513", "#DAA520", "#228B22"]

    valores = []
    for c in cult_cols:
        if (expo_datos is not None and c in expo_datos.columns
                and len(expo_datos) > 0):
            v = expo_datos[c].values[0]
            valores.append(v if pd.notna(v) else 0)
        else:
            valores.append(0)

    ax_bar.barh(range(3), valores, color=bar_colors, edgecolor="0.4",
                linewidth=0.5, height=0.6, alpha=0.8)
    ax_bar.set_yticks(range(3))
    ax_bar.set_yticklabels(cult_names, fontsize=8, fontweight="bold")
    ax_bar.set_xlabel("Hectáreas (ha)", fontsize=7)
    ax_bar.tick_params(axis="x", labelsize=7)
    ax_bar.spines["top"].set_visible(False)
    ax_bar.spines["right"].set_visible(False)

    max_v = max(valores) if max(valores) > 0 else 1
    for i, v in enumerate(valores):
        if v > 0:
            ax_bar.text(v + max_v * 0.03, i, f"{v:.1f} ha",
                        fontsize=7, va="center")

    # Nota quinua (derecha, alineada con barras)
    fig.text(0.62, 0.50,
             "Quinua: 18.36 ha\na nivel provincial\n(ESPAC 2024).\n"
             "Sin dato parroquial.",
             fontsize=6.5, va="top", color="0.4", style="italic",
             bbox=dict(boxstyle="round,pad=0.4", fc="#FFF8E1",
                       ec="0.7", lw=0.5))

    # Separador Z3-Z4
    fig.add_artist(plt.Line2D([0.04, 0.96], [0.42, 0.42],
                               transform=fig.transFigure,
                               color="#D0D0D0", linewidth=0.5))

    # ═══════════════════════════════════════════════════════════
    # ZONA 4: TRAYECTORIA + LEYENDA IR (y: 0.21 – 0.40)
    # ═══════════════════════════════════════════════════════════
    fig.text(0.30, 0.405,
             "Trayectoria de Riesgo bajo SSP5-8.5",
             fontsize=9, fontweight="bold", ha="center", va="top",
             color="#1F4E79")

    ax_tray = fig.add_axes([0.06, 0.22, 0.48, 0.16])

    for cult in CULTIVOS_KEYS:
        ds = ir_datos[
            (ir_datos["cultivo"] == cult) & (ir_datos["ssp"] == "ssp585")
        ].sort_values("horizonte")
        if len(ds) > 0:
            ax_tray.plot(range(len(ds)), ds["indice_riesgo"].values,
                          "o-", color=CULT_COLORS[cult], linewidth=2,
                          markersize=5, label=CULTIVOS[cult]["nombre"])

    ax_tray.set_xticks(range(3))
    ax_tray.set_xticklabels(["2021\u20132040", "2041\u20132060",
                              "2061\u20132080"], fontsize=7)
    ax_tray.set_ylabel("IR", fontsize=8)
    ax_tray.set_ylim(0, 1.0)
    ax_tray.set_xlim(-0.2, 2.2)
    ax_tray.legend(fontsize=6.5, loc="upper left", framealpha=0.9,
                    edgecolor="0.5")
    ax_tray.grid(True, alpha=0.2)
    ax_tray.axhspan(0.70, 1.0, alpha=0.06, color="red")
    ax_tray.axhspan(0.55, 0.70, alpha=0.04, color="orange")
    ax_tray.axhspan(0.0, 0.25, alpha=0.06, color="blue")
    ax_tray.spines["top"].set_visible(False)
    ax_tray.spines["right"].set_visible(False)

    # Leyenda IR (derecha)
    fig.text(0.73, 0.405, "Clasificación del IR",
             fontsize=8, fontweight="bold", ha="center", va="top",
             color="#1F4E79")

    ax_ley = fig.add_axes([0.58, 0.22, 0.36, 0.16])
    ax_ley.set_xlim(0, 10)
    ax_ley.set_ylim(0, 5.5)
    ax_ley.set_axis_off()

    for i, (lbl, clr) in enumerate(zip(IR_LABELS, IR_COLORS)):
        y = 4.5 - i * 1.0
        ax_ley.add_patch(plt.Rectangle((0.3, y - 0.3), 1.5, 0.6,
                                        facecolor=clr, edgecolor="0.4",
                                        linewidth=0.5))
        ax_ley.text(2.3, y,
                     f"{lbl}  ({IR_BINS[i]:.2f} \u2013 {IR_BINS[i+1]:.2f})",
                     fontsize=6.5, va="center")

    # Separador Z4-Z5
    fig.add_artist(plt.Line2D([0.04, 0.96], [0.20, 0.20],
                               transform=fig.transFigure,
                               color="#D0D0D0", linewidth=0.5))

    # ═══════════════════════════════════════════════════════════
    # ZONA 5: RECOMENDACIONES (y: 0.07 – 0.19)
    # ═══════════════════════════════════════════════════════════
    fig.text(0.05, 0.19,
             "Recomendaciones para la gestión territorial:",
             fontsize=9, fontweight="bold", color="#1F4E79", va="top")

    recos = generar_recomendaciones(ir_datos, expo_datos)
    y_rc = 0.172
    for reco in recos[:3]:  # máximo 3 para no desbordar
        lineas = partir_texto(reco, max_chars=105)
        texto = "\u2022  " + lineas[0]
        if len(lineas) > 1:
            texto += "\n   " + "\n   ".join(lineas[1:])
        fig.text(0.06, y_rc, texto, fontsize=7, va="top", color="0.2",
                 linespacing=1.3)
        y_rc -= 0.014 * len(lineas) + 0.008

    # ═══════════════════════════════════════════════════════════
    # ZONA 6: PIE DE PÁGINA (y: 0.01 – 0.06)
    # ═══════════════════════════════════════════════════════════
    fig.add_artist(plt.Line2D([0.04, 0.96], [0.055, 0.055],
                               transform=fig.transFigure,
                               color="#1F4E79", linewidth=0.8))

    fig.text(0.04, 0.042,
             "Fuentes: BASD-CMIP6-PE (Fernandez-Palomino et al., 2024) \u00b7 "
             "CONALI/INEC \u00b7 MapSPAM v2r0 (IFPRI) \u00b7 ESPAC 2024 \u00b7 "
             "Marco IPCC AR6",
             fontsize=5.5, color="0.45", style="italic", va="top")

    fig.text(0.96, 0.042,
             f"V. Pinto Páez | {datetime.now().strftime('%Y-%m')}",
             fontsize=5.5, ha="right", color="0.5", va="top")

    fig.text(0.50, 0.018,
             "Maestría en Prevención y Gestión de Riesgos \u00b7 "
             "Universidad San Gregorio de Portoviejo",
             fontsize=5.5, ha="center", color="0.5", va="top")

    # ═══════════════════════════════════════════════════════════
    # GUARDAR
    # ═══════════════════════════════════════════════════════════
    nm = nombre_archivo(canton_nombre, parr_nombre)
    fig.savefig(outdir / f"{nm}.pdf", dpi=200, facecolor="white")
    plt.close(fig)
    return nm


# =============================================================================
# MAIN
# =============================================================================

def main():
    t0 = time.time()

    print("╔" + "═" * 68 + "╗")
    print("║  SCRIPT 09 v1.2: FICHAS PARROQUIALES \u2014 LAYOUT DEFINITIVO"
          + " " * 8 + "║")
    print("╚" + "═" * 68 + "╝")

    print(f"\n[1/4] CARGA")
    print("─" * 60)

    gdf_parr = gpd.read_file(PARROQUIAS_PATH)
    if gdf_parr.crs is None or gdf_parr.crs.to_epsg() != 32717:
        gdf_parr = gdf_parr.to_crs(epsg=32717)
    print(f"  ✓ Parroquias: {len(gdf_parr)}")

    csv_r = buscar_csv(BN_DIR, "riesgo_parroquial_*.csv")
    df_riesgo = pd.read_csv(csv_r)
    print(f"  ✓ Riesgo: {csv_r.name} ({len(df_riesgo)} filas)")

    csv_e = buscar_csv(EXPO_DIR, "exposicion_resumen_*.csv")
    df_expo = pd.read_csv(csv_e)
    print(f"  ✓ Exposición: {csv_e.name}")

    csv_p = buscar_csv(SINT_DIR, "ranking_priorizacion_*.csv")
    df_ranking = pd.read_csv(csv_p)
    print(f"  ✓ Ranking: {csv_p.name}")

    assert len(df_riesgo) == 1512

    df_riesgo["_k"] = df_riesgo["parroquia"].str.upper().str.strip()
    df_expo["_k"] = df_expo["parroquia"].str.upper().str.strip()
    df_ranking["_k"] = df_ranking["parroquia"].str.upper().str.strip()
    gdf_parr["_k"] = gdf_parr["DPA_DESPAR"].str.upper().str.strip()

    print(f"\n[2/4] GENERACIÓN ({len(gdf_parr)} fichas)")
    print("─" * 60)

    fichas = []
    errores = []

    for idx, row in gdf_parr.iterrows():
        pk = row["_k"]
        try:
            area = row.geometry.area / 1e6
            rk = df_ranking[df_ranking["_k"] == pk]
            ranking = int(rk["ranking"].values[0]) if len(rk) > 0 else 0

            nm = generar_ficha(
                row["DPA_DESPAR"], row["DPA_DESCAN"], area, ranking,
                df_riesgo[df_riesgo["_k"] == pk],
                df_expo[df_expo["_k"] == pk],
                gdf_parr,
                gdf_parr[gdf_parr["_k"] == pk],
                OUTPUT_DIR)

            fichas.append({"parroquia": row["DPA_DESPAR"],
                           "canton": row["DPA_DESCAN"],
                           "ranking": ranking, "archivo": f"{nm}.pdf"})

            if (idx + 1) % 10 == 0 or (idx + 1) == len(gdf_parr):
                print(f"  {idx + 1}/{len(gdf_parr)}")

        except Exception as e:
            errores.append(f"{row['DPA_DESPAR']}: {e}")
            print(f"  ⚠ {row['DPA_DESPAR']}: {e}")

    print(f"  ✓ {len(fichas)}/{len(gdf_parr)} fichas")

    print(f"\n[3/4] ÍNDICE")
    print("─" * 60)
    df_ind = pd.DataFrame(fichas).sort_values("ranking")
    csv_ind = OUTPUT_DIR / f"INDICE_FICHAS_{TS}.csv"
    df_ind.to_csv(csv_ind, index=False, encoding="utf-8-sig")
    print(f"  ✓ {csv_ind.name}")

    print(f"\n[4/4] REPORTE")
    print("─" * 60)
    dur = time.time() - t0
    rep = REPORTS_DIR / f"REPORTE_SCRIPT_09_v12_{TS}.txt"
    with open(rep, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("REPORTE \u2014 SCRIPT 09 v1.2 \u2014 FICHAS PARROQUIALES\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Versión: {VERSION}\n")
        f.write(f"Duración: {dur:.0f}s ({dur/60:.1f} min)\n")
        f.write(f"Fichas: {len(fichas)} | Errores: {len(errores)}\n\n")
        for _, r in df_ind.iterrows():
            f.write(f"  #{r['ranking']:<3} {r['canton']:<20} "
                    f"{r['parroquia']:<25} {r['archivo']}\n")
        f.write(f"\nESTADO: "
                f"{'APROBADO' if len(fichas) == 42 else 'REVISAR'}\n")
        f.write("=" * 70 + "\n")
    print(f"  ✓ {rep.name}")

    print(f"\n╔{'═' * 68}╗")
    print(f"║  ✓ SCRIPT 09 v1.2 COMPLETADO{' ' * 39}║")
    print(f"╚{'═' * 68}╝")
    print(f"  ⏱  {dur:.0f}s · {len(fichas)} fichas · {OUTPUT_DIR}")
    for _, r in df_ind.head(5).iterrows():
        print(f"    #{r['ranking']:<3} {r['canton']:<18} {r['parroquia']}")
    print(f"\n  🔜 DOC_METODOLOGIA_SCRIPT_09")

    return fichas


if __name__ == "__main__":
    fichas = main()