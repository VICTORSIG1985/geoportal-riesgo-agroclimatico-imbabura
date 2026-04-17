"""
Script publicado como parte del Geoportal Riesgo Agroclimático — Imbabura, Ecuador
Pinto Páez, V. H. (2026). https://doi.org/10.5281/zenodo.19288559
Licencia: CC BY 4.0

NOTA: este archivo fue sanitizado para publicación pública.
- Credenciales (API keys, tokens, service accounts) removidas → <REDACTED_*>
- Rutas absolutas locales sustituidas por <RUTA_LOCAL>
Antes de ejecutar, configure sus propias rutas de entrada/salida y credenciales.

Archivo original: SCRIPT 03A CÁLCULO DE EVAPOTRANSPIRACIÓN DE REFERENCIA (ET₀).py
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
SCRIPT 03A: CÁLCULO DE EVAPOTRANSPIRACIÓN DE REFERENCIA (ET₀)
           MÉTODO HARGREAVES-SAMANI (1985) CON RADIACIÓN FAO-56
===============================================================================
Versión: 1.0.0
Fecha: 2026-02-02
Autor: Víctor Hugo Pinto Páez

Descripción:
    Calcula la evapotranspiración de referencia (ET₀) diaria utilizando el
    método de Hargreaves-Samani (1985), recomendado por FAO cuando no hay
    datos de radiación solar, humedad y viento disponibles.
    
    La radiación extraterrestre (Ra) se calcula según las ecuaciones del
    documento FAO-56 (Allen et al., 1998), Capítulo 3.

Metodología:
    ET₀ = 0.0023 × Ra × (Tmean + 17.8) × √(Tmax - Tmin)
    
    Donde:
    - Ra: Radiación extraterrestre (mm/día), calculada según FAO-56 Ec. 21
    - Tmean: Temperatura media diaria (°C) = (Tmax + Tmin) / 2
    - Tmax: Temperatura máxima diaria (°C)
    - Tmin: Temperatura mínima diaria (°C)

Referencias:
    - Hargreaves, G.H. & Samani, Z.A. (1985). Reference crop evapotranspiration
      from temperature. Applied Engineering in Agriculture, 1(2), 96-99.
    - Allen, R.G., Pereira, L.S., Raes, D., & Smith, M. (1998). Crop 
      evapotranspiration: Guidelines for computing crop water requirements.
      FAO Irrigation and Drainage Paper 56. Rome: FAO.

Entrada:
    - NetCDF recortados: tasmin, tasmax de BASD-CMIP6-PE
    
Salida:
    - NetCDF con ET₀ diaria (mm/día) para cada escenario y GCM

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
import json

import numpy as np
import xarray as xr
import pandas as pd

# Suprimir warnings de división por cero (manejados explícitamente)
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
# CONSTANTES FÍSICAS - FAO-56 (Allen et al., 1998)
# ============================================================================

class ConstantesFAO56:
    """
    Constantes físicas según FAO Irrigation and Drainage Paper 56.
    Todas las ecuaciones referenciadas corresponden a este documento.
    """
    # Constante solar (MJ m-2 min-1) - Página 41
    GSC = 0.0820
    
    # Factor de conversión de MJ/m²/día a mm/día de evaporación equivalente
    # Basado en calor latente de vaporización λ = 2.45 MJ/kg
    # 1 MJ/m²/día = 0.408 mm/día (Ecuación 20)
    MJ_TO_MM = 0.408
    
    # Coeficiente empírico de Hargreaves-Samani (adimensional)
    # Valor original: 0.0023 (Hargreaves & Samani, 1985)
    KHS = 0.0023
    
    # Constante de ajuste de temperatura (°C)
    # Valor original: 17.8 (Hargreaves & Samani, 1985)
    TEMP_OFFSET = 17.8

# ============================================================================
# CONFIGURACIÓN DEL PROYECTO
# ============================================================================

class Config:
    """Configuración central del script."""
    
    # Información del proyecto
    VERSION = "1.0.0"
    AUTOR = "Víctor Hugo Pinto Páez"
    FECHA = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Rutas base (según estructura del proyecto - Script 00)
    BASE_DIR = Path(r"<RUTA_LOCAL>")
    
    # Rutas de entrada (NetCDF recortados del Script 02)
    NETCDF_DIR = BASE_DIR / "02_DATOS" / "climaticos" / "BASD_CMIP6_PE" / "recortados"
    
    # Rutas de salida
    OUTPUT_DIR = BASE_DIR / "02_DATOS" / "climaticos" / "indices" / "ET0"
    REPORTS_DIR = BASE_DIR / "05_DOCUMENTACION" / "reportes_auditoria"
    DOCS_DIR = BASE_DIR / "05_DOCUMENTACION"
    
    # Variables requeridas
    VAR_TASMIN = "tasmin"
    VAR_TASMAX = "tasmax"
    
    # Metadatos de salida (CF Conventions)
    ET0_ATTRS = {
        'standard_name': 'water_potential_evaporation_amount',
        'long_name': 'Reference Evapotranspiration (Hargreaves-Samani)',
        'units': 'mm day-1',
        'method': 'Hargreaves-Samani (1985)',
        'reference': 'Allen et al. (1998) FAO-56; Hargreaves & Samani (1985)',
        'cell_methods': 'time: mean',
        'valid_min': 0.0,
        'valid_max': 20.0,  # Valor máximo razonable para ET₀ diaria
    }

# ============================================================================
# FUNCIONES DE CÁLCULO - FAO-56
# ============================================================================

def calcular_dia_juliano(tiempo: xr.DataArray) -> xr.DataArray:
    """
    Calcula el día del año (día juliano) para cada timestep.
    
    Args:
        tiempo: DataArray con coordenada temporal
        
    Returns:
        DataArray con día del año (1-366)
        
    Referencia:
        FAO-56, Capítulo 3: J es el número del día en el año entre 1 (1 enero)
        y 365 o 366 (31 diciembre).
    """
    # Convertir a pandas para extraer día del año
    fechas = pd.to_datetime(tiempo.values)
    dias = fechas.dayofyear
    
    return xr.DataArray(
        dias,
        dims=['time'],
        coords={'time': tiempo},
        attrs={'long_name': 'Day of year', 'units': '1'}
    )


def calcular_distancia_relativa_tierra_sol(J: np.ndarray) -> np.ndarray:
    """
    Calcula la distancia relativa inversa Tierra-Sol (dr).
    
    FAO-56 Ecuación 23:
        dr = 1 + 0.033 × cos(2π × J / 365)
    
    Args:
        J: Día del año (1-366)
        
    Returns:
        dr: Distancia relativa inversa (adimensional)
        
    Nota:
        dr varía entre ~0.967 (afelio, ~4 julio) y ~1.033 (perihelio, ~3 enero)
    """
    return 1 + 0.033 * np.cos(2 * np.pi * J / 365)


def calcular_declinacion_solar(J: np.ndarray) -> np.ndarray:
    """
    Calcula la declinación solar (δ).
    
    FAO-56 Ecuación 24:
        δ = 0.409 × sin(2π × J / 365 - 1.39)
    
    Args:
        J: Día del año (1-366)
        
    Returns:
        delta: Declinación solar (radianes)
        
    Nota:
        δ varía entre -0.409 rad (-23.45°) en solsticio de invierno
        y +0.409 rad (+23.45°) en solsticio de verano.
    """
    return 0.409 * np.sin(2 * np.pi * J / 365 - 1.39)


def calcular_angulo_horario_atardecer(lat_rad: np.ndarray, delta: np.ndarray) -> np.ndarray:
    """
    Calcula el ángulo horario al atardecer (ωs).
    
    FAO-56 Ecuación 25:
        ωs = arccos(-tan(φ) × tan(δ))
    
    Args:
        lat_rad: Latitud en radianes
        delta: Declinación solar en radianes
        
    Returns:
        omega_s: Ángulo horario al atardecer (radianes)
        
    Nota:
        Para latitudes ecuatoriales (Imbabura ~0.5°N), ωs ≈ π/2 todo el año,
        lo que corresponde a ~12 horas de luz solar.
        
    Manejo de casos extremos:
        - Si |tan(φ) × tan(δ)| > 1: día polar o noche polar
        - Se aplica clipping para evitar errores en arccos
    """
    # Calcular argumento del arccos
    argumento = -np.tan(lat_rad) * np.tan(delta)
    
    # Clipping para manejar latitudes extremas (no aplica para Imbabura)
    # Donde argumento < -1: sol nunca se pone (día polar) -> ωs = π
    # Donde argumento > 1: sol nunca sale (noche polar) -> ωs = 0
    argumento = np.clip(argumento, -1.0, 1.0)
    
    return np.arccos(argumento)


def calcular_radiacion_extraterrestre(lat_rad: np.ndarray, J: np.ndarray) -> np.ndarray:
    """
    Calcula la radiación extraterrestre diaria (Ra).
    
    FAO-56 Ecuación 21:
        Ra = (24×60/π) × Gsc × dr × [ωs×sin(φ)×sin(δ) + cos(φ)×cos(δ)×sin(ωs)]
    
    Args:
        lat_rad: Latitud en radianes (array 2D: lat, lon o escalar)
        J: Día del año (array 1D: time)
        
    Returns:
        Ra: Radiación extraterrestre (MJ m-2 día-1)
        
    Nota:
        Para Imbabura (~0.5°N), Ra varía entre ~35-40 MJ/m²/día,
        con máximos en equinoccios (marzo, septiembre) cuando el sol
        está directamente sobre el ecuador.
    """
    # Calcular componentes intermedios
    dr = calcular_distancia_relativa_tierra_sol(J)
    delta = calcular_declinacion_solar(J)
    omega_s = calcular_angulo_horario_atardecer(lat_rad, delta)
    
    # Calcular Ra según FAO-56 Ec. 21
    # Factor constante: (24 × 60 / π) × Gsc = 37.586 MJ m-2 día-1
    factor = (24 * 60 / np.pi) * ConstantesFAO56.GSC
    
    # Componentes trigonométricos
    sin_phi = np.sin(lat_rad)
    cos_phi = np.cos(lat_rad)
    sin_delta = np.sin(delta)
    cos_delta = np.cos(delta)
    sin_omega = np.sin(omega_s)
    
    # Radiación extraterrestre
    Ra = factor * dr * (omega_s * sin_phi * sin_delta + cos_phi * cos_delta * sin_omega)
    
    # Asegurar valores no negativos (físicamente imposible Ra < 0)
    Ra = np.maximum(Ra, 0)
    
    return Ra


def calcular_ET0_hargreaves_samani(
    tasmin: xr.DataArray,
    tasmax: xr.DataArray,
    lat: xr.DataArray
) -> xr.DataArray:
    """
    Calcula la evapotranspiración de referencia usando Hargreaves-Samani (1985).
    
    Ecuación:
        ET₀ = 0.0023 × Ra × (Tmean + 17.8) × √(Tmax - Tmin)
    
    Donde Ra se convierte de MJ/m²/día a mm/día multiplicando por 0.408.
    
    Args:
        tasmin: Temperatura mínima diaria (°C) - DataArray con dims (time, lat, lon)
        tasmax: Temperatura máxima diaria (°C) - DataArray con dims (time, lat, lon)
        lat: Latitudes (grados decimales)
        
    Returns:
        ET0: Evapotranspiración de referencia (mm/día)
        
    Referencias:
        - Hargreaves, G.H. & Samani, Z.A. (1985). Applied Engineering in Agriculture.
        - Allen et al. (1998). FAO-56, Ecuación 52 (versión simplificada).
    """
    logger.info("Calculando ET₀ con método Hargreaves-Samani (1985)...")
    
    # 1. Obtener día del año para cada timestep
    J = calcular_dia_juliano(tasmin.time)
    
    # 2. Convertir latitud a radianes
    # FAO-56: φ es positiva para hemisferio norte, negativa para sur
    lat_rad = np.deg2rad(lat.values)
    
    # 3. Crear arrays 3D para broadcasting
    # J tiene shape (time,)
    # lat_rad tiene shape (lat,)
    # Necesitamos expandir para operaciones elemento a elemento
    
    # Expandir J a (time, 1) para broadcasting con lat_rad (lat,)
    J_expanded = J.values[:, np.newaxis]  # (time, 1)
    lat_expanded = lat_rad[np.newaxis, :]  # (1, lat)
    
    # 4. Calcular Ra para cada combinación de tiempo y latitud
    # Ra tendrá shape (time, lat)
    logger.info("  - Calculando radiación extraterrestre (Ra) según FAO-56...")
    Ra_MJ = calcular_radiacion_extraterrestre(lat_expanded, J_expanded)
    
    # 5. Convertir Ra de MJ/m²/día a mm/día (equivalente de evaporación)
    Ra_mm = Ra_MJ * ConstantesFAO56.MJ_TO_MM
    
    # 6. Expandir Ra a 3D para coincidir con tasmin/tasmax (time, lat, lon)
    # Asumimos que Ra es constante a lo largo de longitud para misma latitud
    n_lon = len(tasmin.lon)
    Ra_3d = np.broadcast_to(Ra_mm[:, :, np.newaxis], (len(tasmin.time), len(lat), n_lon))
    
    # Crear DataArray con las mismas coordenadas
    Ra_da = xr.DataArray(
        Ra_3d,
        dims=['time', 'lat', 'lon'],
        coords={'time': tasmin.time, 'lat': lat, 'lon': tasmin.lon}
    )
    
    # 7. Calcular temperatura media
    logger.info("  - Calculando temperatura media...")
    Tmean = (tasmax + tasmin) / 2
    
    # 8. Calcular rango térmico diario (con protección contra valores negativos)
    logger.info("  - Calculando rango térmico diario...")
    dT = tasmax - tasmin
    
    # Protección: si Tmax < Tmin (error en datos), usar valor mínimo
    dT = xr.where(dT < 0, 0.1, dT)
    
    # 9. Aplicar ecuación de Hargreaves-Samani
    logger.info("  - Aplicando ecuación Hargreaves-Samani...")
    ET0 = ConstantesFAO56.KHS * Ra_da * (Tmean + ConstantesFAO56.TEMP_OFFSET) * np.sqrt(dT)
    
    # 10. Control de calidad: valores físicamente plausibles
    # ET₀ debe ser >= 0 y típicamente < 15 mm/día (máximo ~20 en condiciones extremas)
    ET0 = xr.where(ET0 < 0, 0, ET0)
    ET0 = xr.where(ET0 > 20, 20, ET0)  # Clipping de valores extremos
    
    # 11. Añadir atributos CF-compliant
    ET0.name = 'ET0'
    ET0.attrs = Config.ET0_ATTRS.copy()
    ET0.attrs['computation_date'] = Config.FECHA
    ET0.attrs['source_tasmin'] = str(tasmin.encoding.get('source', 'unknown'))
    ET0.attrs['source_tasmax'] = str(tasmax.encoding.get('source', 'unknown'))
    
    return ET0


# ============================================================================
# FUNCIONES DE PROCESAMIENTO DE ARCHIVOS
# ============================================================================

def encontrar_pares_temperatura(directorio: Path) -> Dict[str, Dict[str, Path]]:
    """
    Encuentra pares de archivos tasmin/tasmax para cada combinación GCM/escenario/período.
    
    Args:
        directorio: Directorio raíz con estructura experiment/GCM/archivos.nc
        
    Returns:
        Diccionario con estructura:
        {
            'clave_unica': {
                'tasmin': Path_tasmin,
                'tasmax': Path_tasmax,
                'experiment': str,
                'gcm': str,
                'period': str
            }
        }
    """
    pares = {}
    
    for exp_dir in directorio.iterdir():
        if not exp_dir.is_dir():
            continue
        experiment = exp_dir.name
        
        for gcm_dir in exp_dir.iterdir():
            if not gcm_dir.is_dir():
                continue
            gcm = gcm_dir.name
            
            # Listar archivos NetCDF
            archivos = list(gcm_dir.glob("*.nc"))
            
            # Agrupar por período temporal
            grupos = {}
            for archivo in archivos:
                # Extraer variable y período del nombre
                # Formato: gcm_variant_experiment_var_daily_year1_year2.nc
                partes = archivo.stem.split('_')
                if len(partes) >= 7:
                    var = partes[3]  # pr, tas, tasmin, tasmax
                    periodo = f"{partes[5]}_{partes[6]}"  # year1_year2
                    
                    if periodo not in grupos:
                        grupos[periodo] = {}
                    grupos[periodo][var] = archivo
            
            # Crear pares donde existan ambas variables
            for periodo, vars_dict in grupos.items():
                if 'tasmin' in vars_dict and 'tasmax' in vars_dict:
                    clave = f"{experiment}_{gcm}_{periodo}"
                    pares[clave] = {
                        'tasmin': vars_dict['tasmin'],
                        'tasmax': vars_dict['tasmax'],
                        'experiment': experiment,
                        'gcm': gcm,
                        'period': periodo
                    }
    
    return pares


def procesar_par_temperatura(
    tasmin_path: Path,
    tasmax_path: Path,
    output_path: Path
) -> Dict:
    """
    Procesa un par de archivos tasmin/tasmax para calcular ET₀.
    
    Args:
        tasmin_path: Ruta al archivo tasmin
        tasmax_path: Ruta al archivo tasmax
        output_path: Ruta de salida para ET₀
        
    Returns:
        Diccionario con estadísticas del procesamiento
    """
    stats = {
        'exitoso': False,
        'archivo_entrada_tasmin': str(tasmin_path),
        'archivo_entrada_tasmax': str(tasmax_path),
        'archivo_salida': str(output_path),
        'error': None
    }
    
    try:
        # Abrir datasets
        ds_tasmin = xr.open_dataset(tasmin_path)
        ds_tasmax = xr.open_dataset(tasmax_path)
        
        # Extraer variables
        tasmin = ds_tasmin['tasmin']
        tasmax = ds_tasmax['tasmax']
        
        # Verificar que las coordenadas coinciden
        assert np.allclose(tasmin.lat.values, tasmax.lat.values), "Latitudes no coinciden"
        assert np.allclose(tasmin.lon.values, tasmax.lon.values), "Longitudes no coinciden"
        assert len(tasmin.time) == len(tasmax.time), "Dimensión temporal no coincide"
        
        # Calcular ET₀
        ET0 = calcular_ET0_hargreaves_samani(tasmin, tasmax, tasmin.lat)
        
        # Crear dataset de salida
        ds_out = xr.Dataset({'ET0': ET0})
        
        # Copiar atributos globales y añadir metadatos de procesamiento
        ds_out.attrs = ds_tasmin.attrs.copy()
        ds_out.attrs['title'] = 'Reference Evapotranspiration (ET0) - Hargreaves-Samani Method'
        ds_out.attrs['institution'] = 'Universidad San Gregorio de Portoviejo'
        ds_out.attrs['source'] = 'Derived from BASD-CMIP6-PE tasmin/tasmax'
        ds_out.attrs['references'] = 'Hargreaves & Samani (1985); Allen et al. (1998) FAO-56'
        ds_out.attrs['history'] = f"{Config.FECHA}: ET0 calculated using Script 03A v{Config.VERSION}"
        ds_out.attrs['Conventions'] = 'CF-1.6'
        
        # Crear directorio de salida si no existe
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Guardar con compresión
        encoding = {
            'ET0': {
                'zlib': True,
                'complevel': 4,
                'dtype': 'float32',
                '_FillValue': -9999.0
            }
        }
        
        ds_out.to_netcdf(output_path, encoding=encoding)
        
        # Estadísticas
        stats['exitoso'] = True
        stats['n_timesteps'] = len(ET0.time)
        stats['ET0_mean'] = float(ET0.mean().values)
        stats['ET0_min'] = float(ET0.min().values)
        stats['ET0_max'] = float(ET0.max().values)
        stats['tamaño_mb'] = output_path.stat().st_size / (1024 * 1024)
        
        # Cerrar datasets
        ds_tasmin.close()
        ds_tasmax.close()
        
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
    logger.info("SCRIPT 03A: CÁLCULO DE ET₀ - HARGREAVES-SAMANI (1985)")
    logger.info("=" * 70)
    logger.info(f"Versión: {Config.VERSION}")
    logger.info(f"Fecha: {Config.FECHA}")
    logger.info("")
    
    # Verificar directorios
    logger.info("Verificando directorios...")
    
    if not Config.NETCDF_DIR.exists():
        logger.error(f"No se encontró directorio de entrada: {Config.NETCDF_DIR}")
        sys.exit(1)
    logger.info(f"  ✓ Directorio de entrada: {Config.NETCDF_DIR}")
    
    Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"  ✓ Directorio de salida: {Config.OUTPUT_DIR}")
    
    Config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Encontrar pares de archivos
    logger.info("")
    logger.info("Buscando pares tasmin/tasmax...")
    pares = encontrar_pares_temperatura(Config.NETCDF_DIR)
    logger.info(f"  ✓ Pares encontrados: {len(pares)}")
    
    if len(pares) == 0:
        logger.error("No se encontraron pares de archivos tasmin/tasmax")
        sys.exit(1)
    
    # Mostrar distribución por experimento
    conteo_exp = {}
    for clave, info in pares.items():
        exp = info['experiment']
        conteo_exp[exp] = conteo_exp.get(exp, 0) + 1
    
    logger.info("  Distribución por experimento:")
    for exp, n in sorted(conteo_exp.items()):
        logger.info(f"    - {exp}: {n} períodos")
    
    # Procesar pares
    logger.info("")
    logger.info("=" * 50)
    logger.info("Iniciando cálculo de ET₀...")
    logger.info("=" * 50)
    
    resultados = []
    total = len(pares)
    
    for i, (clave, info) in enumerate(sorted(pares.items()), 1):
        # Construir nombre de archivo de salida
        # Mantener estructura: experiment/GCM/archivo_ET0.nc
        nombre_base = info['tasmin'].stem.replace('tasmin', 'ET0')
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
        
        stats = procesar_par_temperatura(
            info['tasmin'],
            info['tasmax'],
            output_path
        )
        resultados.append(stats)
        
        if stats['exitoso'] and (i == 1 or i % 50 == 0):
            logger.info(f"  ET₀ media: {stats['ET0_mean']:.2f} mm/día")
    
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
    
    # Estadísticas globales de ET₀
    et0_means = [r['ET0_mean'] for r in resultados if r.get('ET0_mean')]
    if et0_means:
        logger.info(f"  ET₀ media global: {np.mean(et0_means):.2f} mm/día")
        logger.info(f"  ET₀ rango: {np.min(et0_means):.2f} - {np.max(et0_means):.2f} mm/día")
    
    # Generar reporte
    logger.info("")
    logger.info("Generando reporte de auditoría...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    reporte_path = Config.REPORTS_DIR / f"REPORTE_SCRIPT_03A_{timestamp}.txt"
    
    with open(reporte_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("REPORTE DE AUDITORÍA - SCRIPT 03A: CÁLCULO DE ET₀\n")
        f.write("=" * 70 + "\n\n")
        
        f.write("INFORMACIÓN GENERAL\n")
        f.write("-" * 30 + "\n")
        f.write(f"Fecha de ejecución: {Config.FECHA}\n")
        f.write(f"Versión del script: {Config.VERSION}\n")
        f.write(f"Autor: {Config.AUTOR}\n\n")
        
        f.write("METODOLOGÍA\n")
        f.write("-" * 30 + "\n")
        f.write("Método: Hargreaves-Samani (1985)\n")
        f.write("Fórmula: ET₀ = 0.0023 × Ra × (Tmean + 17.8) × √(Tmax - Tmin)\n")
        f.write("Radiación extraterrestre: FAO-56 Ecuación 21\n")
        f.write("Conversión: 1 MJ/m²/día = 0.408 mm/día\n\n")
        
        f.write("Referencias:\n")
        f.write("  - Hargreaves, G.H. & Samani, Z.A. (1985). Applied Engineering in Agriculture, 1(2), 96-99.\n")
        f.write("  - Allen, R.G. et al. (1998). FAO Irrigation and Drainage Paper 56.\n\n")
        
        f.write("RESULTADOS\n")
        f.write("-" * 30 + "\n")
        f.write(f"Total pares procesados: {len(resultados)}\n")
        f.write(f"Exitosos: {exitosos}\n")
        f.write(f"Fallidos: {fallidos}\n")
        f.write(f"Tasa de éxito: {100*exitosos/len(resultados):.1f}%\n\n")
        
        if et0_means:
            f.write("Estadísticas de ET₀:\n")
            f.write(f"  Media global: {np.mean(et0_means):.2f} mm/día\n")
            f.write(f"  Mínimo: {np.min(et0_means):.2f} mm/día\n")
            f.write(f"  Máximo: {np.max(et0_means):.2f} mm/día\n")
            f.write(f"  Desv. estándar: {np.std(et0_means):.2f} mm/día\n\n")
        
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
        f.write(f"[{'✓' if et0_means and np.mean(et0_means) > 0 else '✗'}] ET₀ media > 0 (valores físicamente plausibles)\n")
        f.write(f"[{'✓' if et0_means and np.max(et0_means) < 15 else '✗'}] ET₀ máxima < 15 mm/día (rango esperado para Imbabura)\n")
        f.write(f"[✓] Metadatos CF-compliant incluidos\n\n")
        
        f.write("DECISIÓN\n")
        f.write("-" * 30 + "\n")
        if exitosos == len(resultados) and et0_means:
            f.write("APROBADO - Proceder con Script 03B\n")
        else:
            f.write("REQUIERE REVISIÓN - Verificar archivos fallidos\n")
        
        f.write("\n" + "=" * 70 + "\n")
    
    logger.info(f"  ✓ Reporte guardado: {reporte_path}")
    
    # Estado final
    logger.info("")
    logger.info("=" * 70)
    if exitosos == len(resultados):
        logger.info("✓ SCRIPT 03A COMPLETADO EXITOSAMENTE")
        logger.info("  Siguiente paso: Ejecutar SCRIPT 03B - Cálculo de déficit hídrico")
    else:
        logger.info("⚠ SCRIPT 03A COMPLETADO CON ADVERTENCIAS")
        logger.info(f"  {fallidos} archivos fallaron. Revisar reporte.")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()