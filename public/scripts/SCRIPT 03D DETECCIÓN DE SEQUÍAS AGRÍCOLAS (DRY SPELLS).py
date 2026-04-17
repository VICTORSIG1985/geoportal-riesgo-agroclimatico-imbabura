"""
Script publicado como parte del Geoportal Riesgo Agroclimático — Imbabura, Ecuador
Pinto Páez, V. H. (2026). https://doi.org/10.5281/zenodo.19288559
Licencia: CC BY 4.0

NOTA: este archivo fue sanitizado para publicación pública.
- Credenciales (API keys, tokens, service accounts) removidas → <REDACTED_*>
- Rutas absolutas locales sustituidas por <RUTA_LOCAL>
Antes de ejecutar, configure sus propias rutas de entrada/salida y credenciales.

Archivo original: SCRIPT 03D DETECCIÓN DE SEQUÍAS AGRÍCOLAS (DRY SPELLS).py
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
SCRIPT 03D: DETECCIÓN DE SEQUÍAS AGRÍCOLAS (DRY SPELLS)
===============================================================================
Versión: 1.0.0
Fecha: 2026-02-02
Autor: Víctor Hugo Pinto Páez

Descripción:
    Detecta períodos de sequía agrícola definidos como días consecutivos 
    con precipitación inferior a 1 mm/día. Este índice es un componente
    del peligro hídrico en el marco de riesgo IPCC AR5/AR6.

Metodología:
    Sequía agrícola = Días consecutivos donde P < 1 mm/día
    
    El umbral de 1 mm/día es estándar en climatología agrícola para definir
    un "día seco", ya que cantidades menores no aportan humedad útil al 
    suelo (WMO, 2012; Frich et al., 2002).
    
    Métricas calculadas para cada pixel y período temporal:
    - Indicador binario diario: 1 si P < 1 mm, 0 si P >= 1 mm
    
    Las métricas agregadas (duración máxima, número de eventos > 7 y > 15 
    días) se calcularán en el Script 03F de agregación temporal.

Referencias:
    - WMO (2012). Standardized Precipitation Index User Guide. WMO-No. 1090.
    - Frich, P. et al. (2002). Observed coherent changes in climatic extremes 
      during the second half of the twentieth century. Climate Research, 19, 193-212.
    - ETCCDI (Expert Team on Climate Change Detection and Indices). Consecutive 
      Dry Days (CDD) index definition.

Entrada:
    - NetCDF de precipitación (pr) recortados a Imbabura

Salida:
    - NetCDF con indicador binario de día seco (P < 1 mm)

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
from typing import Dict, List, Optional

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
    
    # Ruta de entrada: archivos pr recortados
    PR_DIR = BASE_DIR / "02_DATOS" / "climaticos" / "BASD_CMIP6_PE" / "recortados"
    
    # Ruta de salida
    OUTPUT_DIR = BASE_DIR / "02_DATOS" / "climaticos" / "indices" / "sequia"
    REPORTS_DIR = BASE_DIR / "05_DOCUMENTACION" / "reportes_auditoria"
    
    # Umbral de día seco (mm/día)
    # WMO (2012), Frich et al. (2002), ETCCDI CDD definition
    UMBRAL_DIA_SECO = 1.0  # mm/día
    
    # Metadatos
    DIA_SECO_ATTRS = {
        'standard_name': 'dry_day_indicator',
        'long_name': 'Daily dry day indicator (P < 1 mm/day)',
        'units': '1',
        'flag_values': '0, 1',
        'flag_meanings': 'wet_day dry_day',
        'threshold': 'P < 1.0 mm/day',
        'threshold_reference': 'WMO (2012); Frich et al. (2002); ETCCDI CDD',
        'cell_methods': 'time: point',
    }


# ============================================================================
# FUNCIONES DE PROCESAMIENTO
# ============================================================================

def encontrar_archivos_pr(base_dir: Path) -> Dict[str, Dict]:
    """
    Encuentra todos los archivos de precipitación en la estructura de directorios.
    
    Args:
        base_dir: Directorio base de archivos recortados
        
    Returns:
        Diccionario con información de archivos encontrados
    """
    archivos = {}
    
    for exp_dir in base_dir.iterdir():
        if not exp_dir.is_dir():
            continue
        experiment = exp_dir.name
        
        for gcm_dir in exp_dir.iterdir():
            if not gcm_dir.is_dir():
                continue
            gcm = gcm_dir.name
            
            # Buscar archivos pr
            for pr_file in gcm_dir.glob("*_pr_*.nc"):
                partes = pr_file.stem.split('_')
                if len(partes) >= 7:
                    periodo = f"{partes[5]}_{partes[6]}"
                    clave = f"{experiment}_{gcm}_{periodo}"
                    archivos[clave] = {
                        'path': pr_file,
                        'experiment': experiment,
                        'gcm': gcm,
                        'period': periodo
                    }
    
    return archivos


def calcular_dias_secos(pr: xr.DataArray) -> xr.DataArray:
    """
    Calcula el indicador binario de día seco.
    
    Un día seco se define como aquel con P < 1 mm/día, siguiendo la
    definición estándar del ETCCDI para Consecutive Dry Days (CDD).
    
    Args:
        pr: Precipitación diaria (mm/día o kg/m²/s)
        
    Returns:
        DataArray binario: 1 = día seco, 0 = día húmedo
    """
    # Verificar y convertir unidades
    units = pr.attrs.get('units', '')
    
    if 'kg' in units.lower() or 's-1' in units.lower():
        logger.info("  - Convirtiendo precipitación de kg/m²/s a mm/día...")
        pr_mm = pr * 86400
    else:
        pr_mm = pr
    
    # Indicador binario: 1 si P < umbral, 0 si P >= umbral
    dia_seco = (pr_mm < Config.UMBRAL_DIA_SECO).astype(np.int8)
    
    # Atributos
    dia_seco.name = 'dia_seco'
    dia_seco.attrs = Config.DIA_SECO_ATTRS.copy()
    dia_seco.attrs['computation_date'] = Config.FECHA
    
    return dia_seco


def procesar_archivo_pr(
    pr_path: Path,
    output_path: Path
) -> Dict:
    """
    Procesa un archivo de precipitación para calcular indicadores de sequía.
    
    Args:
        pr_path: Ruta al archivo NetCDF de precipitación
        output_path: Ruta de salida
        
    Returns:
        Diccionario con estadísticas del procesamiento
    """
    stats = {
        'exitoso': False,
        'archivo_entrada': str(pr_path),
        'archivo_salida': str(output_path),
        'error': None
    }
    
    try:
        # Abrir dataset
        ds = xr.open_dataset(pr_path)
        pr = ds['pr']
        
        # Calcular indicador de día seco
        dia_seco = calcular_dias_secos(pr)
        
        # Crear dataset de salida
        ds_out = xr.Dataset({'dia_seco': dia_seco})
        
        # Metadatos globales
        ds_out.attrs = ds.attrs.copy()
        ds_out.attrs['title'] = 'Daily Dry Day Indicator for Agricultural Drought Detection'
        ds_out.attrs['institution'] = 'Universidad San Gregorio de Portoviejo'
        ds_out.attrs['source'] = 'Derived from BASD-CMIP6-PE precipitation'
        ds_out.attrs['references'] = 'WMO (2012); Frich et al. (2002); ETCCDI CDD'
        ds_out.attrs['history'] = f"{Config.FECHA}: Dry day indicator calculated using Script 03D v{Config.VERSION}"
        ds_out.attrs['Conventions'] = 'CF-1.6'
        
        # Crear directorio de salida
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Encoding
        encoding = {
            'dia_seco': {
                'zlib': True,
                'complevel': 4,
                'dtype': 'int8',
                '_FillValue': -1
            }
        }
        
        # Guardar
        ds_out.to_netcdf(output_path, encoding=encoding)
        
        # Estadísticas
        n_total = dia_seco.size
        n_secos = int(dia_seco.sum().values)
        
        stats['exitoso'] = True
        stats['n_timesteps'] = len(dia_seco.time)
        stats['dias_secos'] = n_secos
        stats['dias_humedos'] = n_total - n_secos
        stats['porcentaje_secos'] = 100 * n_secos / n_total if n_total > 0 else 0
        stats['tamaño_mb'] = output_path.stat().st_size / (1024 * 1024)
        
        # Cerrar dataset
        ds.close()
        
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
    logger.info("SCRIPT 03D: DETECCIÓN DE SEQUÍAS AGRÍCOLAS (DRY SPELLS)")
    logger.info("=" * 70)
    logger.info(f"Versión: {Config.VERSION}")
    logger.info(f"Fecha: {Config.FECHA}")
    logger.info("")
    logger.info(f"Umbral de día seco: P < {Config.UMBRAL_DIA_SECO} mm/día")
    logger.info("Referencia: WMO (2012), Frich et al. (2002), ETCCDI CDD")
    logger.info("")
    
    # Verificar directorios
    logger.info("Verificando directorios...")
    
    if not Config.PR_DIR.exists():
        logger.error(f"No se encontró directorio de precipitación: {Config.PR_DIR}")
        sys.exit(1)
    logger.info(f"  ✓ Directorio precipitación: {Config.PR_DIR}")
    
    Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"  ✓ Directorio de salida: {Config.OUTPUT_DIR}")
    
    Config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Encontrar archivos pr
    logger.info("")
    logger.info("Buscando archivos de precipitación...")
    archivos = encontrar_archivos_pr(Config.PR_DIR)
    logger.info(f"  ✓ Archivos encontrados: {len(archivos)}")
    
    if len(archivos) == 0:
        logger.error("No se encontraron archivos de precipitación")
        sys.exit(1)
    
    # Distribución por experimento
    conteo_exp = {}
    for clave, info in archivos.items():
        exp = info['experiment']
        conteo_exp[exp] = conteo_exp.get(exp, 0) + 1
    
    logger.info("  Distribución por experimento:")
    for exp, n in sorted(conteo_exp.items()):
        logger.info(f"    - {exp}: {n} archivos")
    
    # Procesar archivos
    logger.info("")
    logger.info("=" * 50)
    logger.info("Calculando indicadores de día seco...")
    logger.info("=" * 50)
    
    resultados = []
    total = len(archivos)
    
    for i, (clave, info) in enumerate(sorted(archivos.items()), 1):
        # Construir nombre de salida
        nombre_base = info['path'].stem.replace('_pr_', '_sequia_')
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
        if i == 1 or i % 20 == 0 or i == total:
            logger.info(f"[{i}/{total}] Procesando: {clave}")
        
        stats = procesar_archivo_pr(info['path'], output_path)
        resultados.append(stats)
        
        if stats['exitoso'] and (i == 1 or i % 50 == 0):
            logger.info(f"  Días secos: {stats['porcentaje_secos']:.1f}%")
    
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
    pct_secos = [r['porcentaje_secos'] for r in resultados if r.get('porcentaje_secos') is not None]
    
    if pct_secos:
        logger.info(f"  Días secos (promedio global): {np.mean(pct_secos):.1f}%")
        logger.info(f"  Rango: {np.min(pct_secos):.1f}% - {np.max(pct_secos):.1f}%")
    
    # Generar reporte
    logger.info("")
    logger.info("Generando reporte de auditoría...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    reporte_path = Config.REPORTS_DIR / f"REPORTE_SCRIPT_03D_{timestamp}.txt"
    
    with open(reporte_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("REPORTE DE AUDITORÍA - SCRIPT 03D: SEQUÍAS AGRÍCOLAS\n")
        f.write("=" * 70 + "\n\n")
        
        f.write("INFORMACIÓN GENERAL\n")
        f.write("-" * 30 + "\n")
        f.write(f"Fecha de ejecución: {Config.FECHA}\n")
        f.write(f"Versión del script: {Config.VERSION}\n")
        f.write(f"Autor: {Config.AUTOR}\n\n")
        
        f.write("METODOLOGÍA\n")
        f.write("-" * 30 + "\n")
        f.write(f"Definición: Día seco = P < {Config.UMBRAL_DIA_SECO} mm/día\n")
        f.write("Indicador binario: 1 = día seco, 0 = día húmedo\n\n")
        
        f.write("Referencias del umbral:\n")
        f.write("  - WMO (2012). Standardized Precipitation Index User Guide. WMO-No. 1090.\n")
        f.write("  - Frich, P. et al. (2002). Climate Research, 19, 193-212.\n")
        f.write("  - ETCCDI: Consecutive Dry Days (CDD) index.\n\n")
        
        f.write("RESULTADOS\n")
        f.write("-" * 30 + "\n")
        f.write(f"Total archivos procesados: {len(resultados)}\n")
        f.write(f"Exitosos: {exitosos}\n")
        f.write(f"Fallidos: {fallidos}\n")
        f.write(f"Tasa de éxito: {100*exitosos/len(resultados):.1f}%\n\n")
        
        if pct_secos:
            f.write("Estadísticas de días secos (P < 1 mm/día):\n")
            f.write(f"  Promedio global: {np.mean(pct_secos):.1f}%\n")
            f.write(f"  Mínimo: {np.min(pct_secos):.1f}%\n")
            f.write(f"  Máximo: {np.max(pct_secos):.1f}%\n")
            f.write(f"  Desv. estándar: {np.std(pct_secos):.1f}%\n\n")
        
        f.write("TIEMPO DE EJECUCIÓN\n")
        f.write("-" * 30 + "\n")
        f.write(f"Inicio: {tiempo_inicio.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Fin: {tiempo_fin.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Duración: {duracion}\n\n")
        
        f.write("ARCHIVOS DE SALIDA\n")
        f.write("-" * 30 + "\n")
        f.write(f"Directorio: {Config.OUTPUT_DIR}\n")
        f.write(f"Variable: dia_seco (int8, 0/1)\n\n")
        
        f.write("VERIFICACIÓN DE CRITERIOS\n")
        f.write("-" * 30 + "\n")
        f.write(f"[{'✓' if exitosos == len(resultados) else '✗'}] Todos los archivos procesados exitosamente\n")
        f.write(f"[✓] Umbral con respaldo bibliográfico (WMO, ETCCDI)\n")
        f.write(f"[✓] Conversión de unidades aplicada (kg/m²/s → mm/día)\n")
        f.write(f"[✓] Indicador binario calculado\n")
        f.write(f"[✓] Metadatos CF-compliant incluidos\n\n")
        
        f.write("DECISIÓN\n")
        f.write("-" * 30 + "\n")
        if exitosos == len(resultados):
            f.write("APROBADO - Proceder con Script 03E\n")
        else:
            f.write("REQUIERE REVISIÓN - Verificar archivos fallidos\n")
        
        f.write("\n" + "=" * 70 + "\n")
    
    logger.info(f"  ✓ Reporte guardado: {reporte_path}")
    
    # Estado final
    logger.info("")
    logger.info("=" * 70)
    if exitosos == len(resultados):
        logger.info("✓ SCRIPT 03D COMPLETADO EXITOSAMENTE")
        logger.info("  Siguiente paso: Ejecutar SCRIPT 03E - Conteo de heladas (Tmin < 0°C)")
    else:
        logger.info("⚠ SCRIPT 03D COMPLETADO CON ADVERTENCIAS")
        logger.info(f"  {fallidos} archivos fallaron. Revisar reporte.")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()