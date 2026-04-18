"""
Script publicado como parte del Geoportal Riesgo Agroclimático — Imbabura, Ecuador
Pinto Páez, V. H. (2026). https://doi.org/10.5281/zenodo.19288559
Licencia: CC BY 4.0

NOTA: este archivo fue sanitizado para publicación pública.
- Credenciales (API keys, tokens, service accounts) removidas → <REDACTED_*>
- Rutas absolutas locales sustituidas por <RUTA_LOCAL>
Antes de ejecutar, configure sus propias rutas de entrada/salida y credenciales.

Archivo original: SCRIPT 05A v1.0 DESCARGA Y LIMPIEZA DE OCURRENCIAS GBIF.py
"""

#!/usr/bin/env python3
"""
======================================================================
  SCRIPT 05A v1.0: DESCARGA Y LIMPIEZA DE OCURRENCIAS GBIF
  Riesgo Agroclimático - Imbabura, Ecuador
  
  Componente: VULNERABILIDAD (aptitud climática vía RF/SDM)
  Marco: IPCC AR5/AR6 → Riesgo = f(Peligro × Exposición × Vulnerabilidad)
  
  Objetivo: Obtener registros de presencia georreferenciados de los 4
  cultivos andinos como variable respuesta para el Random Forest (SDM).
  Dominio de calibración: Región Andina (EC, PE, BO, CO).
======================================================================

DECISIONES METODOLÓGICAS:
  D1: Área de calibración = Región Andina completa (EC, PE, BO, CO)
      Justificación: Peterson et al. (2011) establecen que el área de 
      calibración debe cubrir el rango ambiental accesible de la especie.
      Barve et al. (2011) demuestran que restringir el dominio de 
      entrenamiento distorsiona las funciones de respuesta del SDM.
      Referencia: Peterson et al. (2011). Ecological Niches and Geographic 
      Distributions. Princeton University Press.
      Barve et al. (2011). Diversity and Distributions, 17(6), 1183-1194.

  D2: Búsqueda por scientificName en lugar de taxonKey
      Justificación: Algunos registros GBIF no están mapeados al taxonKey 
      del backbone taxonómico. La búsqueda por nombre captura registros 
      con identificación válida pero sin enlace taxonómico completo.
      Referencia: GBIF Secretariat (2024). GBIF Backbone Taxonomy.

  D3: Rarefacción espacial a resolución del raster climático (~0.1°)
      Justificación: Múltiples ocurrencias dentro del mismo píxel climático
      constituyen pseudo-réplicas que inflan artificialmente el peso de esa
      localidad en el entrenamiento del modelo (Boria et al., 2014).
      Referencia: Boria, R.A., Olson, L.E., Goodman, S.M. & Anderson, R.P. 
      (2014). Spatial filtering to reduce sampling bias. Ecological 
      Modelling, 283, 13-20.

  D4: Mínimo 50 registros por especie después de limpieza
      Justificación: Wisz et al. (2008) establecen que SDMs con <50 registros
      tienen desempeño significativamente menor. RF mantiene desempeño 
      aceptable con ≥30 registros (Mi et al., 2017).
      Referencia: Wisz et al. (2008). Diversity and Distributions, 14(5), 763-773.

EJECUCIÓN:
  %runfile '<RUTA_LOCAL>' --wdir
======================================================================
"""

import os
import sys
import json
import time
import logging
import requests
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

# ══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════
BASE_DIR = Path(r"<RUTA_LOCAL>")
OUTPUT_DIR = BASE_DIR / "02_DATOS" / "ocurrencias"
RAW_DIR = OUTPUT_DIR / "raw"
CLEAN_DIR = OUTPUT_DIR / "clean"
AUDITORIA_DIR = BASE_DIR / "05_DOCUMENTACION" / "reportes_auditoria"
METADATOS_DIR = BASE_DIR / "05_DOCUMENTACION" / "metadatos_iso"

for d in [RAW_DIR, CLEAN_DIR, AUDITORIA_DIR, METADATOS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

VERSION = "1.0.0"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# Resolución del raster climático BASD-CMIP6-PE para rarefacción
RASTER_RES = 0.1  # grados (~10 km)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(AUDITORIA_DIR / f"LOG_05A_{TIMESTAMP}.txt", encoding='utf-8')
    ]
)
log = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════
# ESPECIES DE ESTUDIO
# ══════════════════════════════════════════════════════════════
CULTIVOS = {
    "papa": {
        "nombre_cientifico": "Solanum tuberosum",
        "taxon_key": 2930137,
        "familia": "Solanaceae",
        "nombre_comun": "Papa"
    },
    "maiz": {
        "nombre_cientifico": "Zea mays",
        "taxon_key": 5290052,
        "familia": "Poaceae",
        "nombre_comun": "Maíz"
    },
    "frejol": {
        "nombre_cientifico": "Phaseolus vulgaris",
        "taxon_key": 2974859,
        "familia": "Fabaceae",
        "nombre_comun": "Fréjol"
    },
    "quinua": {
        "nombre_cientifico": "Chenopodium quinoa",
        "taxon_key": 3084041,
        "familia": "Amaranthaceae",
        "nombre_comun": "Quinua"
    }
}

# Países de la Región Andina (área de calibración del SDM)
PAISES = {
    "EC": "Ecuador",
    "PE": "Perú",
    "BO": "Bolivia",
    "CO": "Colombia"
}

# Parámetros de descarga
MAX_REGISTROS_POR_PAIS = 5000   # Límite por consulta
MIN_REGISTROS_ESPECIE = 50      # Wisz et al. (2008)

# ══════════════════════════════════════════════════════════════
# FUNCIONES
# ══════════════════════════════════════════════════════════════

def descargar_gbif(nombre_cientifico, codigo_pais, limite=5000):
    """
    Descarga ocurrencias desde la API de GBIF.
    
    Parámetros:
        nombre_cientifico: str - Nombre científico de la especie
        codigo_pais: str - Código ISO 3166-1 alpha-2 del país
        limite: int - Máximo de registros a descargar
    
    Retorna:
        list - Lista de diccionarios con registros
    """
    url = "https://api.gbif.org/v1/occurrence/search"
    registros = []
    offset = 0
    page_size = 300  # Tamaño de página GBIF
    
    while offset < limite:
        params = {
            "scientificName": nombre_cientifico,
            "country": codigo_pais,
            "hasCoordinate": "true",
            "hasGeospatialIssue": "false",
            "limit": min(page_size, limite - offset),
            "offset": offset
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            resultados = data.get("results", [])
            if not resultados:
                break
            
            for r in resultados:
                registros.append({
                    "gbifID": r.get("gbifID"),
                    "scientificName": r.get("scientificName", ""),
                    "species": r.get("species", ""),
                    "decimalLatitude": r.get("decimalLatitude"),
                    "decimalLongitude": r.get("decimalLongitude"),
                    "coordinateUncertaintyInMeters": r.get("coordinateUncertaintyInMeters"),
                    "countryCode": r.get("countryCode", ""),
                    "year": r.get("year"),
                    "basisOfRecord": r.get("basisOfRecord", ""),
                    "institutionCode": r.get("institutionCode", ""),
                    "datasetKey": r.get("datasetKey", ""),
                    "issues": ",".join(r.get("issues", []))
                })
            
            if data.get("endOfRecords", True):
                break
            
            offset += page_size
            time.sleep(0.5)  # Respetar rate limits de GBIF
            
        except requests.exceptions.RequestException as e:
            log.warning(f"    Error descargando {nombre_cientifico} en {codigo_pais}: {e}")
            time.sleep(2)
            break
    
    return registros


def limpiar_ocurrencias(df, resolucion=0.1):
    """
    Limpieza y rarefacción espacial de ocurrencias.
    
    Pasos (cada uno con justificación):
      1. Eliminar registros sin coordenadas válidas
      2. Eliminar registros con coordenadas (0,0) - error conocido en GBIF
      3. Filtrar coordenadas fuera del rango de la región andina
      4. Eliminar duplicados exactos por coordenadas
      5. Rarefacción espacial: 1 registro por celda del raster climático
    
    Parámetros:
        df: DataFrame con columnas decimalLatitude, decimalLongitude
        resolucion: float - Tamaño de celda para rarefacción (grados)
    
    Retorna:
        DataFrame limpio
    """
    n_inicial = len(df)
    
    # 1. Coordenadas válidas
    df = df.dropna(subset=["decimalLatitude", "decimalLongitude"])
    n_sin_na = len(df)
    
    # 2. Eliminar (0, 0)
    df = df[~((df["decimalLatitude"].abs() < 0.01) & 
              (df["decimalLongitude"].abs() < 0.01))]
    n_sin_cero = len(df)
    
    # 3. Filtrar rango de la región andina
    # Lat: -25 a 15 (Bolivia sur a Colombia norte)
    # Lon: -85 a -55 (Pacífico a Amazonía occidental)
    df = df[
        (df["decimalLatitude"] >= -25) & (df["decimalLatitude"] <= 15) &
        (df["decimalLongitude"] >= -85) & (df["decimalLongitude"] <= -55)
    ]
    n_en_rango = len(df)
    
    # 4. Duplicados exactos
    df = df.drop_duplicates(subset=["decimalLatitude", "decimalLongitude"])
    n_sin_dup = len(df)
    
    # 5. Rarefacción espacial (Boria et al., 2014)
    # Asignar cada punto a una celda del raster
    df = df.copy()
    df["cell_lat"] = (df["decimalLatitude"] / resolucion).round(0)
    df["cell_lon"] = (df["decimalLongitude"] / resolucion).round(0)
    df = df.drop_duplicates(subset=["cell_lat", "cell_lon"])
    df = df.drop(columns=["cell_lat", "cell_lon"])
    n_rarefaccion = len(df)
    
    stats = {
        "n_inicial": n_inicial,
        "n_sin_na": n_sin_na,
        "n_sin_cero": n_sin_cero,
        "n_en_rango": n_en_rango,
        "n_sin_dup": n_sin_dup,
        "n_rarefaccion": n_rarefaccion,
        "eliminados_na": n_inicial - n_sin_na,
        "eliminados_cero": n_sin_na - n_sin_cero,
        "eliminados_rango": n_sin_cero - n_en_rango,
        "eliminados_dup": n_en_rango - n_sin_dup,
        "eliminados_rarefaccion": n_sin_dup - n_rarefaccion
    }
    
    return df, stats


# ══════════════════════════════════════════════════════════════
# EJECUCIÓN PRINCIPAL
# ══════════════════════════════════════════════════════════════

print("=" * 70)
print("  SCRIPT 05A v1.0 — DESCARGA Y LIMPIEZA DE OCURRENCIAS GBIF")
print("  Riesgo Agroclimático Imbabura")
print("  Componente: VULNERABILIDAD (SDM con Random Forest)")
print("=" * 70)

log.info("=" * 70)
log.info("SCRIPT 05A v1.0: DESCARGA Y LIMPIEZA DE OCURRENCIAS GBIF")
log.info("=" * 70)
log.info(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
log.info(f"Versión: {VERSION}")

t_inicio = time.time()

# ──────────────────────────────────────────────────────────────
# [1/3] DESCARGA DE OCURRENCIAS
# ──────────────────────────────────────────────────────────────
log.info("")
log.info("=" * 70)
log.info("[1/3] DESCARGA DE OCURRENCIAS GBIF")
log.info("=" * 70)
log.info("  DECISIÓN D1: Área de calibración = Región Andina (EC, PE, BO, CO)")
log.info("    Justificación: Peterson et al. (2011) - el área de calibración debe")
log.info("    cubrir el rango ambiental accesible de la especie.")
log.info("    Barve et al. (2011) - restringir el dominio distorsiona funciones de respuesta.")
log.info("  DECISIÓN D2: Búsqueda por scientificName (captura registros sin taxonKey)")
log.info("")

resumen_descarga = {}

for cultivo_id, info in CULTIVOS.items():
    log.info(f"  Descargando {info['nombre_comun']} ({info['nombre_cientifico']})...")
    
    todos_registros = []
    
    for pais_code, pais_nombre in PAISES.items():
        registros = descargar_gbif(info["nombre_cientifico"], pais_code, MAX_REGISTROS_POR_PAIS)
        log.info(f"    {pais_nombre} ({pais_code}): {len(registros)} registros")
        todos_registros.extend(registros)
    
    # Guardar raw
    df_raw = pd.DataFrame(todos_registros)
    archivo_raw = RAW_DIR / f"ocurrencias_{cultivo_id}_raw_{TIMESTAMP}.csv"
    df_raw.to_csv(archivo_raw, index=False, encoding='utf-8')
    
    total = len(df_raw)
    log.info(f"    TOTAL {info['nombre_comun']}: {total} registros")
    log.info(f"    ✓ Guardado: {archivo_raw.name}")
    
    resumen_descarga[cultivo_id] = {
        "nombre_cientifico": info["nombre_cientifico"],
        "total_raw": total,
        "por_pais": {pc: len([r for r in todos_registros if r.get("countryCode") == pc]) 
                     for pc in PAISES.keys()},
        "archivo_raw": str(archivo_raw)
    }
    
    log.info("")

# Tabla resumen de descarga
log.info("  Resumen de descarga:")
log.info(f"  {'Cultivo':<12s} {'Ecuador':>8s} {'Perú':>8s} {'Bolivia':>8s} {'Colombia':>8s} {'TOTAL':>8s}")
log.info(f"  {'-'*12} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")
total_general = 0
for cultivo_id, datos in resumen_descarga.items():
    pp = datos["por_pais"]
    total = datos["total_raw"]
    total_general += total
    log.info(f"  {CULTIVOS[cultivo_id]['nombre_comun']:<12s} {pp.get('EC',0):>8d} {pp.get('PE',0):>8d} "
             f"{pp.get('BO',0):>8d} {pp.get('CO',0):>8d} {total:>8d}")
log.info(f"  {'TOTAL':<12s} {'':>8s} {'':>8s} {'':>8s} {'':>8s} {total_general:>8d}")

# ──────────────────────────────────────────────────────────────
# [2/3] LIMPIEZA Y RAREFACCIÓN
# ──────────────────────────────────────────────────────────────
log.info("")
log.info("=" * 70)
log.info("[2/3] LIMPIEZA Y RAREFACCIÓN ESPACIAL")
log.info("=" * 70)
log.info("  DECISIÓN D3: Rarefacción a resolución 0.1° (~10 km) del raster BASD-CMIP6-PE")
log.info("    Justificación: Boria et al. (2014) - múltiples ocurrencias en el mismo")
log.info("    píxel climático son pseudo-réplicas que sesgan el modelo.")
log.info("  DECISIÓN D4: Mínimo 50 registros por especie (Wisz et al., 2008)")
log.info("")

resumen_limpieza = {}
datasets_limpios = {}
cultivos_aprobados = []
cultivos_insuficientes = []

for cultivo_id, info in CULTIVOS.items():
    archivo_raw = RAW_DIR / f"ocurrencias_{cultivo_id}_raw_{TIMESTAMP}.csv"
    df = pd.read_csv(archivo_raw)
    
    log.info(f"  Limpiando {info['nombre_comun']} ({len(df)} registros raw)...")
    
    df_limpio, stats = limpiar_ocurrencias(df, resolucion=RASTER_RES)
    
    log.info(f"    Paso 1 - Sin coordenadas:      -{stats['eliminados_na']}")
    log.info(f"    Paso 2 - Coordenadas (0,0):     -{stats['eliminados_cero']}")
    log.info(f"    Paso 3 - Fuera de rango andino: -{stats['eliminados_rango']}")
    log.info(f"    Paso 4 - Duplicados exactos:    -{stats['eliminados_dup']}")
    log.info(f"    Paso 5 - Rarefacción {RASTER_RES}°:      -{stats['eliminados_rarefaccion']}")
    log.info(f"    RESULTADO: {len(df_limpio)} registros limpios")
    
    # Verificar mínimo
    if len(df_limpio) >= MIN_REGISTROS_ESPECIE:
        log.info(f"    ✓ Cumple mínimo ({len(df_limpio)} ≥ {MIN_REGISTROS_ESPECIE})")
        cultivos_aprobados.append(cultivo_id)
    else:
        log.warning(f"    ⚠ BAJO MÍNIMO ({len(df_limpio)} < {MIN_REGISTROS_ESPECIE})")
        cultivos_insuficientes.append(cultivo_id)
    
    # Guardar limpio
    archivo_limpio = CLEAN_DIR / f"ocurrencias_{cultivo_id}_clean_{TIMESTAMP}.csv"
    df_limpio.to_csv(archivo_limpio, index=False, encoding='utf-8')
    log.info(f"    ✓ Guardado: {archivo_limpio.name}")
    
    datasets_limpios[cultivo_id] = df_limpio
    resumen_limpieza[cultivo_id] = {
        **stats,
        "n_final": len(df_limpio),
        "cumple_minimo": len(df_limpio) >= MIN_REGISTROS_ESPECIE,
        "archivo_limpio": str(archivo_limpio)
    }
    
    # Distribución por país después de limpieza
    if len(df_limpio) > 0:
        dist_pais = df_limpio["countryCode"].value_counts().to_dict()
        log.info(f"    Distribución: {dist_pais}")
    
    log.info("")

# Tabla resumen limpieza
log.info("  Resumen de limpieza:")
log.info(f"  {'Cultivo':<12s} {'Raw':>8s} {'Limpio':>8s} {'Retención':>10s} {'Estado':>12s}")
log.info(f"  {'-'*12} {'-'*8} {'-'*8} {'-'*10} {'-'*12}")
for cultivo_id, stats in resumen_limpieza.items():
    retencion = (stats["n_final"] / stats["n_inicial"] * 100) if stats["n_inicial"] > 0 else 0
    estado = "✓ APROBADO" if stats["cumple_minimo"] else "⚠ INSUFICIENTE"
    log.info(f"  {CULTIVOS[cultivo_id]['nombre_comun']:<12s} {stats['n_inicial']:>8d} "
             f"{stats['n_final']:>8d} {retencion:>9.1f}% {estado:>12s}")

# ──────────────────────────────────────────────────────────────
# [3/3] PRODUCTOS Y DOCUMENTACIÓN
# ──────────────────────────────────────────────────────────────
log.info("")
log.info("=" * 70)
log.info("[3/3] PRODUCTOS Y DOCUMENTACIÓN")
log.info("=" * 70)

# Dataset consolidado (todos los cultivos)
frames = []
for cultivo_id, df in datasets_limpios.items():
    df_temp = df.copy()
    df_temp["cultivo"] = cultivo_id
    df_temp["nombre_cientifico"] = CULTIVOS[cultivo_id]["nombre_cientifico"]
    frames.append(df_temp)

df_consolidado = pd.concat(frames, ignore_index=True)
archivo_consolidado = CLEAN_DIR / f"ocurrencias_todas_clean_{TIMESTAMP}.csv"
df_consolidado.to_csv(archivo_consolidado, index=False, encoding='utf-8')
log.info(f"  ✓ Dataset consolidado: {archivo_consolidado.name} ({len(df_consolidado)} registros)")

# Reporte de auditoría
reporte = {
    "script": "05A",
    "version": VERSION,
    "timestamp": TIMESTAMP,
    "objetivo": "Descarga y limpieza de ocurrencias GBIF para SDM (componente Vulnerabilidad)",
    "area_calibracion": "Región Andina (EC, PE, BO, CO)",
    "resolucion_rarefaccion_grados": RASTER_RES,
    "minimo_registros": MIN_REGISTROS_ESPECIE,
    "descarga": resumen_descarga,
    "limpieza": resumen_limpieza,
    "cultivos_aprobados": cultivos_aprobados,
    "cultivos_insuficientes": cultivos_insuficientes,
    "decisiones": {
        "D1": "Área calibración = Región Andina. Ref: Peterson et al. (2011), Barve et al. (2011)",
        "D2": "Búsqueda por scientificName. Ref: GBIF Secretariat (2024)",
        "D3": f"Rarefacción a {RASTER_RES}° (~10 km). Ref: Boria et al. (2014)",
        "D4": f"Mínimo {MIN_REGISTROS_ESPECIE} registros. Ref: Wisz et al. (2008)"
    },
    "archivos_generados": {
        "raw": [str(RAW_DIR / f"ocurrencias_{c}_raw_{TIMESTAMP}.csv") for c in CULTIVOS],
        "clean": [str(CLEAN_DIR / f"ocurrencias_{c}_clean_{TIMESTAMP}.csv") for c in CULTIVOS],
        "consolidado": str(archivo_consolidado)
    }
}

archivo_reporte = AUDITORIA_DIR / f"REPORTE_05A_{TIMESTAMP}.json"
with open(archivo_reporte, 'w', encoding='utf-8') as f:
    json.dump(reporte, f, indent=2, ensure_ascii=False)
log.info(f"  ✓ Reporte: {archivo_reporte.name}")

# Metadatos ISO 19115
metadatos = {
    "fileIdentifier": f"SCRIPT_05A_v{VERSION}_{TIMESTAMP}",
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
        "title": "Ocurrencias GBIF de cultivos andinos para SDM",
        "abstract": "Registros de presencia de papa, maíz, fréjol y quinua "
                    "descargados de GBIF, limpiados y rarefactados a resolución "
                    "0.1° para entrenamiento de Random Forest como SDM.",
        "purpose": "Variable respuesta del componente de Vulnerabilidad "
                   "en el modelo de riesgo agroclimático IPCC AR5/AR6",
        "topicCategory": "farming",
        "extent": {
            "geographicElement": {
                "westBoundLongitude": -85.0,
                "eastBoundLongitude": -55.0,
                "southBoundLatitude": -25.0,
                "northBoundLatitude": 15.0
            }
        },
        "spatialResolution": f"{RASTER_RES}° ({RASTER_RES * 111:.0f} km)"
    },
    "dataQualityInfo": {
        "lineage": {
            "source": "GBIF API v1 (https://api.gbif.org/v1/occurrence/search)",
            "processSteps": [
                "Descarga por scientificName con hasCoordinate=true",
                "Eliminación de registros sin coordenadas",
                "Eliminación de coordenadas (0,0)",
                "Filtrado por rango geográfico andino",
                "Eliminación de duplicados exactos",
                f"Rarefacción espacial a {RASTER_RES}° (Boria et al., 2014)"
            ]
        }
    },
    "distributionInfo": {
        "transferOptions": {
            "onLine": {
                "linkage": "https://doi.org/10.15468/39omei",
                "name": "GBIF Backbone Taxonomy",
                "protocol": "REST API"
            }
        }
    }
}

archivo_meta = METADATOS_DIR / f"ISO19115_SCRIPT_05A_{TIMESTAMP}.json"
with open(archivo_meta, 'w', encoding='utf-8') as f:
    json.dump(metadatos, f, indent=2, ensure_ascii=False)
log.info(f"  ✓ Metadatos ISO: {archivo_meta.name}")

# ──────────────────────────────────────────────────────────────
# RESUMEN FINAL
# ──────────────────────────────────────────────────────────────
duracion = time.time() - t_inicio

log.info("")
log.info("=" * 70)
log.info("  SCRIPT 05A v1.0 COMPLETADO")
log.info("=" * 70)
log.info(f"  Duración: {duracion:.0f} segundos")
log.info(f"  Cultivos descargados: {len(CULTIVOS)}")
log.info(f"  Cultivos aprobados (≥{MIN_REGISTROS_ESPECIE} registros): {len(cultivos_aprobados)}")
if cultivos_insuficientes:
    log.info(f"  Cultivos insuficientes: {cultivos_insuficientes}")
log.info(f"  Total registros limpios: {len(df_consolidado)}")
log.info(f"  Decisiones documentadas: 4")
log.info(f"  Productos en: {OUTPUT_DIR}")
log.info("=" * 70)

# Verificación de criterios
log.info("")
log.info("VERIFICACIÓN DE CRITERIOS:")
log.info(f"  {'Criterio':<45s} {'Requerido':<15s} {'Cumple'}")
log.info(f"  {'-'*45} {'-'*15} {'-'*8}")

c1 = len(CULTIVOS) == 4
log.info(f"  {'4 cultivos descargados':<45s} {'4':<15s} {'✓ SÍ' if c1 else '✗ NO'}")

c2 = all(resumen_descarga[c]["total_raw"] > 0 for c in CULTIVOS)
log.info(f"  {'Todos con registros raw > 0':<45s} {'Sí':<15s} {'✓ SÍ' if c2 else '✗ NO'}")

c3 = len(cultivos_aprobados) >= 3
log.info(f"  {'≥3 cultivos con ≥{0} registros limpios'.format(MIN_REGISTROS_ESPECIE):<45s} {'≥ 3':<15s} {'✓ SÍ' if c3 else '⚠ PARCIAL'} ({len(cultivos_aprobados)})")

c4 = True  # Siempre se genera
log.info(f"  {'Rarefacción espacial aplicada':<45s} {f'{RASTER_RES}°':<15s} {'✓ SÍ'}")

c5 = True  # Siempre se genera
log.info(f"  {'Metadatos ISO 19115':<45s} {'Sí':<15s} {'✓ SÍ'}")

# Estado final
if c1 and c2 and c3:
    log.info("")
    log.info("ESTADO: APROBADO")
    log.info("")
    log.info("SIGUIENTE PASO:")
    log.info("  Script 05B: Cálculo de índices agroclimáticos para dominio completo")
    log.info("  (usa datos raw/ de BASD-CMIP6-PE, 880 archivos, dominio Perú+Ecuador)")
else:
    log.info("")
    log.info("ESTADO: REQUIERE REVISIÓN")
    if cultivos_insuficientes:
        log.info(f"  Cultivos con datos insuficientes: {cultivos_insuficientes}")
        log.info("  Opciones: ampliar búsqueda, incluir más países, o documentar limitación")

print(f"\n  ✓ Script 05A completado. Resultados en: {OUTPUT_DIR}")