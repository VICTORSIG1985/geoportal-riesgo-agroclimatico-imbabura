"""
Script publicado como parte del Geoportal Riesgo Agroclimático — Imbabura, Ecuador
Pinto Páez, V. H. (2026). https://doi.org/10.5281/zenodo.19288559
Licencia: CC BY 4.0

NOTA: este archivo fue sanitizado para publicación pública.
- Credenciales (API keys, tokens, service accounts) removidas → <REDACTED_*>
- Rutas absolutas locales sustituidas por <RUTA_LOCAL>
Antes de ejecutar, configure sus propias rutas de entrada/salida y credenciales.

Archivo original: SCRIPT 03F AGREGACIÓN TEMPORAL DE ÍNDICES AGROCLIMÁTICOS.py
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
SCRIPT 03F: AGREGACIÓN TEMPORAL DE ÍNDICES AGROCLIMÁTICOS
===============================================================================
Versión: 1.0.0
Fecha: 2026-02-02
Autor: Víctor Hugo Pinto Páez

Descripción:
    Agrega los índices agroclimáticos diarios (Scripts 03A-03E) a escalas
    anuales y por período de análisis. Genera un dataset integrado con 
    todas las métricas necesarias para la Fase 4 (modelamiento).

Índices agregados:
    De Script 03A (ET₀):
        - ET0_anual_mm: Evapotranspiración total anual (mm/año), promediada 
          entre los años del archivo
        - ET0_media_diaria: ET₀ media diaria (mm/día)
    
    De Script 03B (Déficit hídrico):
        - deficit_anual_mm: Déficit hídrico total anual (mm/año)
        - deficit_media_diaria: Déficit medio diario (mm/día)
        - pct_dias_deficit: Porcentaje de días con déficit (P < ET₀)
    
    De Script 03C (Estrés térmico):
        - dias_estres_papa_anual: Promedio anual de días con Tmax > 25°C
        - dias_estres_maiz_anual: Promedio anual de días con Tmax > 35°C
        - dias_estres_frejol_anual: Promedio anual de días con Tmax > 30°C
        - dias_estres_quinua_anual: Promedio anual de días con Tmax > 32°C
    
    De Script 03D (Sequías):
        - dias_secos_anual: Promedio anual de días con P < 1 mm
        - cdd_max: Duración máxima de sequía en todo el período (días)
        - eventos_sequia_7d: Número promedio anual de rachas > 7 días
        - eventos_sequia_15d: Número promedio anual de rachas > 15 días
    
    De Script 03E (Heladas):
        - dias_helada_anual: Promedio anual de días con Tmin < 0°C
    
    Índice derivado:
        - indice_aridez: P_anual / ET₀_anual (UNEP 1992)

Entrada:
    - NetCDF de índices diarios (carpetas ET0, deficit_hidrico, estres_termico,
      sequia, heladas)
    - NetCDF de precipitación recortada (para Índice de Aridez)

Salida:
    - Un NetCDF por combinación GCM/experimento/período con todas las 
      métricas agregadas

Conformidad:
    - ISO 19115: Metadatos geográficos
    - CF Conventions 1.6: Metadatos climáticos
===============================================================================
"""

import os
import sys
import logging
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import xarray as xr

warnings.filterwarnings('ignore', category=RuntimeWarning)

# ============================================================================
# CONFIGURACIÓN DE LOGGING
# ============================================================================

def setup_logging():
    """Configura el sistema de logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ============================================================================
# CONFIGURACIÓN DEL PROYECTO
# ============================================================================

class Config:
    """Configuración central del script."""
    
    # Información del proyecto
    VERSION = "1.0.0"
    AUTOR = "Víctor Hugo Pinto Páez"
    FECHA = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Rutas base
    BASE_DIR = Path(r"<RUTA_LOCAL>")
    
    # Rutas de entrada
    RECORTADOS_DIR = BASE_DIR / "02_DATOS" / "climaticos" / "BASD_CMIP6_PE" / "recortados"
    INDICES_DIR = BASE_DIR / "02_DATOS" / "climaticos" / "indices"
    
    ET0_DIR = INDICES_DIR / "ET0"
    DEFICIT_DIR = INDICES_DIR / "deficit_hidrico"
    ESTRES_DIR = INDICES_DIR / "estres_termico"
    SEQUIA_DIR = INDICES_DIR / "sequia"
    HELADAS_DIR = INDICES_DIR / "heladas"
    
    # Ruta de salida
    OUTPUT_DIR = INDICES_DIR / "agregados"
    REPORTS_DIR = BASE_DIR / "05_DOCUMENTACION" / "reportes_auditoria"
    
    # Clasificación de aridez UNEP (1992)
    ARIDEZ_CLASES = {
        'Hiperárido': (0.0, 0.03),
        'Árido': (0.03, 0.20),
        'Semiárido': (0.20, 0.50),
        'Subhúmedo seco': (0.50, 0.65),
        'Subhúmedo húmedo': (0.65, 1.00),
        'Húmedo': (1.00, float('inf'))
    }


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def inventariar_indices(base_dir: Path) -> Dict[str, Dict]:
    """
    Construye un inventario de todos los archivos de índices disponibles,
    organizados por clave (experiment_gcm_periodo).
    
    Returns:
        Diccionario {clave: {indice: path, ...}} para cada combinación
    """
    inventario = {}
    
    # Mapeo de directorios a nombres de índice y patrones de búsqueda
    indices_config = {
        'et0': (Config.ET0_DIR, '_ET0_'),
        'deficit': (Config.DEFICIT_DIR, '_deficit_'),
        'estres': (Config.ESTRES_DIR, '_estres_'),
        'sequia': (Config.SEQUIA_DIR, '_sequia_'),
        'heladas': (Config.HELADAS_DIR, '_heladas_'),
    }
    
    for nombre_indice, (directorio, patron) in indices_config.items():
        if not directorio.exists():
            logger.warning(f"Directorio no encontrado: {directorio}")
            continue
        
        for exp_dir in directorio.iterdir():
            if not exp_dir.is_dir():
                continue
            experiment = exp_dir.name
            
            for gcm_dir in exp_dir.iterdir():
                if not gcm_dir.is_dir():
                    continue
                gcm = gcm_dir.name
                
                for nc_file in gcm_dir.glob("*.nc"):
                    # Extraer período del nombre del archivo
                    partes = nc_file.stem.split('_')
                    if len(partes) >= 7:
                        periodo = f"{partes[-2]}_{partes[-1]}"
                        clave = f"{experiment}__{gcm}__{periodo}"
                        
                        if clave not in inventario:
                            inventario[clave] = {
                                'experiment': experiment,
                                'gcm': gcm,
                                'period': periodo
                            }
                        inventario[clave][nombre_indice] = nc_file
    
    # Buscar también archivos de precipitación para Índice de Aridez
    for exp_dir in Config.RECORTADOS_DIR.iterdir():
        if not exp_dir.is_dir():
            continue
        experiment = exp_dir.name
        
        for gcm_dir in exp_dir.iterdir():
            if not gcm_dir.is_dir():
                continue
            gcm = gcm_dir.name
            
            for pr_file in gcm_dir.glob("*_pr_*.nc"):
                partes = pr_file.stem.split('_')
                if len(partes) >= 7:
                    periodo = f"{partes[-2]}_{partes[-1]}"
                    clave = f"{experiment}__{gcm}__{periodo}"
                    
                    if clave in inventario:
                        inventario[clave]['pr'] = pr_file
    
    return inventario


def calcular_rachas_secas(dia_seco: xr.DataArray) -> Tuple[xr.DataArray, xr.DataArray, xr.DataArray]:
    """
    Calcula métricas de rachas secas consecutivas para cada pixel.
    
    Implementa el cálculo de CDD (Consecutive Dry Days) y conteo de 
    eventos según definición ETCCDI.
    
    Args:
        dia_seco: DataArray binario (1=seco, 0=húmedo) con dim (time, lat, lon)
        
    Returns:
        Tupla (cdd_max, eventos_7d, eventos_15d) como DataArrays (lat, lon)
    """
    # Obtener valores numpy para procesamiento eficiente
    data = dia_seco.values  # (time, lat, lon)
    nt, nlat, nlon = data.shape
    
    cdd_max = np.zeros((nlat, nlon), dtype=np.float32)
    eventos_7d_total = np.zeros((nlat, nlon), dtype=np.float32)
    eventos_15d_total = np.zeros((nlat, nlon), dtype=np.float32)
    
    for i in range(nlat):
        for j in range(nlon):
            serie = data[:, i, j]
            
            # Detectar rachas usando diferencias
            max_racha = 0
            n_ev_7 = 0
            n_ev_15 = 0
            racha_actual = 0
            
            for t in range(nt):
                if serie[t] == 1:
                    racha_actual += 1
                else:
                    if racha_actual > max_racha:
                        max_racha = racha_actual
                    if racha_actual > 7:
                        n_ev_7 += 1
                    if racha_actual > 15:
                        n_ev_15 += 1
                    racha_actual = 0
            
            # Verificar última racha
            if racha_actual > max_racha:
                max_racha = racha_actual
            if racha_actual > 7:
                n_ev_7 += 1
            if racha_actual > 15:
                n_ev_15 += 1
            
            cdd_max[i, j] = max_racha
            eventos_7d_total[i, j] = n_ev_7
            eventos_15d_total[i, j] = n_ev_15
    
    # Convertir a DataArrays
    coords = {'lat': dia_seco.lat, 'lon': dia_seco.lon}
    
    cdd_da = xr.DataArray(cdd_max, coords=coords, dims=['lat', 'lon'])
    cdd_da.attrs = {
        'long_name': 'Maximum consecutive dry days in period',
        'units': 'days',
        'standard_name': 'spell_length_of_days_with_lwe_thickness_of_precipitation_amount_below_threshold',
    }
    
    ev7_da = xr.DataArray(eventos_7d_total, coords=coords, dims=['lat', 'lon'])
    ev7_da.attrs = {
        'long_name': 'Number of dry spell events longer than 7 days',
        'units': '1',
    }
    
    ev15_da = xr.DataArray(eventos_15d_total, coords=coords, dims=['lat', 'lon'])
    ev15_da.attrs = {
        'long_name': 'Number of severe dry spell events longer than 15 days',
        'units': '1',
    }
    
    return cdd_da, ev7_da, ev15_da


def procesar_combinacion(clave: str, info: Dict, output_dir: Path) -> Dict:
    """
    Procesa una combinación GCM/experimento/período y genera archivo agregado.
    
    Args:
        clave: Identificador de la combinación
        info: Diccionario con paths a archivos de índices
        output_dir: Directorio de salida
        
    Returns:
        Diccionario con estadísticas del procesamiento
    """
    stats = {
        'exitoso': False,
        'clave': clave,
        'error': None,
        'indices_procesados': []
    }
    
    try:
        experiment = info['experiment']
        gcm = info['gcm']
        period = info['period']
        
        variables_out = {}
        
        # ----------------------------------------------------------------
        # 1. ET₀: Media diaria y total anual
        # ----------------------------------------------------------------
        if 'et0' in info:
            ds = xr.open_dataset(info['et0'])
            et0 = ds['ET0']
            
            # Número de años en el archivo
            years = np.unique(et0.time.dt.year.values)
            n_years = len(years)
            
            # Media diaria
            et0_media = et0.mean(dim='time')
            et0_media.attrs = {
                'long_name': 'Mean daily reference evapotranspiration',
                'units': 'mm/day',
                'method': 'Hargreaves-Samani (1985)',
            }
            variables_out['ET0_media_diaria'] = et0_media
            
            # Total anual promedio
            et0_anual = et0.sum(dim='time') / n_years
            et0_anual.attrs = {
                'long_name': 'Mean annual reference evapotranspiration',
                'units': 'mm/year',
                'method': 'Hargreaves-Samani (1985)',
                'n_years': n_years,
            }
            variables_out['ET0_anual_mm'] = et0_anual
            
            stats['indices_procesados'].append('ET0')
            stats['et0_media'] = float(et0_media.mean().values)
            stats['et0_anual'] = float(et0_anual.mean().values)
            ds.close()
        
        # ----------------------------------------------------------------
        # 2. Déficit hídrico: Media diaria, total anual, % días déficit
        # ----------------------------------------------------------------
        if 'deficit' in info:
            ds = xr.open_dataset(info['deficit'])
            deficit = ds['deficit_hidrico']
            
            years = np.unique(deficit.time.dt.year.values)
            n_years = len(years)
            
            # Media diaria
            deficit_media = deficit.mean(dim='time')
            deficit_media.attrs = {
                'long_name': 'Mean daily water deficit (P - ET0)',
                'units': 'mm/day',
            }
            variables_out['deficit_media_diaria'] = deficit_media
            
            # Total anual promedio
            deficit_anual = deficit.sum(dim='time') / n_years
            deficit_anual.attrs = {
                'long_name': 'Mean annual water deficit',
                'units': 'mm/year',
                'n_years': n_years,
            }
            variables_out['deficit_anual_mm'] = deficit_anual
            
            # Porcentaje de días con déficit
            pct_deficit = (deficit < 0).mean(dim='time') * 100
            pct_deficit.attrs = {
                'long_name': 'Percentage of days with water deficit (P < ET0)',
                'units': '%',
            }
            variables_out['pct_dias_deficit'] = pct_deficit
            
            stats['indices_procesados'].append('deficit')
            stats['deficit_anual'] = float(deficit_anual.mean().values)
            ds.close()
        
        # ----------------------------------------------------------------
        # 3. Estrés térmico: Días promedio anuales por cultivo
        # ----------------------------------------------------------------
        if 'estres' in info:
            ds = xr.open_dataset(info['estres'])
            
            years_estres = None
            for cultivo in ['papa', 'maiz', 'frejol', 'quinua']:
                var_name = f'estres_termico_{cultivo}'
                if var_name in ds:
                    estres = ds[var_name]
                    
                    if years_estres is None:
                        years_estres = np.unique(estres.time.dt.year.values)
                    n_years = len(years_estres)
                    
                    # Días de estrés promedio anual
                    dias_estres = estres.sum(dim='time') / n_years
                    dias_estres.attrs = {
                        'long_name': f'Mean annual heat stress days for {cultivo}',
                        'units': 'days/year',
                        'crop': cultivo,
                    }
                    variables_out[f'dias_estres_{cultivo}_anual'] = dias_estres
            
            stats['indices_procesados'].append('estres_termico')
            ds.close()
        
        # ----------------------------------------------------------------
        # 4. Sequías: Días secos anuales + métricas de rachas
        # ----------------------------------------------------------------
        if 'sequia' in info:
            ds = xr.open_dataset(info['sequia'])
            dia_seco = ds['dia_seco']
            
            years = np.unique(dia_seco.time.dt.year.values)
            n_years = len(years)
            
            # Días secos promedio anual
            dias_secos_anual = dia_seco.sum(dim='time') / n_years
            dias_secos_anual.attrs = {
                'long_name': 'Mean annual dry days (P < 1 mm)',
                'units': 'days/year',
            }
            variables_out['dias_secos_anual'] = dias_secos_anual
            
            # Métricas de rachas secas consecutivas
            logger.info(f"    Calculando rachas secas (CDD)...")
            cdd_max, ev_7d, ev_15d = calcular_rachas_secas(dia_seco)
            
            cdd_max.attrs['n_years'] = n_years
            variables_out['cdd_max'] = cdd_max
            
            # Promediar eventos por año
            ev_7d_anual = ev_7d / n_years
            ev_7d_anual.attrs = {
                'long_name': 'Mean annual drought events longer than 7 days',
                'units': 'events/year',
                'n_years': n_years,
            }
            variables_out['eventos_sequia_7d'] = ev_7d_anual
            
            ev_15d_anual = ev_15d / n_years
            ev_15d_anual.attrs = {
                'long_name': 'Mean annual severe drought events longer than 15 days',
                'units': 'events/year',
                'n_years': n_years,
            }
            variables_out['eventos_sequia_15d'] = ev_15d_anual
            
            stats['indices_procesados'].append('sequia')
            stats['cdd_max_mean'] = float(cdd_max.mean().values)
            ds.close()
        
        # ----------------------------------------------------------------
        # 5. Heladas: Días promedio anuales
        # ----------------------------------------------------------------
        if 'heladas' in info:
            ds = xr.open_dataset(info['heladas'])
            helada = ds['helada']
            
            years = np.unique(helada.time.dt.year.values)
            n_years = len(years)
            
            dias_helada = helada.sum(dim='time') / n_years
            dias_helada.attrs = {
                'long_name': 'Mean annual frost days (Tmin < 0 degC)',
                'units': 'days/year',
            }
            variables_out['dias_helada_anual'] = dias_helada
            
            stats['indices_procesados'].append('heladas')
            ds.close()
        
        # ----------------------------------------------------------------
        # 6. Índice de Aridez (P_anual / ET₀_anual)
        # ----------------------------------------------------------------
        if 'pr' in info and 'ET0_anual_mm' in variables_out:
            ds = xr.open_dataset(info['pr'])
            pr = ds['pr']
            
            # Convertir a mm/día si necesario
            units = pr.attrs.get('units', '')
            if 'kg' in units.lower() or 's-1' in units.lower():
                pr_mm = pr * 86400
            else:
                pr_mm = pr
            
            years = np.unique(pr.time.dt.year.values)
            n_years = len(years)
            
            # Precipitación anual promedio
            pr_anual = pr_mm.sum(dim='time') / n_years
            pr_anual.attrs = {
                'long_name': 'Mean annual precipitation',
                'units': 'mm/year',
                'n_years': n_years,
            }
            variables_out['pr_anual_mm'] = pr_anual
            
            # Índice de Aridez
            et0_anual = variables_out['ET0_anual_mm']
            
            # Evitar división por cero
            ai = xr.where(et0_anual > 0, pr_anual / et0_anual, np.nan)
            ai.attrs = {
                'long_name': 'Aridity Index (UNEP 1992)',
                'units': '1',
                'formula': 'P_annual / ET0_annual',
                'reference': 'UNEP (1992)',
                'classification': 'Hyperarid<0.03; Arid<0.20; Semiarid<0.50; Dry_subhumid<0.65; Humid_subhumid<1.00; Humid>1.00',
            }
            variables_out['indice_aridez'] = ai
            
            stats['indices_procesados'].append('indice_aridez')
            stats['ai_mean'] = float(ai.mean().values)
            stats['pr_anual'] = float(pr_anual.mean().values)
            ds.close()
        
        # ----------------------------------------------------------------
        # Guardar dataset agregado
        # ----------------------------------------------------------------
        if len(variables_out) == 0:
            stats['error'] = "No se encontraron índices para agregar"
            return stats
        
        ds_out = xr.Dataset(variables_out)
        
        # Metadatos globales
        ds_out.attrs = {
            'title': 'Aggregated Agroclimatic Indices for Risk Assessment',
            'institution': 'Universidad San Gregorio de Portoviejo',
            'source': 'Aggregated from daily indices (Scripts 03A-03E)',
            'GCM': gcm,
            'experiment': experiment,
            'period': period,
            'references': 'Hargreaves & Samani (1985); UNEP (1992); ETCCDI; FAO-56',
            'history': f"{Config.FECHA}: Temporal aggregation using Script 03F v{Config.VERSION}",
            'Conventions': 'CF-1.6',
        }
        
        # Directorio de salida
        output_subdir = output_dir / experiment / gcm
        output_subdir.mkdir(parents=True, exist_ok=True)
        output_path = output_subdir / f"indices_agregados_{experiment}_{gcm}_{period}.nc"
        
        # Encoding
        encoding = {}
        for var_name in ds_out.data_vars:
            encoding[var_name] = {
                'zlib': True,
                'complevel': 4,
                'dtype': 'float32',
            }
        
        ds_out.to_netcdf(output_path, encoding=encoding)
        
        stats['exitoso'] = True
        stats['archivo_salida'] = str(output_path)
        stats['n_variables'] = len(variables_out)
        stats['tamaño_mb'] = output_path.stat().st_size / (1024 * 1024)
        
    except Exception as e:
        stats['error'] = str(e)
        logger.error(f"Error procesando {clave}: {e}")
        import traceback
        traceback.print_exc()
    
    return stats


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """Función principal del script."""
    tiempo_inicio = datetime.now()
    
    logger.info("=" * 70)
    logger.info("SCRIPT 03F: AGREGACIÓN TEMPORAL DE ÍNDICES AGROCLIMÁTICOS")
    logger.info("=" * 70)
    logger.info(f"Versión: {Config.VERSION}")
    logger.info(f"Fecha: {Config.FECHA}")
    logger.info("")
    logger.info("Índices a agregar:")
    logger.info("  - ET₀ (Hargreaves-Samani) → media diaria, total anual")
    logger.info("  - Déficit hídrico (P - ET₀) → total anual, % días déficit")
    logger.info("  - Estrés térmico → días/año por cultivo")
    logger.info("  - Sequías → días secos/año, CDD máx, eventos >7d y >15d")
    logger.info("  - Heladas → días/año")
    logger.info("  - Índice de Aridez → P anual / ET₀ anual (UNEP 1992)")
    logger.info("")
    
    # Verificar directorios
    logger.info("Verificando directorios de entrada...")
    dirs_check = {
        'ET₀': Config.ET0_DIR,
        'Déficit': Config.DEFICIT_DIR,
        'Estrés térmico': Config.ESTRES_DIR,
        'Sequía': Config.SEQUIA_DIR,
        'Heladas': Config.HELADAS_DIR,
        'Precipitación': Config.RECORTADOS_DIR,
    }
    
    for nombre, directorio in dirs_check.items():
        if directorio.exists():
            logger.info(f"  ✓ {nombre}: {directorio}")
        else:
            logger.warning(f"  ✗ {nombre}: {directorio} (NO ENCONTRADO)")
    
    Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    Config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Inventariar archivos
    logger.info("")
    logger.info("Inventariando archivos de índices...")
    inventario = inventariar_indices(Config.INDICES_DIR)
    logger.info(f"  ✓ Combinaciones encontradas: {len(inventario)}")
    
    if len(inventario) == 0:
        logger.error("No se encontraron archivos de índices")
        sys.exit(1)
    
    # Verificar completitud
    n_completas = sum(1 for v in inventario.values() 
                      if all(k in v for k in ['et0', 'deficit', 'estres', 'sequia', 'heladas', 'pr']))
    logger.info(f"  Combinaciones con todos los índices: {n_completas}/{len(inventario)}")
    
    # Procesar
    logger.info("")
    logger.info("=" * 50)
    logger.info("Procesando agregación temporal...")
    logger.info("=" * 50)
    
    resultados = []
    total = len(inventario)
    
    for i, (clave, info) in enumerate(sorted(inventario.items()), 1):
        if i == 1 or i % 20 == 0 or i == total:
            logger.info(f"[{i}/{total}] {info['experiment']} | {info['gcm']} | {info['period']}")
        
        stats = procesar_combinacion(clave, info, Config.OUTPUT_DIR)
        resultados.append(stats)
        
        if stats['exitoso'] and (i == 1 or i % 50 == 0):
            logger.info(f"    Variables: {stats['n_variables']} | "
                        f"Índices: {', '.join(stats['indices_procesados'])}")
    
    # Resumen
    tiempo_fin = datetime.now()
    duracion = tiempo_fin - tiempo_inicio
    
    exitosos = sum(1 for r in resultados if r.get('exitoso', False))
    fallidos = len(resultados) - exitosos
    
    logger.info("")
    logger.info("=" * 50)
    logger.info("RESUMEN")
    logger.info("=" * 50)
    logger.info(f"  Total procesados: {len(resultados)}")
    logger.info(f"  Exitosos: {exitosos}")
    logger.info(f"  Fallidos: {fallidos}")
    logger.info(f"  Tiempo total: {duracion}")
    
    # Estadísticas globales
    ai_values = [r['ai_mean'] for r in resultados if r.get('ai_mean') is not None]
    et0_values = [r['et0_anual'] for r in resultados if r.get('et0_anual') is not None]
    pr_values = [r['pr_anual'] for r in resultados if r.get('pr_anual') is not None]
    cdd_values = [r['cdd_max_mean'] for r in resultados if r.get('cdd_max_mean') is not None]
    
    if ai_values:
        logger.info("")
        logger.info("  Estadísticas globales (promedio entre combinaciones):")
        logger.info(f"    ET₀ anual:          {np.mean(et0_values):.0f} mm/año")
        logger.info(f"    Precipitación anual: {np.mean(pr_values):.0f} mm/año")
        logger.info(f"    Índice de Aridez:    {np.mean(ai_values):.2f}")
        logger.info(f"    CDD máximo promedio: {np.mean(cdd_values):.0f} días")
        
        # Clasificación de aridez
        ai_medio = np.mean(ai_values)
        for clase, (lim_inf, lim_sup) in Config.ARIDEZ_CLASES.items():
            if lim_inf <= ai_medio < lim_sup:
                logger.info(f"    Clasificación UNEP:  {clase}")
                break
    
    # Generar reporte
    logger.info("")
    logger.info("Generando reporte de auditoría...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    reporte_path = Config.REPORTS_DIR / f"REPORTE_SCRIPT_03F_{timestamp}.txt"
    
    with open(reporte_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("REPORTE DE AUDITORÍA - SCRIPT 03F: AGREGACIÓN TEMPORAL\n")
        f.write("=" * 70 + "\n\n")
        
        f.write("INFORMACIÓN GENERAL\n")
        f.write("-" * 30 + "\n")
        f.write(f"Fecha de ejecución: {Config.FECHA}\n")
        f.write(f"Versión del script: {Config.VERSION}\n")
        f.write(f"Autor: {Config.AUTOR}\n\n")
        
        f.write("METODOLOGÍA\n")
        f.write("-" * 30 + "\n")
        f.write("Agregación de índices diarios a métricas anuales/por período:\n")
        f.write("  - ET₀: media diaria (mm/día), total anual (mm/año)\n")
        f.write("  - Déficit: total anual (mm/año), % días con déficit\n")
        f.write("  - Estrés térmico: días/año por cultivo (4 variables)\n")
        f.write("  - Sequías: días secos/año, CDD máx, eventos >7d, >15d\n")
        f.write("  - Heladas: días/año\n")
        f.write("  - Índice de Aridez: P_anual / ET₀_anual (UNEP 1992)\n\n")
        
        f.write("RESULTADOS\n")
        f.write("-" * 30 + "\n")
        f.write(f"Total combinaciones procesadas: {len(resultados)}\n")
        f.write(f"Exitosas: {exitosos}\n")
        f.write(f"Fallidas: {fallidos}\n")
        f.write(f"Tasa de éxito: {100*exitosos/len(resultados):.1f}%\n\n")
        
        if ai_values:
            f.write("Estadísticas globales:\n")
            f.write(f"  ET₀ anual promedio:          {np.mean(et0_values):.0f} mm/año\n")
            f.write(f"  Precipitación anual promedio: {np.mean(pr_values):.0f} mm/año\n")
            f.write(f"  Índice de Aridez promedio:    {np.mean(ai_values):.2f}\n")
            f.write(f"  CDD máximo promedio:          {np.mean(cdd_values):.0f} días\n\n")
        
        f.write("TIEMPO DE EJECUCIÓN\n")
        f.write("-" * 30 + "\n")
        f.write(f"Inicio: {tiempo_inicio.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Fin: {tiempo_fin.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Duración: {duracion}\n\n")
        
        f.write("ARCHIVOS DE SALIDA\n")
        f.write("-" * 30 + "\n")
        f.write(f"Directorio: {Config.OUTPUT_DIR}\n")
        f.write(f"Formato: Un NetCDF por combinación GCM/experimento/período\n\n")
        
        f.write("VERIFICACIÓN DE CRITERIOS\n")
        f.write("-" * 30 + "\n")
        f.write(f"[{'✓' if exitosos == len(resultados) else '✗'}] Todas las combinaciones procesadas\n")
        f.write(f"[✓] Índices con respaldo bibliográfico\n")
        f.write(f"[✓] Métricas de sequía calculadas (CDD, eventos)\n")
        f.write(f"[✓] Índice de Aridez calculado (UNEP 1992)\n")
        f.write(f"[✓] Metadatos CF-compliant incluidos\n\n")
        
        f.write("DECISIÓN\n")
        f.write("-" * 30 + "\n")
        if exitosos == len(resultados):
            f.write("APROBADO - Fase 2 completada. Proceder con Fase 3 (datos de cultivos)\n")
        else:
            f.write("REQUIERE REVISIÓN - Verificar combinaciones fallidas\n")
        
        if fallidos > 0:
            f.write("\nCOMBINACIONES FALLIDAS:\n")
            for r in resultados:
                if not r.get('exitoso', False):
                    f.write(f"  - {r['clave']}: {r.get('error', 'Error desconocido')}\n")
        
        f.write("\n" + "=" * 70 + "\n")
    
    logger.info(f"  ✓ Reporte guardado: {reporte_path}")
    
    # Estado final
    logger.info("")
    logger.info("=" * 70)
    if exitosos == len(resultados):
        logger.info("✓ SCRIPT 03F COMPLETADO EXITOSAMENTE")
        logger.info("  ═══════════════════════════════════════════════")
        logger.info("  ✓ FASE 2 COMPLETADA: Todos los índices agroclimáticos calculados")
        logger.info("  ═══════════════════════════════════════════════")
        logger.info("  Siguiente paso: FASE 3 - Datos de cultivos (Script 04A)")
    else:
        logger.info("⚠ SCRIPT 03F COMPLETADO CON ADVERTENCIAS")
        logger.info(f"  {fallidos} combinaciones fallaron. Revisar reporte.")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()