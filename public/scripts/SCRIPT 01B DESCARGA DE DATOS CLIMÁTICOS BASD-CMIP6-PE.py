"""
Script publicado como parte del Geoportal Riesgo Agroclimático — Imbabura, Ecuador
Pinto Páez, V. H. (2026). https://doi.org/10.5281/zenodo.19288559
Licencia: CC BY 4.0

NOTA: este archivo fue sanitizado para publicación pública.
- Credenciales (API keys, tokens, service accounts) removidas → <REDACTED_*>
- Rutas absolutas locales sustituidas por <RUTA_LOCAL>
Antes de ejecutar, configure sus propias rutas de entrada/salida y credenciales.

Archivo original: SCRIPT 01B DESCARGA DE DATOS CLIMÁTICOS BASD-CMIP6-PE.py
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
SCRIPT 01: DESCARGA DE DATOS CLIMÁTICOS BASD-CMIP6-PE
===============================================================================
Versión: 1.2.0
Fecha: 2026-02-01
Autor: Víctor Hugo Pinto Páez

CORRECCIÓN v1.2.0:
- Nombres de archivo EXACTOS del servidor (mantienen guiones y minúsculas)
- Variant IDs correctos: r1i1p1f2 para UKESM1-0-LL, CNRM-CM6-1, CNRM-ESM2-1
- Diccionario explícito GCM → (carpeta, prefijo_archivo, variant_id)
===============================================================================
"""

import os
import sys
import requests
from datetime import datetime
from pathlib import Path
import time

# =============================================================================
# CONFIGURACIÓN CORREGIDA - NOMBRES EXACTOS DEL SERVIDOR PIK-POTSDAM
# =============================================================================

# URL base del servidor PIK (verificada y funcionando)
URL_BASE = "https://www.pik-potsdam.de/data/doi10.5880PIK.2023.001/BASD-CMIP6-PE/daily"

# Diccionario con nombres EXACTOS: GCM → (nombre_carpeta, prefijo_archivo, variant_id)
# Verificado directamente del servidor el 2026-02-01
GCMS_CONFIG = {
    "CanESM5":       ("CanESM5",       "canesm5",       "r1i1p1f1"),
    "MIROC6":        ("MIROC6",        "miroc6",        "r1i1p1f1"),
    "IPSL-CM6A-LR":  ("IPSL-CM6A-LR",  "ipsl-cm6a-lr",  "r1i1p1f1"),
    "GFDL-ESM4":     ("GFDL-ESM4",     "gfdl-esm4",     "r1i1p1f1"),
    "MRI-ESM2-0":    ("MRI-ESM2-0",    "mri-esm2-0",    "r1i1p1f1"),
    "MPI-ESM1-2-HR": ("MPI-ESM1-2-HR", "mpi-esm1-2-hr", "r1i1p1f1"),
    "EC-Earth3":     ("EC-Earth3",     "ec-earth3",     "r1i1p1f1"),
    # Estos tres usan r1i1p1f2 (no f1)
    "UKESM1-0-LL":   ("UKESM1-0-LL",   "ukesm1-0-ll",   "r1i1p1f2"),
    "CNRM-CM6-1":    ("CNRM-CM6-1",    "cnrm-cm6-1",    "r1i1p1f2"),
    "CNRM-ESM2-1":   ("CNRM-ESM2-1",   "cnrm-esm2-1",   "r1i1p1f2"),
}

# Variables climáticas
VARIABLES = ["pr", "tas", "tasmin", "tasmax"]

# Experimentos
EXPERIMENTS = {
    "historical": "historical",
    "ssp126": "ssp126",
    "ssp370": "ssp370",
    "ssp585": "ssp585"
}

# Segmentos temporales EXACTOS del dataset
SEGMENTOS_HISTORICO = [
    (1981, 1990),
    (1991, 2000),
    (2001, 2010),
    (2011, 2014)
]

SEGMENTOS_FUTURO = [
    (2015, 2020),
    (2021, 2030),
    (2031, 2040),
    (2041, 2050),
    (2051, 2060),
    (2061, 2070),
    (2071, 2080),
    (2081, 2090),
    (2091, 2100)
]

# Períodos de interés para la tesis (subconjunto de segmentos)
PERIODOS_INTERES = {
    "historico": [(1981, 1990), (1991, 2000), (2001, 2010), (2011, 2014)],
    "futuro_cercano": [(2021, 2030), (2031, 2040)],
    "futuro_medio": [(2041, 2050), (2051, 2060)],
    "futuro_lejano": [(2061, 2070), (2071, 2080)]
}

# Directorio base de salida
DIR_SALIDA = Path(r"<RUTA_LOCAL>")


def construir_url(gcm_key, experiment, variable, year_start, year_end):
    """
    Construye la URL exacta para un archivo NetCDF.
    
    Formato real del servidor:
    {URL_BASE}/{experiment}/{GCM_FOLDER}/{prefix}_{variant}_{experiment}_{var}_daily_{y1}_{y2}.nc
    
    Ejemplo real:
    .../historical/IPSL-CM6A-LR/ipsl-cm6a-lr_r1i1p1f1_historical_pr_daily_1981_1990.nc
    """
    folder, prefix, variant = GCMS_CONFIG[gcm_key]
    filename = f"{prefix}_{variant}_{experiment}_{variable}_daily_{year_start}_{year_end}.nc"
    url = f"{URL_BASE}/{experiment}/{folder}/{filename}"
    return url, filename


def descargar_archivo(url, filepath, max_reintentos=3):
    """Descarga un archivo con reintentos y headers de navegador."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/octet-stream,*/*',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    for intento in range(max_reintentos):
        try:
            response = requests.get(url, headers=headers, stream=True, timeout=300)
            if response.status_code == 200:
                total_size = int(response.headers.get('content-length', 0))
                with open(filepath, 'wb') as f:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192*10):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                pct = (downloaded / total_size) * 100
                                print(f"\r  Progreso: {pct:.1f}% ({downloaded/1024/1024:.1f} MB)", end='')
                print()  # Nueva línea
                return True, None
            else:
                error = f"HTTP {response.status_code}"
        except requests.exceptions.Timeout:
            error = "Timeout"
        except requests.exceptions.RequestException as e:
            error = str(e)[:100]
        
        if intento < max_reintentos - 1:
            print(f"  Reintento {intento + 2}/{max_reintentos}...")
            time.sleep(5)
    
    return False, error


def generar_lista_descarga():
    """Genera lista de URLs para descarga manual."""
    lista = []
    
    # Histórico (todos los GCMs)
    for gcm in GCMS_CONFIG.keys():
        for var in VARIABLES:
            for y1, y2 in PERIODOS_INTERES["historico"]:
                url, filename = construir_url(gcm, "historical", var, y1, y2)
                lista.append((url, filename, "historical", gcm))
    
    # Futuros (todos los SSPs)
    for ssp in ["ssp126", "ssp370", "ssp585"]:
        for gcm in GCMS_CONFIG.keys():
            for var in VARIABLES:
                for periodo in ["futuro_cercano", "futuro_medio", "futuro_lejano"]:
                    for y1, y2 in PERIODOS_INTERES[periodo]:
                        url, filename = construir_url(gcm, ssp, var, y1, y2)
                        lista.append((url, filename, ssp, gcm))
    
    return lista


def main():
    """Función principal."""
    print("=" * 70)
    print("DESCARGA DE DATOS BASD-CMIP6-PE - VERSIÓN 1.2.0 (CORREGIDA)")
    print("=" * 70)
    print(f"\nFecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Dataset DOI: 10.5880/pik.2023.001")
    print(f"Citación: Fernandez-Palomino et al. (2024). Scientific Data, 11, 34.")
    
    print("\n" + "-" * 70)
    print("CORRECCIONES EN ESTA VERSIÓN:")
    print("-" * 70)
    print("1. Nombres de archivo mantienen guiones: ipsl-cm6a-lr, gfdl-esm4, etc.")
    print("2. Variant IDs correctos:")
    print("   - r1i1p1f1: CanESM5, MIROC6, IPSL-CM6A-LR, GFDL-ESM4, MRI-ESM2-0,")
    print("              MPI-ESM1-2-HR, EC-Earth3")
    print("   - r1i1p1f2: UKESM1-0-LL, CNRM-CM6-1, CNRM-ESM2-1")
    
    # Generar lista de archivos
    lista_descarga = generar_lista_descarga()
    total_archivos = len(lista_descarga)
    
    print(f"\n" + "-" * 70)
    print(f"ARCHIVOS A DESCARGAR: {total_archivos}")
    print("-" * 70)
    
    # Contar por experimento
    conteo = {}
    for _, _, exp, _ in lista_descarga:
        conteo[exp] = conteo.get(exp, 0) + 1
    for exp, n in sorted(conteo.items()):
        print(f"  {exp}: {n} archivos")
    
    # Menú de opciones
    print("\n" + "=" * 70)
    print("OPCIONES:")
    print("=" * 70)
    print("1. Descargar automáticamente (HTTP)")
    print("2. Generar lista de URLs para descarga manual")
    print("3. Procesar archivos ya descargados")
    print("4. Verificar URLs (test sin descargar)")
    print("0. Salir")
    
    opcion = input("\nSeleccione opción [1-4, 0]: ").strip()
    
    if opcion == "0":
        print("Saliendo...")
        return
    
    elif opcion == "4":
        # Verificar URLs sin descargar
        print("\n" + "=" * 70)
        print("VERIFICANDO URLs (primeros 5 de cada GCM)...")
        print("=" * 70)
        
        verificados = {}
        for gcm in GCMS_CONFIG.keys():
            url, filename = construir_url(gcm, "historical", "pr", 1981, 1990)
            try:
                response = requests.head(url, timeout=10)
                status = "✓ OK" if response.status_code == 200 else f"✗ HTTP {response.status_code}"
            except Exception as e:
                status = f"✗ Error: {str(e)[:30]}"
            verificados[gcm] = status
            print(f"  {gcm}: {status}")
            print(f"    URL: {url}")
        
        ok_count = sum(1 for s in verificados.values() if "OK" in s)
        print(f"\n{ok_count}/{len(GCMS_CONFIG)} GCMs verificados correctamente")
        return
    
    elif opcion == "2":
        # Generar lista para descarga manual
        lista_path = DIR_SALIDA / "LISTA_DESCARGA_MANUAL_v1.2.txt"
        lista_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(lista_path, 'w') as f:
            f.write("# LISTA DE URLs PARA DESCARGA MANUAL - BASD-CMIP6-PE\n")
            f.write(f"# Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total archivos: {total_archivos}\n")
            f.write("# \n")
            f.write("# Instrucciones:\n")
            f.write("# 1. Use un gestor de descargas como JDownloader, wget, o curl\n")
            f.write("# 2. Organice los archivos en carpetas: historical/, ssp126/, ssp370/, ssp585/\n")
            f.write("# 3. Dentro de cada carpeta, cree subcarpetas por GCM\n")
            f.write("#\n\n")
            
            current_exp = None
            current_gcm = None
            for url, filename, exp, gcm in lista_descarga:
                if exp != current_exp:
                    f.write(f"\n# === {exp.upper()} ===\n")
                    current_exp = exp
                    current_gcm = None
                if gcm != current_gcm:
                    f.write(f"\n# {gcm}\n")
                    current_gcm = gcm
                f.write(f"{url}\n")
        
        print(f"\n✓ Lista generada: {lista_path}")
        print(f"  Total URLs: {total_archivos}")
        return
    
    elif opcion == "1":
        # Descarga automática
        print("\n" + "=" * 70)
        print("INICIANDO DESCARGA AUTOMÁTICA")
        print("=" * 70)
        
        exitosos = 0
        fallidos = []
        
        for i, (url, filename, exp, gcm) in enumerate(lista_descarga, 1):
            # Crear directorio de destino
            folder, _, _ = GCMS_CONFIG[gcm]
            dir_destino = DIR_SALIDA / "raw" / exp / folder
            dir_destino.mkdir(parents=True, exist_ok=True)
            
            filepath = dir_destino / filename
            
            # Verificar si ya existe
            if filepath.exists() and filepath.stat().st_size > 1000000:  # > 1MB
                print(f"[{i}/{total_archivos}] Ya existe: {filename}")
                exitosos += 1
                continue
            
            print(f"\n[{i}/{total_archivos}] Descargando: {filename}")
            print(f"  GCM: {gcm} | Exp: {exp}")
            
            exito, error = descargar_archivo(url, filepath)
            
            if exito:
                print(f"  ✓ Completado")
                exitosos += 1
            else:
                print(f"  ✗ Error: {error}")
                fallidos.append((filename, url, error))
                # Eliminar archivo parcial si existe
                if filepath.exists():
                    filepath.unlink()
            
            # Pausa entre descargas para no sobrecargar servidor
            if i % 10 == 0:
                print(f"\n  --- Pausa de 2 segundos ---")
                time.sleep(2)
        
        # Reporte final
        print("\n" + "=" * 70)
        print("REPORTE DE DESCARGA")
        print("=" * 70)
        print(f"Total archivos: {total_archivos}")
        print(f"Exitosos: {exitosos}")
        print(f"Fallidos: {len(fallidos)}")
        
        # Guardar reporte
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reporte_path = DIR_SALIDA / f"REPORTE_DESCARGA_v1.2_{timestamp}.txt"
        
        with open(reporte_path, 'w') as f:
            f.write("=" * 70 + "\n")
            f.write("REPORTE DE DESCARGA - BASD-CMIP6-PE v1.2.0\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total archivos: {total_archivos}\n")
            f.write(f"Exitosos: {exitosos}\n")
            f.write(f"Fallidos: {len(fallidos)}\n\n")
            
            if fallidos:
                f.write("-" * 70 + "\n")
                f.write("ARCHIVOS FALLIDOS:\n")
                f.write("-" * 70 + "\n\n")
                for filename, url, error in fallidos:
                    f.write(f"  - {filename}\n")
                    f.write(f"    URL: {url}\n")
                    f.write(f"    Error: {error}\n\n")
        
        print(f"\nReporte guardado: {reporte_path}")
        
        if fallidos:
            print(f"\n⚠ {len(fallidos)} archivos requieren descarga manual.")
            print("  Consulte el reporte para ver las URLs.")
    
    elif opcion == "3":
        print("\n[Opción 3: Procesar archivos existentes - Por implementar]")
        print("Use el Script 02 para procesar los archivos descargados.")


if __name__ == "__main__":
    main()