"""
Script publicado como parte del Geoportal Riesgo Agroclimático — Imbabura, Ecuador
Pinto Páez, V. H. (2026). https://doi.org/10.5281/zenodo.19288559
Licencia: CC BY 4.0

NOTA: este archivo fue sanitizado para publicación pública.
- Credenciales (API keys, tokens, service accounts) removidas → <REDACTED_*>
- Rutas absolutas locales sustituidas por <RUTA_LOCAL>
Antes de ejecutar, configure sus propias rutas de entrada/salida y credenciales.

Archivo original: SCRIPT 00 CONFIGURACIÓN INICIAL DEL PROYECTO.py
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCRIPT 00: CONFIGURACIÓN INICIAL DEL PROYECTO
==============================================
Versión: 1.0.0
Fecha: 2026-02-01
Autor: Víctor Hugo Pinto Páez
Universidad: Universidad San Gregorio de Portoviejo
Programa: Maestría en Prevención y Gestión de Riesgos

Descripción:
    Configura la estructura inicial del proyecto de tesis, creando todas
    las carpetas necesarias según el Protocolo Metodológico Maestro,
    archivos de configuración y documentación base para garantizar la
    trazabilidad científica del proyecto.

Estándares:
    - ISO 19115: Metadatos geográficos
    - ISO 19157: Calidad de datos geográficos
    - Principios FAIR: Findable, Accessible, Interoperable, Reusable
"""

import os
import json
from datetime import datetime
from pathlib import Path

# =============================================================================
# CONFIGURACIÓN DEL PROYECTO
# =============================================================================

# Ruta base del proyecto
RUTA_BASE = Path(r"<RUTA_LOCAL>")

# Información del proyecto
PROYECTO = {
    "titulo": "Modelamiento del riesgo agroclimático mediante Random Forest y Redes Bayesianas bajo escenarios CMIP6: Aplicación a cultivos andinos en Imbabura, Ecuador",
    "autor": "Víctor Hugo Pinto Páez",
    "universidad": "Universidad San Gregorio de Portoviejo",
    "programa": "Maestría en Prevención y Gestión de Riesgos - Mención en Variabilidad Climática y Resiliencia Territorial",
    "area_estudio": "Provincia de Imbabura, Ecuador",
    "version_protocolo": "1.0.0",
    "fecha_inicio": datetime.now().strftime("%Y-%m-%d")
}

# Cultivos objetivo con claves taxonómicas GBIF
CULTIVOS = {
    "papa": {
        "nombre_cientifico": "Solanum tuberosum L.",
        "taxon_key": 2930137,
        "familia": "Solanaceae",
        "t_optima_min": 15,
        "t_optima_max": 20,
        "t_critica": 25,
        "p_minima_mm": 500
    },
    "maiz": {
        "nombre_cientifico": "Zea mays L.",
        "taxon_key": 5290052,
        "familia": "Poaceae",
        "t_optima_min": 20,
        "t_optima_max": 30,
        "t_critica": 35,
        "p_minima_mm": 500
    },
    "frejol": {
        "nombre_cientifico": "Phaseolus vulgaris L.",
        "taxon_key": 2974859,
        "familia": "Fabaceae",
        "t_optima_min": 18,
        "t_optima_max": 24,
        "t_critica": 30,
        "p_minima_mm": 400
    },
    "quinua": {
        "nombre_cientifico": "Chenopodium quinoa Willd.",
        "taxon_key": 3084041,
        "familia": "Amaranthaceae",
        "t_optima_min": 15,
        "t_optima_max": 20,
        "t_critica": 32,
        "p_minima_mm": 300
    }
}

# Escenarios climáticos CMIP6
ESCENARIOS_CLIMATICOS = {
    "dataset": "BASD-CMIP6-PE",
    "doi": "10.1038/s41597-023-02863-z",
    "resolucion_espacial": "0.1° (~10 km)",
    "resolucion_temporal": "diaria",
    "periodo_historico": "1850-2014",
    "periodo_futuro": "2015-2100",
    "variables": ["pr", "tas", "tasmin", "tasmax"],
    "escenarios_ssp": ["SSP1-2.6", "SSP3-7.0", "SSP5-8.5"],
    "gcms": [
        "CanESM5", "IPSL-CM6A-LR", "UKESM1-0-LL", "CNRM-CM6-1",
        "CNRM-ESM2-1", "MIROC6", "GFDL-ESM4", "MRI-ESM2-0",
        "MPI-ESM1-2-HR", "EC-Earth3"
    ],
    "horizontes_temporales": {
        "historico": "1981-2014",
        "futuro_cercano": "2021-2040",
        "futuro_medio": "2041-2060",
        "futuro_lejano": "2061-2080"
    }
}

# Criterios de aceptación para modelos
CRITERIOS_MODELOS = {
    "random_forest": {
        "auc_roc_minimo": 0.75,
        "tss_minimo": 0.50,
        "kappa_minimo": 0.40,
        "oob_error_maximo": 0.30,
        "diferencia_train_test_maxima": 0.10
    },
    "red_bayesiana": {
        "coherencia_probabilistica": 1.0,
        "tolerancia_cpt": 0.001
    }
}

# =============================================================================
# ESTRUCTURA DE CARPETAS
# =============================================================================

ESTRUCTURA_CARPETAS = {
    "01_PROTOCOLO": {
        "descripcion": "Protocolo metodológico y documentos de validación",
        "subcarpetas": ["validaciones", "versiones"]
    },
    "02_DATOS": {
        "descripcion": "Datos crudos y procesados",
        "subcarpetas": [
            "ocurrencias/raw",
            "ocurrencias/clean",
            "ocurrencias/thinned",
            "climaticos/BASD_CMIP6_PE/historico",
            "climaticos/BASD_CMIP6_PE/futuro/SSP126",
            "climaticos/BASD_CMIP6_PE/futuro/SSP370",
            "climaticos/BASD_CMIP6_PE/futuro/SSP585",
            "climaticos/bioclimaticos/historico",
            "climaticos/bioclimaticos/futuro",
            "limites/imbabura",
            "limites/parroquias",
            "cultivos/sigtierras",
            "cultivos/espac",
            "topografia"
        ]
    },
    "03_SCRIPTS": {
        "descripcion": "Código fuente en Python y R",
        "subcarpetas": ["python", "R", "utils"]
    },
    "04_RESULTADOS": {
        "descripcion": "Salidas organizadas por fase",
        "subcarpetas": [
            "FASE1_preparacion/datos_climaticos",
            "FASE1_preparacion/datos_cultivos",
            "FASE1_preparacion/integracion",
            "FASE2_random_forest/modelos",
            "FASE2_random_forest/validacion",
            "FASE2_random_forest/importancia_variables",
            "FASE2_random_forest/proyecciones",
            "FASE3_red_bayesiana/estructura",
            "FASE3_red_bayesiana/cpts",
            "FASE3_red_bayesiana/inferencia",
            "FASE4_productos/mapas",
            "FASE4_productos/tablas",
            "FASE4_productos/fichas_parroquiales",
            "FASE4_productos/reportes"
        ]
    },
    "05_DOCUMENTACION": {
        "descripcion": "Reportes de auditoría, metadatos ISO, figuras",
        "subcarpetas": [
            "reportes_auditoria",
            "metadatos_iso",
            "figuras",
            "logs"
        ]
    },
    "06_TESIS": {
        "descripcion": "Documento final de tesis",
        "subcarpetas": [
            "capitulos",
            "anexos",
            "presentacion",
            "versiones_borrador"
        ]
    }
}

# =============================================================================
# FUNCIONES
# =============================================================================

def crear_estructura_carpetas():
    """Crea la estructura completa de carpetas del proyecto."""
    carpetas_creadas = 0
    
    print("=" * 60)
    print("CREANDO ESTRUCTURA DE CARPETAS")
    print("=" * 60)
    
    for carpeta_principal, config in ESTRUCTURA_CARPETAS.items():
        # Crear carpeta principal
        ruta_principal = RUTA_BASE / carpeta_principal
        ruta_principal.mkdir(parents=True, exist_ok=True)
        carpetas_creadas += 1
        print(f"\n[+] {carpeta_principal}/")
        print(f"    Descripción: {config['descripcion']}")
        
        # Crear subcarpetas
        for subcarpeta in config["subcarpetas"]:
            ruta_sub = ruta_principal / subcarpeta
            ruta_sub.mkdir(parents=True, exist_ok=True)
            carpetas_creadas += 1
            print(f"    └── {subcarpeta}/")
    
    return carpetas_creadas


def crear_config_json():
    """Genera el archivo de configuración principal del proyecto."""
    config = {
        "proyecto": PROYECTO,
        "cultivos": CULTIVOS,
        "escenarios_climaticos": ESCENARIOS_CLIMATICOS,
        "criterios_modelos": CRITERIOS_MODELOS,
        "rutas": {
            "base": str(RUTA_BASE),
            "protocolo": str(RUTA_BASE / "01_PROTOCOLO"),
            "datos": str(RUTA_BASE / "02_DATOS"),
            "scripts": str(RUTA_BASE / "03_SCRIPTS"),
            "resultados": str(RUTA_BASE / "04_RESULTADOS"),
            "documentacion": str(RUTA_BASE / "05_DOCUMENTACION"),
            "tesis": str(RUTA_BASE / "06_TESIS")
        },
        "metadatos": {
            "fecha_creacion": datetime.now().isoformat(),
            "version_config": "1.0.0",
            "estandar_iso": "ISO 19115:2014"
        }
    }
    
    ruta_config = RUTA_BASE / "01_PROTOCOLO" / "config.json"
    with open(ruta_config, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"\n[✓] Archivo de configuración creado: {ruta_config}")
    return ruta_config


def crear_readme():
    """Genera el archivo README.md del proyecto."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    contenido = f"""# {PROYECTO['titulo']}

## Información del Proyecto

| Campo | Valor |
|-------|-------|
| **Autor** | {PROYECTO['autor']} |
| **Universidad** | {PROYECTO['universidad']} |
| **Programa** | {PROYECTO['programa']} |
| **Área de estudio** | {PROYECTO['area_estudio']} |
| **Fecha de inicio** | {PROYECTO['fecha_inicio']} |

## Estructura del Proyecto

```
{RUTA_BASE}/
├── 01_PROTOCOLO/       # Protocolo metodológico y validaciones
├── 02_DATOS/           # Datos crudos y procesados
├── 03_SCRIPTS/         # Código fuente (Python y R)
├── 04_RESULTADOS/      # Salidas organizadas por fase
├── 05_DOCUMENTACION/   # Reportes, metadatos ISO, figuras
└── 06_TESIS/           # Documento final
```

## Metodología

Este proyecto implementa un marco metodológico basado en:

1. **Random Forest**: Para modelamiento de distribución de especies (SDM)
2. **Redes Bayesianas**: Para integración del riesgo agroclimático
3. **BASD-CMIP6-PE**: Dataset climático corregido para Ecuador y Perú

### Marco de Riesgo IPCC

**RIESGO = f(Peligro, Exposición, Vulnerabilidad)**

## Cultivos Objetivo

| Cultivo | Nombre Científico | Familia |
|---------|-------------------|---------|
| Papa | *Solanum tuberosum* L. | Solanaceae |
| Maíz | *Zea mays* L. | Poaceae |
| Fréjol | *Phaseolus vulgaris* L. | Fabaceae |
| Quinua | *Chenopodium quinoa* Willd. | Amaranthaceae |

## Escenarios Climáticos

- **Dataset**: BASD-CMIP6-PE (DOI: 10.1038/s41597-023-02863-z)
- **Escenarios SSP**: SSP1-2.6, SSP3-7.0, SSP5-8.5
- **GCMs**: 10 modelos del ensemble CMIP6
- **Horizontes**: 2021-2040, 2041-2060, 2061-2080

## Estándares de Calidad

- ISO 19115: Metadatos geográficos
- ISO 19157: Calidad de datos geográficos
- Principios FAIR
- Directrices IPCC AR6

## Referencias

Ver `01_PROTOCOLO/PROTOCOLO_METODOLOGICO_MAESTRO.md` para referencias completas.

---
*Generado automáticamente por SCRIPT_00 el {timestamp}*
"""
    
    ruta_readme = RUTA_BASE / "README.md"
    with open(ruta_readme, 'w', encoding='utf-8') as f:
        f.write(contenido)
    
    print(f"[✓] README.md creado: {ruta_readme}")
    return ruta_readme


def crear_validacion_script():
    """Genera el documento de validación del Script 00."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fecha_archivo = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    contenido = f"""# VALIDACIÓN SCRIPT 00: CONFIGURACIÓN INICIAL

**Fecha de ejecución:** {timestamp}
**Versión del script:** 1.0.0

## 1. Verificación de Criterios

| Criterio | Requerido | Cumple |
|----------|-----------|--------|
| Estructura de carpetas completa | Sí | ✓ |
| Archivo config.json generado | Sí | ✓ |
| Archivo README.md generado | Sí | ✓ |
| Ejecución sin errores | Sí | ✓ |

## 2. Archivos Generados

- `01_PROTOCOLO/config.json`
- `README.md`
- `01_PROTOCOLO/validaciones/VAL_SCRIPT_00_{fecha_archivo}.md`

## 3. Decisión

**ESTADO: APROBADO**

El script se ejecutó correctamente y todos los criterios de aceptación se cumplen.

## 4. Siguiente Paso

Ejecutar **SCRIPT 01**: Descarga de ocurrencias GBIF para los cuatro cultivos andinos.

---
*Firma de validación*
Fecha: {timestamp}
"""
    
    ruta_val = RUTA_BASE / "01_PROTOCOLO" / "validaciones" / f"VAL_SCRIPT_00_{fecha_archivo}.md"
    with open(ruta_val, 'w', encoding='utf-8') as f:
        f.write(contenido)
    
    print(f"[✓] Validación creada: {ruta_val}")
    return ruta_val


def generar_reporte_auditoria():
    """Genera el reporte de auditoría del Script 00."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fecha_archivo = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    contenido = f"""================================================================================
REPORTE DE AUDITORÍA - SCRIPT 00: CONFIGURACIÓN INICIAL
================================================================================

Fecha de ejecución: {timestamp}
Versión del script: 1.0.0
Autor: {PROYECTO['autor']}

--------------------------------------------------------------------------------
1. INFORMACIÓN DEL PROYECTO
--------------------------------------------------------------------------------

Título: {PROYECTO['titulo']}
Universidad: {PROYECTO['universidad']}
Programa: {PROYECTO['programa']}
Área de estudio: {PROYECTO['area_estudio']}

--------------------------------------------------------------------------------
2. ESTRUCTURA CREADA
--------------------------------------------------------------------------------

Ruta base: {RUTA_BASE}

Carpetas principales:
"""
    
    for carpeta, config in ESTRUCTURA_CARPETAS.items():
        contenido += f"\n  {carpeta}/\n"
        contenido += f"    Descripción: {config['descripcion']}\n"
        contenido += f"    Subcarpetas: {len(config['subcarpetas'])}\n"
    
    contenido += f"""
--------------------------------------------------------------------------------
3. ARCHIVOS DE CONFIGURACIÓN
--------------------------------------------------------------------------------

  - config.json: Parámetros del proyecto, cultivos, escenarios climáticos
  - README.md: Documentación general del proyecto
  - VAL_SCRIPT_00_{fecha_archivo}.md: Documento de validación

--------------------------------------------------------------------------------
4. CULTIVOS CONFIGURADOS
--------------------------------------------------------------------------------

"""
    
    for nombre, info in CULTIVOS.items():
        contenido += f"  {nombre.upper()}:\n"
        contenido += f"    Nombre científico: {info['nombre_cientifico']}\n"
        contenido += f"    TaxonKey GBIF: {info['taxon_key']}\n"
        contenido += f"    T óptima: {info['t_optima_min']}-{info['t_optima_max']}°C\n"
        contenido += f"    T crítica: >{info['t_critica']}°C\n"
        contenido += f"    P mínima: {info['p_minima_mm']} mm\n\n"

    contenido += f"""--------------------------------------------------------------------------------
5. ESCENARIOS CLIMÁTICOS CONFIGURADOS
--------------------------------------------------------------------------------

  Dataset: {ESCENARIOS_CLIMATICOS['dataset']}
  DOI: {ESCENARIOS_CLIMATICOS['doi']}
  Resolución: {ESCENARIOS_CLIMATICOS['resolucion_espacial']}
  
  Escenarios SSP: {', '.join(ESCENARIOS_CLIMATICOS['escenarios_ssp'])}
  
  GCMs ({len(ESCENARIOS_CLIMATICOS['gcms'])} modelos):
    {', '.join(ESCENARIOS_CLIMATICOS['gcms'][:5])}
    {', '.join(ESCENARIOS_CLIMATICOS['gcms'][5:])}

--------------------------------------------------------------------------------
6. ESTADO DE EJECUCIÓN
--------------------------------------------------------------------------------

  Estado: COMPLETADO EXITOSAMENTE
  Errores: 0
  Advertencias: 0

================================================================================
FIN DEL REPORTE
================================================================================
"""
    
    ruta_reporte = RUTA_BASE / "05_DOCUMENTACION" / "reportes_auditoria" / f"REPORTE_SCRIPT_00_{fecha_archivo}.txt"
    with open(ruta_reporte, 'w', encoding='utf-8') as f:
        f.write(contenido)
    
    print(f"[✓] Reporte de auditoría creado: {ruta_reporte}")
    return ruta_reporte


# =============================================================================
# EJECUCIÓN PRINCIPAL
# =============================================================================

def main():
    """Función principal del script."""
    print("\n" + "=" * 60)
    print("SCRIPT 00: CONFIGURACIÓN INICIAL DEL PROYECTO")
    print("Versión 1.0.0")
    print("=" * 60)
    print(f"\nTesis: {PROYECTO['titulo']}")
    print(f"Autor: {PROYECTO['autor']}")
    print(f"Ruta base: {RUTA_BASE}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Crear estructura de carpetas
    n_carpetas = crear_estructura_carpetas()
    
    # Crear archivos de configuración
    print("\n" + "=" * 60)
    print("GENERANDO ARCHIVOS DE CONFIGURACIÓN")
    print("=" * 60)
    
    crear_config_json()
    crear_readme()
    crear_validacion_script()
    generar_reporte_auditoria()
    
    # Resumen final
    print("\n" + "=" * 60)
    print("RESUMEN DE EJECUCIÓN")
    print("=" * 60)
    print(f"\n  Carpetas creadas/verificadas: {n_carpetas}")
    print(f"  Archivos de configuración: 4")
    print(f"  Estado: COMPLETADO EXITOSAMENTE")
    
    print("\n" + "=" * 60)
    print("SIGUIENTE PASO")
    print("=" * 60)
    print("\n  Ejecutar SCRIPT 01: Descarga de ocurrencias GBIF")
    print("  - Cultivos: Papa, Maíz, Fréjol, Quinua")
    print("  - Región: Andes (Ecuador, Perú, Bolivia, Colombia)")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()