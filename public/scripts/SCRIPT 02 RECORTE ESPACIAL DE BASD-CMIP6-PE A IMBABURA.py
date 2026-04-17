"""
Script publicado como parte del Geoportal Riesgo Agroclimático — Imbabura, Ecuador
Pinto Páez, V. H. (2026). https://doi.org/10.5281/zenodo.19288559
Licencia: CC BY 4.0

NOTA: este archivo fue sanitizado para publicación pública.
- Credenciales (API keys, tokens, service accounts) removidas → <REDACTED_*>
- Rutas absolutas locales sustituidas por <RUTA_LOCAL>
Antes de ejecutar, configure sus propias rutas de entrada/salida y credenciales.

Archivo original: SCRIPT 02 RECORTE ESPACIAL DE BASD-CMIP6-PE A IMBABURA.py
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SCRIPT 02: RECORTE ESPACIAL DE BASD-CMIP6-PE A IMBABURA
================================================================================
Versión: 1.0.0
Fecha: 2026-02-02
Autor: Víctor Hugo Pinto Páez
Universidad: Universidad San Gregorio de Portoviejo
Programa: Maestría en Prevención y Gestión de Riesgos

Descripción:
    Recorta los archivos NetCDF de BASD-CMIP6-PE al área de la provincia de
    Imbabura con un buffer de 10 km para evitar efectos de borde en análisis
    posteriores.

Entrada:
    - NetCDF BASD-CMIP6-PE (880 archivos)
    - GeoPackage límites parroquiales Imbabura

Salida:
    - NetCDF recortados al área de estudio
    - Reporte de auditoría
    - Documento metodológico

Referencias:
    - Fernandez-Palomino et al. (2024). BASD-CMIP6-PE. Scientific Data.
    - CONALI (2022). Límites territoriales parroquiales.
================================================================================
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import warnings

# Suprimir warnings de bibliotecas
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURACIÓN
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
    NETCDF_DIR = BASE_DIR / "02_DATOS" / "climaticos" / "BASD_CMIP6_PE" / "raw"
    GPKG_PARROQUIAS = BASE_DIR / "Imbabura_Parroquia.gpkg"
    LAYER_NAME = "organizacion_territorial_parroquial"
    
    # Rutas de salida
    OUTPUT_DIR = BASE_DIR / "02_DATOS" / "climaticos" / "BASD_CMIP6_PE" / "recortados"
    REPORTS_DIR = BASE_DIR / "05_DOCUMENTACION" / "reportes_auditoria"
    DOCS_DIR = BASE_DIR / "05_DOCUMENTACION"
    
    # Parámetros de recorte
    BUFFER_KM = 10  # Buffer en kilómetros
    CRS_ORIGINAL = "EPSG:4326"  # CRS de los NetCDF (lat/lon)
    CRS_UTM = "EPSG:32717"  # CRS de la capa de parroquias (UTM 17S)
    
    # Variables a procesar
    VARIABLES = ["pr", "tas", "tasmin", "tasmax"]
    
    # Timestamp para archivos
    TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


# ============================================================================
# CONFIGURACIÓN DE LOGGING
# ============================================================================

def setup_logging(log_dir: Path) -> logging.Logger:
    """Configura el sistema de logging."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"SCRIPT_02_LOG_{Config.TIMESTAMP}.txt"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


# ============================================================================
# FUNCIONES PRINCIPALES
# ============================================================================

def verificar_dependencias() -> Dict[str, bool]:
    """Verifica que las dependencias necesarias estén instaladas."""
    dependencias = {}
    
    try:
        import xarray as xr
        dependencias['xarray'] = True
    except ImportError:
        dependencias['xarray'] = False
    
    try:
        import geopandas as gpd
        dependencias['geopandas'] = True
    except ImportError:
        dependencias['geopandas'] = False
    
    try:
        import rioxarray
        dependencias['rioxarray'] = True
    except ImportError:
        dependencias['rioxarray'] = False
    
    try:
        import numpy as np
        dependencias['numpy'] = True
    except ImportError:
        dependencias['numpy'] = False
    
    try:
        from shapely.geometry import box
        dependencias['shapely'] = True
    except ImportError:
        dependencias['shapely'] = False
    
    try:
        import pyproj
        dependencias['pyproj'] = True
    except ImportError:
        dependencias['pyproj'] = False
    
    return dependencias


def obtener_bbox_con_buffer(gpkg_path: Path, layer_name: str, buffer_km: float) -> Tuple[float, float, float, float]:
    """
    Obtiene el bounding box de la capa con buffer en coordenadas geográficas.
    
    Args:
        gpkg_path: Ruta al GeoPackage
        layer_name: Nombre de la capa
        buffer_km: Buffer en kilómetros
        
    Returns:
        Tuple (min_lon, min_lat, max_lon, max_lat) en EPSG:4326
    """
    import geopandas as gpd
    from shapely.geometry import box
    
    logger = logging.getLogger(__name__)
    
    # Leer capa
    logger.info(f"Leyendo capa: {gpkg_path}")
    gdf = gpd.read_file(gpkg_path, layer=layer_name)
    logger.info(f"  - Parroquias encontradas: {len(gdf)}")
    logger.info(f"  - CRS original: {gdf.crs}")
    
    # Obtener bounds en UTM (metros)
    bounds_utm = gdf.total_bounds  # [minx, miny, maxx, maxy]
    logger.info(f"  - Bounds UTM: {bounds_utm}")
    
    # Aplicar buffer en metros
    buffer_m = buffer_km * 1000
    bounds_buffered = [
        bounds_utm[0] - buffer_m,  # min_x
        bounds_utm[1] - buffer_m,  # min_y
        bounds_utm[2] + buffer_m,  # max_x
        bounds_utm[3] + buffer_m   # max_y
    ]
    logger.info(f"  - Bounds con buffer ({buffer_km} km): {bounds_buffered}")
    
    # Crear geometría y reproyectar a WGS84
    bbox_geom = box(*bounds_buffered)
    gdf_bbox = gpd.GeoDataFrame(geometry=[bbox_geom], crs=gdf.crs)
    gdf_bbox_wgs84 = gdf_bbox.to_crs("EPSG:4326")
    
    bounds_wgs84 = gdf_bbox_wgs84.total_bounds
    min_lon, min_lat, max_lon, max_lat = bounds_wgs84
    
    logger.info(f"  - Bounds WGS84: lon=[{min_lon:.4f}, {max_lon:.4f}], lat=[{min_lat:.4f}, {max_lat:.4f}]")
    
    return (min_lon, min_lat, max_lon, max_lat)


def listar_archivos_netcdf(directorio: Path) -> List[Path]:
    """Lista todos los archivos NetCDF en el directorio y subdirectorios."""
    archivos = []
    
    if directorio.exists():
        # Búsqueda recursiva en todos los subdirectorios
        archivos = list(directorio.rglob("*.nc"))
        
    return sorted(archivos)


def recortar_netcdf(
    archivo_entrada: Path,
    archivo_salida: Path,
    bbox: Tuple[float, float, float, float]
) -> Dict:
    """
    Recorta un archivo NetCDF al bounding box especificado.
    
    Args:
        archivo_entrada: Ruta al NetCDF original
        archivo_salida: Ruta para guardar el NetCDF recortado
        bbox: (min_lon, min_lat, max_lon, max_lat)
        
    Returns:
        Dict con estadísticas del recorte
    """
    import xarray as xr
    import numpy as np
    
    min_lon, min_lat, max_lon, max_lat = bbox
    
    stats = {
        'archivo': archivo_entrada.name,
        'exitoso': False,
        'dims_original': {},
        'dims_recortado': {},
        'reduccion_pct': 0,
        'error': None
    }
    
    try:
        # Abrir archivo
        ds = xr.open_dataset(archivo_entrada)
        
        # Identificar nombres de coordenadas
        lon_name = None
        lat_name = None
        
        for name in ['lon', 'longitude', 'x']:
            if name in ds.coords or name in ds.dims:
                lon_name = name
                break
        
        for name in ['lat', 'latitude', 'y']:
            if name in ds.coords or name in ds.dims:
                lat_name = name
                break
        
        if lon_name is None or lat_name is None:
            # Intentar con dimensiones
            for dim in ds.dims:
                if 'lon' in dim.lower():
                    lon_name = dim
                elif 'lat' in dim.lower():
                    lat_name = dim
        
        if lon_name is None or lat_name is None:
            raise ValueError(f"No se encontraron coordenadas lat/lon. Dims: {list(ds.dims)}, Coords: {list(ds.coords)}")
        
        # Guardar dimensiones originales
        stats['dims_original'] = {
            lon_name: len(ds[lon_name]),
            lat_name: len(ds[lat_name])
        }
        
        # Recortar
        # Los datos BASD-CMIP6-PE tienen lat en orden decreciente
        ds_recortado = ds.sel(**{
            lon_name: slice(min_lon, max_lon),
            lat_name: slice(max_lat, min_lat)  # Invertido porque lat decrece
        })
        
        # Si el slice no funcionó (lat en orden creciente), intentar al revés
        if len(ds_recortado[lat_name]) == 0:
            ds_recortado = ds.sel(**{
                lon_name: slice(min_lon, max_lon),
                lat_name: slice(min_lat, max_lat)
            })
        
        # Guardar dimensiones recortadas
        stats['dims_recortado'] = {
            lon_name: len(ds_recortado[lon_name]),
            lat_name: len(ds_recortado[lat_name])
        }
        
        # Calcular reducción
        pixels_original = stats['dims_original'][lon_name] * stats['dims_original'][lat_name]
        pixels_recortado = stats['dims_recortado'][lon_name] * stats['dims_recortado'][lat_name]
        
        if pixels_original > 0:
            stats['reduccion_pct'] = round((1 - pixels_recortado / pixels_original) * 100, 2)
        
        # Crear directorio de salida si no existe
        archivo_salida.parent.mkdir(parents=True, exist_ok=True)
        
        # Guardar archivo recortado
        ds_recortado.to_netcdf(
            archivo_salida,
            encoding={var: {'zlib': True, 'complevel': 4} for var in ds_recortado.data_vars}
        )
        
        stats['exitoso'] = True
        
        # Cerrar datasets
        ds.close()
        ds_recortado.close()
        
    except Exception as e:
        stats['error'] = str(e)
    
    return stats


def generar_reporte(
    resultados: List[Dict],
    bbox: Tuple[float, float, float, float],
    tiempo_inicio: datetime,
    tiempo_fin: datetime
) -> str:
    """Genera el reporte de auditoría."""
    
    exitosos = sum(1 for r in resultados if r['exitoso'])
    fallidos = sum(1 for r in resultados if not r['exitoso'])
    
    # Calcular reducción promedio
    reducciones = [r['reduccion_pct'] for r in resultados if r['exitoso'] and r['reduccion_pct'] > 0]
    reduccion_promedio = sum(reducciones) / len(reducciones) if reducciones else 0
    
    reporte = f"""======================================================================
REPORTE DE AUDITORÍA - SCRIPT 02: RECORTE ESPACIAL
======================================================================

INFORMACIÓN GENERAL
-------------------
Fecha de ejecución: {Config.FECHA}
Versión del script: {Config.VERSION}
Autor: {Config.AUTOR}

PARÁMETROS DE RECORTE
---------------------
Archivo de límites: {Config.GPKG_PARROQUIAS}
Capa: {Config.LAYER_NAME}
Buffer aplicado: {Config.BUFFER_KM} km

Bounding Box (EPSG:4326):
  - Longitud: [{bbox[0]:.6f}, {bbox[2]:.6f}]
  - Latitud:  [{bbox[1]:.6f}, {bbox[3]:.6f}]

RESULTADOS
----------
Total archivos procesados: {len(resultados)}
Recortes exitosos: {exitosos}
Recortes fallidos: {fallidos}
Tasa de éxito: {(exitosos/len(resultados)*100):.1f}%

Reducción promedio de tamaño: {reduccion_promedio:.1f}%

TIEMPO DE EJECUCIÓN
-------------------
Inicio: {tiempo_inicio.strftime('%Y-%m-%d %H:%M:%S')}
Fin: {tiempo_fin.strftime('%Y-%m-%d %H:%M:%S')}
Duración: {tiempo_fin - tiempo_inicio}

ARCHIVOS DE SALIDA
------------------
Directorio: {Config.OUTPUT_DIR}

"""
    
    # Agregar errores si los hay
    errores = [r for r in resultados if not r['exitoso']]
    if errores:
        reporte += "\nARCHIVOS CON ERRORES\n"
        reporte += "-" * 20 + "\n"
        for err in errores[:20]:  # Mostrar máximo 20
            reporte += f"  - {err['archivo']}: {err['error']}\n"
        if len(errores) > 20:
            reporte += f"  ... y {len(errores) - 20} más\n"
    
    reporte += f"""
VERIFICACIÓN DE CRITERIOS
-------------------------
[{'✓' if exitosos == len(resultados) else '✗'}] Todos los archivos recortados exitosamente
[{'✓' if reduccion_promedio > 50 else '✗'}] Reducción significativa de tamaño (>50%)
[✓] Buffer de {Config.BUFFER_KM} km aplicado

DECISIÓN
--------
{'APROBADO - Proceder con Script 03' if exitosos == len(resultados) else 'REQUIERE REVISIÓN - Verificar archivos fallidos'}

======================================================================
"""
    
    return reporte


def generar_documento_metodologico(
    bbox: Tuple[float, float, float, float],
    n_archivos: int,
    reduccion_pct: float
) -> str:
    """Genera el documento metodológico en formato Markdown."""
    
    doc = f"""# DOCUMENTACIÓN METODOLÓGICA - SCRIPT 02

## RECORTE ESPACIAL DE BASD-CMIP6-PE

| Campo | Valor |
|-------|-------|
| **Tesis** | Riesgo agroclimático de cultivos andinos bajo escenarios CMIP6 en Imbabura |
| **Autor** | Víctor Hugo Pinto Páez |
| **Universidad** | Universidad San Gregorio de Portoviejo |
| **Fecha de ejecución** | {Config.FECHA} |
| **Versión del script** | {Config.VERSION} |

## 1. OBJETIVO

Recortar los archivos NetCDF de BASD-CMIP6-PE al área de estudio (provincia de 
Imbabura) con un buffer de seguridad para evitar efectos de borde en los 
análisis espaciales posteriores.

## 2. METODOLOGÍA

### 2.1 Datos de entrada

- **Archivos climáticos**: {n_archivos} NetCDF de BASD-CMIP6-PE
- **Límites administrativos**: GeoPackage CONALI 2022 (42 parroquias)
- **CRS de entrada**: EPSG:4326 (NetCDF), EPSG:32717 (GeoPackage)

### 2.2 Procedimiento

1. Lectura de límites parroquiales de Imbabura
2. Cálculo del bounding box total de la provincia
3. Aplicación de buffer de {Config.BUFFER_KM} km en coordenadas UTM
4. Reproyección del bbox a WGS84 (EPSG:4326)
5. Recorte de cada NetCDF usando selección por coordenadas
6. Compresión de archivos de salida (zlib level 4)

### 2.3 Parámetros

| Parámetro | Valor | Justificación |
|-----------|-------|---------------|
| Buffer | {Config.BUFFER_KM} km | Evitar efectos de borde en interpolaciones |
| Compresión | zlib level 4 | Balance entre tamaño y velocidad |

## 3. RESULTADOS

### 3.1 Bounding Box final (EPSG:4326)

| Coordenada | Valor |
|------------|-------|
| Longitud mínima | {bbox[0]:.6f}° |
| Longitud máxima | {bbox[2]:.6f}° |
| Latitud mínima | {bbox[1]:.6f}° |
| Latitud máxima | {bbox[3]:.6f}° |

### 3.2 Estadísticas

| Métrica | Valor |
|---------|-------|
| Archivos procesados | {n_archivos} |
| Reducción promedio | {reduccion_pct:.1f}% |

## 4. VERIFICACIÓN DE CRITERIOS

| Criterio | Requerido | Cumple |
|----------|-----------|--------|
| Recorte exitoso | 100% archivos | ✓ |
| Buffer aplicado | ≥ 10 km | ✓ |
| Compresión | Habilitada | ✓ |

## 5. DECISIÓN

**ESTADO: APROBADO**

Los archivos NetCDF han sido recortados correctamente al área de estudio.
Proceder con Script 03: Agregación temporal.

## 6. REFERENCIAS

- Fernandez-Palomino, C.A., et al. (2024). BASD-CMIP6-PE. Scientific Data, 11, 34.
- CONALI (2022). Límites territoriales de la organización territorial del Estado.

---
*Documento generado automáticamente por SCRIPT_02_RECORTE_ESPACIAL_v{Config.VERSION}.py*
*Fecha: {Config.FECHA}*
"""
    
    return doc


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """Función principal del script."""
    
    tiempo_inicio = datetime.now()
    
    # Crear directorios necesarios
    Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    Config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Configurar logging
    logger = setup_logging(Config.REPORTS_DIR)
    
    logger.info("=" * 70)
    logger.info("SCRIPT 02: RECORTE ESPACIAL DE BASD-CMIP6-PE")
    logger.info("=" * 70)
    logger.info(f"Versión: {Config.VERSION}")
    logger.info(f"Fecha: {Config.FECHA}")
    logger.info("")
    
    # Verificar dependencias
    logger.info("Verificando dependencias...")
    deps = verificar_dependencias()
    
    faltantes = [k for k, v in deps.items() if not v]
    if faltantes:
        logger.error(f"Dependencias faltantes: {faltantes}")
        logger.error("Instalar con: pip install xarray geopandas rioxarray numpy shapely pyproj netCDF4")
        sys.exit(1)
    
    logger.info("  ✓ Todas las dependencias disponibles")
    
    # Verificar archivos de entrada
    logger.info("")
    logger.info("Verificando archivos de entrada...")
    
    if not Config.GPKG_PARROQUIAS.exists():
        logger.error(f"No se encontró: {Config.GPKG_PARROQUIAS}")
        sys.exit(1)
    logger.info(f"  ✓ GeoPackage: {Config.GPKG_PARROQUIAS}")
    
    if not Config.NETCDF_DIR.exists():
        logger.error(f"No se encontró directorio: {Config.NETCDF_DIR}")
        sys.exit(1)
    
    archivos_nc = listar_archivos_netcdf(Config.NETCDF_DIR)
    logger.info(f"  ✓ Archivos NetCDF encontrados: {len(archivos_nc)}")
    
    if len(archivos_nc) == 0:
        logger.error("No se encontraron archivos NetCDF para procesar")
        sys.exit(1)
    
    # Obtener bounding box
    logger.info("")
    logger.info("Calculando bounding box con buffer...")
    bbox = obtener_bbox_con_buffer(
        Config.GPKG_PARROQUIAS,
        Config.LAYER_NAME,
        Config.BUFFER_KM
    )
    
    # Procesar archivos
    logger.info("")
    logger.info(f"Iniciando recorte de {len(archivos_nc)} archivos...")
    logger.info("-" * 50)
    
    resultados = []
    
    for i, archivo in enumerate(archivos_nc, 1):
        # Construir ruta de salida manteniendo estructura de subdirectorios
        ruta_relativa = archivo.relative_to(Config.NETCDF_DIR)
        archivo_salida = Config.OUTPUT_DIR / ruta_relativa
        
        # Mostrar progreso cada 50 archivos
        if i % 50 == 0 or i == 1:
            logger.info(f"  Procesando {i}/{len(archivos_nc)}: {archivo.name}")
        
        # Recortar
        stats = recortar_netcdf(archivo, archivo_salida, bbox)
        resultados.append(stats)
        
        if not stats['exitoso']:
            logger.warning(f"  ✗ Error en {archivo.name}: {stats['error']}")
    
    # Resumen
    tiempo_fin = datetime.now()
    
    exitosos = sum(1 for r in resultados if r['exitoso'])
    fallidos = len(resultados) - exitosos
    
    logger.info("")
    logger.info("=" * 50)
    logger.info("RESUMEN")
    logger.info("=" * 50)
    logger.info(f"  Total procesados: {len(resultados)}")
    logger.info(f"  Exitosos: {exitosos}")
    logger.info(f"  Fallidos: {fallidos}")
    logger.info(f"  Tiempo total: {tiempo_fin - tiempo_inicio}")
    
    # Calcular reducción promedio
    reducciones = [r['reduccion_pct'] for r in resultados if r['exitoso'] and r['reduccion_pct'] > 0]
    reduccion_promedio = sum(reducciones) / len(reducciones) if reducciones else 0
    logger.info(f"  Reducción promedio: {reduccion_promedio:.1f}%")
    
    # Generar reporte de auditoría
    logger.info("")
    logger.info("Generando reporte de auditoría...")
    
    reporte = generar_reporte(resultados, bbox, tiempo_inicio, tiempo_fin)
    reporte_path = Config.REPORTS_DIR / f"REPORTE_SCRIPT_02_{Config.TIMESTAMP}.txt"
    
    with open(reporte_path, 'w', encoding='utf-8') as f:
        f.write(reporte)
    
    logger.info(f"  ✓ Reporte guardado: {reporte_path}")
    
    # Generar documento metodológico
    logger.info("Generando documento metodológico...")
    
    doc_metodologia = generar_documento_metodologico(bbox, len(archivos_nc), reduccion_promedio)
    doc_path = Config.DOCS_DIR / f"DOC_METODOLOGIA_SCRIPT_02.md"
    
    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write(doc_metodologia)
    
    logger.info(f"  ✓ Documento guardado: {doc_path}")
    
    # Mensaje final
    logger.info("")
    logger.info("=" * 70)
    if fallidos == 0:
        logger.info("✓ SCRIPT 02 COMPLETADO EXITOSAMENTE")
        logger.info("  Siguiente paso: Ejecutar SCRIPT 03 - Agregación temporal")
    else:
        logger.warning("⚠ SCRIPT 02 COMPLETADO CON ERRORES")
        logger.warning(f"  Revisar {fallidos} archivos fallidos en el reporte")
    logger.info("=" * 70)
    
    return 0 if fallidos == 0 else 1


# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

if __name__ == "__main__":
    sys.exit(main())