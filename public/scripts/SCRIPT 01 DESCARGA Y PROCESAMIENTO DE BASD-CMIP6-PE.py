"""
Script publicado como parte del Geoportal Riesgo Agroclimático — Imbabura, Ecuador
Pinto Páez, V. H. (2026). https://doi.org/10.5281/zenodo.19288559
Licencia: CC BY 4.0

NOTA: este archivo fue sanitizado para publicación pública.
- Credenciales (API keys, tokens, service accounts) removidas → <REDACTED_*>
- Rutas absolutas locales sustituidas por <RUTA_LOCAL>
Antes de ejecutar, configure sus propias rutas de entrada/salida y credenciales.

Archivo original: SCRIPT 01 DESCARGA Y PROCESAMIENTO DE BASD-CMIP6-PE.py
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCRIPT 01: DESCARGA Y PROCESAMIENTO DE BASD-CMIP6-PE
Versión 1.1.0

Tesis: Modelamiento del riesgo agroclimático mediante Random Forest y Redes
       Bayesianas bajo escenarios CMIP6: Aplicación a cultivos andinos en
       Imbabura, Ecuador

Autor: Víctor Hugo Pinto Páez
Universidad: Universidad San Gregorio de Portoviejo

Descripción:
    Descarga datos climáticos del dataset BASD-CMIP6-PE desde el repositorio
    PIK-Potsdam, recorta espacialmente a Imbabura y genera climatologías.

Dataset:
    Fernandez-Palomino et al. (2024). BASD-CMIP6-PE: bias-adjusted and 
    statistically downscaled CMIP6 projections over Peru and Ecuador.
    Scientific Data, 11, 34. https://doi.org/10.1038/s41597-023-02863-z
    
    DOI: 10.5880/pik.2023.001
    Licencia: CC BY 4.0

Métodos de descarga:
    1. HTTP directo desde PIK-Potsdam (preferido)
    2. FTP desde GFZ Data Services (alternativo)
    3. Descarga manual + procesamiento local (si 1 y 2 fallan)
"""

import os
import json
import shutil
import requests
import ftplib
import numpy as np
import xarray as xr
import geopandas as gpd
from datetime import datetime
from pathlib import Path
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

# Ruta base del proyecto
RUTA_BASE = Path(r"<RUTA_LOCAL>")
RUTA_DATOS = RUTA_BASE / "02_DATOS" / "climaticos" / "BASD_CMIP6_PE"
RUTA_DOCUMENTACION = RUTA_BASE / "05_DOCUMENTACION"
RUTA_RAW = RUTA_DATOS / "raw"  # Archivos originales descargados
RUTA_PROCESSED = RUTA_DATOS / "processed"  # Archivos recortados a Imbabura

# Crear carpetas si no existen
RUTA_RAW.mkdir(parents=True, exist_ok=True)
RUTA_PROCESSED.mkdir(parents=True, exist_ok=True)

# AOI de Imbabura
AOI_PATH = Path(r"<RUTA_LOCAL>")

# Cargar configuración del proyecto
CONFIG_PATH = RUTA_BASE / "01_PROTOCOLO" / "config.json"
if CONFIG_PATH.exists():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        CONFIG = json.load(f)
else:
    CONFIG = {}

# =============================================================================
# CONFIGURACIÓN DEL DATASET BASD-CMIP6-PE
# =============================================================================

# URLs de acceso al dataset
BASD_CONFIG = {
    # Servidor PIK-Potsdam (HTTP)
    "pik_base_url": "https://www.pik-potsdam.de/data/doi10.5880PIK.2023.001/BASD-CMIP6-PE/daily",
    
    # Servidor GFZ (FTP) - alternativo
    "gfz_ftp_host": "datapub.gfz-potsdam.de",
    "gfz_ftp_path": "/download/10.5880.PIK.2023.001",
    
    # Metadatos del dataset
    "doi": "10.5880/pik.2023.001",
    "citation": "Fernandez-Palomino et al. (2024). Scientific Data, 11, 34.",
    "license": "CC BY 4.0",
    "resolution_spatial": "0.1 degrees (~10 km)",
    "resolution_temporal": "daily",
    "domain": {"lat_min": -19.0, "lat_max": 2.0, "lon_min": -82.0, "lon_max": -67.0},
    
    # Variables disponibles
    "variables": ["pr", "tas", "tasmin", "tasmax"],
    "var_descriptions": {
        "pr": "Precipitation (mm/day)",
        "tas": "Mean temperature (°C)",
        "tasmin": "Minimum temperature (°C)",
        "tasmax": "Maximum temperature (°C)"
    },
    
    # GCMs disponibles (10 modelos)
    "gcms": [
        "CanESM5", "IPSL-CM6A-LR", "UKESM1-0-LL", "CNRM-CM6-1", "CNRM-ESM2-1",
        "MIROC6", "GFDL-ESM4", "MRI-ESM2-0", "MPI-ESM1-2-HR", "EC-Earth3"
    ],
    
    # Escenarios SSP
    "ssps": ["ssp126", "ssp370", "ssp585"],
    
    # Períodos temporales (archivos divididos en segmentos de ~10 años)
    # Estructura real verificada del servidor PIK
    "historical_segments": [
        (1850, 1850),  # Primer año solo
        (1851, 1860), (1861, 1870), (1871, 1880), (1881, 1890),
        (1891, 1900), (1901, 1910), (1911, 1920), (1921, 1930),
        (1931, 1940), (1941, 1950), (1951, 1960), (1961, 1970),
        (1971, 1980), (1981, 1990), (1991, 2000), (2001, 2010),
        (2011, 2014)  # Último segmento hasta 2014
    ],
    "future_segments": [
        (2015, 2020), (2021, 2030), (2031, 2040), (2041, 2050),
        (2051, 2060), (2061, 2070), (2071, 2080), (2081, 2090),
        (2091, 2100)
    ]
}

# Períodos de interés para la tesis (subconjunto)
PERIODOS_INTERES = {
    "historico": {"inicio": 1981, "fin": 2014, "nombre": "baseline"},
    "futuro_cercano": {"inicio": 2021, "fin": 2040, "nombre": "near_future"},
    "futuro_medio": {"inicio": 2041, "fin": 2060, "nombre": "mid_future"},
    "futuro_lejano": {"inicio": 2061, "fin": 2080, "nombre": "far_future"}
}


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def cargar_aoi_bounds():
    """Carga el AOI de Imbabura y retorna los bounds con buffer."""
    if not AOI_PATH.exists():
        raise FileNotFoundError(f"No se encontró el AOI en: {AOI_PATH}")
    
    gdf = gpd.read_file(AOI_PATH)
    if gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")
    
    bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
    buffer = 0.1  # ~10 km de buffer
    
    return {
        "lon_min": float(bounds[0] - buffer),
        "lat_min": float(bounds[1] - buffer),
        "lon_max": float(bounds[2] + buffer),
        "lat_max": float(bounds[3] + buffer)
    }


def construir_nombre_archivo(variable, gcm, experiment, year_start, year_end):
    """
    Construye el nombre de archivo según la convención BASD-CMIP6-PE.
    
    Ejemplo: canesm5_r1i1p1f1_historical_pr_daily_1980_1984.nc
    """
    gcm_lower = gcm.lower().replace("-", "").replace("_", "")
    return f"{gcm_lower}_r1i1p1f1_{experiment}_{variable}_daily_{year_start}_{year_end}.nc"


def construir_url_pik(variable, gcm, experiment, year_start, year_end):
    """Construye URL para descarga desde servidor PIK."""
    filename = construir_nombre_archivo(variable, gcm, experiment, year_start, year_end)
    folder = "historical" if experiment == "historical" else experiment
    return f"{BASD_CONFIG['pik_base_url']}/{folder}/{gcm}/{filename}"


def descargar_archivo_http(url, destino, timeout=300):
    """
    Descarga un archivo vía HTTP con manejo de errores.
    
    Returns:
        bool: True si la descarga fue exitosa
    """
    try:
        # Usar headers de navegador para evitar bloqueo 403
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/x-netcdf,*/*',
            'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
        }
        
        response = requests.get(url, headers=headers, stream=True, timeout=timeout)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(destino, 'wb') as f:
            if total_size == 0:
                f.write(response.content)
            else:
                with tqdm(total=total_size, unit='B', unit_scale=True, desc=destino.name) as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        pbar.update(len(chunk))
        
        return True
    
    except requests.exceptions.HTTPError as e:
        print(f"    [!] Error HTTP: {e}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"    [!] Error de conexión: {e}")
        return False
    except Exception as e:
        print(f"    [!] Error inesperado: {e}")
        return False


def descargar_archivo_ftp(host, remote_path, destino):
    """
    Descarga un archivo vía FTP.
    
    Returns:
        bool: True si la descarga fue exitosa
    """
    try:
        with ftplib.FTP(host) as ftp:
            ftp.login()  # Anónimo
            with open(destino, 'wb') as f:
                ftp.retrbinary(f'RETR {remote_path}', f.write)
        return True
    except Exception as e:
        print(f"    [!] Error FTP: {e}")
        return False


def recortar_a_imbabura(ds, bounds):
    """
    Recorta un dataset xarray a los límites de Imbabura.
    
    Args:
        ds: xarray.Dataset
        bounds: dict con lon_min, lon_max, lat_min, lat_max
    
    Returns:
        xarray.Dataset recortado
    """
    # Identificar nombres de coordenadas
    lat_name = 'lat' if 'lat' in ds.coords else 'latitude'
    lon_name = 'lon' if 'lon' in ds.coords else 'longitude'
    
    # Recortar
    ds_recortado = ds.sel(
        **{
            lat_name: slice(bounds['lat_min'], bounds['lat_max']),
            lon_name: slice(bounds['lon_min'], bounds['lon_max'])
        }
    )
    
    return ds_recortado


def extraer_periodo(ds, year_start, year_end):
    """
    Extrae un período temporal específico del dataset.
    
    Args:
        ds: xarray.Dataset con dimensión time
        year_start: Año inicial
        year_end: Año final
    
    Returns:
        xarray.Dataset filtrado
    """
    return ds.sel(time=slice(f"{year_start}-01-01", f"{year_end}-12-31"))


def calcular_climatologia_mensual(ds, variable):
    """
    Calcula la climatología mensual (media de cada mes).
    
    Args:
        ds: xarray.Dataset
        variable: nombre de la variable
    
    Returns:
        xarray.Dataset con climatología mensual
    """
    return ds[variable].groupby('time.month').mean(dim='time')


def generar_reporte_descarga(resultados, ruta_salida):
    """Genera un reporte de auditoría de las descargas."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    reporte_path = ruta_salida / f"REPORTE_DESCARGA_BASD_{timestamp}.txt"
    
    with open(reporte_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("REPORTE DE DESCARGA - BASD-CMIP6-PE\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Dataset DOI: {BASD_CONFIG['doi']}\n")
        f.write(f"Citación: {BASD_CONFIG['citation']}\n\n")
        
        f.write("-" * 70 + "\n")
        f.write("RESUMEN DE DESCARGAS\n")
        f.write("-" * 70 + "\n\n")
        
        exitosos = sum(1 for r in resultados if r['status'] == 'OK')
        fallidos = sum(1 for r in resultados if r['status'] == 'ERROR')
        
        f.write(f"Total archivos: {len(resultados)}\n")
        f.write(f"Exitosos: {exitosos}\n")
        f.write(f"Fallidos: {fallidos}\n\n")
        
        if fallidos > 0:
            f.write("-" * 70 + "\n")
            f.write("ARCHIVOS FALLIDOS (requieren descarga manual)\n")
            f.write("-" * 70 + "\n\n")
            for r in resultados:
                if r['status'] == 'ERROR':
                    f.write(f"  - {r['archivo']}\n")
                    f.write(f"    URL: {r['url']}\n")
                    f.write(f"    Error: {r.get('error', 'Desconocido')}\n\n")
    
    return reporte_path


# =============================================================================
# FUNCIÓN PRINCIPAL DE DESCARGA
# =============================================================================

def descargar_basd_cmip6_pe(
    variables=None,
    gcms=None,
    ssps=None,
    solo_periodos_interes=True,
    metodo='http'
):
    """
    Descarga datos BASD-CMIP6-PE y los recorta a Imbabura.
    
    Args:
        variables: Lista de variables (default: todas)
        gcms: Lista de GCMs (default: todos)
        ssps: Lista de SSPs (default: todos)
        solo_periodos_interes: Si True, solo descarga períodos relevantes para la tesis
        metodo: 'http' o 'ftp'
    
    Returns:
        dict: Resultados de la descarga
    """
    # Valores por defecto
    if variables is None:
        variables = BASD_CONFIG['variables']
    if gcms is None:
        gcms = BASD_CONFIG['gcms']
    if ssps is None:
        ssps = BASD_CONFIG['ssps']
    
    # Cargar bounds de Imbabura
    bounds = cargar_aoi_bounds()
    print(f"\nBounds de Imbabura (con buffer): {bounds}")
    
    # Determinar segmentos a descargar
    if solo_periodos_interes:
        # Filtrar solo los segmentos que coinciden con períodos de interés
        hist_segments = [
            (y1, y2) for y1, y2 in BASD_CONFIG['historical_segments']
            if y2 >= PERIODOS_INTERES['historico']['inicio'] and 
               y1 <= PERIODOS_INTERES['historico']['fin']
        ]
        fut_segments = [
            (y1, y2) for y1, y2 in BASD_CONFIG['future_segments']
            if any(
                y2 >= p['inicio'] and y1 <= p['fin']
                for k, p in PERIODOS_INTERES.items() if k != 'historico'
            )
        ]
    else:
        hist_segments = BASD_CONFIG['historical_segments']
        fut_segments = BASD_CONFIG['future_segments']
    
    print(f"\nSegmentos históricos a descargar: {len(hist_segments)}")
    print(f"Segmentos futuros a descargar: {len(fut_segments)} por SSP")
    
    resultados = []
    
    # =========================================================================
    # DESCARGAR DATOS HISTÓRICOS
    # =========================================================================
    print("\n" + "=" * 70)
    print("DESCARGANDO PERÍODO HISTÓRICO")
    print("=" * 70)
    
    for variable in variables:
        for gcm in gcms:
            for y1, y2 in hist_segments:
                filename = construir_nombre_archivo(variable, gcm, "historical", y1, y2)
                destino = RUTA_RAW / "historical" / gcm / filename
                destino.parent.mkdir(parents=True, exist_ok=True)
                
                # Verificar si ya existe
                if destino.exists():
                    print(f"  [✓] Ya existe: {filename}")
                    resultados.append({
                        'archivo': filename,
                        'status': 'OK',
                        'metodo': 'existente'
                    })
                    continue
                
                print(f"\n  [→] Descargando: {filename}")
                
                # Intentar descarga HTTP
                url = construir_url_pik(variable, gcm, "historical", y1, y2)
                print(f"      URL: {url}")
                
                if descargar_archivo_http(url, destino):
                    resultados.append({
                        'archivo': filename,
                        'status': 'OK',
                        'metodo': 'http',
                        'url': url
                    })
                else:
                    resultados.append({
                        'archivo': filename,
                        'status': 'ERROR',
                        'metodo': 'http',
                        'url': url,
                        'error': 'Descarga fallida'
                    })
    
    # =========================================================================
    # DESCARGAR DATOS FUTUROS (por SSP)
    # =========================================================================
    for ssp in ssps:
        print("\n" + "=" * 70)
        print(f"DESCARGANDO ESCENARIO {ssp.upper()}")
        print("=" * 70)
        
        for variable in variables:
            for gcm in gcms:
                for y1, y2 in fut_segments:
                    filename = construir_nombre_archivo(variable, gcm, ssp, y1, y2)
                    destino = RUTA_RAW / ssp / gcm / filename
                    destino.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Verificar si ya existe
                    if destino.exists():
                        print(f"  [✓] Ya existe: {filename}")
                        resultados.append({
                            'archivo': filename,
                            'status': 'OK',
                            'metodo': 'existente'
                        })
                        continue
                    
                    print(f"\n  [→] Descargando: {filename}")
                    
                    url = construir_url_pik(variable, gcm, ssp, y1, y2)
                    print(f"      URL: {url}")
                    
                    if descargar_archivo_http(url, destino):
                        resultados.append({
                            'archivo': filename,
                            'status': 'OK',
                            'metodo': 'http',
                            'url': url
                        })
                    else:
                        resultados.append({
                            'archivo': filename,
                            'status': 'ERROR',
                            'metodo': 'http',
                            'url': url,
                            'error': 'Descarga fallida'
                        })
    
    return resultados


def generar_lista_descarga_manual():
    """
    Genera una lista de URLs para descarga manual en navegador.
    
    Útil cuando el acceso automático está bloqueado.
    """
    bounds = cargar_aoi_bounds()
    
    # Solo períodos de interés
    hist_segments = [
        (y1, y2) for y1, y2 in BASD_CONFIG['historical_segments']
        if y2 >= PERIODOS_INTERES['historico']['inicio'] and 
           y1 <= PERIODOS_INTERES['historico']['fin']
    ]
    fut_segments = [
        (y1, y2) for y1, y2 in BASD_CONFIG['future_segments']
        if any(
            y2 >= p['inicio'] and y1 <= p['fin']
            for k, p in PERIODOS_INTERES.items() if k != 'historico'
        )
    ]
    
    urls = []
    
    # Histórico
    for variable in BASD_CONFIG['variables']:
        for gcm in BASD_CONFIG['gcms']:
            for y1, y2 in hist_segments:
                url = construir_url_pik(variable, gcm, "historical", y1, y2)
                urls.append({
                    'url': url,
                    'destino': f"raw/historical/{gcm}/{construir_nombre_archivo(variable, gcm, 'historical', y1, y2)}"
                })
    
    # Futuros
    for ssp in BASD_CONFIG['ssps']:
        for variable in BASD_CONFIG['variables']:
            for gcm in BASD_CONFIG['gcms']:
                for y1, y2 in fut_segments:
                    url = construir_url_pik(variable, gcm, ssp, y1, y2)
                    urls.append({
                        'url': url,
                        'destino': f"raw/{ssp}/{gcm}/{construir_nombre_archivo(variable, gcm, ssp, y1, y2)}"
                    })
    
    # Guardar lista
    lista_path = RUTA_DATOS / "LISTA_DESCARGA_MANUAL.txt"
    with open(lista_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("LISTA DE ARCHIVOS PARA DESCARGA MANUAL - BASD-CMIP6-PE\n")
        f.write("=" * 80 + "\n\n")
        f.write("Instrucciones:\n")
        f.write("1. Abrir cada URL en el navegador\n")
        f.write("2. Guardar el archivo en la carpeta indicada en 'destino'\n")
        f.write("3. Ejecutar el script de procesamiento una vez descargados\n\n")
        f.write(f"Total de archivos: {len(urls)}\n")
        f.write(f"Carpeta base: {RUTA_DATOS}\n\n")
        f.write("-" * 80 + "\n\n")
        
        for i, item in enumerate(urls, 1):
            f.write(f"[{i:04d}] {item['url']}\n")
            f.write(f"       -> {item['destino']}\n\n")
    
    print(f"\n[✓] Lista de descarga manual guardada en: {lista_path}")
    print(f"    Total de archivos: {len(urls)}")
    
    return urls


# =============================================================================
# EJECUCIÓN PRINCIPAL
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("SCRIPT 01: DESCARGA Y PROCESAMIENTO DE BASD-CMIP6-PE")
    print("Versión 1.1.0")
    print("=" * 70)
    print(f"\nFecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Área de estudio: Imbabura, Ecuador")
    
    # Verificar AOI
    if not AOI_PATH.exists():
        print(f"\n[ERROR] No se encontró el AOI: {AOI_PATH}")
        exit(1)
    
    bounds = cargar_aoi_bounds()
    print(f"Bounds (con buffer 0.1°): {bounds}")
    
    # Copiar AOI al proyecto
    AOI_PROYECTO = RUTA_BASE / "02_DATOS" / "limites" / "imbabura" / "AOI_IMBABURA_CANTON.gpkg"
    if not AOI_PROYECTO.exists():
        AOI_PROYECTO.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(AOI_PATH, AOI_PROYECTO)
        print(f"\n[✓] AOI copiado a: {AOI_PROYECTO}")
    
    print("\n" + "=" * 70)
    print("INFORMACIÓN DEL DATASET")
    print("=" * 70)
    print(f"DOI: {BASD_CONFIG['doi']}")
    print(f"Resolución: {BASD_CONFIG['resolution_spatial']}")
    print(f"Variables: {', '.join(BASD_CONFIG['variables'])}")
    print(f"GCMs: {len(BASD_CONFIG['gcms'])} modelos")
    print(f"SSPs: {', '.join(BASD_CONFIG['ssps'])}")
    
    print("\n" + "=" * 70)
    print("PERÍODOS DE INTERÉS PARA LA TESIS")
    print("=" * 70)
    for nombre, periodo in PERIODOS_INTERES.items():
        print(f"  - {nombre}: {periodo['inicio']}-{periodo['fin']}")
    
    # Preguntar método de descarga
    print("\n" + "=" * 70)
    print("OPCIONES DE DESCARGA")
    print("=" * 70)
    print("1. Intentar descarga automática (HTTP)")
    print("2. Generar lista para descarga manual (si HTTP falla)")
    print("3. Procesar archivos ya descargados")
    
    opcion = input("\nSeleccione opción [1/2/3]: ").strip()
    
    if opcion == "1":
        # Intentar descarga automática
        print("\n[→] Iniciando descarga automática...")
        resultados = descargar_basd_cmip6_pe(
            solo_periodos_interes=True,
            metodo='http'
        )
        
        # Generar reporte
        reporte = generar_reporte_descarga(
            resultados, 
            RUTA_DOCUMENTACION / "reportes_auditoria"
        )
        print(f"\n[✓] Reporte guardado en: {reporte}")
        
        # Verificar si hay errores
        errores = sum(1 for r in resultados if r['status'] == 'ERROR')
        if errores > 0:
            print(f"\n[!] ADVERTENCIA: {errores} archivos no pudieron descargarse")
            print("    Generando lista para descarga manual...")
            generar_lista_descarga_manual()
    
    elif opcion == "2":
        # Generar lista para descarga manual
        generar_lista_descarga_manual()
    
    elif opcion == "3":
        # Procesar archivos existentes
        print("\n[→] Verificando archivos existentes...")
        # TODO: Implementar procesamiento de archivos ya descargados
        print("    Funcionalidad en desarrollo")
    
    print("\n" + "=" * 70)
    print("SCRIPT FINALIZADO")
    print("=" * 70)