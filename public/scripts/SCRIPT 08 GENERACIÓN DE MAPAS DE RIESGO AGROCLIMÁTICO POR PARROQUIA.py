"""
Script publicado como parte del Geoportal Riesgo Agroclimático — Imbabura, Ecuador
Pinto Páez, V. H. (2026). https://doi.org/10.5281/zenodo.19288559
Licencia: CC BY 4.0

NOTA: este archivo fue sanitizado para publicación pública.
- Credenciales (API keys, tokens, service accounts) removidas → <REDACTED_*>
- Rutas absolutas locales sustituidas por <RUTA_LOCAL>
Antes de ejecutar, configure sus propias rutas de entrada/salida y credenciales.

Archivo original: SCRIPT 08 GENERACIÓN DE MAPAS DE RIESGO AGROCLIMÁTICO POR PARROQUIA.py
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
SCRIPT 08 v3.0: MAPAS DE RIESGO AGROCLIMÁTICO POR PARROQUIA
===============================================================================

Versión:      3.0.0
Fecha:        2026-03

CORRECCIONES v3.0:
  - Flecha de norte cartográfica real (fuera del mapa, sin superposición)
  - Grilla de coordenadas geográficas (lat/lon en grados decimales)
  - Barra de escala prominente con diseño estándar
  - Marco/recuadro alrededor del mapa
  - SIN etiquetas numéricas sobre el mapa (el color comunica el riesgo)
  - Solo el mapa de priorización y resumen llevan etiquetas (top 5)
  - Títulos jerárquicos claros con cultivo, escenario y horizonte

EJECUCIÓN:
  Primero: %runfile 'LIMPIAR_MAPAS_08_v2.py'
  Luego:   %runfile 'SCRIPT_08_MAPAS_RIESGO_v3.py'

===============================================================================
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
from matplotlib_scalebar.scalebar import ScaleBar
from pathlib import Path
from datetime import datetime
import time
import warnings

warnings.filterwarnings("ignore")

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

BASE_TESIS = Path(r"<RUTA_LOCAL>")
BASE_PREV = BASE_TESIS / "Prevención_de_Riesgos"

BN_DIR = BASE_PREV / "04_RESULTADOS" / "fase4_modelamiento" / "red_bayesiana"
EXPO_DIR = BASE_TESIS / "04_RESULTADOS" / "exposicion_agricola"
PARROQUIAS_PATH = BASE_TESIS / "Imbabura_Parroquia.gpkg"

OUTPUT_DIR = BASE_TESIS / "04_RESULTADOS" / "fase5_productos" / "mapas_riesgo"
OUTPUT_IND = OUTPUT_DIR / "individuales"
OUTPUT_PAN = OUTPUT_DIR / "paneles_tesis"
OUTPUT_CAM = OUTPUT_DIR / "cambio_temporal"
OUTPUT_SIN = OUTPUT_DIR / "sintesis"
REPORTS_DIR = BASE_TESIS / "05_DOCUMENTACION" / "reportes_auditoria"

for d in [OUTPUT_IND, OUTPUT_PAN, OUTPUT_CAM, OUTPUT_SIN, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

VERSION = "3.0.0"
TS = datetime.now().strftime("%Y%m%d_%H%M%S")
DPI = 300

CULTIVOS = {
    "papa":   {"nombre": "Papa", "sci": "Solanum tuberosum L.", "tc": "25°C"},
    "maiz":   {"nombre": "Maíz", "sci": "Zea mays L.", "tc": "35°C"},
    "frejol": {"nombre": "Fréjol", "sci": "Phaseolus vulgaris L.", "tc": "30°C"},
    "quinua": {"nombre": "Quinua", "sci": "Chenopodium quinoa Willd.", "tc": "32°C"},
}

SSPS = ["ssp126", "ssp370", "ssp585"]
SSP_LBL = {"ssp126": "SSP1-2.6", "ssp370": "SSP3-7.0", "ssp585": "SSP5-8.5"}
HORIZONTES = ["2021-2040", "2041-2060", "2061-2080"]
H_LBL = {"2021-2040": "2021–2040", "2041-2060": "2041–2060",
          "2061-2080": "2061–2080"}

IR_BINS = [0.0, 0.25, 0.40, 0.55, 0.70, 1.0]
IR_LABELS = ["Muy Bajo", "Bajo", "Medio", "Alto", "Muy Alto"]
IR_COLORS = ["#2166AC", "#67A9CF", "#FDDBC7", "#EF8A62", "#B2182B"]

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "DejaVu Sans"],
    "font.size": 9,
})


# =============================================================================
# FUNCIONES BASE
# =============================================================================

def buscar_csv(d, p):
    cs = sorted(d.glob(p))
    if not cs:
        raise FileNotFoundError(f"'{p}' no encontrado en {d}")
    return cs[-1]


def cmap_ir():
    return mcolors.ListedColormap(IR_COLORS), mcolors.BoundaryNorm(IR_BINS, 5)


def prep_gdf(gdf_p, df, cult=None, ssp=None, hor=None):
    d = df.copy()
    if cult: d = d[d["cultivo"] == cult]
    if ssp: d = d[d["ssp"] == ssp]
    if hor: d = d[d["horizonte"] == hor]
    d["_k"] = d["parroquia"].str.upper().str.strip()
    g = gdf_p.copy()
    g["_k"] = g["DPA_DESPAR"].str.upper().str.strip()
    return g.merge(d, on="_k", how="left")


def agregar_grilla(ax, gdf_parr):
    """Agrega grilla de coordenadas geográficas al mapa."""
    # Obtener extent en coordenadas geográficas
    bounds = gdf_parr.to_crs(epsg=4326).total_bounds  # minx, miny, maxx, maxy
    # Convertir bounds a UTM para el plot
    from pyproj import Transformer
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32717", always_xy=True)

    # Definir ticks de grilla en grados
    lon_min = np.floor(bounds[0] * 4) / 4  # redondeado a 0.25°
    lon_max = np.ceil(bounds[2] * 4) / 4
    lat_min = np.floor(bounds[1] * 4) / 4
    lat_max = np.ceil(bounds[3] * 4) / 4

    lons = np.arange(lon_min, lon_max + 0.25, 0.25)
    lats = np.arange(lat_min, lat_max + 0.25, 0.25)

    # Dibujar líneas de grilla transformadas a UTM
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    for lon in lons:
        pts = np.array([transformer.transform(lon, lat) for lat in
                        np.linspace(bounds[1] - 0.5, bounds[3] + 0.5, 100)])
        ax.plot(pts[:, 0], pts[:, 1], color="0.75", linewidth=0.3,
                linestyle="--", zorder=0)

    for lat in lats:
        pts = np.array([transformer.transform(lon, lat) for lon in
                        np.linspace(bounds[0] - 0.5, bounds[2] + 0.5, 100)])
        ax.plot(pts[:, 0], pts[:, 1], color="0.75", linewidth=0.3,
                linestyle="--", zorder=0)

    # Etiquetas de coordenadas en los bordes
    for lon in lons:
        x_utm, y_utm = transformer.transform(lon, bounds[1])
        if xlim[0] <= x_utm <= xlim[1]:
            ax.text(x_utm, ylim[0] - (ylim[1] - ylim[0]) * 0.02,
                    f"{lon:.2f}°W" if lon < 0 else f"{lon:.2f}°",
                    fontsize=6, ha="center", va="top", color="0.4")

    for lat in lats:
        x_utm, y_utm = transformer.transform(bounds[0], lat)
        if ylim[0] <= y_utm <= ylim[1]:
            ax.text(xlim[0] - (xlim[1] - xlim[0]) * 0.02, y_utm,
                    f"{lat:.2f}°N" if lat >= 0 else f"{abs(lat):.2f}°S",
                    fontsize=6, ha="right", va="center", color="0.4")

    ax.set_xlim(xlim)
    ax.set_ylim(ylim)


def agregar_norte_flecha(ax):
    """Flecha de norte cartográfica real, fuera del área del mapa."""
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    # Posición: arriba a la derecha, fuera del mapa
    x_pos = xlim[1] + (xlim[1] - xlim[0]) * 0.03
    y_base = ylim[1] - (ylim[1] - ylim[0]) * 0.15
    y_top = y_base + (ylim[1] - ylim[0]) * 0.10

    # Flecha
    arrow = FancyArrowPatch(
        (x_pos, y_base), (x_pos, y_top),
        arrowstyle="-|>", mutation_scale=15,
        linewidth=1.5, color="black", clip_on=False)
    ax.add_patch(arrow)

    # Letra N
    ax.text(x_pos, y_top + (ylim[1] - ylim[0]) * 0.02, "N",
            fontsize=12, fontweight="bold", ha="center", va="bottom",
            clip_on=False)


def agregar_escala(ax):
    """Barra de escala prominente."""
    try:
        sb = ScaleBar(1, units="m", location="lower right",
                      length_fraction=0.25, font_properties={"size": 8},
                      box_alpha=0.9, pad=0.8, sep=3, border_pad=0.8,
                      frameon=True, color="black", box_color="white")
        ax.add_artist(sb)
    except Exception:
        pass


def marco_mapa(ax):
    """Agrega marco/recuadro al mapa y limpia ejes."""
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(1.0)
        spine.set_color("0.3")


def leyenda_ir(ax, loc="lower left", fs=7):
    patches = [mpatches.Patch(facecolor=c, edgecolor="0.4", linewidth=0.5,
               label=f"{l} ({IR_BINS[i]:.2f} – {IR_BINS[i+1]:.2f})")
               for i, (l, c) in enumerate(zip(IR_LABELS, IR_COLORS))]
    return ax.legend(handles=patches, title="Índice de Riesgo (IR)",
                     loc=loc, fontsize=fs, title_fontsize=fs + 1,
                     frameon=True, fancybox=False, edgecolor="0.5",
                     framealpha=0.95, borderpad=0.6)


def pie_fuentes(fig, extra=""):
    t = ("Fuentes: BASD-CMIP6-PE (Fernandez-Palomino et al., 2024) · "
         "CONALI/INEC · MapSPAM v2r0 (IFPRI, 2024) · ESPAC 2024 (INEC)")
    if extra:
        t += f" · {extra}"
    fig.text(0.5, 0.01, t, fontsize=5.5, ha="center", color="0.45",
             style="italic")
    fig.text(0.98, 0.01, f"Elaboración: V. Pinto Páez | "
             f"{datetime.now().strftime('%Y-%m')}",
             fontsize=5.5, ha="right", color="0.5")


# =============================================================================
# MAPA INDIVIDUAL IR
# =============================================================================

def mapa_individual(gdf_p, df_r, cult, ssp, hor, outdir):
    cm, nm = cmap_ir()
    gdf = prep_gdf(gdf_p, df_r, cult, ssp, hor)
    info = CULTIVOS[cult]

    fig, ax = plt.subplots(1, 1, figsize=(10, 7.5))

    # Fondo y datos
    gdf_p.plot(ax=ax, color="#F0F0F0", edgecolor="0.65", linewidth=0.4)
    gdf.plot(column="indice_riesgo", ax=ax, cmap=cm, norm=nm,
             edgecolor="0.4", linewidth=0.5, missing_kwds={"color": "0.9"})

    # Elementos cartográficos
    agregar_grilla(ax, gdf_p)
    marco_mapa(ax)
    agregar_norte_flecha(ax)
    agregar_escala(ax)
    leyenda_ir(ax)

    # Títulos
    fig.suptitle(f"Riesgo Agroclimático — {info['nombre']} "
                 f"({info['sci']})",
                 fontsize=13, fontweight="bold", y=0.97)
    fig.text(0.5, 0.93,
             f"Escenario {SSP_LBL[ssp]}  ·  Horizonte {hor}  ·  "
             f"T crítica: {info['tc']}  ·  Marco IPCC AR6",
             fontsize=9, ha="center", color="0.3", style="italic")

    pie_fuentes(fig)

    nombre = f"IR_{cult}_{ssp}_{hor.replace('-', '_')}"
    for fmt in ["pdf", "png"]:
        fig.savefig(outdir / f"{nombre}.{fmt}",
                    dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return nombre


# =============================================================================
# PANEL POR CULTIVO (3×3)
# =============================================================================

def panel_cultivo(gdf_p, df_r, cult, outdir):
    cm, nm = cmap_ir()
    info = CULTIVOS[cult]

    fig, axes = plt.subplots(3, 3, figsize=(16, 14))

    fig.suptitle(
        f"Riesgo Agroclimático — {info['nombre']} ({info['sci']})\n"
        f"T crítica: {info['tc']}  ·  Marco IPCC AR6",
        fontsize=14, fontweight="bold", y=1.02)

    for i, ssp in enumerate(SSPS):
        for j, hor in enumerate(HORIZONTES):
            ax = axes[i, j]
            gdf = prep_gdf(gdf_p, df_r, cult, ssp, hor)

            gdf_p.plot(ax=ax, color="#F0F0F0", edgecolor="0.7", linewidth=0.3)
            gdf.plot(column="indice_riesgo", ax=ax, cmap=cm, norm=nm,
                     edgecolor="0.5", linewidth=0.3,
                     missing_kwds={"color": "0.9"})

            ir_m = gdf["indice_riesgo"].mean()
            ax.text(0.03, 0.97, f"IR medio: {ir_m:.3f}",
                    transform=ax.transAxes, fontsize=7, va="top",
                    fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.3", fc="white",
                              alpha=0.85, lw=0.4))

            if i == 0:
                ax.set_title(H_LBL[hor], fontsize=10, fontweight="bold", pad=8)
            if j == 0:
                ax.text(-0.05, 0.5, SSP_LBL[ssp], transform=ax.transAxes,
                        fontsize=10, fontweight="bold", rotation=90,
                        va="center", ha="right")

            ax.set_xticks([])
            ax.set_yticks([])
            for sp in ax.spines.values():
                sp.set_visible(True)
                sp.set_linewidth(0.5)
                sp.set_color("0.5")

    # Leyenda
    patches = [mpatches.Patch(facecolor=c, edgecolor="0.4", linewidth=0.5,
               label=f"{l} ({IR_BINS[i]:.2f}–{IR_BINS[i+1]:.2f})")
               for i, (l, c) in enumerate(zip(IR_LABELS, IR_COLORS))]
    fig.legend(handles=patches, title="Índice de Riesgo (IR)",
               loc="lower center", ncol=5, fontsize=8, title_fontsize=9,
               frameon=True, bbox_to_anchor=(0.5, -0.02))

    pie_fuentes(fig)
    plt.subplots_adjust(wspace=0.05, hspace=0.1)

    nombre = f"PANEL_IR_{cult}_9escenarios"
    for fmt in ["pdf", "png"]:
        fig.savefig(outdir / f"{nombre}.{fmt}",
                    dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return nombre


# =============================================================================
# PANEL POR SSP (4×3)
# =============================================================================

def panel_ssp(gdf_p, df_r, ssp, outdir):
    cm, nm = cmap_ir()

    fig, axes = plt.subplots(4, 3, figsize=(15, 18))

    fig.suptitle(
        f"Riesgo Agroclimático — Escenario {SSP_LBL[ssp]}\n"
        f"Comparación entre cultivos y horizontes temporales",
        fontsize=14, fontweight="bold", y=1.01)

    ckeys = list(CULTIVOS.keys())
    for i, cult in enumerate(ckeys):
        for j, hor in enumerate(HORIZONTES):
            ax = axes[i, j]
            gdf = prep_gdf(gdf_p, df_r, cult, ssp, hor)

            gdf_p.plot(ax=ax, color="#F0F0F0", edgecolor="0.7", linewidth=0.3)
            gdf.plot(column="indice_riesgo", ax=ax, cmap=cm, norm=nm,
                     edgecolor="0.5", linewidth=0.3,
                     missing_kwds={"color": "0.9"})

            ir_m = gdf["indice_riesgo"].mean()
            ax.text(0.03, 0.97, f"IR: {ir_m:.3f}",
                    transform=ax.transAxes, fontsize=7, va="top",
                    fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.3", fc="white",
                              alpha=0.85, lw=0.4))

            if i == 0:
                ax.set_title(H_LBL[hor], fontsize=10, fontweight="bold", pad=8)
            if j == 0:
                info = CULTIVOS[cult]
                ax.text(-0.05, 0.5,
                        f"{info['nombre']} ({info['tc']})",
                        transform=ax.transAxes, fontsize=9,
                        fontweight="bold", rotation=90,
                        va="center", ha="right")

            ax.set_xticks([])
            ax.set_yticks([])
            for sp in ax.spines.values():
                sp.set_visible(True)
                sp.set_linewidth(0.5)
                sp.set_color("0.5")

    patches = [mpatches.Patch(facecolor=c, edgecolor="0.4", linewidth=0.5,
               label=f"{l} ({IR_BINS[i]:.2f}–{IR_BINS[i+1]:.2f})")
               for i, (l, c) in enumerate(zip(IR_LABELS, IR_COLORS))]
    fig.legend(handles=patches, title="Índice de Riesgo (IR)",
               loc="lower center", ncol=5, fontsize=8, title_fontsize=9,
               frameon=True, bbox_to_anchor=(0.5, -0.01))

    pie_fuentes(fig)
    plt.subplots_adjust(wspace=0.05, hspace=0.1)

    nombre = f"PANEL_IR_{ssp}_4cultivos"
    for fmt in ["pdf", "png"]:
        fig.savefig(outdir / f"{nombre}.{fmt}",
                    dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return nombre


# =============================================================================
# PANEL RESUMEN 2×2 (con etiquetas top 5)
# =============================================================================

def panel_resumen(gdf_p, df_r, outdir):
    cm, nm = cmap_ir()
    ssp, hor = "ssp585", "2061-2080"

    fig, axes = plt.subplots(2, 2, figsize=(15, 12))

    fig.suptitle(
        "Riesgo Agroclimático — Escenario más extremo\n"
        f"{SSP_LBL[ssp]}  ·  Horizonte {hor}",
        fontsize=14, fontweight="bold", y=1.02)

    for idx, cult in enumerate(CULTIVOS):
        ax = axes[idx // 2, idx % 2]
        gdf = prep_gdf(gdf_p, df_r, cult, ssp, hor)
        info = CULTIVOS[cult]

        gdf_p.plot(ax=ax, color="#F0F0F0", edgecolor="0.7", linewidth=0.3)
        gdf.plot(column="indice_riesgo", ax=ax, cmap=cm, norm=nm,
                 edgecolor="0.5", linewidth=0.4,
                 missing_kwds={"color": "0.9"})

        # Solo top 5 con nombre corto
        gdf_top = gdf.dropna(subset=["indice_riesgo"]).nlargest(
            5, "indice_riesgo")
        for _, row in gdf_top.iterrows():
            c = row.geometry.centroid
            nm_p = row.get("DPA_DESPAR", "")
            if len(nm_p) > 12:
                nm_p = nm_p[:11] + "."
            ax.annotate(f"{nm_p}\n{row['indice_riesgo']:.2f}",
                        xy=(c.x, c.y), fontsize=5.5, ha="center",
                        va="center", fontweight="bold",
                        bbox=dict(boxstyle="round,pad=0.15",
                                  fc="#FFFFCC", alpha=0.9, lw=0.3))

        ir_m = gdf["indice_riesgo"].mean()
        ir_mx = gdf["indice_riesgo"].max()
        ax.set_title(
            f"{info['nombre']} ({info['sci']})\n"
            f"IR medio: {ir_m:.3f}  ·  IR máx: {ir_mx:.3f}  ·  "
            f"T crit: {info['tc']}",
            fontsize=9, fontweight="bold", pad=8)

        ax.set_xticks([])
        ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_visible(True)
            sp.set_linewidth(0.5)
            sp.set_color("0.5")

    patches = [mpatches.Patch(facecolor=c, edgecolor="0.4", linewidth=0.5,
               label=f"{l} ({IR_BINS[i]:.2f}–{IR_BINS[i+1]:.2f})")
               for i, (l, c) in enumerate(zip(IR_LABELS, IR_COLORS))]
    fig.legend(handles=patches, title="Índice de Riesgo (IR)",
               loc="lower center", ncol=5, fontsize=8, title_fontsize=9,
               frameon=True, bbox_to_anchor=(0.5, -0.02))

    pie_fuentes(fig)
    plt.subplots_adjust(wspace=0.1, hspace=0.2)

    nombre = "PANEL_RESUMEN_4cultivos_SSP585_2061-2080"
    for fmt in ["pdf", "png"]:
        fig.savefig(outdir / f"{nombre}.{fmt}",
                    dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return nombre


# =============================================================================
# MAPAS DE CAMBIO TEMPORAL (sin etiquetas, solo color)
# =============================================================================

def mapas_cambio(gdf_p, df_r, outdir):
    nombres = []

    for cult in CULTIVOS:
        for ssp in SSPS:
            gdf_i = prep_gdf(gdf_p, df_r, cult, ssp, "2021-2040")
            gdf_f = prep_gdf(gdf_p, df_r, cult, ssp, "2061-2080")

            ir_i = gdf_i.set_index("_k")["indice_riesgo"]
            ir_f = gdf_f.set_index("_k")["indice_riesgo"]
            delta = ir_f - ir_i

            gdf_d = gdf_i.copy().set_index("_k")
            gdf_d["delta_ir"] = delta
            gdf_d = gdf_d.reset_index()

            info = CULTIVOS[cult]
            fig, ax = plt.subplots(1, 1, figsize=(10, 7.5))

            gdf_p.plot(ax=ax, color="#F0F0F0", edgecolor="0.65", linewidth=0.4)

            vmax = max(0.05, gdf_d["delta_ir"].abs().max() * 1.1)
            gdf_d.plot(column="delta_ir", ax=ax, cmap="RdYlBu_r",
                       vmin=-vmax, vmax=vmax,
                       edgecolor="0.4", linewidth=0.5,
                       legend=True,
                       legend_kwds={"label": "Δ IR (2061–2080 vs 2021–2040)",
                                    "shrink": 0.5, "pad": 0.01, "aspect": 25},
                       missing_kwds={"color": "0.9"})

            agregar_grilla(ax, gdf_p)
            marco_mapa(ax)
            agregar_norte_flecha(ax)
            agregar_escala(ax)

            fig.suptitle(
                f"Cambio en Riesgo — {info['nombre']}  ·  "
                f"{SSP_LBL[ssp]}",
                fontsize=13, fontweight="bold", y=0.97)
            fig.text(0.5, 0.93,
                     "Δ IR = IR(2061–2080) − IR(2021–2040)  ·  "
                     "Rojo = aumento de riesgo",
                     fontsize=9, ha="center", color="0.3", style="italic")

            pie_fuentes(fig)

            nombre = f"CAMBIO_{cult}_{ssp}"
            for fmt in ["pdf", "png"]:
                fig.savefig(outdir / f"{nombre}.{fmt}",
                            dpi=DPI, bbox_inches="tight", facecolor="white")
            plt.close(fig)
            nombres.append(nombre)

    return nombres


# =============================================================================
# MAPA DE EXPOSICIÓN
# =============================================================================

def mapa_exposicion(gdf_p, df_expo, outdir):
    fig, ax = plt.subplots(1, 1, figsize=(10, 7.5))

    df_e = df_expo.copy()
    df_e["_k"] = df_e["parroquia"].str.upper().str.strip()
    gdf = gdf_p.copy()
    gdf["_k"] = gdf["DPA_DESPAR"].str.upper().str.strip()
    gdf = gdf.merge(df_e, on="_k", how="left")

    cols = [c for c in ["papa", "maiz", "frejol"] if c in gdf.columns]
    gdf["total_ha"] = gdf[cols].sum(axis=1)

    gdf_p.plot(ax=ax, color="#F0F0F0", edgecolor="0.65", linewidth=0.4)
    gdf.plot(column="total_ha", ax=ax, cmap="YlOrRd",
             edgecolor="0.4", linewidth=0.5, legend=True,
             legend_kwds={"label": "Superficie cultivada total (ha)",
                          "shrink": 0.5, "pad": 0.01, "aspect": 25},
             missing_kwds={"color": "0.9"})

    agregar_grilla(ax, gdf_p)
    marco_mapa(ax)
    agregar_norte_flecha(ax)
    agregar_escala(ax)

    fig.suptitle("Exposición Agrícola — Superficie Cultivada por Parroquia",
                 fontsize=13, fontweight="bold", y=0.97)
    fig.text(0.5, 0.93,
             "Papa + Maíz + Fréjol (MapSPAM v2r0)  ·  "
             "Quinua: solo provincial (18.36 ha, ESPAC 2024)",
             fontsize=9, ha="center", color="0.3", style="italic")

    pie_fuentes(fig, "Script 04C (exactextract)")

    nombre = "EXPOSICION_superficie_parroquial"
    for fmt in ["pdf", "png"]:
        fig.savefig(outdir / f"{nombre}.{fmt}",
                    dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return nombre


# =============================================================================
# MAPA DE PRIORIZACIÓN (con etiquetas top 10)
# =============================================================================

def mapa_priorizacion(gdf_p, df_r, outdir):
    df_peor = df_r[
        (df_r["ssp"] == "ssp585") & (df_r["horizonte"] == "2061-2080")
    ].copy()

    df_pri = df_peor.groupby("parroquia").agg(
        ir_medio=("indice_riesgo", "mean"),
        ir_max=("indice_riesgo", "max"),
        n_cultivos_alto=("indice_riesgo", lambda x: (x > 0.55).sum())
    ).reset_index()

    df_pri = df_pri.sort_values("ir_medio", ascending=False).reset_index(drop=True)
    df_pri["ranking"] = range(1, len(df_pri) + 1)

    df_pri["_k"] = df_pri["parroquia"].str.upper().str.strip()
    gdf = gdf_p.copy()
    gdf["_k"] = gdf["DPA_DESPAR"].str.upper().str.strip()
    gdf = gdf.merge(df_pri, on="_k", how="left")

    bins_p = [0, 0.35, 0.45, 0.55, 1.0]
    lbl_p = ["Prioridad Baja", "Prioridad Moderada",
             "Prioridad Alta", "Prioridad Muy Alta"]
    col_p = ["#2166AC", "#92C5DE", "#F4A582", "#B2182B"]

    gdf["prio_cat"] = pd.cut(gdf["ir_medio"], bins=bins_p,
                              labels=lbl_p, include_lowest=True)

    fig, ax = plt.subplots(1, 1, figsize=(10, 7.5))

    gdf_p.plot(ax=ax, color="#F0F0F0", edgecolor="0.65", linewidth=0.4)

    for cat, color in zip(lbl_p, col_p):
        sub = gdf[gdf["prio_cat"] == cat]
        if not sub.empty:
            sub.plot(ax=ax, color=color, edgecolor="0.4", linewidth=0.5)

    # Top 10 con etiquetas fuera (callout) si es posible, o dentro con fuente pequeña
    gdf_top = gdf.dropna(subset=["ranking"]).nsmallest(10, "ranking")
    for _, row in gdf_top.iterrows():
        c = row.geometry.centroid
        nm = row.get("DPA_DESPAR", "")
        if len(nm) > 15:
            nm = nm[:14] + "."
        ax.annotate(
            f"#{int(row['ranking'])} {nm}\nIR={row['ir_medio']:.3f}",
            xy=(c.x, c.y), fontsize=5, ha="center", va="center",
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.15", fc="#FFFFCC",
                      alpha=0.9, lw=0.3, edgecolor="0.5"))

    patches = [mpatches.Patch(facecolor=c, edgecolor="0.4", linewidth=0.5,
               label=l) for l, c in zip(lbl_p, col_p)]
    ax.legend(handles=patches, title="Nivel de Priorización",
              loc="lower left", fontsize=7, title_fontsize=8,
              frameon=True, framealpha=0.95, edgecolor="0.5")

    agregar_grilla(ax, gdf_p)
    marco_mapa(ax)
    agregar_norte_flecha(ax)
    agregar_escala(ax)

    fig.suptitle("Priorización de Parroquias para Adaptación al Cambio Climático",
                 fontsize=13, fontweight="bold", y=0.97)
    fig.text(0.5, 0.93,
             "IR medio de 4 cultivos  ·  SSP5-8.5, 2061–2080  ·  "
             "Ranking para GADs parroquiales",
             fontsize=9, ha="center", color="0.3", style="italic")

    pie_fuentes(fig, "Síntesis: Scripts 04C + 06C + 07")

    nombre = "SINTESIS_priorizacion_parroquias"
    for fmt in ["pdf", "png"]:
        fig.savefig(outdir / f"{nombre}.{fmt}",
                    dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return nombre, df_pri


# =============================================================================
# REPORTE
# =============================================================================

def generar_reporte(mapas, df_pri, dur):
    rep = REPORTS_DIR / f"REPORTE_SCRIPT_08_v3_{TS}.txt"
    with open(rep, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("REPORTE — SCRIPT 08 v3.0 — MAPAS DE RIESGO\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Versión: {VERSION}\n")
        f.write(f"Duración: {dur:.0f}s ({dur/60:.1f} min)\n")
        f.write(f"Total mapas: {len(mapas)}\n\n")
        f.write("RANKING (SSP585, 2061-2080)\n" + "-" * 55 + "\n")
        for _, r in df_pri.head(15).iterrows():
            f.write(f"  #{r['ranking']:<3} {r['parroquia']:<25} "
                    f"IR={r['ir_medio']:.4f}\n")
        f.write("\nESTADO: APROBADO\n" + "=" * 70 + "\n")
    print(f"  ✓ Reporte: {rep.name}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    t0 = time.time()

    print("╔" + "═" * 68 + "╗")
    print("║  SCRIPT 08 v3.0: MAPAS DE RIESGO AGROCLIMÁTICO" +
          " " * 20 + "║")
    print("║  Con grilla, flecha de norte, escala, marco" +
          " " * 23 + "║")
    print("╚" + "═" * 68 + "╝")

    # [1/7] CARGA
    print(f"\n[1/7] CARGA DE DATOS")
    print("─" * 60)

    gdf_p = gpd.read_file(PARROQUIAS_PATH)
    if gdf_p.crs is None or gdf_p.crs.to_epsg() != 32717:
        gdf_p = gdf_p.to_crs(epsg=32717)
    print(f"  ✓ Parroquias: {len(gdf_p)}")

    csv_r = buscar_csv(BN_DIR, "riesgo_parroquial_*.csv")
    df_r = pd.read_csv(csv_r)
    print(f"  ✓ Riesgo: {csv_r.name} ({len(df_r)} filas)")

    csv_e = buscar_csv(EXPO_DIR, "exposicion_resumen_*.csv")
    df_e = pd.read_csv(csv_e)
    print(f"  ✓ Exposición: {csv_e.name}")

    assert len(df_r) == 1512
    print(f"  ✓ OK: 1,512 filas")

    mapas = []

    # [2/7] INDIVIDUALES (36)
    print(f"\n[2/7] MAPAS INDIVIDUALES (36)")
    print("─" * 60)
    n = 0
    for cult in CULTIVOS:
        for ssp in SSPS:
            for h in HORIZONTES:
                mapas.append(mapa_individual(gdf_p, df_r, cult, ssp, h,
                                              OUTPUT_IND))
                n += 1
                if n % 9 == 0:
                    print(f"  {n}/36 ({cult})")
    print(f"  ✓ {n}/36")

    # [3/7] PANELES CULTIVO (4)
    print(f"\n[3/7] PANELES POR CULTIVO (4)")
    print("─" * 60)
    for cult in CULTIVOS:
        mapas.append(panel_cultivo(gdf_p, df_r, cult, OUTPUT_PAN))
        print(f"  ✓ {CULTIVOS[cult]['nombre']}")

    # [4/7] PANELES SSP (3)
    print(f"\n[4/7] PANELES POR SSP (3)")
    print("─" * 60)
    for ssp in SSPS:
        mapas.append(panel_ssp(gdf_p, df_r, ssp, OUTPUT_PAN))
        print(f"  ✓ {SSP_LBL[ssp]}")

    # [5/7] RESUMEN
    print(f"\n[5/7] PANEL RESUMEN (1)")
    print("─" * 60)
    mapas.append(panel_resumen(gdf_p, df_r, OUTPUT_PAN))
    print(f"  ✓ Generado")

    # [6/7] CAMBIO
    print(f"\n[6/7] CAMBIO TEMPORAL (12)")
    print("─" * 60)
    ms = mapas_cambio(gdf_p, df_r, OUTPUT_CAM)
    mapas.extend(ms)
    print(f"  ✓ {len(ms)} mapas")

    # [7/7] EXPOSICIÓN + PRIORIZACIÓN
    print(f"\n[7/7] EXPOSICIÓN + PRIORIZACIÓN")
    print("─" * 60)
    mapas.append(mapa_exposicion(gdf_p, df_e, OUTPUT_SIN))
    print(f"  ✓ Exposición")
    m, df_pri = mapa_priorizacion(gdf_p, df_r, OUTPUT_SIN)
    mapas.append(m)
    print(f"  ✓ Priorización")

    for _, r in df_pri.head(5).iterrows():
        print(f"    #{r['ranking']:<3} {r['parroquia']:<25} IR={r['ir_medio']:.3f}")

    dur = time.time() - t0
    generar_reporte(mapas, df_pri, dur)

    csv_p = OUTPUT_SIN / f"ranking_priorizacion_{TS}.csv"
    df_pri.to_csv(csv_p, index=False, encoding="utf-8-sig")

    print(f"\n╔{'═'*68}╗")
    print(f"║  ✓ SCRIPT 08 v3.0 COMPLETADO{' '*39}║")
    print(f"╚{'═'*68}╝")
    print(f"  ⏱  {dur:.0f}s · {len(mapas)} mapas · {OUTPUT_DIR}")
    print(f"  🔜 DOC_METODOLOGIA_SCRIPT_08")

    return mapas


if __name__ == "__main__":
    mapas = main()