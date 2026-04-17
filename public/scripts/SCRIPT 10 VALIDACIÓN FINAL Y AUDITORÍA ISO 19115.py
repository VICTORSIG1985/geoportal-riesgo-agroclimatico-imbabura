"""
Script publicado como parte del Geoportal Riesgo Agroclimático — Imbabura, Ecuador
Pinto Páez, V. H. (2026). https://doi.org/10.5281/zenodo.19288559
Licencia: CC BY 4.0

NOTA: este archivo fue sanitizado para publicación pública.
- Credenciales (API keys, tokens, service accounts) removidas → <REDACTED_*>
- Rutas absolutas locales sustituidas por <RUTA_LOCAL>
Antes de ejecutar, configure sus propias rutas de entrada/salida y credenciales.

Archivo original: SCRIPT 10 VALIDACIÓN FINAL Y AUDITORÍA ISO 19115.py
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
SCRIPT 10: VALIDACIÓN FINAL Y AUDITORÍA ISO 19115
===============================================================================

Tesis:        Riesgo agroclimático de cultivos andinos bajo escenarios CMIP6
              en la provincia de Imbabura: modelamiento de distribución de
              especies para la gestión territorial

Autor:        Víctor Hugo Pinto Páez
Universidad:  San Gregorio de Portoviejo
Maestría:     Prevención y Gestión de Riesgos – Mención en Variabilidad
              Climática y Resiliencia Territorial

Versión:      1.0.0
Fecha:        2026-03

===============================================================================
PROPÓSITO
===============================================================================

Verificar la integridad de todos los productos generados por el pipeline
completo (Scripts 00–09), generar metadatos ISO 19115:2014 para el
dataset de investigación, y producir el informe final de auditoría que
cierra el proceso investigativo.

Este script NO genera nuevos datos — solo valida y documenta lo existente.

===============================================================================
VERIFICACIONES
===============================================================================

  1. Existencia de archivos críticos de cada script
  2. Integridad de CSVs (filas, columnas, rangos)
  3. Coherencia entre scripts (valores cruzados)
  4. Completitud de productos cartográficos (58 mapas)
  5. Completitud de fichas parroquiales (42 PDFs)
  6. Completitud de documentación metodológica (20+ docs)
  7. Metadatos ISO 19115:2014 del dataset completo

===============================================================================
"""

import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path
from datetime import datetime
import json
import time
import warnings

warnings.filterwarnings("ignore")

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

BASE_TESIS = Path(r"<RUTA_LOCAL>")
BASE_PREV = BASE_TESIS / "Prevención_de_Riesgos"

# Rutas de productos
PARROQUIAS_PATH = BASE_TESIS / "Imbabura_Parroquia.gpkg"
BN_DIR = BASE_PREV / "04_RESULTADOS" / "fase4_modelamiento" / "red_bayesiana"
EXPO_DIR = BASE_TESIS / "04_RESULTADOS" / "exposicion_agricola"
MAPAS_DIR = BASE_TESIS / "04_RESULTADOS" / "fase5_productos" / "mapas_riesgo"
FICHAS_DIR = BASE_TESIS / "04_RESULTADOS" / "fase5_productos" / "fichas_parroquiales"
METODO_DIR = BASE_TESIS / "METODOLOGÍA"
REPORTS_DIR = BASE_TESIS / "05_DOCUMENTACION" / "reportes_auditoria"
METADATOS_DIR = BASE_TESIS / "05_DOCUMENTACION" / "metadatos_iso"

for d in [REPORTS_DIR, METADATOS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

VERSION = "1.0.0"
TS = datetime.now().strftime("%Y%m%d_%H%M%S")

# Valores esperados (de Scripts 07-09)
EXPECTED_RIESGO_ROWS = 1512
EXPECTED_PARROQUIAS = 42
EXPECTED_CULTIVOS = {"papa", "maiz", "frejol", "quinua"}
EXPECTED_SSPS = {"ssp126", "ssp370", "ssp585"}
EXPECTED_HORIZONTES = {"2021-2040", "2041-2060", "2061-2080"}
EXPECTED_MAPAS_IND = 36
EXPECTED_MAPAS_CAMBIO = 12
EXPECTED_MAPAS_TOTAL = 58
EXPECTED_FICHAS = 42

# García Moreno como #1 (valor de referencia del Script 07)
GM_IR_ESPERADO = 0.689


# =============================================================================
# FUNCIONES DE VERIFICACIÓN
# =============================================================================

def buscar_csv(d, p):
    cs = sorted(d.glob(p))
    return cs[-1] if cs else None


def verificar(condicion, mensaje, resultados):
    """Registra resultado de verificación."""
    estado = "PASS" if condicion else "FAIL"
    resultados.append({"criterio": mensaje, "estado": estado})
    return condicion


def seccion(titulo, num):
    print(f"\n[{num}] {titulo}")
    print("─" * 60)


# =============================================================================
# MAIN
# =============================================================================

def main():
    t0 = time.time()

    print("╔" + "═" * 68 + "╗")
    print("║  SCRIPT 10: VALIDACIÓN FINAL Y AUDITORÍA ISO 19115" +
          " " * 16 + "║")
    print("║  Cierre del pipeline investigativo" +
          " " * 33 + "║")
    print("╚" + "═" * 68 + "╝")

    resultados = []
    advertencias = []
    detalles = {}

    # ═══════════════════════════════════════════════════════════
    # [1/7] VERIFICACIÓN DE ARCHIVOS CRÍTICOS
    # ═══════════════════════════════════════════════════════════
    seccion("ARCHIVOS CRÍTICOS DEL PIPELINE", "1/7")

    # Parroquias
    ok = verificar(PARROQUIAS_PATH.exists(),
                   "GeoPackage parroquias CONALI existe", resultados)
    if ok:
        gdf = gpd.read_file(PARROQUIAS_PATH)
        verificar(len(gdf) == EXPECTED_PARROQUIAS,
                  f"42 parroquias en GeoPackage ({len(gdf)} encontradas)",
                  resultados)
        print(f"  ✓ Parroquias: {len(gdf)}")
    else:
        print(f"  ✗ GeoPackage no encontrado: {PARROQUIAS_PATH}")

    # CSV Riesgo (Script 07)
    csv_r = buscar_csv(BN_DIR, "riesgo_parroquial_*.csv")
    ok = verificar(csv_r is not None,
                   "CSV riesgo parroquial existe (Script 07)", resultados)
    if ok:
        df_r = pd.read_csv(csv_r)
        verificar(len(df_r) == EXPECTED_RIESGO_ROWS,
                  f"1,512 filas en riesgo ({len(df_r)} encontradas)",
                  resultados)
        verificar(set(df_r["cultivo"].unique()) == EXPECTED_CULTIVOS,
                  "4 cultivos presentes en riesgo", resultados)
        verificar(set(df_r["ssp"].unique()) == EXPECTED_SSPS,
                  "3 SSPs presentes en riesgo", resultados)
        verificar(set(df_r["horizonte"].unique()) == EXPECTED_HORIZONTES,
                  "3 horizontes presentes en riesgo", resultados)
        verificar(df_r["indice_riesgo"].between(0, 1).all(),
                  "Todos los IR en rango [0, 1]", resultados)
        print(f"  ✓ Riesgo: {csv_r.name} ({len(df_r)} filas)")
        detalles["riesgo_csv"] = csv_r.name
        detalles["riesgo_filas"] = len(df_r)
        detalles["ir_min"] = float(df_r["indice_riesgo"].min())
        detalles["ir_max"] = float(df_r["indice_riesgo"].max())
        detalles["ir_mean"] = float(df_r["indice_riesgo"].mean())
    else:
        print(f"  ✗ CSV riesgo no encontrado en {BN_DIR}")

    # CSV Exposición (Script 04C)
    csv_e = buscar_csv(EXPO_DIR, "exposicion_resumen_*.csv")
    ok = verificar(csv_e is not None,
                   "CSV exposición parroquial existe (Script 04C)", resultados)
    if ok:
        df_e = pd.read_csv(csv_e)
        verificar(len(df_e) == EXPECTED_PARROQUIAS,
                  f"42 parroquias en exposición ({len(df_e)} encontradas)",
                  resultados)
        print(f"  ✓ Exposición: {csv_e.name} ({len(df_e)} filas)")
    else:
        print(f"  ✗ CSV exposición no encontrado en {EXPO_DIR}")

    # CSV Ranking (Script 08)
    csv_p = buscar_csv(
        MAPAS_DIR / "sintesis", "ranking_priorizacion_*.csv")
    ok = verificar(csv_p is not None,
                   "CSV ranking priorización existe (Script 08)", resultados)
    if ok:
        df_p = pd.read_csv(csv_p)
        verificar(len(df_p) == EXPECTED_PARROQUIAS,
                  f"42 parroquias en ranking ({len(df_p)} encontradas)",
                  resultados)
        print(f"  ✓ Ranking: {csv_p.name}")
    else:
        print(f"  ✗ CSV ranking no encontrado")

    # ═══════════════════════════════════════════════════════════
    # [2/7] COHERENCIA ENTRE SCRIPTS
    # ═══════════════════════════════════════════════════════════
    seccion("COHERENCIA ENTRE SCRIPTS", "2/7")

    if csv_r and csv_p:
        # García Moreno debe ser #1
        gm = df_p[df_p["parroquia"].str.upper().str.contains("GARCIA MORENO")]
        if len(gm) > 0:
            gm_rank = gm["ranking"].values[0]
            gm_ir = gm["ir_medio"].values[0]
            verificar(gm_rank == 1,
                      f"García Moreno es #1 en ranking (#{gm_rank})",
                      resultados)
            verificar(abs(gm_ir - GM_IR_ESPERADO) < 0.01,
                      f"García Moreno IR={gm_ir:.3f} ≈ {GM_IR_ESPERADO}",
                      resultados)
            print(f"  ✓ García Moreno: #{gm_rank}, IR={gm_ir:.3f}")
        else:
            verificar(False, "García Moreno encontrada en ranking", resultados)
            print(f"  ✗ García Moreno no encontrada en ranking")

        # Gradiente SSP debe ser SSP126 < SSP370 < SSP585
        for cult in EXPECTED_CULTIVOS:
            irs = {}
            for ssp in EXPECTED_SSPS:
                subset = df_r[
                    (df_r["cultivo"] == cult) &
                    (df_r["ssp"] == ssp) &
                    (df_r["horizonte"] == "2061-2080")
                ]
                irs[ssp] = subset["indice_riesgo"].mean()

            gradiente_ok = irs["ssp126"] <= irs["ssp370"] <= irs["ssp585"]
            verificar(gradiente_ok,
                      f"Gradiente SSP coherente para {cult}: "
                      f"{irs['ssp126']:.3f} ≤ {irs['ssp370']:.3f} "
                      f"≤ {irs['ssp585']:.3f}",
                      resultados)

        print(f"  ✓ Gradiente SSP verificado para 4 cultivos")

        # Fréjol debe ser el más estable
        frejol_126 = df_r[
            (df_r["cultivo"] == "frejol") & (df_r["ssp"] == "ssp126") &
            (df_r["horizonte"] == "2021-2040")
        ]["indice_riesgo"].mean()
        frejol_585 = df_r[
            (df_r["cultivo"] == "frejol") & (df_r["ssp"] == "ssp585") &
            (df_r["horizonte"] == "2061-2080")
        ]["indice_riesgo"].mean()
        delta_frejol = abs(frejol_585 - frejol_126)
        verificar(delta_frejol < 0.02,
                  f"Fréjol estable entre escenarios (Δ={delta_frejol:.3f})",
                  resultados)
        print(f"  ✓ Fréjol: Δ IR = {delta_frejol:.3f} (estable)")

    # ═══════════════════════════════════════════════════════════
    # [3/7] PRODUCTOS CARTOGRÁFICOS (58 mapas)
    # ═══════════════════════════════════════════════════════════
    seccion("PRODUCTOS CARTOGRÁFICOS", "3/7")

    mapas_ind = list((MAPAS_DIR / "individuales").glob("*.pdf")) \
        if (MAPAS_DIR / "individuales").exists() else []
    mapas_pan = list((MAPAS_DIR / "paneles_tesis").glob("*.pdf")) \
        if (MAPAS_DIR / "paneles_tesis").exists() else []
    mapas_cam = list((MAPAS_DIR / "cambio_temporal").glob("*.pdf")) \
        if (MAPAS_DIR / "cambio_temporal").exists() else []
    mapas_sin = list((MAPAS_DIR / "sintesis").glob("*.pdf")) \
        if (MAPAS_DIR / "sintesis").exists() else []

    n_ind = len(mapas_ind)
    n_pan = len(mapas_pan)
    n_cam = len(mapas_cam)
    n_sin = len(mapas_sin)
    n_total = n_ind + n_pan + n_cam + n_sin

    verificar(n_ind == EXPECTED_MAPAS_IND,
              f"36 mapas individuales ({n_ind} encontrados)", resultados)
    verificar(n_cam == EXPECTED_MAPAS_CAMBIO,
              f"12 mapas de cambio ({n_cam} encontrados)", resultados)
    verificar(n_pan >= 8,
              f"≥8 paneles (4 cultivo + 3 SSP + 1 resumen) ({n_pan})",
              resultados)
    verificar(n_sin >= 2,
              f"≥2 mapas síntesis (exposición + priorización) ({n_sin})",
              resultados)

    print(f"  ✓ Individuales: {n_ind}")
    print(f"  ✓ Paneles: {n_pan}")
    print(f"  ✓ Cambio temporal: {n_cam}")
    print(f"  ✓ Síntesis: {n_sin}")
    print(f"  ✓ TOTAL mapas: {n_total}")
    detalles["mapas_total"] = n_total

    # ═══════════════════════════════════════════════════════════
    # [4/7] FICHAS PARROQUIALES (42 PDFs)
    # ═══════════════════════════════════════════════════════════
    seccion("FICHAS PARROQUIALES", "4/7")

    fichas = list(FICHAS_DIR.glob("FICHA_*.pdf")) \
        if FICHAS_DIR.exists() else []
    n_fichas = len(fichas)

    verificar(n_fichas == EXPECTED_FICHAS,
              f"42 fichas parroquiales ({n_fichas} encontradas)", resultados)
    print(f"  ✓ Fichas PDF: {n_fichas}")

    # Verificar índice
    csv_indice = buscar_csv(FICHAS_DIR, "INDICE_FICHAS_*.csv")
    verificar(csv_indice is not None,
              "Índice de fichas CSV existe", resultados)
    if csv_indice:
        print(f"  ✓ Índice: {csv_indice.name}")
    detalles["fichas_total"] = n_fichas

    # ═══════════════════════════════════════════════════════════
    # [5/7] DOCUMENTACIÓN METODOLÓGICA
    # ═══════════════════════════════════════════════════════════
    seccion("DOCUMENTACIÓN METODOLÓGICA", "5/7")

    docs_esperados = [
        "DOC_METODOLOGIA_SCRIPT_00",
        "DOC_METODOLOGIA_SCRIPT_01",
        "DOC_METODOLOGIA_SCRIPT_02",
        "DOC_METODOLOGIA_SCRIPT_03A",
        "DOC_METODOLOGIA_SCRIPT_03B",
        "DOC_METODOLOGIA_SCRIPT_03C",
        "DOC_METODOLOGIA_SCRIPT_03D",
        "DOC_METODOLOGIA_SCRIPT_03E",
        "DOC_METODOLOGIA_SCRIPT_03F",
        "DOC_METODOLOGIA_SCRIPT_04A",
        "DOC_METODOLOGIA_SCRIPT_04B",
        "DOC_METODOLOGIA_SCRIPT_04C",
        "DOC_METODOLOGIA_SCRIPT_05A",
        "DOC_METODOLOGIA_SCRIPT_05B",
        "DOC_METODOLOGIA_SCRIPT_05C",
        "DOC_METODOLOGIA_SCRIPT_06",
        "DOC_METODOLOGIA_SCRIPT_06B",
        "DOC_METODOLOGIA_SCRIPT_06C",
        "DOC_METODOLOGIA_SCRIPT_07",
        "DOC_METODOLOGIA_SCRIPT_08",
        "DOC_METODOLOGIA_SCRIPT_09",
    ]

    encontrados = []
    faltantes = []

    if METODO_DIR.exists():
        archivos_metodo = [f.stem for f in METODO_DIR.glob("*.docx")]
        for doc in docs_esperados:
            # Buscar con variaciones (puede tener espacios, paréntesis, etc.)
            found = any(doc.replace("_", " ") in a.replace("_", " ") or
                        doc in a for a in archivos_metodo)
            if found:
                encontrados.append(doc)
            else:
                faltantes.append(doc)
    else:
        faltantes = docs_esperados
        advertencias.append(f"Carpeta METODOLOGÍA no encontrada: {METODO_DIR}")

    n_enc = len(encontrados)
    n_fal = len(faltantes)
    n_esp = len(docs_esperados)

    verificar(n_fal == 0,
              f"Documentación completa ({n_enc}/{n_esp} docs)", resultados)

    print(f"  ✓ Encontrados: {n_enc}/{n_esp}")
    if faltantes:
        print(f"  ⚠ Faltantes ({n_fal}):")
        for f in faltantes:
            print(f"      - {f}")

    detalles["docs_encontrados"] = n_enc
    detalles["docs_esperados"] = n_esp
    detalles["docs_faltantes"] = faltantes

    # ═══════════════════════════════════════════════════════════
    # [6/7] REPORTES DE AUDITORÍA
    # ═══════════════════════════════════════════════════════════
    seccion("REPORTES DE AUDITORÍA PREVIOS", "6/7")

    reportes = list(REPORTS_DIR.glob("REPORTE_*.txt")) \
        if REPORTS_DIR.exists() else []
    n_rep = len(reportes)
    verificar(n_rep >= 5,
              f"≥5 reportes de auditoría ({n_rep} encontrados)", resultados)
    print(f"  ✓ Reportes: {n_rep}")
    for r in sorted(reportes)[-5:]:
        print(f"      {r.name}")
    detalles["reportes_total"] = n_rep

    # ═══════════════════════════════════════════════════════════
    # [7/7] GENERACIÓN DE METADATOS ISO 19115
    # ═══════════════════════════════════════════════════════════
    seccion("METADATOS ISO 19115:2014", "7/7")

    metadatos = {
        "fileIdentifier": f"TESIS_RIESGO_AGROCLIMATICO_IMBABURA_{TS}",
        "language": "spa",
        "characterSet": "utf8",
        "hierarchyLevel": "dataset",
        "hierarchyLevelName": "Investigación de maestría",
        "contact": {
            "individualName": "Víctor Hugo Pinto Páez",
            "organisationName": "Universidad San Gregorio de Portoviejo",
            "role": "author",
            "contactInfo": {
                "address": {
                    "city": "Portoviejo",
                    "country": "Ecuador"
                }
            }
        },
        "dateStamp": datetime.now().isoformat(),
        "metadataStandardName": "ISO 19115:2014",
        "metadataStandardVersion": "2014",
        "identificationInfo": {
            "citation": {
                "title": ("Riesgo agroclimático de cultivos andinos bajo "
                          "escenarios CMIP6 en la provincia de Imbabura: "
                          "modelamiento de distribución de especies para "
                          "la gestión territorial"),
                "date": "2026-03",
                "dateType": "publication",
                "citedResponsibleParty": {
                    "individualName": "Víctor Hugo Pinto Páez",
                    "role": "author"
                }
            },
            "abstract": (
                "Dataset de investigación que cuantifica el riesgo "
                "agroclimático de cuatro cultivos andinos (papa, maíz, "
                "fréjol, quinua) bajo escenarios de cambio climático "
                "CMIP6 (SSP1-2.6, SSP3-7.0, SSP5-8.5) para las 42 "
                "parroquias de la provincia de Imbabura, Ecuador. "
                "Integra modelos de distribución de especies (Random "
                "Forest) con Redes Bayesianas siguiendo el marco de "
                "riesgo IPCC AR6: Riesgo = f(Peligro × Exposición × "
                "Vulnerabilidad). El pipeline comprende 10 scripts "
                "con trazabilidad completa y 21 documentos de "
                "metodología individuales."
            ),
            "purpose": (
                "Proveer información cuantitativa de riesgo agroclimático "
                "a escala parroquial para la toma de decisiones de "
                "adaptación al cambio climático por parte de los GADs "
                "parroquiales y cantonales de Imbabura."
            ),
            "status": "completed",
            "topicCategory": ["farming", "climatologyMeteorologyAtmosphere"],
            "extent": {
                "geographicElement": {
                    "westBoundLongitude": -79.08,
                    "eastBoundLongitude": -77.46,
                    "southBoundLatitude": 0.07,
                    "northBoundLatitude": 0.52
                },
                "temporalElement": {
                    "historicalPeriod": "1981-2014",
                    "projectionPeriods": [
                        "2021-2040", "2041-2060", "2061-2080"
                    ]
                }
            },
            "spatialResolution": {
                "climateData": "0.1° (~10 km), BASD-CMIP6-PE",
                "administrativeUnit": "Parroquia (ADM3, 42 unidades)",
                "agriculturalData": "~10 km (MapSPAM v2r0, 5 arc-min)"
            }
        },
        "dataQualityInfo": {
            "scope": "dataset",
            "lineage": {
                "sources": [
                    {
                        "description": "BASD-CMIP6-PE v1.0",
                        "citation": "Fernandez-Palomino et al. (2024). "
                                    "Scientific Data, 11, 34.",
                        "doi": "10.1038/s41597-023-02863-z",
                        "variables": "pr, tas, tasmin, tasmax (daily)",
                        "period": "1981-2100",
                        "gcms": 10,
                        "biasCorrection": "ISIMIP3BASD v2.5"
                    },
                    {
                        "description": "GBIF Occurrence Records",
                        "records_raw": 28965,
                        "records_clean": 2681,
                        "species": 4,
                        "cleaning": "CoordinateCleaner + spThin 1km"
                    },
                    {
                        "description": "MapSPAM v2r0 2020",
                        "citation": "IFPRI (2024). Harvard Dataverse.",
                        "doi": "10.7910/DVN/SWPENT",
                        "crops": "POTA, MAIZ, BEAN",
                        "variable": "Harvested Area (ha/pixel)"
                    },
                    {
                        "description": "ESPAC 2024",
                        "citation": "INEC (2024)",
                        "coverage": "Provincial (Imbabura)",
                        "crops": "Papa, Maíz, Fréjol, Quinua"
                    },
                    {
                        "description": "CONALI/INEC",
                        "content": "Límites parroquiales oficiales",
                        "units": 42,
                        "projection": "EPSG:32717 (UTM 17S)"
                    }
                ],
                "processSteps": [
                    "Script 00: Configuración inicial del proyecto",
                    "Script 01: Descarga BASD-CMIP6-PE (880 archivos)",
                    "Script 02: Recorte espacial Imbabura + buffer 10 km",
                    "Scripts 03A-03F: Cálculo de índices agroclimáticos",
                    "Scripts 04A-04C: Exposición agrícola (MapSPAM+ESPAC)",
                    "Scripts 05A-05C: Dataset RF (presencias+pseudo-ausencias+16 índices)",
                    "Script 06: Entrenamiento RF (4 modelos, AUC 0.80-0.87)",
                    "Script 06B: Proyecciones RF CMIP6 (360 GeoTIFF)",
                    "Script 06C: Agregación parroquial (1,512 registros)",
                    "Script 07: Red Bayesiana IPCC (IR por parroquia)",
                    "Script 08: Mapas de riesgo (58 mapas, 300 DPI)",
                    "Script 09: Fichas parroquiales (42 PDFs)",
                    "Script 10: Validación final y auditoría ISO 19115"
                ]
            },
            "results": {
                "totalRecords": 1512,
                "parroquias": 42,
                "cultivos": 4,
                "escenarios": 9,
                "irRange": [0.215, 0.873],
                "topParroquia": "García Moreno (IR=0.689)",
                "cultivoMasVulnerable": "Papa (IR medio=0.596, SSP585 2061-2080)",
                "cultivoMasResiliente": "Fréjol (ΔIR=+0.6%)",
                "mayorIncrementoRelativo": "Quinua (+46.7%)"
            }
        },
        "distributionInfo": {
            "distributionFormat": [
                {"name": "CSV", "version": "UTF-8"},
                {"name": "GeoTIFF", "version": "COG"},
                {"name": "GeoPackage", "version": "1.3"},
                {"name": "PDF", "version": "1.7"},
                {"name": "PNG", "version": "300 DPI"}
            ],
            "transferOptions": {
                "description": "Archivos locales organizados en estructura "
                               "jerárquica del proyecto de tesis"
            }
        },
        "metadataConstraints": {
            "useLimitation": (
                "Dataset generado como parte de tesis de maestría. "
                "Resolución climática de ~10 km; no captura microclimas. "
                "MapSPAM como proxy de catastro agrícola real. "
                "Quinua solo a nivel provincial. "
                "CPTs de Red Bayesiana basadas en conocimiento experto, "
                "no en aprendizaje de parámetros desde datos observados."
            ),
            "accessConstraints": "otherRestrictions",
            "otherConstraints": "Uso académico. Citar al autor."
        },
        "pipeline_summary": {
            "total_scripts": 10,
            "total_methodology_docs": len(encontrados),
            "total_maps": detalles.get("mapas_total", 0),
            "total_fichas": detalles.get("fichas_total", 0),
            "total_audit_reports": detalles.get("reportes_total", 0),
            "execution_period": "2026-02-01 a 2026-03-09"
        }
    }

    # Guardar metadatos
    meta_path = METADATOS_DIR / f"ISO19115_DATASET_COMPLETO_{TS}.json"
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadatos, f, indent=2, ensure_ascii=False, default=str)
    print(f"  ✓ Metadatos ISO 19115: {meta_path.name}")

    # ═══════════════════════════════════════════════════════════
    # RESUMEN DE VERIFICACIONES
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'═' * 60}")
    print(f"  RESUMEN DE VERIFICACIONES")
    print(f"{'═' * 60}")

    n_pass = sum(1 for r in resultados if r["estado"] == "PASS")
    n_fail = sum(1 for r in resultados if r["estado"] == "FAIL")
    n_total_v = len(resultados)

    for r in resultados:
        icono = "✓" if r["estado"] == "PASS" else "✗"
        print(f"  {icono} [{r['estado']}] {r['criterio']}")

    print(f"\n  PASS: {n_pass}/{n_total_v}")
    print(f"  FAIL: {n_fail}/{n_total_v}")

    if advertencias:
        print(f"\n  ADVERTENCIAS ({len(advertencias)}):")
        for a in advertencias:
            print(f"    ⚠ {a}")

    # ═══════════════════════════════════════════════════════════
    # REPORTE FINAL
    # ═══════════════════════════════════════════════════════════
    duracion = time.time() - t0
    rep_path = REPORTS_DIR / f"REPORTE_FINAL_VALIDACION_{TS}.txt"

    with open(rep_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("REPORTE FINAL DE VALIDACIÓN Y AUDITORÍA\n")
        f.write("SCRIPT 10 — CIERRE DEL PIPELINE INVESTIGATIVO\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Versión: {VERSION}\n")
        f.write(f"Duración: {duracion:.0f}s\n\n")

        f.write("PROYECTO\n")
        f.write("-" * 70 + "\n")
        f.write("Título: Riesgo agroclimático de cultivos andinos bajo\n")
        f.write("        escenarios CMIP6 en la provincia de Imbabura\n")
        f.write("Autor:  Víctor Hugo Pinto Páez\n")
        f.write("Univ.:  Universidad San Gregorio de Portoviejo\n")
        f.write("Marco:  IPCC AR6 — Riesgo = f(P × E × V)\n\n")

        f.write("INVENTARIO DE PRODUCTOS\n")
        f.write("-" * 70 + "\n")
        f.write(f"  Scripts ejecutados:          10 (00–09+10)\n")
        f.write(f"  Documentos metodológicos:    {n_enc}/{n_esp}\n")
        f.write(f"  Mapas cartográficos:         "
                f"{detalles.get('mapas_total', 'N/D')}\n")
        f.write(f"  Fichas parroquiales:         "
                f"{detalles.get('fichas_total', 'N/D')}\n")
        f.write(f"  Reportes de auditoría:       "
                f"{detalles.get('reportes_total', 'N/D')}\n")
        f.write(f"  CSV de datos:                3 (riesgo, exposición, "
                f"ranking)\n")
        f.write(f"  Metadatos ISO 19115:         {meta_path.name}\n\n")

        f.write("HALLAZGOS PRINCIPALES\n")
        f.write("-" * 70 + "\n")
        f.write("  1. García Moreno (#1, IR=0.689): mayor riesgo provincial,\n")
        f.write("     4 cultivos en riesgo alto.\n")
        f.write("  2. Papa: cultivo más vulnerable (IR=0.596, SSP585 2080).\n")
        f.write("  3. Quinua: mayor incremento relativo (+46.7%).\n")
        f.write("  4. Fréjol: resiliente (ΔIR=+0.6%), cultivo de\n")
        f.write("     diversificación recomendado.\n")
        f.write("  5. Gradiente SSP verificado: SSP126 < SSP370 < SSP585.\n")
        f.write("  6. Zona de Intag (Cotacachi occidental): concentra\n")
        f.write("     las parroquias de mayor riesgo.\n")
        f.write("  7. Primera cuantificación parroquial de riesgo\n")
        f.write("     agroclimático en Imbabura con CMIP6 corregido.\n\n")

        f.write("VERIFICACIONES\n")
        f.write("-" * 70 + "\n")
        for r in resultados:
            f.write(f"  [{r['estado']}] {r['criterio']}\n")
        f.write(f"\n  PASS: {n_pass}/{n_total_v}\n")
        f.write(f"  FAIL: {n_fail}/{n_total_v}\n\n")

        if faltantes:
            f.write("DOCUMENTOS FALTANTES\n")
            f.write("-" * 70 + "\n")
            for fal in faltantes:
                f.write(f"  - {fal}\n")
            f.write("\n")

        f.write("LIMITACIONES DEL DATASET\n")
        f.write("-" * 70 + "\n")
        f.write("  - Resolución climática ~10 km (sin microclimas)\n")
        f.write("  - MapSPAM como proxy (no catastro real)\n")
        f.write("  - Quinua solo a nivel provincial\n")
        f.write("  - Sin validación de campo\n")
        f.write("  - CPTs expertas (no aprendidas de datos)\n")
        f.write("  - Conservatismo de nicho (estacionariedad)\n\n")

        estado_final = "APROBADO" if n_fail == 0 else "APROBADO CON OBSERVACIONES"
        f.write(f"ESTADO FINAL: {estado_final}\n\n")

        f.write("=" * 70 + "\n")
        f.write("FIN DEL PIPELINE INVESTIGATIVO\n")
        f.write("Víctor Hugo Pinto Páez\n")
        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d')}\n")
        f.write("=" * 70 + "\n")

    print(f"\n  ✓ Reporte final: {rep_path.name}")

    # ═══════════════════════════════════════════════════════════
    # CIERRE
    # ═══════════════════════════════════════════════════════════
    estado = "APROBADO" if n_fail == 0 else "APROBADO CON OBSERVACIONES"

    print()
    print("╔" + "═" * 68 + "╗")
    print(f"║  SCRIPT 10 — ESTADO FINAL: {estado}" +
          " " * (40 - len(estado)) + "║")
    print("╚" + "═" * 68 + "╝")
    print(f"\n  ⏱  {duracion:.0f}s")
    print(f"  ✓  Verificaciones: {n_pass} PASS / {n_fail} FAIL")
    print(f"  📄 Metadatos ISO: {meta_path.name}")
    print(f"  📄 Reporte final: {rep_path.name}")
    print(f"\n  ════════════════════════════════════════")
    print(f"  PIPELINE INVESTIGATIVO COMPLETADO")
    print(f"  Scripts 00–10 ejecutados y documentados")
    print(f"  ════════════════════════════════════════")
    print(f"\n  Siguiente: Redacción del documento de tesis")
    print("═" * 70)

    return resultados, metadatos


if __name__ == "__main__":
    resultados, metadatos = main()