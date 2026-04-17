"""
Script publicado como parte del Geoportal Riesgo Agroclimático — Imbabura, Ecuador
Pinto Páez, V. H. (2026). https://doi.org/10.5281/zenodo.19288559
Licencia: CC BY 4.0

NOTA: este archivo fue sanitizado para publicación pública.
- Credenciales (API keys, tokens, service accounts) removidas → <REDACTED_*>
- Rutas absolutas locales sustituidas por <RUTA_LOCAL>
Antes de ejecutar, configure sus propias rutas de entrada/salida y credenciales.

Archivo original: SCRIPT 05C AGREGAR VARIABLES TÉRMICAS A DATASETS DE ENTRENAMIENTO RF.py
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
SCRIPT 05C: AGREGAR VARIABLES TÉRMICAS A DATASETS DE ENTRENAMIENTO RF
===============================================================================
Versión: 1.0.0
Fecha: 2026-02-26
Autor: Víctor Hugo Pinto Páez

===============================================================================
PROPÓSITO
===============================================================================

Calcular 3 variables térmicas faltantes a partir de los datos diarios
BASD-CMIP6-PE (tasmax, tasmin) y agregarlas a los datasets de entrenamiento
del Script 05B. Estas variables aportan información independiente que
ET₀ no captura completamente:

  tmax_media_anual (°C):
    Media anual de la temperatura máxima diaria.
    Controla el régimen térmico máximo del cultivo.
    Diferente de ET₀ porque ET₀ integra radiación solar, no solo temperatura.

  tmin_media_anual (°C):
    Media anual de la temperatura mínima diaria.
    Principal limitante de distribución altitudinal en Andes.
    Referencia: Hijmans et al. (2003) - relación tmin-altitud.

  rango_termico_diurno (°C):
    Media anual de (tasmax - tasmin) diario.
    Afecta fotosíntesis diurna y respiración nocturna.
    Amplitudes >15°C favorecen tuberización en papa (CIP, 2020).
    Equivalente a bio02 de WorldClim (Mean Diurnal Range).

===============================================================================
PROCESO
===============================================================================

1. Leer tasmax y tasmin diarios de cada GCM (período histórico 1981-2014)
2. Calcular promedios anuales por GCM
3. Calcular ensemble (media de 10 GCMs)
4. Extraer valores en cada punto de presencia/pseudo-ausencia
5. Agregar columnas a los 4 datasets CSV + dataset consolidado
6. Guardar datasets actualizados

===============================================================================
REFERENCIAS
===============================================================================

CIP (2020). Potato Facts and Figures. International Potato Center, Lima.
Hijmans, R.J., et al. (2003). Very high resolution interpolated climate
    surfaces for global land areas. Int. J. Climatol., 25, 1965-1978.

===============================================================================
"""

import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List

warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import xarray as xr


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

# Rutas
RECORTADOS_DIR = Path(r"<RUTA_LOCAL>")
DATASETS_DIR = Path(r"<RUTA_LOCAL>")
AGREGADOS_DIR = Path(r"<RUTA_LOCAL>")

# GCMs disponibles
GCMS = [
    'CanESM5', 'CNRM-CM6-1', 'CNRM-ESM2-1', 'EC-Earth3',
    'GFDL-ESM4', 'IPSL-CM6A-LR', 'MIROC6', 'MPI-ESM1-2-HR',
    'MRI-ESM2-0', 'UKESM1-0-LL'
]

TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')


# =============================================================================
# FUNCIONES
# =============================================================================

def cargar_variable_diaria(gcm_dir: Path, variable: str) -> xr.DataArray:
    """
    Carga todos los archivos de una variable diaria para un GCM
    y los concatena en un solo DataArray.
    """
    patron = f"*_{variable}_daily_*.nc"
    archivos = sorted(gcm_dir.glob(patron))

    if not archivos:
        return None

    datasets = []
    for f in archivos:
        ds = xr.open_dataset(f)
        # Buscar la variable (puede ser el nombre directo o la primera data_var)
        if variable in ds.data_vars:
            datasets.append(ds[variable])
        else:
            # Tomar la primera variable
            var_name = list(ds.data_vars)[0]
            datasets.append(ds[var_name])
        ds.close()

    if len(datasets) == 1:
        return datasets[0]

    return xr.concat(datasets, dim='time')


def calcular_medias_anuales_gcm(gcm_dir: Path) -> Dict[str, np.ndarray]:
    """
    Calcula tmax_media_anual, tmin_media_anual y rango_termico_diurno
    para un GCM, promediando sobre todos los años disponibles.
    """
    # Cargar tasmax y tasmin
    tasmax = cargar_variable_diaria(gcm_dir, 'tasmax')
    tasmin = cargar_variable_diaria(gcm_dir, 'tasmin')

    if tasmax is None or tasmin is None:
        return None

    # Promedios temporales (media sobre todos los días = media climatológica)
    tmax_mean = float(tasmax.mean(dim='time').values.mean())  # Para diagnóstico
    tmin_mean = float(tasmin.mean(dim='time').values.mean())

    tmax_media = tasmax.mean(dim='time').values
    tmin_media = tasmin.mean(dim='time').values

    # Rango térmico diurno: media del (tasmax - tasmin) diario
    rango_diario = tasmax - tasmin
    rango_media = rango_diario.mean(dim='time').values

    # Limpiar memoria
    tasmax.close()
    tasmin.close()

    return {
        'tmax_media_anual': tmax_media,
        'tmin_media_anual': tmin_media,
        'rango_termico_diurno': rango_media
    }


def extraer_valores_en_puntos(data_2d: np.ndarray, lats_grid: np.ndarray,
                                lons_grid: np.ndarray, lats_pts: np.ndarray,
                                lons_pts: np.ndarray) -> np.ndarray:
    """
    Extrae valores de una grilla 2D en puntos específicos usando
    interpolación al vecino más cercano.
    """
    valores = np.full(len(lats_pts), np.nan)

    for i in range(len(lats_pts)):
        # Encontrar celda más cercana
        lat_idx = np.argmin(np.abs(lats_grid - lats_pts[i]))
        lon_idx = np.argmin(np.abs(lons_grid - lons_pts[i]))

        if lat_idx < data_2d.shape[0] and lon_idx < data_2d.shape[1]:
            val = data_2d[lat_idx, lon_idx]
            if not np.isnan(val) and val > -999:
                valores[i] = val

    return valores


# =============================================================================
# EJECUCIÓN PRINCIPAL
# =============================================================================

def main():
    print("\n" + "╔" + "═"*68 + "╗")
    print("║" + " SCRIPT 05C: AGREGAR VARIABLES TÉRMICAS A DATASETS RF".center(68) + "║")
    print("║" + f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(68) + "║")
    print("╚" + "═"*68 + "╝")

    t_inicio = datetime.now()

    # =====================================================================
    # PASO 1: Calcular medias por GCM
    # =====================================================================
    print(f"\n[1/4] Calculando variables térmicas por GCM...")
    print(f"      Directorio: {RECORTADOS_DIR}")

    resultados_gcm = {}
    lats_grid = None
    lons_grid = None
    gcms_procesados = 0

    for gcm in GCMS:
        gcm_dir = RECORTADOS_DIR / gcm
        if not gcm_dir.exists():
            print(f"  ⚠ {gcm}: directorio no encontrado, saltando")
            continue

        print(f"  Procesando {gcm}...", end=" ", flush=True)

        resultado = calcular_medias_anuales_gcm(gcm_dir)
        if resultado is None:
            print("✗ (sin datos tasmax/tasmin)")
            continue

        resultados_gcm[gcm] = resultado
        gcms_procesados += 1

        # Obtener coordenadas de la grilla (del primer archivo)
        if lats_grid is None:
            archivo_ref = sorted(gcm_dir.glob("*_tasmax_*.nc"))[0]
            ds_ref = xr.open_dataset(archivo_ref)
            lats_grid = ds_ref.lat.values if 'lat' in ds_ref.dims else ds_ref.latitude.values
            lons_grid = ds_ref.lon.values if 'lon' in ds_ref.dims else ds_ref.longitude.values
            ds_ref.close()

        # Diagnóstico rápido
        tmax_m = np.nanmean(resultado['tmax_media_anual'])
        tmin_m = np.nanmean(resultado['tmin_media_anual'])
        rango_m = np.nanmean(resultado['rango_termico_diurno'])
        print(f"✓ (Tmax={tmax_m:.1f}°C, Tmin={tmin_m:.1f}°C, Rango={rango_m:.1f}°C)")

    if gcms_procesados == 0:
        print("\n✗ No se pudieron procesar GCMs. Verificar datos.")
        sys.exit(1)

    print(f"\n  GCMs procesados: {gcms_procesados}/{len(GCMS)}")

    # =====================================================================
    # PASO 2: Calcular ensemble (media de GCMs)
    # =====================================================================
    print(f"\n[2/4] Calculando ensemble multi-modelo...")

    ensemble = {}
    for var_name in ['tmax_media_anual', 'tmin_media_anual', 'rango_termico_diurno']:
        arrays = [resultados_gcm[gcm][var_name] for gcm in resultados_gcm]
        ensemble[var_name] = np.nanmean(np.stack(arrays, axis=0), axis=0)

    # Diagnóstico del ensemble
    print(f"  Ensemble tmax_media_anual:    {np.nanmean(ensemble['tmax_media_anual']):.2f}°C "
          f"(rango: {np.nanmin(ensemble['tmax_media_anual']):.1f} a "
          f"{np.nanmax(ensemble['tmax_media_anual']):.1f}°C)")
    print(f"  Ensemble tmin_media_anual:    {np.nanmean(ensemble['tmin_media_anual']):.2f}°C "
          f"(rango: {np.nanmin(ensemble['tmin_media_anual']):.1f} a "
          f"{np.nanmax(ensemble['tmin_media_anual']):.1f}°C)")
    print(f"  Ensemble rango_termico_diurno: {np.nanmean(ensemble['rango_termico_diurno']):.2f}°C "
          f"(rango: {np.nanmin(ensemble['rango_termico_diurno']):.1f} a "
          f"{np.nanmax(ensemble['rango_termico_diurno']):.1f}°C)")

    # =====================================================================
    # PASO 3: Extraer valores y actualizar datasets
    # =====================================================================
    print(f"\n[3/4] Actualizando datasets de entrenamiento...")
    print(f"      Directorio: {DATASETS_DIR}")

    datasets_actualizados = 0

    for csv_file in sorted(DATASETS_DIR.glob("dataset_rf_*.csv")):
        print(f"\n  Procesando: {csv_file.name}")
        df = pd.read_csv(csv_file)

        # Verificar si ya tiene las variables
        nuevas_vars = ['tmax_media_anual', 'tmin_media_anual', 'rango_termico_diurno']
        ya_existentes = [v for v in nuevas_vars if v in df.columns]
        if len(ya_existentes) == 3:
            print(f"    ✓ Las 3 variables ya existen. Saltando.")
            continue

        # Extraer valores para cada punto
        lats_pts = df['lat'].values
        lons_pts = df['lon'].values

        for var_name in nuevas_vars:
            if var_name in df.columns:
                print(f"    {var_name}: ya existe, saltando")
                continue

            valores = extraer_valores_en_puntos(
                ensemble[var_name], lats_grid, lons_grid,
                lats_pts, lons_pts
            )

            n_nan = np.isnan(valores).sum()
            n_valid = len(valores) - n_nan
            media = np.nanmean(valores)

            df[var_name] = valores
            print(f"    {var_name}: {n_valid} válidos, {n_nan} NaN, "
                  f"media={media:.2f}")

        # Eliminar filas con NaN en las nuevas variables
        n_antes = len(df)
        df = df.dropna(subset=nuevas_vars)
        n_despues = len(df)
        n_eliminados = n_antes - n_despues

        if n_eliminados > 0:
            print(f"    ⚠ Eliminados {n_eliminados} registros con NaN "
                  f"({n_eliminados/n_antes*100:.1f}%)")

        # Guardar (sobreescribir el archivo original)
        df.to_csv(csv_file, index=False)
        print(f"    ✓ Guardado: {csv_file.name} ({len(df)} registros, "
              f"{len(df.columns)} columnas)")

        datasets_actualizados += 1

    # =====================================================================
    # PASO 4: Verificación final
    # =====================================================================
    print(f"\n[4/4] Verificación final...")

    for csv_file in sorted(DATASETS_DIR.glob("dataset_rf_*.csv")):
        if 'training' in csv_file.name:
            continue
        df = pd.read_csv(csv_file)
        n_vars = len([c for c in df.columns if c not in
                      ['cultivo', 'lat', 'lon', 'presencia', 'elevation']])
        cultivo = csv_file.name.split('_')[2]
        n_pres = (df['presencia'] == 1).sum()
        n_aus = (df['presencia'] == 0).sum()
        has_new = all(v in df.columns for v in nuevas_vars)

        print(f"  {csv_file.name}")
        print(f"    Columnas: {list(df.columns)}")
        print(f"    Variables predictoras: {n_vars}")
        print(f"    Presencias: {n_pres}, Pseudo-ausencias: {n_aus}")
        print(f"    tmax_media_anual: {'✓' if 'tmax_media_anual' in df.columns else '✗'}")
        print(f"    tmin_media_anual: {'✓' if 'tmin_media_anual' in df.columns else '✗'}")
        print(f"    rango_termico_diurno: {'✓' if 'rango_termico_diurno' in df.columns else '✗'}")

    # Resumen
    t_fin = datetime.now()
    print(f"\n{'═'*70}")
    print(f"  ✓ SCRIPT 05C COMPLETADO")
    print(f"  Datasets actualizados: {datasets_actualizados}")
    print(f"  Variables agregadas: tmax_media_anual, tmin_media_anual, rango_termico_diurno")
    print(f"  Tiempo: {t_fin - t_inicio}")
    print(f"\n  Siguiente paso: Ejecutar LIMPIAR_RESULTADOS_06_INCORRECTOS.py")
    print(f"  Luego: Ejecutar SCRIPT_06_RANDOM_FOREST_SHAP_v1.1.py")
    print(f"{'═'*70}\n")


if __name__ == "__main__":
    main()