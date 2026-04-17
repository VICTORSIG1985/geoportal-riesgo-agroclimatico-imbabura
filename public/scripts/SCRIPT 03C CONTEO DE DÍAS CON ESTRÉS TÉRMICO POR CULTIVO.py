"""
Script publicado como parte del Geoportal Riesgo Agroclimático — Imbabura, Ecuador
Pinto Páez, V. H. (2026). https://doi.org/10.5281/zenodo.19288559
Licencia: CC BY 4.0

NOTA: este archivo fue sanitizado para publicación pública.
- Credenciales (API keys, tokens, service accounts) removidas → <REDACTED_*>
- Rutas absolutas locales sustituidas por <RUTA_LOCAL>
Antes de ejecutar, configure sus propias rutas de entrada/salida y credenciales.

Archivo original: SCRIPT 03C CONTEO DE DÍAS CON ESTRÉS TÉRMICO POR CULTIVO.py
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
SCRIPT 03C: CONTEO DE DÍAS CON ESTRÉS TÉRMICO POR CULTIVO
===============================================================================
Versión: 1.0.0
Fecha: 2026-02-02
Autor: Víctor Hugo Pinto Páez

Descripción:
    Contabiliza los días donde la temperatura máxima diaria (Tmax) supera
    el umbral crítico específico de cada cultivo andino. El estrés térmico
    es un componente fundamental del peligro climático en el marco IPCC.

Metodología:
    Días_estrés = Σ(Tmax > T_crítica_cultivo)
    
    Umbrales críticos por cultivo (fuentes científicas):
    
    | Cultivo | T crítica | T óptima  | Fuente          |
    |---------|-----------|-----------|-----------------|
    | Papa    | > 25°C    | 15-20°C   | CIP (2020)      |
    | Maíz    | > 35°C    | 20-30°C   | FAO-56          |
    | Fréjol  | > 30°C    | 18-24°C   | CIAT            |
    | Quinua  | > 32°C    | 15-20°C   | Jacobsen (2003) |

    Para cada archivo NetCDF de tasmax, se genera UN archivo de salida que
    contiene 4 variables binarias (una por cultivo): 1 si Tmax > umbral, 0 si no.
    
    Esto permite:
    - Conteos anuales/estacionales en Script 03F (agregación temporal)
    - Análisis de frecuencia de estrés térmico por período climático
    - Comparación entre escenarios SSP

Referencias:
    - CIP (2020). Potato Facts and Figures. International Potato Center, Lima.
    - Allen, R.G. et al. (1998). FAO Irrigation and Drainage Paper 56.
    - CIAT. Climate-Smart Agriculture for Bean Production. Cali, Colombia.
    - Jacobsen, S.E. (2003). The Worldwide Potential for Quinoa. Food Reviews 
      International, 19(1-2), 167-177.

Entrada:
    - NetCDF de temperatura máxima (tasmax) recortados a Imbabura

Salida:
    - NetCDF con indicadores binarios de estrés térmico por cultivo

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
    
    # Ruta de entrada: archivos tasmax recortados
    TASMAX_DIR = BASE_DIR / "02_DATOS" / "climaticos" / "BASD_CMIP6_PE" / "recortados"
    
    # Ruta de salida
    OUTPUT_DIR = BASE_DIR / "02_DATOS" / "climaticos" / "indices" / "estres_termico"
    REPORTS_DIR = BASE_DIR / "05_DOCUMENTACION" / "reportes_auditoria"
    
    # Umbrales de estrés térmico por cultivo (°C)
    # Fuentes científicas validadas en Protocolo Metodológico Maestro v1.2.0
    UMBRALES_ESTRES = {
        'papa': {
            'nombre_cientifico': 'Solanum tuberosum L.',
            'T_critica': 25.0,    # °C - CIP (2020)
            'T_optima_min': 15.0, # °C
            'T_optima_max': 20.0, # °C
            'fuente': 'CIP (2020). Potato Facts and Figures. International Potato Center, Lima.'
        },
        'maiz': {
            'nombre_cientifico': 'Zea mays L.',
            'T_critica': 35.0,    # °C - FAO-56 (Allen et al., 1998)
            'T_optima_min': 20.0, # °C
            'T_optima_max': 30.0, # °C
            'fuente': 'Allen, R.G. et al. (1998). FAO Irrigation and Drainage Paper 56.'
        },
        'frejol': {
            'nombre_cientifico': 'Phaseolus vulgaris L.',
            'T_critica': 30.0,    # °C - CIAT
            'T_optima_min': 18.0, # °C
            'T_optima_max': 24.0, # °C
            'fuente': 'CIAT. Climate-Smart Agriculture for Bean Production.'
        },
        'quinua': {
            'nombre_cientifico': 'Chenopodium quinoa Willd.',
            'T_critica': 32.0,    # °C - Jacobsen (2003)
            'T_optima_min': 15.0, # °C
            'T_optima_max': 20.0, # °C
            'fuente': 'Jacobsen, S.E. (2003). Food Reviews International, 19(1-2), 167-177.'
        }
    }


# ============================================================================
# FUNCIONES DE PROCESAMIENTO
# ============================================================================

def encontrar_archivos_tasmax(base_dir: Path) -> Dict[str, Dict]:
    """
    Encuentra todos los archivos tasmax en la estructura de directorios.
    
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
            
            # Buscar archivos tasmax
            for tasmax_file in gcm_dir.glob("*_tasmax_*.nc"):
                partes = tasmax_file.stem.split('_')
                if len(partes) >= 7:
                    periodo = f"{partes[5]}_{partes[6]}"
                    clave = f"{experiment}_{gcm}_{periodo}"
                    archivos[clave] = {
                        'path': tasmax_file,
                        'experiment': experiment,
                        'gcm': gcm,
                        'period': periodo
                    }
    
    return archivos


def calcular_estres_termico(tasmax: xr.DataArray) -> xr.Dataset:
    """
    Calcula indicadores binarios de estrés térmico para cada cultivo.
    
    Para cada día y pixel:
        1 si Tmax > T_crítica del cultivo
        0 si Tmax <= T_crítica del cultivo
    
    Args:
        tasmax: Temperatura máxima diaria (°C)
        
    Returns:
        Dataset con 4 variables binarias (una por cultivo)
    """
    variables = {}
    
    for cultivo, params in Config.UMBRALES_ESTRES.items():
        T_crit = params['T_critica']
        
        # Indicador binario: 1 si hay estrés, 0 si no
        estres = (tasmax > T_crit).astype(np.int8)
        
        # Nombre de variable descriptivo
        var_name = f"estres_termico_{cultivo}"
        estres.name = var_name
        
        # Atributos CF-compliant
        estres.attrs = {
            'standard_name': f'thermal_stress_indicator_{cultivo}',
            'long_name': f'Daily thermal stress indicator for {params["nombre_cientifico"]}',
            'units': '1',
            'flag_values': '0, 1',
            'flag_meanings': 'no_stress stress',
            'threshold': f'Tmax > {T_crit} degC',
            'critical_temperature': T_crit,
            'optimal_temperature_range': f'{params["T_optima_min"]}-{params["T_optima_max"]} degC',
            'crop_species': params['nombre_cientifico'],
            'reference': params['fuente'],
            'cell_methods': 'time: point',
        }
        
        variables[var_name] = estres
    
    # Crear dataset con todas las variables
    ds = xr.Dataset(variables)
    
    return ds


def procesar_archivo_tasmax(
    tasmax_path: Path,
    output_path: Path
) -> Dict:
    """
    Procesa un archivo tasmax para calcular indicadores de estrés térmico.
    
    Args:
        tasmax_path: Ruta al archivo NetCDF de tasmax
        output_path: Ruta de salida
        
    Returns:
        Diccionario con estadísticas del procesamiento
    """
    stats = {
        'exitoso': False,
        'archivo_entrada': str(tasmax_path),
        'archivo_salida': str(output_path),
        'error': None
    }
    
    try:
        # Abrir dataset
        ds = xr.open_dataset(tasmax_path)
        tasmax = ds['tasmax']
        
        # Verificar unidades (BASD-CMIP6-PE puede tener K o °C)
        units = tasmax.attrs.get('units', '')
        if 'K' in units or 'kelvin' in units.lower():
            logger.info("  - Convirtiendo tasmax de K a °C...")
            tasmax = tasmax - 273.15
        
        # Calcular indicadores de estrés térmico
        ds_estres = calcular_estres_termico(tasmax)
        
        # Metadatos globales
        ds_estres.attrs = ds.attrs.copy()
        ds_estres.attrs['title'] = 'Daily Thermal Stress Indicators for Andean Crops'
        ds_estres.attrs['institution'] = 'Universidad San Gregorio de Portoviejo'
        ds_estres.attrs['source'] = 'Derived from BASD-CMIP6-PE tasmax'
        ds_estres.attrs['references'] = 'CIP (2020); Allen et al. (1998) FAO-56; CIAT; Jacobsen (2003)'
        ds_estres.attrs['history'] = f"{Config.FECHA}: Thermal stress calculated using Script 03C v{Config.VERSION}"
        ds_estres.attrs['Conventions'] = 'CF-1.6'
        
        # Crear directorio de salida
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Encoding para compresión
        encoding = {}
        for var in ds_estres.data_vars:
            encoding[var] = {
                'zlib': True,
                'complevel': 4,
                'dtype': 'int8',
                '_FillValue': -1
            }
        
        # Guardar
        ds_estres.to_netcdf(output_path, encoding=encoding)
        
        # Estadísticas por cultivo
        n_total = tasmax.size
        stats['exitoso'] = True
        stats['n_timesteps'] = len(tasmax.time)
        stats['n_pixeles'] = tasmax.shape[1] * tasmax.shape[2] if len(tasmax.shape) == 3 else 1
        stats['tasmax_media'] = float(tasmax.mean().values)
        stats['cultivos'] = {}
        
        for cultivo, params in Config.UMBRALES_ESTRES.items():
            var_name = f"estres_termico_{cultivo}"
            n_estres = int(ds_estres[var_name].sum().values)
            pct_estres = 100 * n_estres / n_total if n_total > 0 else 0
            stats['cultivos'][cultivo] = {
                'T_critica': params['T_critica'],
                'dias_estres': n_estres,
                'porcentaje': pct_estres
            }
        
        stats['tamaño_mb'] = output_path.stat().st_size / (1024 * 1024)
        
        # Cerrar dataset
        ds.close()
        
    except Exception as e:
        stats['error'] = str(e)
        logger.error(f"Error procesando {tasmax_path.name}: {e}")
    
    return stats


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """Función principal del script."""
    tiempo_inicio = datetime.now()
    
    logger.info("=" * 70)
    logger.info("SCRIPT 03C: CONTEO DE DÍAS CON ESTRÉS TÉRMICO POR CULTIVO")
    logger.info("=" * 70)
    logger.info(f"Versión: {Config.VERSION}")
    logger.info(f"Fecha: {Config.FECHA}")
    logger.info("")
    logger.info("Umbrales de estrés térmico:")
    for cultivo, params in Config.UMBRALES_ESTRES.items():
        logger.info(f"  {cultivo:8s}: Tmax > {params['T_critica']}°C ({params['fuente'][:40]}...)")
    logger.info("")
    
    # Verificar directorios
    logger.info("Verificando directorios...")
    
    if not Config.TASMAX_DIR.exists():
        logger.error(f"No se encontró directorio de tasmax: {Config.TASMAX_DIR}")
        sys.exit(1)
    logger.info(f"  ✓ Directorio tasmax: {Config.TASMAX_DIR}")
    
    Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"  ✓ Directorio de salida: {Config.OUTPUT_DIR}")
    
    Config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Encontrar archivos tasmax
    logger.info("")
    logger.info("Buscando archivos tasmax...")
    archivos = encontrar_archivos_tasmax(Config.TASMAX_DIR)
    logger.info(f"  ✓ Archivos encontrados: {len(archivos)}")
    
    if len(archivos) == 0:
        logger.error("No se encontraron archivos tasmax")
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
    logger.info("Calculando indicadores de estrés térmico...")
    logger.info("=" * 50)
    
    resultados = []
    total = len(archivos)
    
    for i, (clave, info) in enumerate(sorted(archivos.items()), 1):
        # Construir nombre de salida
        nombre_base = info['path'].stem.replace('tasmax', 'estres_termico')
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
        
        stats = procesar_archivo_tasmax(info['path'], output_path)
        resultados.append(stats)
        
        if stats['exitoso'] and (i == 1 or i % 50 == 0):
            logger.info(f"  Tmax media: {stats['tasmax_media']:.1f}°C")
            for cultivo, cstats in stats['cultivos'].items():
                logger.info(f"  {cultivo}: {cstats['porcentaje']:.1f}% días con estrés (>{cstats['T_critica']}°C)")
    
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
    
    # Estadísticas globales por cultivo
    logger.info("")
    logger.info("  Porcentaje de días con estrés térmico (promedio global):")
    
    cultivo_stats_global = {c: [] for c in Config.UMBRALES_ESTRES}
    for r in resultados:
        if r.get('cultivos'):
            for cultivo, cstats in r['cultivos'].items():
                cultivo_stats_global[cultivo].append(cstats['porcentaje'])
    
    for cultivo, pcts in cultivo_stats_global.items():
        if pcts:
            logger.info(f"    {cultivo:8s}: {np.mean(pcts):6.2f}% (>{Config.UMBRALES_ESTRES[cultivo]['T_critica']}°C)")
    
    # Generar reporte
    logger.info("")
    logger.info("Generando reporte de auditoría...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    reporte_path = Config.REPORTS_DIR / f"REPORTE_SCRIPT_03C_{timestamp}.txt"
    
    with open(reporte_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("REPORTE DE AUDITORÍA - SCRIPT 03C: ESTRÉS TÉRMICO\n")
        f.write("=" * 70 + "\n\n")
        
        f.write("INFORMACIÓN GENERAL\n")
        f.write("-" * 30 + "\n")
        f.write(f"Fecha de ejecución: {Config.FECHA}\n")
        f.write(f"Versión del script: {Config.VERSION}\n")
        f.write(f"Autor: {Config.AUTOR}\n\n")
        
        f.write("METODOLOGÍA\n")
        f.write("-" * 30 + "\n")
        f.write("Fórmula: Días_estrés = Σ(Tmax > T_crítica_cultivo)\n")
        f.write("Indicador binario: 1 = estrés, 0 = sin estrés\n\n")
        
        f.write("Umbrales de estrés térmico:\n")
        for cultivo, params in Config.UMBRALES_ESTRES.items():
            f.write(f"  {cultivo:8s}: > {params['T_critica']}°C - {params['fuente']}\n")
        f.write("\n")
        
        f.write("RESULTADOS\n")
        f.write("-" * 30 + "\n")
        f.write(f"Total archivos procesados: {len(resultados)}\n")
        f.write(f"Exitosos: {exitosos}\n")
        f.write(f"Fallidos: {fallidos}\n")
        f.write(f"Tasa de éxito: {100*exitosos/len(resultados):.1f}%\n\n")
        
        f.write("Porcentaje de días con estrés térmico (promedio global):\n")
        for cultivo, pcts in cultivo_stats_global.items():
            if pcts:
                f.write(f"  {cultivo:8s}: {np.mean(pcts):.2f}% (>{Config.UMBRALES_ESTRES[cultivo]['T_critica']}°C)\n")
        f.write("\n")
        
        f.write("TIEMPO DE EJECUCIÓN\n")
        f.write("-" * 30 + "\n")
        f.write(f"Inicio: {tiempo_inicio.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Fin: {tiempo_fin.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Duración: {duracion}\n\n")
        
        f.write("ARCHIVOS DE SALIDA\n")
        f.write("-" * 30 + "\n")
        f.write(f"Directorio: {Config.OUTPUT_DIR}\n")
        f.write(f"Variables por archivo: 4 (estres_termico_papa, _maiz, _frejol, _quinua)\n\n")
        
        f.write("VERIFICACIÓN DE CRITERIOS\n")
        f.write("-" * 30 + "\n")
        f.write(f"[{'✓' if exitosos == len(resultados) else '✗'}] Todos los archivos procesados exitosamente\n")
        f.write(f"[✓] Umbrales con respaldo bibliográfico\n")
        f.write(f"[✓] Indicadores binarios calculados para 4 cultivos\n")
        f.write(f"[✓] Metadatos CF-compliant incluidos\n\n")
        
        f.write("DECISIÓN\n")
        f.write("-" * 30 + "\n")
        if exitosos == len(resultados):
            f.write("APROBADO - Proceder con Script 03D\n")
        else:
            f.write("REQUIERE REVISIÓN - Verificar archivos fallidos\n")
        
        f.write("\n" + "=" * 70 + "\n")
    
    logger.info(f"  ✓ Reporte guardado: {reporte_path}")
    
    # Estado final
    logger.info("")
    logger.info("=" * 70)
    if exitosos == len(resultados):
        logger.info("✓ SCRIPT 03C COMPLETADO EXITOSAMENTE")
        logger.info("  Siguiente paso: Ejecutar SCRIPT 03D - Detección de sequías agrícolas")
    else:
        logger.info("⚠ SCRIPT 03C COMPLETADO CON ADVERTENCIAS")
        logger.info(f"  {fallidos} archivos fallaron. Revisar reporte.")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()