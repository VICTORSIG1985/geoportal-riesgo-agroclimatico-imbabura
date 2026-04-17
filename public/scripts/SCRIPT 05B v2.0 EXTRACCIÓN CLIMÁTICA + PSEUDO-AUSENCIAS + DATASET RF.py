"""
Script publicado como parte del Geoportal Riesgo Agroclimático — Imbabura, Ecuador
Pinto Páez, V. H. (2026). https://doi.org/10.5281/zenodo.19288559
Licencia: CC BY 4.0

NOTA: este archivo fue sanitizado para publicación pública.
- Credenciales (API keys, tokens, service accounts) removidas → <REDACTED_*>
- Rutas absolutas locales sustituidas por <RUTA_LOCAL>
Antes de ejecutar, configure sus propias rutas de entrada/salida y credenciales.

Archivo original: SCRIPT 05B v2.0 EXTRACCIÓN CLIMÁTICA + PSEUDO-AUSENCIAS + DATASET RF.py
"""

#!/usr/bin/env python3
"""
======================================================================
  SCRIPT 05B v2.1: EXTRACCIÓN CLIMÁTICA + PSEUDO-AUSENCIAS + DATASET RF
  Riesgo Agroclimático - Imbabura, Ecuador
  
  Componente: VULNERABILIDAD (aptitud climática vía RF/SDM)
  Marco: IPCC AR5/AR6 → Riesgo = f(Peligro × Exposición × Vulnerabilidad)
  
  Objetivo: Extraer variables climáticas de BASD-CMIP6-PE (raw/) en los
  puntos de presencia GBIF y pseudo-ausencias, calcular los 16 índices
  agroclimáticos, y compilar el dataset de entrenamiento para RF.
  
  v2.0: Reescritura VECTORIZADA para rendimiento óptimo.
        Extracción simultánea de todos los puntos mediante fancy indexing
        en arrays NumPy. Mismo resultado científico que v1.0.
  
  v2.1: CORRECCIONES CRÍTICAS:
        - Ra convertida a mm/día (×0.408) antes de H-S (FAO-56 Eq. 52)
        - Pseudo-ausencias solo de celdas terrestres (filtro NaN en pr)
        - NaN oceánicos NO se rellenan → registros descartados post-ensemble
======================================================================

DECISIONES METODOLÓGICAS:
  D5: Extracción puntual en vez de rasters de dominio completo
      Justificación: Solo se necesitan valores en ~5,000 puntos (presencias
      + pseudo-ausencias). Procesar todo el dominio (~203 GB) sería 
      computacionalmente ineficiente sin beneficio para el entrenamiento RF.
      Los rasters de Imbabura (recortados/) ya existen para proyección.
  
  D6: Pseudo-ausencias por muestreo aleatorio del background
      Justificación: Barbet-Massin et al. (2012) recomiendan muestreo 
      aleatorio del background con ratio 1:1 para RF. El background se
      define como el dominio climático del dataset BASD-CMIP6-PE menos
      las celdas con presencia documentada.
      Referencia: Barbet-Massin, M., Jiguet, F., Albert, C.H. & Thuiller, W.
      (2012). Selecting pseudo-absences for species distribution models.
      Methods in Ecology and Evolution, 3(4), 803-814.
  
  D7: Ensemble mean de 10 GCMs para período histórico
      Justificación: El principio de "democracia de modelos" (Knutti, 2010)
      asegura que el ensemble mean captura la señal climática central 
      eliminando sesgos individuales de cada GCM.
      Referencia: Knutti, R. (2010). The end of model democracy? 
      Climatic Change, 102, 395-404.
  
  D8: Mismos 16 índices que Script 03F para consistencia
      Justificación: Las variables predictoras del SDM deben ser idénticas
      a las disponibles para proyección. Los recortados/ de Imbabura ya 
      tienen estos 16 índices calculados por 03F.

EJECUCIÓN:
  %runfile 'D:/POSGRADOS/TESIS/03_SCRIPTS/python/SCRIPT_05B_EXTRACCION_CLIMATICA_DATASET_RF.py' --wdir
======================================================================
"""

import os
import sys
import json
import time
import logging
import numpy as np
import pandas as pd
import xarray as xr
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════
BASE_DIR = Path(r"<RUTA_LOCAL>")
RAW_DIR = BASE_DIR / "02_DATOS" / "climaticos" / "BASD_CMIP6_PE" / "raw"
OCURRENCIAS_DIR = BASE_DIR / "02_DATOS" / "ocurrencias" / "clean"
OUTPUT_DIR = BASE_DIR / "02_DATOS" / "sdm_training"
AUDITORIA_DIR = BASE_DIR / "05_DOCUMENTACION" / "reportes_auditoria"
METADATOS_DIR = BASE_DIR / "05_DOCUMENTACION" / "metadatos_iso"

for d in [OUTPUT_DIR, AUDITORIA_DIR, METADATOS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

VERSION = "2.1.0"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(AUDITORIA_DIR / f"LOG_05B_{TIMESTAMP}.txt", encoding='utf-8')
    ]
)
log = logging.getLogger(__name__)

# Parámetros
RASTER_RES = 0.1  # Resolución BASD-CMIP6-PE (grados)
PSEUDO_ABSENCE_RATIO = 1.0  # 1:1 presencia:pseudo-ausencia (Barbet-Massin et al., 2012)
RANDOM_SEED = 42

# GCMs esperados
GCMS = [
    "CanESM5", "CNRM-CM6-1", "CNRM-ESM2-1", "EC-Earth3",
    "GFDL-ESM4", "IPSL-CM6A-LR", "MIROC6", "MPI-ESM1-2-HR",
    "MRI-ESM2-0", "UKESM1-0-LL"
]

# Umbrales de estrés térmico (mismos que Script 03C)
UMBRALES_TERMICOS = {
    "papa": 25.0,    # CIP (2020)
    "maiz": 35.0,    # FAO-56
    "frejol": 30.0,  # CIAT
    "quinua": 32.0   # Jacobsen (2003)
}

CULTIVOS = ["papa", "maiz", "frejol", "quinua"]


# ══════════════════════════════════════════════════════════════
# FUNCIONES DE DESCUBRIMIENTO DE ARCHIVOS
# ══════════════════════════════════════════════════════════════

def descubrir_archivos_raw(raw_dir, experimento="historical"):
    """
    Descubre automáticamente la estructura de archivos en raw/.
    Estrategia multi-nivel: subdirectorios > archivos sueltos > recursivo.
    Retorna dict: {gcm: {variable: [lista_de_archivos_ordenados]}}
    """
    resultado = {}
    
    # Estrategia 1: raw/historical/GCM/variable_*.nc (estructura estándar)
    exp_dir = raw_dir / experimento
    if exp_dir.exists():
        for gcm_dir in sorted(exp_dir.iterdir()):
            if gcm_dir.is_dir():
                gcm_name = gcm_dir.name
                archivos_por_var = defaultdict(list)
                for nc in sorted(gcm_dir.glob("*.nc")):
                    name = nc.stem.lower()
                    for var in ["tasmax", "tasmin", "tas", "pr"]:
                        if name.startswith(var + "_") or f"_{var}_" in name:
                            archivos_por_var[var].append(nc)
                            break
                if archivos_por_var:
                    resultado[gcm_name] = dict(archivos_por_var)
        if resultado:
            return resultado
    
    # Estrategia 2: Archivos sueltos en raw/ con nombre que incluye GCM
    archivos_nc = sorted(raw_dir.glob("*.nc"))
    if archivos_nc:
        for nc in archivos_nc:
            name = nc.stem
            if experimento not in name.lower():
                continue
            gcm_found = None
            for gcm in GCMS:
                if gcm.lower() in name.lower() or gcm.replace("-", "").lower() in name.replace("-", "").lower():
                    gcm_found = gcm
                    break
            if not gcm_found:
                continue
            var_found = None
            for var in ["tasmax", "tasmin", "tas", "pr"]:
                if name.lower().startswith(var + "_") or f"_{var}_" in name.lower():
                    var_found = var
                    break
            if not var_found:
                continue
            if gcm_found not in resultado:
                resultado[gcm_found] = defaultdict(list)
            resultado[gcm_found][var_found].append(nc)
    
    # Estrategia 3: Búsqueda recursiva
    if not resultado:
        for nc in sorted(raw_dir.rglob("*.nc")):
            name = nc.stem
            if experimento not in name.lower():
                continue
            gcm_found = None
            for gcm in GCMS:
                if gcm.lower() in name.lower() or gcm.replace("-", "").lower() in name.replace("-", "").lower():
                    gcm_found = gcm
                    break
            var_found = None
            for var in ["tasmax", "tasmin", "tas", "pr"]:
                if name.lower().startswith(var + "_") or f"_{var}_" in name.lower():
                    var_found = var
                    break
            if gcm_found and var_found:
                if gcm_found not in resultado:
                    resultado[gcm_found] = defaultdict(list)
                resultado[gcm_found][var_found].append(nc)
    
    return resultado


# ══════════════════════════════════════════════════════════════
# FUNCIONES VECTORIZADAS DE CÁLCULO DE ÍNDICES
# ══════════════════════════════════════════════════════════════

def calcular_ra_vectorizada(lats_rad, n_dias):
    """
    Radiación extraterrestre diaria vectorizada - Allen et al. (1998) FAO-56.
    
    Parámetros:
        lats_rad: array (n_puntos,) - Latitudes en radianes
        n_dias: int - Número de días en la serie
    
    Retorna:
        Ra: array (n_dias, n_puntos) - mm/día equivalente
        
    Nota: Se aplica conversión MJ/m²/día → mm/día dividiendo por
    λ = 2.45 MJ/kg (calor latente de vaporización), equivalente a
    multiplicar por 0.408. Ref: Allen et al. (1998) FAO-56 Eq. 52.
    """
    LAMBDA_CONVERSION = 0.408  # 1/λ = 1/2.45 MJ/kg → mm/día
    Gsc = 0.0820  # MJ/m²/min
    doy = np.arange(1, n_dias + 1) % 365
    doy[doy == 0] = 365
    
    # Broadcasting: doy (n_dias,1) × lats (1,n_puntos)
    doy_2d = doy[:, np.newaxis]  # (n_dias, 1)
    lat_2d = lats_rad[np.newaxis, :]  # (1, n_puntos)
    
    dr = 1 + 0.033 * np.cos(2 * np.pi * doy_2d / 365)
    delta = 0.409 * np.sin(2 * np.pi * doy_2d / 365 - 1.39)
    
    # ws con clipping para estabilidad numérica
    arg = -np.tan(lat_2d) * np.tan(delta)
    arg = np.clip(arg, -1.0, 1.0)
    ws = np.arccos(arg)
    
    Ra = (24 * 60 / np.pi) * Gsc * dr * (
        ws * np.sin(lat_2d) * np.sin(delta) +
        np.cos(lat_2d) * np.cos(delta) * np.sin(ws)
    )
    # Convertir MJ/m²/día → mm/día equivalente (FAO-56 Eq. 52)
    return np.maximum(Ra * LAMBDA_CONVERSION, 0)


def calcular_cdd_vectorizado(dias_secos_2d):
    """
    Calcula CDD máximo, eventos >7d y >15d para cada punto.
    Usa loop por punto pero optimizado con NumPy diff.
    
    Parámetros:
        dias_secos_2d: array bool (n_dias, n_puntos)
    
    Retorna:
        cdd_max, eventos_7d, eventos_15d: arrays (n_puntos,)
    """
    n_dias, n_puntos = dias_secos_2d.shape
    cdd_max = np.zeros(n_puntos, dtype=np.int32)
    eventos_7d = np.zeros(n_puntos, dtype=np.int32)
    eventos_15d = np.zeros(n_puntos, dtype=np.int32)
    
    for j in range(n_puntos):
        col = dias_secos_2d[:, j].astype(np.int8)
        # Detectar inicio/fin de rachas usando diff
        padded = np.concatenate(([0], col, [0]))
        d = np.diff(padded)
        starts = np.where(d == 1)[0]
        ends = np.where(d == -1)[0]
        
        if len(starts) == 0:
            continue
        
        duraciones = ends - starts
        cdd_max[j] = duraciones.max()
        eventos_7d[j] = np.sum(duraciones > 7)
        eventos_15d[j] = np.sum(duraciones > 15)
    
    return cdd_max, eventos_7d, eventos_15d


def calcular_indices_vectorizados(pr, tmin, tmax, lats, n_anios):
    """
    Calcula los 16 índices agroclimáticos de forma vectorizada
    para todos los puntos simultáneamente.
    
    Replica exactamente la metodología de Scripts 03A-03F.
    
    Parámetros:
        pr: array (n_dias, n_puntos) - Precipitación diaria (mm/día)
        tmin: array (n_dias, n_puntos) - Temperatura mínima diaria (°C)
        tmax: array (n_dias, n_puntos) - Temperatura máxima diaria (°C)
        lats: array (n_puntos,) - Latitudes en grados
        n_anios: float - Número de años del período
    
    Retorna:
        dict con 16 arrays (n_puntos,) de índices
    """
    n_dias, n_puntos = pr.shape
    
    # Consistencia física
    tmax = np.maximum(tmax, tmin + 0.1)
    tmean = (tmax + tmin) / 2.0
    
    # ── ET₀ Hargreaves-Samani (Script 03A) ──
    lats_rad = np.radians(lats)
    Ra = calcular_ra_vectorizada(lats_rad, n_dias)  # (n_dias, n_puntos)
    dt = np.maximum(tmax - tmin, 0.1)
    ET0 = 0.0023 * Ra * (tmean + 17.8) * np.sqrt(dt)
    ET0 = np.maximum(ET0, 0)
    
    # ── Déficit hídrico (Script 03B) ──
    deficit_diario = pr - ET0
    pct_dias_deficit = np.sum(deficit_diario < 0, axis=0) / n_dias * 100
    
    # ── Estrés térmico por cultivo (Script 03C) ──
    estres = {}
    for cultivo, umbral in UMBRALES_TERMICOS.items():
        estres[cultivo] = np.sum(tmax > umbral, axis=0) / n_anios
    
    # ── Sequías (Script 03D) ──
    dias_secos = (pr < 1.0)
    dias_secos_anual = np.sum(dias_secos, axis=0) / n_anios
    
    log.info("      Calculando CDD (rachas de sequía)...")
    cdd_max, eventos_7d, eventos_15d = calcular_cdd_vectorizado(dias_secos)
    
    # ── Heladas (Script 03E) ──
    dias_helada = np.sum(tmin < 0, axis=0) / n_anios
    
    # ── Totales anuales ──
    pr_anual = np.sum(pr, axis=0) / n_anios
    et0_anual = np.sum(ET0, axis=0) / n_anios
    deficit_anual = np.sum(deficit_diario, axis=0) / n_anios
    
    # ── Índice de Aridez (UNEP 1992) ──
    with np.errstate(divide='ignore', invalid='ignore'):
        indice_aridez = np.where(et0_anual > 0, pr_anual / et0_anual, np.nan)
    
    return {
        "ET0_media_diaria": np.mean(ET0, axis=0),
        "ET0_anual_mm": et0_anual,
        "deficit_media_diaria": np.mean(deficit_diario, axis=0),
        "deficit_anual_mm": deficit_anual,
        "pct_dias_deficit": pct_dias_deficit,
        "dias_estres_papa_anual": estres["papa"],
        "dias_estres_maiz_anual": estres["maiz"],
        "dias_estres_frejol_anual": estres["frejol"],
        "dias_estres_quinua_anual": estres["quinua"],
        "dias_secos_anual": dias_secos_anual,
        "cdd_max": cdd_max.astype(float),
        "eventos_sequia_7d": eventos_7d / n_anios,
        "eventos_sequia_15d": eventos_15d / n_anios,
        "dias_helada_anual": dias_helada,
        "pr_anual_mm": pr_anual,
        "indice_aridez": indice_aridez
    }


# ══════════════════════════════════════════════════════════════
# FUNCIONES AUXILIARES
# ══════════════════════════════════════════════════════════════

def detectar_nombres_coords(ds):
    """Detecta nombres de coordenadas lat/lon en un dataset xarray."""
    lat_name = None
    lon_name = None
    for name in ["lat", "latitude", "LAT", "Lat"]:
        if name in ds.coords or name in ds.dims:
            lat_name = name
            break
    for name in ["lon", "longitude", "LON", "Lon"]:
        if name in ds.coords or name in ds.dims:
            lon_name = name
            break
    if lat_name is None:
        lat_name = list(ds.dims)[0]
    if lon_name is None:
        lon_name = list(ds.dims)[1]
    return lat_name, lon_name


def detectar_nombre_variable(ds, candidatos):
    """Detecta el nombre de la variable de datos en un dataset."""
    for v in candidatos:
        if v in ds.data_vars:
            return v
    return list(ds.data_vars)[0]


def mapear_puntos_a_grilla(lats_punto, lons_punto, lats_grid, lons_grid):
    """
    Mapea puntos a índices de grilla usando vecino más cercano vectorizado.
    
    Retorna:
        lat_indices, lon_indices: arrays de índices en la grilla
        distancias_km: distancia al centroide de celda más cercana
    """
    # Broadcasting: (n_puntos,) vs (n_grid,) → argmin
    lat_indices = np.argmin(np.abs(lats_grid[:, None] - lats_punto[None, :]), axis=0)
    lon_indices = np.argmin(np.abs(lons_grid[:, None] - lons_punto[None, :]), axis=0)
    
    # Distancias aproximadas (km)
    dlat = (lats_grid[lat_indices] - lats_punto) * 111.0
    dlon = (lons_grid[lon_indices] - lons_punto) * 111.0 * np.cos(np.radians(lats_punto))
    distancias_km = np.sqrt(dlat**2 + dlon**2)
    
    return lat_indices, lon_indices, distancias_km


# ══════════════════════════════════════════════════════════════
# EJECUCIÓN PRINCIPAL
# ══════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("  SCRIPT 05B v2.1 — EXTRACCIÓN CLIMÁTICA + DATASET RF")
    print("  Riesgo Agroclimático Imbabura — VECTORIZADO + CORRECCIONES")
    print("  Componente: VULNERABILIDAD (SDM con Random Forest)")
    print("=" * 70)
    
    log.info("=" * 70)
    log.info("SCRIPT 05B v2.1: EXTRACCIÓN CLIMÁTICA + DATASET RF (VECTORIZADO)")
    log.info("=" * 70)
    log.info(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    t_inicio = time.time()
    
    # ──────────────────────────────────────────────────────────
    # [1/5] CARGAR OCURRENCIAS LIMPIAS
    # ──────────────────────────────────────────────────────────
    log.info("")
    log.info("=" * 70)
    log.info("[1/5] CARGAR OCURRENCIAS LIMPIAS (Script 05A)")
    log.info("=" * 70)
    
    archivos_clean = sorted(OCURRENCIAS_DIR.glob("ocurrencias_todas_clean_*.csv"))
    if not archivos_clean:
        log.error(f"No se encontraron archivos en: {OCURRENCIAS_DIR}")
        log.error("Ejecutar primero Script 05A.")
        sys.exit(1)
    
    archivo_ocurrencias = archivos_clean[-1]
    log.info(f"  Archivo: {archivo_ocurrencias.name}")
    
    df_presencias = pd.read_csv(archivo_ocurrencias)
    
    # Normalizar nombres de columnas
    col_map = {}
    for col in df_presencias.columns:
        cl = col.lower().strip()
        if cl in ['decimallatitude', 'lat', 'latitude']:
            col_map[col] = 'decimalLatitude'
        elif cl in ['decimallongitude', 'lon', 'longitude']:
            col_map[col] = 'decimalLongitude'
    df_presencias = df_presencias.rename(columns=col_map)
    
    # Asegurar columna 'cultivo'
    if 'cultivo' not in df_presencias.columns:
        for col in df_presencias.columns:
            if col.lower() in ['species', 'especie', 'nombre_cientifico']:
                species_map = {
                    'Solanum tuberosum': 'papa', 'Zea mays': 'maiz',
                    'Phaseolus vulgaris': 'frejol', 'Chenopodium quinoa': 'quinua'
                }
                df_presencias['cultivo'] = df_presencias[col].apply(
                    lambda x: next((v for k, v in species_map.items() if k in str(x)), 'desconocido')
                )
                break
    
    log.info(f"  Total registros: {len(df_presencias)}")
    for cultivo in CULTIVOS:
        n = len(df_presencias[df_presencias["cultivo"] == cultivo])
        log.info(f"    {cultivo}: {n}")
    
    # ──────────────────────────────────────────────────────────
    # [2/5] DESCUBRIR ARCHIVOS CLIMÁTICOS
    # ──────────────────────────────────────────────────────────
    log.info("")
    log.info("=" * 70)
    log.info("[2/5] DESCUBRIR ARCHIVOS CLIMÁTICOS (raw/historical)")
    log.info("=" * 70)
    log.info(f"  Directorio: {RAW_DIR}")
    
    archivos_historicos = descubrir_archivos_raw(RAW_DIR, "historical")
    
    if not archivos_historicos:
        log.error("No se encontraron archivos históricos en raw/")
        log.error(f"  Buscando en: {RAW_DIR}")
        sys.exit(1)
    
    gcms_encontrados = sorted(archivos_historicos.keys())
    log.info(f"  GCMs encontrados: {len(gcms_encontrados)}")
    for gcm in gcms_encontrados:
        vars_gcm = archivos_historicos[gcm]
        n_archivos = sum(len(v) for v in vars_gcm.values())
        vars_list = sorted(vars_gcm.keys())
        log.info(f"    {gcm}: {n_archivos} archivos, variables: {vars_list}")
    
    # Verificar variables completas
    vars_requeridas = {"pr", "tasmin", "tasmax"}
    gcms_completos = []
    for gcm, vars_gcm in archivos_historicos.items():
        if vars_requeridas.issubset(set(vars_gcm.keys())):
            gcms_completos.append(gcm)
    
    log.info(f"  GCMs con variables completas (pr, tasmin, tasmax): {len(gcms_completos)}")
    if not gcms_completos:
        log.error("Ningún GCM tiene las 3 variables requeridas.")
        sys.exit(1)
    
    # ──────────────────────────────────────────────────────────
    # [3/5] GENERAR PSEUDO-AUSENCIAS
    # ──────────────────────────────────────────────────────────
    log.info("")
    log.info("=" * 70)
    log.info("[3/5] GENERAR PSEUDO-AUSENCIAS")
    log.info("=" * 70)
    log.info("  DECISIÓN D6: Muestreo aleatorio del background (Barbet-Massin et al., 2012)")
    log.info(f"  Ratio presencia:pseudo-ausencia = 1:{PSEUDO_ABSENCE_RATIO}")
    
    # Obtener dominio espacial del primer archivo NetCDF raw
    primer_gcm = gcms_completos[0]
    primer_archivo = archivos_historicos[primer_gcm]["pr"][0]
    log.info(f"  Leyendo dominio de: {primer_archivo.name}")
    
    ds_ref = xr.open_dataset(primer_archivo)
    lat_name_ref, lon_name_ref = detectar_nombres_coords(ds_ref)
    lats_grid = ds_ref[lat_name_ref].values
    lons_grid = ds_ref[lon_name_ref].values
    
    # Identificar celdas TERRESTRES (con datos válidos de precipitación)
    pr_var_ref = detectar_nombre_variable(ds_ref, ["pr", "precipitation", "precip"])
    # Leer una muestra temporal (primer mes) para detectar celdas oceánicas
    pr_sample = ds_ref[pr_var_ref].isel(time=slice(0, 30)).values  # (30, nlat, nlon)
    # Una celda es terrestre si tiene al menos 1 valor no-NaN
    mascara_terrestre = ~np.all(np.isnan(pr_sample), axis=0)  # (nlat, nlon)
    n_terrestres = mascara_terrestre.sum()
    n_oceanicas = (~mascara_terrestre).sum()
    ds_ref.close()
    
    log.info(f"  Dominio raw: lat [{lats_grid.min():.2f}, {lats_grid.max():.2f}], "
             f"lon [{lons_grid.min():.2f}, {lons_grid.max():.2f}]")
    log.info(f"  Grid: {len(lats_grid)} × {len(lons_grid)} = {len(lats_grid)*len(lons_grid)} celdas")
    log.info(f"  Celdas terrestres: {n_terrestres} | Celdas oceánicas: {n_oceanicas}")
    
    # Crear set SOLO de celdas terrestres
    all_cells = set()
    for i, lat in enumerate(lats_grid):
        for j, lon in enumerate(lons_grid):
            if mascara_terrestre[i, j]:
                all_cells.add((round(lat, 4), round(lon, 4)))
    
    log.info(f"  Celdas disponibles para background: {len(all_cells)} (solo terrestres)")
    
    # Generar pseudo-ausencias por cultivo
    np.random.seed(RANDOM_SEED)
    pseudo_ausencias = []
    
    for cultivo in CULTIVOS:
        df_cult = df_presencias[df_presencias["cultivo"] == cultivo]
        n_presencias = len(df_cult)
        n_pseudo = int(n_presencias * PSEUDO_ABSENCE_RATIO)
        
        # Identificar celdas con presencia (para excluirlas)
        celdas_presencia = set()
        for _, row in df_cult.iterrows():
            lat_cell = round(round(row["decimalLatitude"] / RASTER_RES) * RASTER_RES, 4)
            lon_cell = round(round(row["decimalLongitude"] / RASTER_RES) * RASTER_RES, 4)
            celdas_presencia.add((lat_cell, lon_cell))
        
        # Celdas disponibles para pseudo-ausencia
        celdas_background = list(all_cells - celdas_presencia)
        
        if len(celdas_background) < n_pseudo:
            log.warning(f"  {cultivo}: solo {len(celdas_background)} celdas background "
                       f"(necesita {n_pseudo})")
            n_pseudo = len(celdas_background)
        
        # Muestrear
        indices_sample = np.random.choice(len(celdas_background), size=n_pseudo, replace=False)
        
        for idx in indices_sample:
            lat_pa, lon_pa = celdas_background[idx]
            pseudo_ausencias.append({
                "cultivo": cultivo,
                "decimalLatitude": lat_pa,
                "decimalLongitude": lon_pa,
                "presencia": 0
            })
        
        log.info(f"  {cultivo}: {n_presencias} presencias → {n_pseudo} pseudo-ausencias generadas")
    
    df_pseudo = pd.DataFrame(pseudo_ausencias)
    
    # Combinar presencias + pseudo-ausencias
    df_presencias_con_label = df_presencias.copy()
    df_presencias_con_label["presencia"] = 1
    
    df_todos = pd.concat([
        df_presencias_con_label[["cultivo", "decimalLatitude", "decimalLongitude", "presencia"]],
        df_pseudo
    ], ignore_index=True)
    
    log.info(f"\n  Total puntos para extracción: {len(df_todos)} "
             f"({len(df_presencias)} presencias + {len(df_pseudo)} pseudo-ausencias)")
    
    # ──────────────────────────────────────────────────────────
    # [4/5] EXTRACCIÓN CLIMÁTICA VECTORIZADA + CÁLCULO DE ÍNDICES
    # ──────────────────────────────────────────────────────────
    log.info("")
    log.info("=" * 70)
    log.info("[4/5] EXTRACCIÓN CLIMÁTICA VECTORIZADA + CÁLCULO DE ÍNDICES")
    log.info("=" * 70)
    log.info("  DECISIÓN D7: Ensemble mean de GCMs para período histórico")
    log.info("  DECISIÓN D8: 16 índices idénticos a Script 03F")
    log.info(f"  GCMs a procesar: {len(gcms_completos)}")
    log.info("  MÉTODO: Extracción vectorizada (fancy indexing NumPy)")
    
    # Puntos únicos para extracción
    puntos_unicos = df_todos[["decimalLatitude", "decimalLongitude"]].drop_duplicates().reset_index(drop=True)
    n_puntos = len(puntos_unicos)
    lats_punto = puntos_unicos["decimalLatitude"].values
    lons_punto = puntos_unicos["decimalLongitude"].values
    
    log.info(f"  Puntos únicos a extraer: {n_puntos}")
    
    # Pre-mapear puntos a grilla (se hace una vez, válido para todos los GCMs)
    log.info("  Mapeando puntos a grilla (vectorizado)...")
    lat_indices, lon_indices, distancias_km = mapear_puntos_a_grilla(
        lats_punto, lons_punto, lats_grid, lons_grid
    )
    
    log.info(f"    Celdas únicas ocupadas: {len(set(zip(lat_indices, lon_indices)))}")
    log.info(f"    Distancia al centroide: media={distancias_km.mean():.1f} km, "
             f"máx={distancias_km.max():.1f} km")
    
    # Alertar si hay puntos lejos (esperado para dominio grande)
    n_lejos = np.sum(distancias_km > 15)
    if n_lejos > 0:
        log.info(f"    Puntos a >15 km del centroide: {n_lejos} "
                f"(normal para grid de {RASTER_RES}° ≈ {RASTER_RES*111:.0f} km)")
    
    # Almacenar índices por GCM para cada punto
    # Shape: (n_gcms, 16, n_puntos) - se promedia sobre eje 0
    indices_nombres = [
        "ET0_media_diaria", "ET0_anual_mm", "deficit_media_diaria",
        "deficit_anual_mm", "pct_dias_deficit",
        "dias_estres_papa_anual", "dias_estres_maiz_anual",
        "dias_estres_frejol_anual", "dias_estres_quinua_anual",
        "dias_secos_anual", "cdd_max", "eventos_sequia_7d", "eventos_sequia_15d",
        "dias_helada_anual", "pr_anual_mm", "indice_aridez"
    ]
    
    # Acumular resultados de cada GCM: lista de dicts
    resultados_gcms = []  # cada elemento: dict {nombre_indice: array(n_puntos)}
    gcms_procesados = []
    gcms_fallidos = []
    
    for ig, gcm in enumerate(gcms_completos):
        t_gcm = time.time()
        log.info(f"\n  ─── GCM [{ig+1}/{len(gcms_completos)}]: {gcm} ───")
        
        vars_gcm = archivos_historicos[gcm]
        
        try:
            # Cargar las 3 variables y extraer vectorizado
            datos = {}
            for var, candidatos in [
                ("pr", ["pr", "precipitation", "precip"]),
                ("tasmin", ["tasmin", "tmin"]),
                ("tasmax", ["tasmax", "tmax"])
            ]:
                archivos = vars_gcm[var]
                log.info(f"    {var}: abriendo {len(archivos)} archivos...")
                ds = xr.open_mfdataset(archivos, combine="by_coords", engine="netcdf4")
                
                lat_name, lon_name = detectar_nombres_coords(ds)
                var_name = detectar_nombre_variable(ds, candidatos)
                
                # Seleccionar período 1981-2014
                time_name = "time" if "time" in ds.dims else list(ds.dims)[0]
                ds_sel = ds.sel({time_name: slice("1981-01-01", "2014-12-31")})
                
                # Extraer array completo y luego fancy-index
                data_array = ds_sel[var_name].values  # (n_dias, n_lat, n_lon)
                
                # Fancy indexing: extraer todos los puntos a la vez
                extracted = data_array[:, lat_indices, lon_indices]  # (n_dias, n_puntos)
                
                ds.close()
                
                # Verificar unidades
                if var in ["tasmin", "tasmax"] and np.nanmean(extracted) > 100:
                    extracted = extracted - 273.15
                    log.info(f"      → Convertido de Kelvin a °C")
                
                if var == "pr" and 0 < np.nanmean(extracted) < 0.5:
                    extracted = extracted * 86400
                    log.info(f"      → Convertido de kg/m²/s a mm/día")
                
                log.info(f"      Shape: {extracted.shape}, "
                        f"rango: [{np.nanmin(extracted):.2f}, {np.nanmax(extracted):.2f}]")
                
                datos[var] = extracted
            
            # ── Manejo de NaN ──
            # Detectar puntos con >50% NaN (celdas oceánicas/sin datos)
            # Solo rellenar NaN esporádicos en puntos terrestres válidos
            for var in datos:
                pct_nan_por_punto = np.isnan(datos[var]).sum(axis=0) / datos[var].shape[0]
                puntos_invalidos = pct_nan_por_punto > 0.5
                
                if puntos_invalidos.any():
                    log.info(f"      {var}: {puntos_invalidos.sum()} puntos con >50% NaN (oceánicos)")
                
                # Para puntos válidos con NaN esporádicos: rellenar con mediana temporal
                mask_nan = np.isnan(datos[var])
                puntos_validos_con_nan = mask_nan.any(axis=0) & ~puntos_invalidos
                if puntos_validos_con_nan.any():
                    col_median = np.nanmedian(datos[var][:, puntos_validos_con_nan], axis=0)
                    for t in range(datos[var].shape[0]):
                        row_mask = mask_nan[t, :] & puntos_validos_con_nan
                        if row_mask.any():
                            median_vals = np.nanmedian(datos[var][:, row_mask], axis=0)
                            datos[var][t, row_mask] = median_vals
                
                # Para puntos oceánicos: dejar NaN → producirán NaN en índices
                # Los NaN se propagarán y esos registros se descartarán al final
            
            # Calcular índices vectorizados
            n_dias = datos["pr"].shape[0]
            n_anios = n_dias / 365.25
            
            log.info(f"    Calculando 16 índices ({n_dias} días × {n_puntos} puntos)...")
            
            indices_gcm = calcular_indices_vectorizados(
                datos["pr"], datos["tasmin"], datos["tasmax"],
                lats_punto, n_anios
            )
            
            resultados_gcms.append(indices_gcm)
            gcms_procesados.append(gcm)
            
            t_elapsed = time.time() - t_gcm
            log.info(f"    ✓ {gcm} completado en {t_elapsed:.1f}s")
            
            # Estadísticas rápidas
            log.info(f"      ET₀ anual: {indices_gcm['ET0_anual_mm'].mean():.0f} mm/año")
            log.info(f"      P anual: {indices_gcm['pr_anual_mm'].mean():.0f} mm/año")
            log.info(f"      Aridez: {np.nanmean(indices_gcm['indice_aridez']):.2f}")
            
        except Exception as e:
            log.warning(f"    ⚠ Error procesando {gcm}: {e}")
            gcms_fallidos.append(gcm)
            continue
    
    # ──────────────────────────────────────────────────────────
    # CALCULAR ENSEMBLE MEAN + STD
    # ──────────────────────────────────────────────────────────
    log.info("")
    log.info("  Calculando ensemble mean + std...")
    log.info(f"  GCMs exitosos: {len(gcms_procesados)}/{len(gcms_completos)}")
    
    if not resultados_gcms:
        log.error("Ningún GCM se procesó exitosamente.")
        sys.exit(1)
    
    # Stack: (n_gcms, n_puntos) por cada índice → mean y std sobre eje 0
    ensemble_mean = {}
    ensemble_std = {}
    
    for nombre in indices_nombres:
        stack = np.array([r[nombre] for r in resultados_gcms])  # (n_gcms, n_puntos)
        ensemble_mean[nombre] = np.nanmean(stack, axis=0)
        ensemble_std[nombre] = np.nanstd(stack, axis=0)
    
    log.info(f"  Ensemble calculado para {n_puntos} puntos × {len(indices_nombres)} índices")
    
    # ──────────────────────────────────────────────────────────
    # [5/5] COMPILAR DATASET DE ENTRENAMIENTO
    # ──────────────────────────────────────────────────────────
    log.info("")
    log.info("=" * 70)
    log.info("[5/5] COMPILAR DATASET DE ENTRENAMIENTO")
    log.info("=" * 70)
    
    # Crear lookup: (lat_round, lon_round) → índice en puntos_unicos
    punto_a_idx = {}
    for i in range(n_puntos):
        key = (round(lats_punto[i], 4), round(lons_punto[i], 4))
        punto_a_idx[key] = i
    
    # Asignar índices a cada registro
    registros_finales = []
    n_sin_datos = 0
    
    for _, row in df_todos.iterrows():
        punto_key = (round(row["decimalLatitude"], 4), round(row["decimalLongitude"], 4))
        
        if punto_key in punto_a_idx:
            idx = punto_a_idx[punto_key]
            registro = {
                "cultivo": row["cultivo"],
                "lat": row["decimalLatitude"],
                "lon": row["decimalLongitude"],
                "presencia": row["presencia"],
            }
            for nombre in indices_nombres:
                registro[nombre] = ensemble_mean[nombre][idx]
            registros_finales.append(registro)
        else:
            n_sin_datos += 1
    
    df_dataset = pd.DataFrame(registros_finales)
    
    log.info(f"  Registros con datos climáticos: {len(df_dataset)}")
    log.info(f"  Registros sin match en grilla (descartados): {n_sin_datos}")
    
    # Eliminar registros con NaN en variables climáticas (puntos oceánicos residuales)
    n_antes = len(df_dataset)
    df_dataset = df_dataset.dropna(subset=indices_nombres).reset_index(drop=True)
    n_nan_eliminados = n_antes - len(df_dataset)
    if n_nan_eliminados > 0:
        log.info(f"  Registros con NaN climático eliminados: {n_nan_eliminados}")
    log.info(f"  Dataset final limpio: {len(df_dataset)} registros")
    
    # Estadísticas por cultivo
    log.info("")
    log.info("  Resumen por cultivo:")
    log.info(f"  {'Cultivo':<12s} {'Presencias':>11s} {'Ausencias':>11s} {'Total':>8s}")
    log.info(f"  {'-'*12} {'-'*11} {'-'*11} {'-'*8}")
    for cultivo in CULTIVOS:
        df_c = df_dataset[df_dataset["cultivo"] == cultivo]
        n_pres = len(df_c[df_c["presencia"] == 1])
        n_aus = len(df_c[df_c["presencia"] == 0])
        log.info(f"  {cultivo:<12s} {n_pres:>11d} {n_aus:>11d} {len(df_c):>8d}")
    
    total_pres = len(df_dataset[df_dataset["presencia"] == 1])
    total_aus = len(df_dataset[df_dataset["presencia"] == 0])
    log.info(f"  {'TOTAL':<12s} {total_pres:>11d} {total_aus:>11d} {len(df_dataset):>8d}")
    
    # Estadísticas de variables climáticas
    log.info("")
    log.info("  Estadísticas de variables climáticas (ensemble mean):")
    variables_indices = [c for c in df_dataset.columns if c not in ["cultivo", "lat", "lon", "presencia"]]
    for var in variables_indices:
        vals = df_dataset[var].dropna()
        if len(vals) > 0:
            log.info(f"    {var:<30s}  min={vals.min():>8.1f}  mean={vals.mean():>8.1f}  max={vals.max():>8.1f}")
    
    # ──────────────────────────────────────────────────────────
    # GUARDAR DATASETS
    # ──────────────────────────────────────────────────────────
    log.info("")
    log.info("  Guardando datasets...")
    
    # Dataset combinado
    archivo_dataset = OUTPUT_DIR / f"dataset_rf_training_{TIMESTAMP}.csv"
    df_dataset.to_csv(archivo_dataset, index=False, encoding='utf-8')
    log.info(f"  ✓ Dataset combinado: {archivo_dataset.name} ({len(df_dataset)} registros)")
    
    # Datasets por cultivo
    for cultivo in CULTIVOS:
        df_c = df_dataset[df_dataset["cultivo"] == cultivo]
        archivo_c = OUTPUT_DIR / f"dataset_rf_{cultivo}_{TIMESTAMP}.csv"
        df_c.to_csv(archivo_c, index=False, encoding='utf-8')
        log.info(f"  ✓ Dataset {cultivo}: {archivo_c.name} ({len(df_c)} registros)")
    
    # ──────────────────────────────────────────────────────────
    # DOCUMENTACIÓN Y METADATOS
    # ──────────────────────────────────────────────────────────
    log.info("")
    log.info("  Generando documentación...")
    
    # Reporte JSON
    reporte = {
        "script": "05B",
        "version": VERSION,
        "timestamp": TIMESTAMP,
        "objetivo": "Extracción climática puntual + pseudo-ausencias + dataset de entrenamiento RF",
        "fuente_climatica": "BASD-CMIP6-PE raw/ (dominio Perú+Ecuador)",
        "periodo_historico": "1981-2014",
        "metodo_extraccion": "Vectorizado (fancy indexing NumPy) - v2.0",
        "gcms_procesados": gcms_procesados,
        "gcms_fallidos": gcms_fallidos,
        "n_gcms": len(gcms_procesados),
        "ocurrencias": {
            "archivo_fuente": str(archivo_ocurrencias),
            "total_presencias": int(total_pres),
            "total_pseudo_ausencias": int(total_aus),
            "ratio": PSEUDO_ABSENCE_RATIO
        },
        "dataset": {
            "total_registros": len(df_dataset),
            "registros_sin_datos": n_sin_datos,
            "variables": variables_indices,
            "n_variables": len(variables_indices),
            "por_cultivo": {c: int(len(df_dataset[df_dataset["cultivo"] == c])) for c in CULTIVOS}
        },
        "grilla": {
            "dominio_lat": [float(lats_grid.min()), float(lats_grid.max())],
            "dominio_lon": [float(lons_grid.min()), float(lons_grid.max())],
            "resolucion_grados": RASTER_RES,
            "n_celdas": len(all_cells),
            "distancia_media_km": float(distancias_km.mean()),
            "distancia_max_km": float(distancias_km.max())
        },
        "decisiones": {
            "D5": "Extracción puntual vs rasters completos",
            "D6": f"Pseudo-ausencias ratio {PSEUDO_ABSENCE_RATIO}:1. Ref: Barbet-Massin et al. (2012)",
            "D7": f"Ensemble mean de {len(gcms_procesados)} GCMs. Ref: Knutti (2010)",
            "D8": "16 índices idénticos a Script 03F"
        }
    }
    
    archivo_reporte = AUDITORIA_DIR / f"REPORTE_05B_{TIMESTAMP}.json"
    with open(archivo_reporte, 'w', encoding='utf-8') as f:
        json.dump(reporte, f, indent=2, ensure_ascii=False, default=str)
    log.info(f"  ✓ Reporte: {archivo_reporte.name}")
    
    # Metadatos ISO 19115
    metadatos = {
        "fileIdentifier": f"SCRIPT_05B_v{VERSION}_{TIMESTAMP}",
        "language": "spa",
        "characterSet": "utf8",
        "hierarchyLevel": "dataset",
        "contact": {
            "individualName": "Víctor Hugo Pinto Páez",
            "organisationName": "Universidad San Gregorio de Portoviejo",
            "role": "author"
        },
        "dateStamp": datetime.now().isoformat(),
        "identificationInfo": {
            "title": "Dataset de entrenamiento RF para SDM de cultivos andinos",
            "abstract": (
                f"Dataset con {len(df_dataset)} registros (presencias GBIF + "
                f"pseudo-ausencias) y {len(variables_indices)} índices agroclimáticos "
                f"calculados como ensemble mean de {len(gcms_procesados)} GCMs CMIP6 "
                f"del período histórico 1981-2014 de BASD-CMIP6-PE."
            ),
            "purpose": (
                "Entrenamiento de Random Forest como SDM para el componente de "
                "Vulnerabilidad en el modelo de riesgo agroclimático IPCC AR5/AR6"
            ),
            "topicCategory": "farming",
            "extent": {
                "geographicElement": {
                    "westBoundLongitude": float(lons_grid.min()),
                    "eastBoundLongitude": float(lons_grid.max()),
                    "southBoundLatitude": float(lats_grid.min()),
                    "northBoundLatitude": float(lats_grid.max())
                }
            },
            "spatialResolution": f"{RASTER_RES}° ({RASTER_RES * 111:.0f} km)"
        },
        "dataQualityInfo": {
            "lineage": {
                "sources": [
                    "GBIF API (presencias, Script 05A)",
                    "BASD-CMIP6-PE raw/ (datos climáticos históricos)"
                ],
                "processSteps": [
                    "Carga de ocurrencias limpias (Script 05A)",
                    f"Generación de pseudo-ausencias (ratio {PSEUDO_ABSENCE_RATIO}:1)",
                    f"Extracción vectorizada de datos diarios de {len(gcms_procesados)} GCMs",
                    "Cálculo de 16 índices agroclimáticos por punto (vectorizado)",
                    "Cálculo de ensemble mean + std inter-GCM",
                    "Compilación de dataset final por cultivo"
                ]
            }
        }
    }
    
    archivo_meta = METADATOS_DIR / f"ISO19115_SCRIPT_05B_{TIMESTAMP}.json"
    with open(archivo_meta, 'w', encoding='utf-8') as f:
        json.dump(metadatos, f, indent=2, ensure_ascii=False)
    log.info(f"  ✓ Metadatos ISO: {archivo_meta.name}")
    
    # ──────────────────────────────────────────────────────────
    # RESUMEN FINAL
    # ──────────────────────────────────────────────────────────
    duracion = time.time() - t_inicio
    
    log.info("")
    log.info("=" * 70)
    log.info("  SCRIPT 05B v2.1 COMPLETADO")
    log.info("=" * 70)
    log.info(f"  Duración: {duracion:.0f} segundos ({duracion/60:.1f} minutos)")
    log.info(f"  GCMs procesados: {len(gcms_procesados)}")
    log.info(f"  Puntos extraídos: {n_puntos}")
    log.info(f"  Dataset total: {len(df_dataset)} registros")
    log.info(f"  Variables: {len(variables_indices)}")
    log.info(f"  Decisiones documentadas: 4")
    log.info(f"  Productos en: {OUTPUT_DIR}")
    log.info("=" * 70)
    
    # Verificación de criterios
    log.info("")
    log.info("VERIFICACIÓN DE CRITERIOS:")
    log.info(f"  {'Criterio':<45s} {'Requerido':<15s} {'Cumple'}")
    log.info(f"  {'-'*45} {'-'*15} {'-'*8}")
    
    c1 = len(gcms_procesados) >= 3
    log.info(f"  {'GCMs con datos completos':<45s} {'≥ 3':<15s} "
             f"{'✓ SÍ' if c1 else '✗ NO'} ({len(gcms_procesados)})")
    
    c2 = all(len(df_dataset[df_dataset["cultivo"] == c]) >= 50 for c in CULTIVOS)
    log.info(f"  {'≥50 registros/cultivo':<45s} {'≥ 50':<15s} "
             f"{'✓ SÍ' if c2 else '⚠ PARCIAL'}")
    
    c3 = len(variables_indices) == 16
    log.info(f"  {'16 variables climáticas':<45s} {'16':<15s} "
             f"{'✓ SÍ' if c3 else '⚠'} ({len(variables_indices)})")
    
    cobertura = (1 - n_sin_datos / max(len(df_todos), 1)) * 100
    c4 = cobertura > 90
    log.info(f"  {'Cobertura climática >90%':<45s} {'>90%':<15s} "
             f"{'✓ SÍ' if c4 else '⚠'} ({cobertura:.1f}%)")
    
    log.info(f"  {'Metadatos ISO 19115':<45s} {'Sí':<15s} ✓ SÍ")
    
    if c1 and c2 and c3 and c4:
        log.info("")
        log.info("ESTADO: APROBADO")
        log.info("")
        log.info("SIGUIENTE PASO:")
        log.info("  Script 06: Entrenamiento RF por cultivo + análisis SHAP")
        log.info(f"  (usa dataset_rf_[cultivo]_*.csv en {OUTPUT_DIR})")
    else:
        log.info("")
        log.info("ESTADO: REQUIERE REVISIÓN")
    
    print(f"\n  ✓ Script 05B v2.1 completado. Dataset en: {OUTPUT_DIR}")
    
    return df_dataset


# ══════════════════════════════════════════════════════════════
# EJECUCIÓN
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    df = main()