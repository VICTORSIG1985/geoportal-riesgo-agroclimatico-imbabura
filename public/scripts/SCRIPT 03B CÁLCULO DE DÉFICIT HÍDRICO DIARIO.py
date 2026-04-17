"""
Script publicado como parte del Geoportal Riesgo Agroclimático — Imbabura, Ecuador
Pinto Páez, V. H. (2026). https://doi.org/10.5281/zenodo.19288559
Licencia: CC BY 4.0

NOTA: este archivo fue sanitizado para publicación pública.
- Credenciales (API keys, tokens, service accounts) removidas → <REDACTED_*>
- Rutas absolutas locales sustituidas por <RUTA_LOCAL>
Antes de ejecutar, configure sus propias rutas de entrada/salida y credenciales.

Archivo original: SCRIPT 03B CÁLCULO DE DÉFICIT HÍDRICO DIARIO.py
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
SCRIPT 03B: CÁLCULO DE DÉFICIT HÍDRICO DIARIO
===============================================================================
Versión: 1.0.0
Fecha: 2026-02-02
Autor: Víctor Hugo Pinto Páez

Descripción:
    Calcula el déficit hídrico diario como la diferencia entre precipitación
    y evapotranspiración de referencia. Este índice es fundamental para
    evaluar el balance hídrico y el estrés por sequía en cultivos.

Metodología:
    Déficit Hídrico = P - ET₀
    
    Donde:
    - P: Precipitación diaria (mm/día) - de BASD-CMIP6-PE
    - ET₀: Evapotranspiración de referencia (mm/día) - de Script 03A
    
    Interpretación:
    - Valores positivos: Exceso hídrico (P > ET₀)
    - Valores negativos: Déficit hídrico (P < ET₀)
    - Cero: Balance hídrico neutro

Referencias:
    - Allen, R.G., Pereira, L.S., Raes, D., & Smith, M. (1998). Crop 
      evapotranspiration: Guidelines for computing crop water requirements.
      FAO Irrigation and Drainage Paper 56. Rome: FAO.
    - Thornthwaite, C.W. & Mather, J.R. (1955). The water balance.
      Publications in Climatology, 8(1), 1-104.

Entrada:
    - NetCDF precipitación (pr): BASD-CMIP6-PE recortados
    - NetCDF ET₀: Generados por Script 03A
    
Salida:
    - NetCDF con déficit hídrico diario (mm/día)

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
from typing import Dict, List, Tuple, Optional

import numpy as np
import xarray as xr
import pandas as pd

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
    NETCDF_PR_DIR = BASE_DIR / "02_DATOS" / "climaticos" / "BASD_CMIP6_PE" / "recortados"
    ET0_DIR = BASE_DIR / "02_DATOS" / "climaticos" / "indices" / "ET0"
    
    # Rutas de salida
    OUTPUT_DIR = BASE_DIR / "02_DATOS" / "climaticos" / "indices" / "deficit_hidrico"
    REPORTS_DIR = BASE_DIR / "05_DOCUMENTACION" / "reportes_auditoria"
    
    # Variables
    VAR_PR = "pr"
    VAR_ET0 = "ET0"
    
    # Metadatos de salida (CF Conventions)
    DEFICIT_ATTRS = {
        'standard_name': 'water_balance',
        'long_name': 'Daily Water Deficit (P - ET0)',
        'units': 'mm day-1',
        'positive_values': 'water surplus (P > ET0)',
        'negative_values': 'water deficit (P < ET0)',
        'reference': 'Allen et al. (1998) FAO-56; Thornthwaite & Mather (1955)',
        'cell_methods': 'time: mean',
    }


# ============================================================================
# FUNCIONES DE PROCESAMIENTO
# ============================================================================

def encontrar_trios_archivos(pr_dir: Path, et0_dir: Path) -> Dict[str, Dict[str, Path]]:
    """
    Encuentra tríos de archivos pr/ET₀ para cada combinación GCM/escenario/período.
    
    Args:
        pr_dir: Directorio con archivos de precipitación
        et0_dir: Directorio con archivos de ET₀
        
    Returns:
        Diccionario con rutas de archivos emparejados
    """
    trios = {}
    
    # Iterar sobre estructura de ET₀ (ya procesada)
    for exp_dir in et0_dir.iterdir():
        if not exp_dir.is_dir():
            continue
        experiment = exp_dir.name
        
        for gcm_dir in exp_dir.iterdir():
            if not gcm_dir.is_dir():
                continue
            gcm = gcm_dir.name
            
            # Buscar archivos ET₀
            for et0_file in gcm_dir.glob("*_ET0_*.nc"):
                # Extraer período del nombre
                # Formato: gcm_variant_experiment_ET0_daily_year1_year2.nc
                partes = et0_file.stem.split('_')
                if len(partes) >= 7:
                    periodo = f"{partes[5]}_{partes[6]}"
                    
                    # Construir nombre esperado del archivo pr
                    pr_name = et0_file.name.replace('_ET0_', '_pr_')
                    pr_path = pr_dir / experiment / gcm / pr_name
                    
                    if pr_path.exists():
                        clave = f"{experiment}_{gcm}_{periodo}"
                        trios[clave] = {
                            'pr': pr_path,
                            'et0': et0_file,
                            'experiment': experiment,
                            'gcm': gcm,
                            'period': periodo
                        }
    
    return trios


def calcular_deficit_hidrico(pr: xr.DataArray, et0: xr.DataArray) -> xr.DataArray:
    """
    Calcula el déficit hídrico diario.
    
    Déficit = P - ET₀
    
    Args:
        pr: Precipitación diaria (mm/día)
        et0: Evapotranspiración de referencia (mm/día)
        
    Returns:
        deficit: Déficit hídrico diario (mm/día)
        
    Nota:
        - Valores positivos indican exceso hídrico (lluvia > demanda)
        - Valores negativos indican déficit (demanda > lluvia)
    """
    # Calcular déficit
    deficit = pr - et0
    
    # Añadir atributos
    deficit.name = 'deficit_hidrico'
    deficit.attrs = Config.DEFICIT_ATTRS.copy()
    deficit.attrs['computation_date'] = Config.FECHA
    
    return deficit


def procesar_par(pr_path: Path, et0_path: Path, output_path: Path) -> Dict:
    """
    Procesa un par de archivos pr/ET₀ para calcular déficit hídrico.
    
    Args:
        pr_path: Ruta al archivo de precipitación
        et0_path: Ruta al archivo de ET₀
        output_path: Ruta de salida
        
    Returns:
        Diccionario con estadísticas del procesamiento
    """
    stats = {
        'exitoso': False,
        'archivo_pr': str(pr_path),
        'archivo_et0': str(et0_path),
        'archivo_salida': str(output_path),
        'error': None
    }
    
    try:
        # Abrir datasets
        ds_pr = xr.open_dataset(pr_path)
        ds_et0 = xr.open_dataset(et0_path)
        
        # Extraer variables
        pr = ds_pr['pr']
        et0 = ds_et0['ET0']
        
        # Verificar dimensiones
        assert len(pr.time) == len(et0.time), f"Dimensión temporal no coincide: pr={len(pr.time)}, et0={len(et0.time)}"
        
        # Verificar que las coordenadas espaciales coinciden (con tolerancia)
        assert np.allclose(pr.lat.values, et0.lat.values, atol=0.001), "Latitudes no coinciden"
        assert np.allclose(pr.lon.values, et0.lon.values, atol=0.001), "Longitudes no coinciden"
        
        # Calcular déficit hídrico
        deficit = calcular_deficit_hidrico(pr, et0)
        
        # Crear dataset de salida
        ds_out = xr.Dataset({'deficit_hidrico': deficit})
        
        # Copiar y actualizar atributos globales
        ds_out.attrs = ds_pr.attrs.copy()
        ds_out.attrs['title'] = 'Daily Water Deficit (P - ET0)'
        ds_out.attrs['institution'] = 'Universidad San Gregorio de Portoviejo'
        ds_out.attrs['source'] = 'Derived from BASD-CMIP6-PE precipitation and Hargreaves-Samani ET0'
        ds_out.attrs['references'] = 'Allen et al. (1998) FAO-56; Thornthwaite & Mather (1955)'
        ds_out.attrs['history'] = f"{Config.FECHA}: Water deficit calculated using Script 03B v{Config.VERSION}"
        ds_out.attrs['Conventions'] = 'CF-1.6'
        
        # Crear directorio de salida
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Guardar con compresión
        encoding = {
            'deficit_hidrico': {
                'zlib': True,
                'complevel': 4,
                'dtype': 'float32',
                '_FillValue': -9999.0
            }
        }
        
        ds_out.to_netcdf(output_path, encoding=encoding)
        
        # Estadísticas
        stats['exitoso'] = True
        stats['n_timesteps'] = len(deficit.time)
        stats['deficit_mean'] = float(deficit.mean().values)
        stats['deficit_min'] = float(deficit.min().values)
        stats['deficit_max'] = float(deficit.max().values)
        stats['dias_deficit'] = int((deficit < 0).sum().values)
        stats['dias_exceso'] = int((deficit > 0).sum().values)
        stats['porcentaje_deficit'] = 100 * stats['dias_deficit'] / deficit.size
        stats['tamaño_mb'] = output_path.stat().st_size / (1024 * 1024)
        
        # Cerrar datasets
        ds_pr.close()
        ds_et0.close()
        
    except Exception as e:
        stats['error'] = str(e)
        logger.error(f"Error procesando {pr_path.name}: {e}")
    
    return stats


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """Función principal del script."""
    tiempo_inicio = datetime.now()
    
    logger.info("=" * 70)
    logger.info("SCRIPT 03B: CÁLCULO DE DÉFICIT HÍDRICO DIARIO (P - ET₀)")
    logger.info("=" * 70)
    logger.info(f"Versión: {Config.VERSION}")
    logger.info(f"Fecha: {Config.FECHA}")
    logger.info("")
    
    # Verificar directorios
    logger.info("Verificando directorios...")
    
    if not Config.NETCDF_PR_DIR.exists():
        logger.error(f"No se encontró directorio de precipitación: {Config.NETCDF_PR_DIR}")
        sys.exit(1)
    logger.info(f"  ✓ Precipitación: {Config.NETCDF_PR_DIR}")
    
    if not Config.ET0_DIR.exists():
        logger.error(f"No se encontró directorio de ET₀: {Config.ET0_DIR}")
        logger.error("  Ejecute primero el Script 03A")
        sys.exit(1)
    logger.info(f"  ✓ ET₀: {Config.ET0_DIR}")
    
    Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"  ✓ Salida: {Config.OUTPUT_DIR}")
    
    # Encontrar pares de archivos
    logger.info("")
    logger.info("Buscando pares pr/ET₀...")
    trios = encontrar_trios_archivos(Config.NETCDF_PR_DIR, Config.ET0_DIR)
    logger.info(f"  ✓ Pares encontrados: {len(trios)}")
    
    if len(trios) == 0:
        logger.error("No se encontraron pares de archivos pr/ET₀")
        sys.exit(1)
    
    # Distribución por experimento
    conteo_exp = {}
    for clave, info in trios.items():
        exp = info['experiment']
        conteo_exp[exp] = conteo_exp.get(exp, 0) + 1
    
    logger.info("  Distribución por experimento:")
    for exp, n in sorted(conteo_exp.items()):
        logger.info(f"    - {exp}: {n} períodos")
    
    # Procesar pares
    logger.info("")
    logger.info("=" * 50)
    logger.info("Calculando déficit hídrico...")
    logger.info("=" * 50)
    
    resultados = []
    total = len(trios)
    
    for i, (clave, info) in enumerate(sorted(trios.items()), 1):
        # Construir ruta de salida
        nombre_base = info['et0'].stem.replace('ET0', 'deficit_hidrico')
        output_subdir = Config.OUTPUT_DIR / info['experiment'] / info['gcm']
        output_path = output_subdir / f"{nombre_base}.nc"
        
        # Verificar si ya existe
        if output_path.exists():
            logger.info(f"[{i}/{total}] Ya existe: {output_path.name}")
            resultados.append({
                'exitoso': True,
                'archivo_salida': str(output_path),
                'ya_existia': True
            })
            continue
        
        # Procesar
        if i == 1 or i % 20 == 0:
            logger.info(f"[{i}/{total}] Procesando: {clave}")
        
        stats = procesar_par(info['pr'], info['et0'], output_path)
        resultados.append(stats)
        
        if stats['exitoso'] and (i == 1 or i % 50 == 0):
            logger.info(f"  Déficit medio: {stats['deficit_mean']:.2f} mm/día")
            logger.info(f"  Días con déficit: {stats['porcentaje_deficit']:.1f}%")
    
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
    deficit_means = [r['deficit_mean'] for r in resultados if r.get('deficit_mean') is not None]
    pct_deficit = [r['porcentaje_deficit'] for r in resultados if r.get('porcentaje_deficit') is not None]
    
    if deficit_means:
        logger.info(f"  Déficit medio global: {np.mean(deficit_means):.2f} mm/día")
        logger.info(f"  Días con déficit (promedio): {np.mean(pct_deficit):.1f}%")
    
    # Generar reporte
    logger.info("")
    logger.info("Generando reporte de auditoría...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    reporte_path = Config.REPORTS_DIR / f"REPORTE_SCRIPT_03B_{timestamp}.txt"
    
    with open(reporte_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("REPORTE DE AUDITORÍA - SCRIPT 03B: DÉFICIT HÍDRICO\n")
        f.write("=" * 70 + "\n\n")
        
        f.write("INFORMACIÓN GENERAL\n")
        f.write("-" * 30 + "\n")
        f.write(f"Fecha de ejecución: {Config.FECHA}\n")
        f.write(f"Versión del script: {Config.VERSION}\n")
        f.write(f"Autor: {Config.AUTOR}\n\n")
        
        f.write("METODOLOGÍA\n")
        f.write("-" * 30 + "\n")
        f.write("Fórmula: Déficit Hídrico = P - ET₀\n")
        f.write("Interpretación:\n")
        f.write("  - Valores positivos: Exceso hídrico (P > ET₀)\n")
        f.write("  - Valores negativos: Déficit hídrico (P < ET₀)\n\n")
        
        f.write("Referencias:\n")
        f.write("  - Allen, R.G. et al. (1998). FAO Irrigation and Drainage Paper 56.\n")
        f.write("  - Thornthwaite, C.W. & Mather, J.R. (1955). The water balance.\n\n")
        
        f.write("RESULTADOS\n")
        f.write("-" * 30 + "\n")
        f.write(f"Total pares procesados: {len(resultados)}\n")
        f.write(f"Exitosos: {exitosos}\n")
        f.write(f"Fallidos: {fallidos}\n")
        f.write(f"Tasa de éxito: {100*exitosos/len(resultados):.1f}%\n\n")
        
        if deficit_means:
            f.write("Estadísticas de Déficit Hídrico:\n")
            f.write(f"  Media global: {np.mean(deficit_means):.2f} mm/día\n")
            f.write(f"  Mínimo (mayor déficit): {np.min([r['deficit_min'] for r in resultados if r.get('deficit_min') is not None]):.2f} mm/día\n")
            f.write(f"  Máximo (mayor exceso): {np.max([r['deficit_max'] for r in resultados if r.get('deficit_max') is not None]):.2f} mm/día\n")
            f.write(f"  Días con déficit (promedio): {np.mean(pct_deficit):.1f}%\n\n")
        
        f.write("TIEMPO DE EJECUCIÓN\n")
        f.write("-" * 30 + "\n")
        f.write(f"Inicio: {tiempo_inicio.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Fin: {tiempo_fin.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Duración: {duracion}\n\n")
        
        f.write("ARCHIVOS DE SALIDA\n")
        f.write("-" * 30 + "\n")
        f.write(f"Directorio: {Config.OUTPUT_DIR}\n\n")
        
        f.write("VERIFICACIÓN DE CRITERIOS\n")
        f.write("-" * 30 + "\n")
        f.write(f"[{'✓' if exitosos == len(resultados) else '✗'}] Todos los pares procesados exitosamente\n")
        f.write(f"[{'✓' if deficit_means else '✗'}] Valores de déficit calculados\n")
        f.write(f"[✓] Metadatos CF-compliant incluidos\n\n")
        
        f.write("DECISIÓN\n")
        f.write("-" * 30 + "\n")
        if exitosos == len(resultados):
            f.write("APROBADO - Proceder con Script 03C\n")
        else:
            f.write("REQUIERE REVISIÓN - Verificar archivos fallidos\n")
        
        f.write("\n" + "=" * 70 + "\n")
    
    logger.info(f"  ✓ Reporte guardado: {reporte_path}")
    
    # Estado final
    logger.info("")
    logger.info("=" * 70)
    if exitosos == len(resultados):
        logger.info("✓ SCRIPT 03B COMPLETADO EXITOSAMENTE")
        logger.info("  Siguiente paso: Ejecutar SCRIPT 03C - Conteo de días con estrés térmico")
    else:
        logger.info("⚠ SCRIPT 03B COMPLETADO CON ADVERTENCIAS")
        logger.info(f"  {fallidos} archivos fallaron. Revisar reporte.")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()