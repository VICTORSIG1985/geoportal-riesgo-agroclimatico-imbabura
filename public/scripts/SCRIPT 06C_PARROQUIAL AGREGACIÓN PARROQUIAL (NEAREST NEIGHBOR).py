"""
Script publicado como parte del Geoportal Riesgo Agroclimático — Imbabura, Ecuador
Pinto Páez, V. H. (2026). https://doi.org/10.5281/zenodo.19288559
Licencia: CC BY 4.0

NOTA: este archivo fue sanitizado para publicación pública.
- Credenciales (API keys, tokens, service accounts) removidas → <REDACTED_*>
- Rutas absolutas locales sustituidas por <RUTA_LOCAL>
Antes de ejecutar, configure sus propias rutas de entrada/salida y credenciales.

Archivo original: SCRIPT 06C_PARROQUIAL AGREGACIÓN PARROQUIAL (NEAREST NEIGHBOR).py
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
SCRIPT 06C_PARROQUIAL: AGREGACIÓN PARROQUIAL (NEAREST NEIGHBOR)
===============================================================================
Autor:   Víctor Hugo Pinto Páez
Versión: 1.0.0 | 2026-02-26

PROPÓSITO:
    Post-procesamiento de los GeoTIFFs de ensemble generados por Script 06B.
    Asigna a cada parroquia el valor del píxel más cercano a su centroide
    (nearest neighbor), resolviendo el problema de parroquias sin píxeles
    internos debido a la resolución de ~10 km.

JUSTIFICACIÓN:
    Con grilla de 0.1° (~11 km), 18 de 42 parroquias no contienen el centro
    de ningún píxel. La distancia máxima centroide-píxel es 6.4 km (< 1 píxel),
    lo que hace nearest neighbor el método estándar para esta resolución.
    Referencia: Fernandez-Palomino et al. (2024), Sci. Data, 11, 34.

ENTRADA:
    - GeoTIFFs ensemble: proyecciones/ensemble/{cultivo}/{ssp}/{horiz}/
    - Parroquias: Imbabura_Parroquia.gpkg

SALIDA:
    - CSV consolidado: proyecciones/parroquial/aptitud_parroquial_42parr.csv
    - CSV pivote: proyecciones/parroquial/pivote_aptitud_42parr.csv
    - Reporte de auditoría

===============================================================================
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from pathlib import Path
from datetime import datetime
from shapely.geometry import Point, MultiPoint
from shapely.ops import nearest_points


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

BASE_PREV = Path(r"<RUTA_LOCAL>")
BASE_DIR = Path(r"<RUTA_LOCAL>")

ENSEMBLE_DIR = BASE_PREV / "04_RESULTADOS" / "fase4_modelamiento" / "random_forest" / "proyecciones" / "ensemble"
OUTPUT_DIR = BASE_PREV / "04_RESULTADOS" / "fase4_modelamiento" / "random_forest" / "proyecciones" / "parroquial"
REPORTS_DIR = BASE_PREV / "05_DOCUMENTACION" / "reportes_auditoria"
PARROQUIAS_PATH = BASE_DIR / "Imbabura_Parroquia.gpkg"

CULTIVOS = ['papa', 'maiz', 'frejol', 'quinua']
SSPS = ['ssp126', 'ssp370', 'ssp585']
HORIZONTES = ['2021-2040', '2041-2060', '2061-2080']

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


# =============================================================================
# FUNCIONES
# =============================================================================

def leer_tiff_como_puntos(tiff_path: Path) -> gpd.GeoDataFrame:
    """Lee un GeoTIFF y retorna GeoDataFrame con puntos válidos."""
    with rasterio.open(tiff_path) as src:
        data = src.read(1).astype(np.float64)
        transform = src.transform
        nodata = src.nodata if src.nodata else -9999

        rows, cols = np.where((data != nodata) & ~np.isnan(data))
        lons = [transform[2] + (c + 0.5) * transform[0] for c in cols]
        lats = [transform[5] + (r + 0.5) * transform[4] for r in rows]
        vals = [float(data[r, c]) for r, c in zip(rows, cols)]

    return gpd.GeoDataFrame(
        {'aptitud': vals},
        geometry=[Point(x, y) for x, y in zip(lons, lats)],
        crs="EPSG:4326"
    )


def asignar_nearest(pts: gpd.GeoDataFrame,
                     parroquias: gpd.GeoDataFrame) -> pd.DataFrame:
    """
    Asigna a cada parroquia el valor del píxel más cercano a su centroide.
    Para parroquias con múltiples píxeles internos, calcula media.
    Para parroquias sin píxeles internos, usa el más cercano.
    """
    todos_puntos = MultiPoint(list(pts.geometry))
    resultados = []

    for _, parr in parroquias.iterrows():
        nombre = parr['DPA_DESPAR']
        canton = parr['DPA_DESCAN']
        centroide = parr.geometry.centroid

        # Primero intentar within (más preciso si hay píxeles dentro)
        dentro = pts[pts.within(parr.geometry)]

        if len(dentro) > 0:
            resultados.append({
                'parroquia': nombre,
                'canton': canton,
                'aptitud_media': float(dentro['aptitud'].mean()),
                'aptitud_mediana': float(dentro['aptitud'].median()),
                'aptitud_sd': float(dentro['aptitud'].std()) if len(dentro) > 1 else 0.0,
                'aptitud_min': float(dentro['aptitud'].min()),
                'aptitud_max': float(dentro['aptitud'].max()),
                'n_pixeles': len(dentro),
                'metodo': 'within',
                'dist_centroide_km': float(centroide.distance(dentro.geometry.iloc[0]) * 111),
            })
        else:
            # Nearest neighbor al centroide
            nearest_pt = nearest_points(centroide, todos_puntos)[1]
            idx = pts.distance(nearest_pt).idxmin()
            val = float(pts.loc[idx, 'aptitud'])
            dist = float(centroide.distance(nearest_pt) * 111)

            resultados.append({
                'parroquia': nombre,
                'canton': canton,
                'aptitud_media': val,
                'aptitud_mediana': val,
                'aptitud_sd': 0.0,
                'aptitud_min': val,
                'aptitud_max': val,
                'n_pixeles': 1,
                'metodo': 'nearest',
                'dist_centroide_km': dist,
            })

    return pd.DataFrame(resultados)


# =============================================================================
# MAIN
# =============================================================================

def main():
    t0 = datetime.now()

    print("╔" + "═"*68 + "╗")
    print("║  SCRIPT 06B_PARROQUIAL: AGREGACIÓN NEAREST NEIGHBOR" + " "*16 + "║")
    print("║  42 parroquias × 4 cultivos × 3 SSP × 3 horizontes" + " "*16 + "║")
    print("║  " + t0.strftime('%Y-%m-%d %H:%M:%S') + " "*45 + "║")
    print("╚" + "═"*68 + "╝")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # ── Cargar parroquias ────────────────────────────────────────────
    print("\n[1/3] CARGA DE DATOS")
    print("─"*60)

    gdf = gpd.read_file(PARROQUIAS_PATH)
    if gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")
    print(f"  ✓ Parroquias: {len(gdf)} ({PARROQUIAS_PATH.name})")

    # Inventariar GeoTIFFs
    tiffs = list(ENSEMBLE_DIR.rglob("*_mean.tif"))
    print(f"  ✓ GeoTIFFs ensemble: {len(tiffs)}")
    if not tiffs:
        print("  ❌ Sin GeoTIFFs. Ejecutar Script 06B primero.")
        return

    # ── Procesar cada combinación ────────────────────────────────────
    print(f"\n[2/3] AGREGACIÓN PARROQUIAL")
    print("─"*60)

    total = len(CULTIVOS) * len(SSPS) * len(HORIZONTES)
    todos_resultados = []
    procesados = 0
    errores = []

    for cultivo in CULTIVOS:
        for ssp in SSPS:
            for horizonte in HORIZONTES:
                tiff_path = ENSEMBLE_DIR / cultivo / ssp / horizonte / f"aptitud_{cultivo}_mean.tif"

                if not tiff_path.exists():
                    errores.append(f"No existe: {cultivo}/{ssp}/{horizonte}")
                    continue

                try:
                    pts = leer_tiff_como_puntos(tiff_path)
                    df_parr = asignar_nearest(pts, gdf)

                    df_parr['cultivo'] = cultivo
                    df_parr['ssp'] = ssp
                    df_parr['horizonte'] = horizonte

                    todos_resultados.append(df_parr)
                    procesados += 1

                    n_within = (df_parr['metodo'] == 'within').sum()
                    n_nearest = (df_parr['metodo'] == 'nearest').sum()
                    media = df_parr['aptitud_media'].mean()

                    print(f"  ✓ {cultivo:8s} {ssp:6s} {horizonte:10s} "
                          f"→ 42 parr (within:{n_within} nearest:{n_nearest}) "
                          f"media={media:.3f}")

                except Exception as e:
                    errores.append(f"{cultivo}/{ssp}/{horizonte}: {str(e)[:60]}")
                    print(f"  ✗ {cultivo:8s} {ssp:6s} {horizonte:10s} → ERROR")

    # ── Consolidar y guardar ─────────────────────────────────────────
    print(f"\n[3/3] RESULTADOS")
    print("─"*60)

    if not todos_resultados:
        print("  ❌ Sin resultados.")
        return

    df_full = pd.concat(todos_resultados, ignore_index=True)

    # CSV completo
    csv_full = OUTPUT_DIR / f"aptitud_parroquial_42parr_{TIMESTAMP}.csv"
    df_full.to_csv(csv_full, index=False, float_format='%.4f')
    print(f"  ✓ {csv_full.name}")
    print(f"    {len(df_full)} filas ({df_full['parroquia'].nunique()} parroquias)")

    # Pivote: parroquia × cultivo vs ssp/horizonte
    pivote = df_full.pivot_table(
        values='aptitud_media',
        index=['parroquia', 'canton'],
        columns=['cultivo', 'ssp', 'horizonte'],
        aggfunc='mean'
    )
    csv_piv = OUTPUT_DIR / f"pivote_aptitud_42parr_{TIMESTAMP}.csv"
    pivote.to_csv(csv_piv, float_format='%.4f')
    print(f"  ✓ {csv_piv.name}")

    # Resumen por cultivo × escenario
    print(f"\n  {'Cultivo':10s} {'SSP':8s} {'Horizonte':12s} {'Media':>8s} {'Min':>8s} {'Max':>8s}")
    print(f"  {'─'*10} {'─'*8} {'─'*12} {'─'*8} {'─'*8} {'─'*8}")
    resumen = df_full.groupby(['cultivo', 'ssp', 'horizonte'])['aptitud_media'].agg(
        ['mean', 'min', 'max']
    ).reset_index()
    for _, r in resumen.sort_values(['cultivo', 'ssp', 'horizonte']).iterrows():
        print(f"  {r['cultivo']:10s} {r['ssp']:8s} {r['horizonte']:12s} "
              f"{r['mean']:8.4f} {r['min']:8.4f} {r['max']:8.4f}")

    # Métodos usados
    metodos = df_full.groupby('metodo').size()
    total_asig = metodos.sum()
    print(f"\n  Método de asignación:")
    print(f"    within:  {metodos.get('within', 0):5d} ({metodos.get('within', 0)/total_asig*100:.1f}%)")
    print(f"    nearest: {metodos.get('nearest', 0):5d} ({metodos.get('nearest', 0)/total_asig*100:.1f}%)")

    dist_nearest = df_full[df_full['metodo'] == 'nearest']['dist_centroide_km']
    if len(dist_nearest) > 0:
        print(f"    Dist. nearest max:  {dist_nearest.max():.1f} km")
        print(f"    Dist. nearest media: {dist_nearest.mean():.1f} km")

    # ── Reporte ──────────────────────────────────────────────────────
    rep = REPORTS_DIR / f"REPORTE_06B_PARROQUIAL_{TIMESTAMP}.txt"
    with open(rep, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("REPORTE - AGREGACIÓN PARROQUIAL (NEAREST NEIGHBOR)\n")
        f.write("="*70 + "\n\n")
        f.write(f"Fecha: {datetime.now()}\n")
        f.write(f"Autor: Víctor Hugo Pinto Páez\n\n")
        f.write("MÉTODO:\n")
        f.write("  Para parroquias con píxeles internos: media espacial (within)\n")
        f.write("  Para parroquias sin píxeles internos: píxel más cercano al\n")
        f.write("  centroide (nearest neighbor)\n\n")
        f.write("JUSTIFICACIÓN:\n")
        f.write("  Resolución de grilla: 0.1° (~11 km)\n")
        f.write("  18/42 parroquias no contienen centro de píxel\n")
        f.write(f"  Distancia máxima centroide-píxel: {dist_nearest.max():.1f} km (< 1 píxel)\n")
        f.write("  Nearest neighbor es estándar para esta resolución.\n")
        f.write("  Ref: Fernandez-Palomino et al. (2024), Sci. Data, 11, 34.\n\n")
        f.write(f"RESULTADOS:\n")
        f.write(f"  Combinaciones procesadas: {procesados}/{total}\n")
        f.write(f"  Parroquias totales: {df_full['parroquia'].nunique()}\n")
        f.write(f"  Método within: {metodos.get('within', 0)} asignaciones\n")
        f.write(f"  Método nearest: {metodos.get('nearest', 0)} asignaciones\n\n")
        if errores:
            f.write("ERRORES:\n")
            for e in errores:
                f.write(f"  - {e}\n")
        f.write("="*70 + "\n")

    print(f"\n  ✓ Reporte: {rep.name}")

    # Final
    t_total = datetime.now() - t0
    print()
    print("╔" + "═"*68 + "╗")
    print("║  ✓ AGREGACIÓN PARROQUIAL COMPLETADA" + " "*32 + "║")
    print("╚" + "═"*68 + "╝")
    print(f"  ⏱  Tiempo: {t_total}")
    print(f"  📊 {procesados} combinaciones × 42 parroquias = {len(df_full)} registros")
    print(f"  📁 {OUTPUT_DIR}")
    print("═"*70)


if __name__ == "__main__":
    main()