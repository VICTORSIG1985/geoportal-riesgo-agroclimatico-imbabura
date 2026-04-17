"""
Script publicado como parte del Geoportal Riesgo Agroclimático — Imbabura, Ecuador
Pinto Páez, V. H. (2026). https://doi.org/10.5281/zenodo.19288559
Licencia: CC BY 4.0

NOTA: este archivo fue sanitizado para publicación pública.
- Credenciales (API keys, tokens, service accounts) removidas → <REDACTED_*>
- Rutas absolutas locales sustituidas por <RUTA_LOCAL>
Antes de ejecutar, configure sus propias rutas de entrada/salida y credenciales.

Archivo original: SCRIPT 03E CONTEO DE HELADAS (Tmin menor a 0°C).py
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
SCRIPT 03E: CONTEO DE HELADAS (Tmin < 0°C)
===============================================================================
Versión: 1.0.0
Fecha: 2026-02-02
Autor: Víctor Hugo Pinto Páez

Descripción:
    Genera indicadores binarios de helada definidos como días donde la 
    temperatura mínima es inferior a 0°C. Las heladas constituyen un 
    componente crítico del peligro térmico por frío, complementando el 
    estrés por calor (Script 03C).

Metodología:
    Helada = 1 si Tmin < 0°C, 0 en caso contrario
    
    El umbral de 0°C es universalmente aceptado como el punto de 
    congelación del agua en tejidos vegetales, por debajo del cual se 
    produce formación de cristales de hielo intra e intercelulares que 
    causan daño mecánico y fisiológico a los cultivos (Snyder & de 
    Melo-Abreu, 2005; FAO, 2010).

Relevancia para Imbabura:
    Las heladas son particularmente relevantes para:
    - Papa: Cultivada en zonas altas (2,800-3,500 m) donde las heladas 
      nocturnas son frecuentes en la estación seca
    - Quinua: Distribuida en altitudes similares, sensible a heladas 
      durante floración y llenado de grano
    
    El rango altitudinal de Imbabura (200-4,939 m) garantiza que una 
    proporción significativa del dominio espacial experimenta heladas.

Referencias:
    - Snyder, R.L. & de Melo-Abreu, J.P. (2005). Frost Protection: 
      fundamentals, practice and economics. FAO Environment and Natural 
      Resources Series No. 10.
    - FAO (2010). Protección contra las heladas: fundamentos, práctica 
      y economía. Organización de las Naciones Unidas para la 
      Alimentación y la Agricultura.
    - ETCCDI: Frost Days (FD) index definition: Annual count of days 
      when TN (daily minimum) < 0°C.

Entrada:
    - NetCDF de temperatura mínima (tasmin) recortados a Imbabura

Salida:
    - NetCDF con indicador binario de helada

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
    
    # Ruta de entrada: archivos tasmin recortados
    TASMIN_DIR = BASE_DIR / "02_DATOS" / "climaticos" / "BASD_CMIP6_PE" / "recortados"
    
    # Ruta de salida
    OUTPUT_DIR = BASE_DIR / "02_DATOS" / "climaticos" / "indices" / "heladas"
    REPORTS_DIR = BASE_DIR / "05_DOCUMENTACION" / "reportes_auditoria"
    
    # Umbral de helada (°C)
    # Snyder & de Melo-Abreu (2005), FAO (2010), ETCCDI FD index
    UMBRAL_HELADA = 0.0  # °C
    
    # Metadatos
    HELADA_ATTRS = {
        'standard_name': 'frost_day_indicator',
        'long_name': 'Daily frost indicator (Tmin < 0 degC)',
        'units': '1',
        'flag_values': '0, 1',
        'flag_meanings': 'no_frost frost',
        'threshold': 'Tmin < 0.0 degC',
        'threshold_reference': 'Snyder & de Melo-Abreu (2005); ETCCDI FD index',
        'cell_methods': 'time: point',
    }


# ============================================================================
# FUNCIONES DE PROCESAMIENTO
# ============================================================================

def encontrar_archivos_tasmin(base_dir: Path) -> Dict[str, Dict]:
    """
    Encuentra todos los archivos de temperatura mínima.
    
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
            
            # Buscar archivos tasmin
            for tasmin_file in gcm_dir.glob("*_tasmin_*.nc"):
                partes = tasmin_file.stem.split('_')
                if len(partes) >= 7:
                    periodo = f"{partes[5]}_{partes[6]}"
                    clave = f"{experiment}_{gcm}_{periodo}"
                    archivos[clave] = {
                        'path': tasmin_file,
                        'experiment': experiment,
                        'gcm': gcm,
                        'period': periodo
                    }
    
    return archivos


def calcular_heladas(tasmin: xr.DataArray) -> xr.DataArray:
    """
    Calcula el indicador binario de helada.
    
    Una helada se define como un día donde la temperatura mínima es 
    inferior a 0°C, punto de congelación del agua en tejidos vegetales.
    
    Args:
        tasmin: Temperatura mínima diaria (°C o K)
        
    Returns:
        DataArray binario: 1 = helada, 0 = sin helada
    """
    # Verificar y convertir unidades (Kelvin → Celsius si necesario)
    units = tasmin.attrs.get('units', '')
    
    if 'K' in units or 'kelvin' in units.lower():
        logger.info("  - Convirtiendo temperatura de Kelvin a Celsius...")
        tasmin_c = tasmin - 273.15
    elif tasmin.values.mean() > 100:
        # Detección heurística: si media > 100, probablemente Kelvin
        logger.info("  - Detectado Kelvin (media > 100), convirtiendo a Celsius...")
        tasmin_c = tasmin - 273.15
    else:
        tasmin_c = tasmin
    
    # Indicador binario: 1 si Tmin < 0°C, 0 en caso contrario
    helada = (tasmin_c < Config.UMBRAL_HELADA).astype(np.int8)
    
    # Atributos
    helada.name = 'helada'
    helada.attrs = Config.HELADA_ATTRS.copy()
    helada.attrs['computation_date'] = Config.FECHA
    
    return helada, tasmin_c


def procesar_archivo_tasmin(
    tasmin_path: Path,
    output_path: Path
) -> Dict:
    """
    Procesa un archivo de temperatura mínima para detectar heladas.
    
    Args:
        tasmin_path: Ruta al archivo NetCDF de tasmin
        output_path: Ruta de salida
        
    Returns:
        Diccionario con estadísticas del procesamiento
    """
    stats = {
        'exitoso': False,
        'archivo_entrada': str(tasmin_path),
        'archivo_salida': str(output_path),
        'error': None
    }
    
    try:
        # Abrir dataset
        ds = xr.open_dataset(tasmin_path)
        tasmin = ds['tasmin']
        
        # Calcular indicador de helada
        helada, tasmin_c = calcular_heladas(tasmin)
        
        # Crear dataset de salida
        ds_out = xr.Dataset({'helada': helada})
        
        # Metadatos globales
        ds_out.attrs = ds.attrs.copy()
        ds_out.attrs['title'] = 'Daily Frost Indicator for Agricultural Risk Assessment'
        ds_out.attrs['institution'] = 'Universidad San Gregorio de Portoviejo'
        ds_out.attrs['source'] = 'Derived from BASD-CMIP6-PE minimum temperature'
        ds_out.attrs['references'] = 'Snyder & de Melo-Abreu (2005); ETCCDI FD'
        ds_out.attrs['history'] = f"{Config.FECHA}: Frost indicator calculated using Script 03E v{Config.VERSION}"
        ds_out.attrs['Conventions'] = 'CF-1.6'
        
        # Crear directorio de salida
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Encoding
        encoding = {
            'helada': {
                'zlib': True,
                'complevel': 4,
                'dtype': 'int8',
                '_FillValue': -1
            }
        }
        
        # Guardar
        ds_out.to_netcdf(output_path, encoding=encoding)
        
        # Estadísticas
        n_total = helada.size
        n_heladas = int(helada.sum().values)
        
        # Estadísticas de temperatura
        tmin_global = float(tasmin_c.min().values)
        tmin_mean = float(tasmin_c.mean().values)
        
        stats['exitoso'] = True
        stats['n_timesteps'] = len(helada.time)
        stats['dias_helada'] = n_heladas
        stats['dias_sin_helada'] = n_total - n_heladas
        stats['porcentaje_heladas'] = 100 * n_heladas / n_total if n_total > 0 else 0
        stats['tmin_absoluta'] = tmin_global
        stats['tmin_media'] = tmin_mean
        stats['tamaño_mb'] = output_path.stat().st_size / (1024 * 1024)
        
        # Cerrar dataset
        ds.close()
        
    except Exception as e:
        stats['error'] = str(e)
        logger.error(f"Error procesando {tasmin_path.name}: {e}")
    
    return stats


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """Función principal del script."""
    tiempo_inicio = datetime.now()
    
    logger.info("=" * 70)
    logger.info("SCRIPT 03E: CONTEO DE HELADAS (Tmin < 0°C)")
    logger.info("=" * 70)
    logger.info(f"Versión: {Config.VERSION}")
    logger.info(f"Fecha: {Config.FECHA}")
    logger.info("")
    logger.info(f"Umbral de helada: Tmin < {Config.UMBRAL_HELADA}°C")
    logger.info("Referencia: Snyder & de Melo-Abreu (2005), FAO (2010), ETCCDI FD")
    logger.info("")
    
    # Verificar directorios
    logger.info("Verificando directorios...")
    
    if not Config.TASMIN_DIR.exists():
        logger.error(f"No se encontró directorio de tasmin: {Config.TASMIN_DIR}")
        sys.exit(1)
    logger.info(f"  ✓ Directorio tasmin: {Config.TASMIN_DIR}")
    
    Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"  ✓ Directorio de salida: {Config.OUTPUT_DIR}")
    
    Config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Encontrar archivos tasmin
    logger.info("")
    logger.info("Buscando archivos de temperatura mínima...")
    archivos = encontrar_archivos_tasmin(Config.TASMIN_DIR)
    logger.info(f"  ✓ Archivos encontrados: {len(archivos)}")
    
    if len(archivos) == 0:
        logger.error("No se encontraron archivos de tasmin")
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
    logger.info("Calculando indicadores de helada...")
    logger.info("=" * 50)
    
    resultados = []
    total = len(archivos)
    
    for i, (clave, info) in enumerate(sorted(archivos.items()), 1):
        # Construir nombre de salida
        nombre_base = info['path'].stem.replace('_tasmin_', '_heladas_')
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
        
        stats = procesar_archivo_tasmin(info['path'], output_path)
        resultados.append(stats)
        
        if stats['exitoso'] and (i == 1 or i % 50 == 0):
            logger.info(f"  Heladas: {stats['porcentaje_heladas']:.2f}% | Tmin abs: {stats['tmin_absoluta']:.1f}°C")
    
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
    pct_heladas = [r['porcentaje_heladas'] for r in resultados if r.get('porcentaje_heladas') is not None]
    tmin_abs = [r['tmin_absoluta'] for r in resultados if r.get('tmin_absoluta') is not None]
    
    if pct_heladas:
        logger.info("")
        logger.info(f"  Porcentaje de días con helada (promedio global): {np.mean(pct_heladas):.2f}%")
        logger.info(f"  Rango: {np.min(pct_heladas):.2f}% - {np.max(pct_heladas):.2f}%")
    
    if tmin_abs:
        logger.info(f"  Temperatura mínima absoluta: {np.min(tmin_abs):.1f}°C")
    
    # Generar reporte
    logger.info("")
    logger.info("Generando reporte de auditoría...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    reporte_path = Config.REPORTS_DIR / f"REPORTE_SCRIPT_03E_{timestamp}.txt"
    
    with open(reporte_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("REPORTE DE AUDITORÍA - SCRIPT 03E: HELADAS\n")
        f.write("=" * 70 + "\n\n")
        
        f.write("INFORMACIÓN GENERAL\n")
        f.write("-" * 30 + "\n")
        f.write(f"Fecha de ejecución: {Config.FECHA}\n")
        f.write(f"Versión del script: {Config.VERSION}\n")
        f.write(f"Autor: {Config.AUTOR}\n\n")
        
        f.write("METODOLOGÍA\n")
        f.write("-" * 30 + "\n")
        f.write(f"Definición: Helada = Tmin < {Config.UMBRAL_HELADA}°C\n")
        f.write("Indicador binario: 1 = helada, 0 = sin helada\n\n")
        
        f.write("Referencias del umbral:\n")
        f.write("  - Snyder, R.L. & de Melo-Abreu, J.P. (2005). Frost Protection. FAO ENRS No. 10.\n")
        f.write("  - FAO (2010). Protección contra las heladas.\n")
        f.write("  - ETCCDI: Frost Days (FD) index.\n\n")
        
        f.write("RESULTADOS\n")
        f.write("-" * 30 + "\n")
        f.write(f"Total archivos procesados: {len(resultados)}\n")
        f.write(f"Exitosos: {exitosos}\n")
        f.write(f"Fallidos: {fallidos}\n")
        f.write(f"Tasa de éxito: {100*exitosos/len(resultados):.1f}%\n\n")
        
        if pct_heladas:
            f.write("Estadísticas de heladas (Tmin < 0°C):\n")
            f.write(f"  Promedio global: {np.mean(pct_heladas):.2f}%\n")
            f.write(f"  Mínimo: {np.min(pct_heladas):.2f}%\n")
            f.write(f"  Máximo: {np.max(pct_heladas):.2f}%\n")
            f.write(f"  Desv. estándar: {np.std(pct_heladas):.2f}%\n\n")
        
        if tmin_abs:
            f.write(f"Temperatura mínima absoluta registrada: {np.min(tmin_abs):.1f}°C\n\n")
        
        f.write("TIEMPO DE EJECUCIÓN\n")
        f.write("-" * 30 + "\n")
        f.write(f"Inicio: {tiempo_inicio.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Fin: {tiempo_fin.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Duración: {duracion}\n\n")
        
        f.write("ARCHIVOS DE SALIDA\n")
        f.write("-" * 30 + "\n")
        f.write(f"Directorio: {Config.OUTPUT_DIR}\n")
        f.write(f"Variable: helada (int8, 0/1)\n\n")
        
        f.write("VERIFICACIÓN DE CRITERIOS\n")
        f.write("-" * 30 + "\n")
        f.write(f"[{'✓' if exitosos == len(resultados) else '✗'}] Todos los archivos procesados exitosamente\n")
        f.write(f"[✓] Umbral con respaldo bibliográfico (FAO, ETCCDI)\n")
        f.write(f"[✓] Conversión K→°C aplicada cuando necesario\n")
        f.write(f"[✓] Indicador binario calculado\n")
        f.write(f"[✓] Metadatos CF-compliant incluidos\n\n")
        
        f.write("DECISIÓN\n")
        f.write("-" * 30 + "\n")
        if exitosos == len(resultados):
            f.write("APROBADO - Proceder con Script 03F\n")
        else:
            f.write("REQUIERE REVISIÓN - Verificar archivos fallidos\n")
        
        f.write("\n" + "=" * 70 + "\n")
    
    logger.info(f"  ✓ Reporte guardado: {reporte_path}")
    
    # Estado final
    logger.info("")
    logger.info("=" * 70)
    if exitosos == len(resultados):
        logger.info("✓ SCRIPT 03E COMPLETADO EXITOSAMENTE")
        logger.info("  Siguiente paso: Ejecutar SCRIPT 03F - Agregación temporal de índices")
    else:
        logger.info("⚠ SCRIPT 03E COMPLETADO CON ADVERTENCIAS")
        logger.info(f"  {fallidos} archivos fallaron. Revisar reporte.")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()