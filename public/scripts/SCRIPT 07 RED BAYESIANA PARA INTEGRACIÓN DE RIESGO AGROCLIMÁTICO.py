"""
Script publicado como parte del Geoportal Riesgo Agroclimático — Imbabura, Ecuador
Pinto Páez, V. H. (2026). https://doi.org/10.5281/zenodo.19288559
Licencia: CC BY 4.0

NOTA: este archivo fue sanitizado para publicación pública.
- Credenciales (API keys, tokens, service accounts) removidas → <REDACTED_*>
- Rutas absolutas locales sustituidas por <RUTA_LOCAL>
Antes de ejecutar, configure sus propias rutas de entrada/salida y credenciales.

Archivo original: SCRIPT 07 RED BAYESIANA PARA INTEGRACIÓN DE RIESGO AGROCLIMÁTICO.py
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
SCRIPT 07: RED BAYESIANA PARA INTEGRACIÓN DE RIESGO AGROCLIMÁTICO
===============================================================================

Tesis: Riesgo agroclimático de cultivos andinos bajo escenarios CMIP6
       en la provincia de Imbabura: modelamiento de distribución de
       especies para la gestión territorial

Autor:       Víctor Hugo Pinto Páez
Universidad: San Gregorio de Portoviejo
Maestría:    Prevención y Gestión de Riesgos – Mención en Variabilidad
             Climática y Resiliencia Territorial

Versión: 1.0.0
Fecha:   2026-02-26

PROPÓSITO:
    Construir e inferir una Red Bayesiana que integre los tres componentes
    del marco de riesgo IPCC AR6 (Peligro × Exposición × Vulnerabilidad)
    para calcular la probabilidad de riesgo agroclimático por parroquia,
    cultivo, escenario SSP y horizonte temporal.

MARCO TEÓRICO:
    RIESGO = f(Peligro × Exposición × Vulnerabilidad)

    Donde:
    - Peligro:        Índices agroclimáticos futuros (déficit hídrico,
                      estrés térmico, sequías) → Scripts 03A-03F
    - Exposición:     Superficie cultivada por parroquia → Script 04C
    - Vulnerabilidad: Aptitud climática RF invertida (1 - aptitud) → Script 06C

ESTRUCTURA DAG:
    [Deficit_Hidrico] ─┐
    [Estres_Termico]  ─┼→ [Peligro] ───┐
    [Sequia]          ─┘                │
                                        ├→ [Riesgo]
    [Superficie_ha]   ──→ [Exposicion]──┤
                                        │
    [Aptitud_RF]      ──→ [Vulnerab] ──┘

ENTRADA:
    - Vulnerabilidad: 04_RESULTADOS/.../proyecciones/parroquial/aptitud_parroquial_42parr_*.csv
    - Exposición:     04_RESULTADOS/exposicion_agricola/exposicion_parroquial_resumen_*.csv
    - Peligro:        02_DATOS/climaticos/indices/agregados/{ssp}/{GCM}/

SALIDA:
    - CSV riesgo:     04_RESULTADOS/fase4_modelamiento/red_bayesiana/riesgo_parroquial_*.csv
    - Pivote:         04_RESULTADOS/fase4_modelamiento/red_bayesiana/pivote_riesgo_*.csv
    - BN modelo:      04_RESULTADOS/fase4_modelamiento/red_bayesiana/modelo_bn_*.pkl
    - Reporte:        05_DOCUMENTACION/reportes_auditoria/REPORTE_SCRIPT_07_*.txt

REFERENCIAS:
    IPCC (2022). AR6 WG2. Cambridge University Press.
    Pearl (1988). Probabilistic Reasoning in Intelligent Systems. Morgan Kaufmann.
    Kjærulff & Madsen (2013). Bayesian Networks and Influence Diagrams. Springer.
    Knutti et al. (2010). J. Climate, 23(10), 2739-2758.
    Koller & Friedman (2009). Probabilistic Graphical Models. MIT Press.

DEPENDENCIAS:
    pip install pgmpy pandas numpy geopandas xarray netCDF4 --break-system-packages

===============================================================================
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import xarray as xr
import pickle
import warnings
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# pgmpy imports
try:
    from pgmpy.models import DiscreteBayesianNetwork as BayesianNetwork
except ImportError:
    from pgmpy.models import BayesianNetwork
from pgmpy.factors.discrete import TabularCPD
from pgmpy.inference import VariableElimination

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

# Rutas base
BASE_PREV = Path(r"<RUTA_LOCAL>")
BASE_DATOS = Path(r"<RUTA_LOCAL>")

# Entradas
VULN_DIR = BASE_PREV / "04_RESULTADOS" / "fase4_modelamiento" / "random_forest" / "proyecciones" / "parroquial"
EXPO_DIR = Path(r"<RUTA_LOCAL>")
INDICES_DIR = BASE_DATOS / "climaticos" / "indices" / "agregados"
PARROQUIAS_PATH = Path(r"<RUTA_LOCAL>")

# Salidas
BN_DIR = BASE_PREV / "04_RESULTADOS" / "fase4_modelamiento" / "red_bayesiana"
REPORTS_DIR = BASE_PREV / "05_DOCUMENTACION" / "reportes_auditoria"

# Parámetros
CULTIVOS = ['papa', 'maiz', 'frejol', 'quinua']
SSPS = ['ssp126', 'ssp370', 'ssp585']
HORIZONTES = {
    '2021-2040': (2021, 2040),
    '2041-2060': (2041, 2060),
    '2061-2080': (2061, 2080)
}
GCMS = [
    'CNRM-CM6-1', 'CNRM-ESM2-1', 'CanESM5', 'EC-Earth3',
    'GFDL-ESM4', 'IPSL-CM6A-LR', 'MIROC6', 'MPI-ESM1-2-HR',
    'MRI-ESM2-0', 'UKESM1-0-LL'
]

# Umbrales de estrés térmico (°C) - Ref: CIP 2020, FAO-56, CIAT, Jacobsen 2003
UMBRALES_TERMICOS = {
    'papa': 25.0,
    'maiz': 35.0,
    'frejol': 30.0,
    'quinua': 32.0
}

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
AUTOR = "Víctor Hugo Pinto Páez"


# =============================================================================
# DISCRETIZACIÓN
# =============================================================================
# Umbrales basados en literatura científica para discretizar variables continuas
# en categorías que la Red Bayesiana pueda procesar.
#
# Cada variable se discretiza en 3 niveles: Bajo (0), Medio (1), Alto (2)
# para mantener CPTs manejables y evitar sobreparametrización.
#
# Referencias:
#   - Déficit hídrico: Allen et al. (1998) FAO-56; UNEP (1992)
#   - Estrés térmico: CIP (2020); Jacobsen (2003); FAO-56
#   - Sequía (CDD): McKee et al. (1993); WMO (2012)
#   - Exposición: Cuartiles naturales de la distribución de superficie
#   - Vulnerabilidad: Terciles de (1 - aptitud RF)

def discretizar_peligro_deficit(deficit_mm):
    """
    Discretiza déficit hídrico anual.
    Ref: Allen et al. (1998) FAO-56; UNEP (1992) clasificación de aridez.
    
    Bajo (0):  déficit < -200 mm (superávit o déficit leve)
    Medio (1): -200 ≤ déficit < -500 mm (déficit moderado)
    Alto (2):  déficit ≤ -500 mm (déficit severo)
    
    Nota: valores negativos = déficit (P < ET0)
    """
    if deficit_mm > -200:
        return 0  # Bajo
    elif deficit_mm > -500:
        return 1  # Medio
    else:
        return 2  # Alto


def discretizar_peligro_termico(dias_estres):
    """
    Discretiza días de estrés térmico anual.
    Ref: Challinor et al. (2014); Lobell et al. (2012).
    
    Bajo (0):  < 10 días/año
    Medio (1): 10-30 días/año
    Alto (2):  > 30 días/año
    """
    if dias_estres < 10:
        return 0
    elif dias_estres <= 30:
        return 1
    else:
        return 2


def discretizar_peligro_sequia(cdd_max):
    """
    Discretiza duración máxima de sequía (CDD = Consecutive Dry Days).
    Ref: McKee et al. (1993); WMO (2012) drought monitoring.
    
    Bajo (0):  CDD < 15 días
    Medio (1): 15-30 días
    Alto (2):  > 30 días
    """
    if cdd_max < 15:
        return 0
    elif cdd_max <= 30:
        return 1
    else:
        return 2


def discretizar_exposicion(ha, umbrales_ha):
    """
    Discretiza superficie cultivada usando terciles de la distribución.
    
    Bajo (0):  < P33 de la distribución provincial
    Medio (1): P33 - P66
    Alto (2):  > P66
    """
    if ha <= umbrales_ha[0]:
        return 0
    elif ha <= umbrales_ha[1]:
        return 1
    else:
        return 2


def discretizar_vulnerabilidad(aptitud):
    """
    Discretiza vulnerabilidad = 1 - aptitud_RF.
    Mayor aptitud = menor vulnerabilidad.
    
    Bajo (0):  aptitud > 0.7 (alta aptitud → baja vulnerabilidad)
    Medio (1): 0.4 - 0.7
    Alto (2):  aptitud < 0.4 (baja aptitud → alta vulnerabilidad)
    """
    if aptitud > 0.7:
        return 0  # Baja vulnerabilidad
    elif aptitud >= 0.4:
        return 1  # Media
    else:
        return 2  # Alta vulnerabilidad


# =============================================================================
# ESTRUCTURA DE LA RED BAYESIANA
# =============================================================================

def construir_red_bayesiana():
    """
    Construye la estructura DAG y parametriza las CPTs de la Red Bayesiana.
    
    Estructura:
        Peligro_Deficit  ──┐
        Peligro_Termico  ──┼→ Peligro ───┐
        Peligro_Sequia   ──┘              │
                                          ├→ Riesgo
        Exposicion       ─────────────────┤
                                          │
        Vulnerabilidad   ─────────────────┘
    
    Nodos intermedios:
        - Peligro: Integra los 3 sub-peligros (Déficit + Térmico + Sequía)
        - Riesgo:  Integra Peligro × Exposición × Vulnerabilidad
    
    CPTs parametrizadas desde:
        - Relaciones causales documentadas en IPCC AR6 WG2 Cap. 5
        - Coherencia con umbrales fisiológicos de cultivos andinos
        - Principio de máxima entropía para estados sin información directa
    
    Returns:
        modelo: BayesianNetwork (pgmpy)
        inferencia: VariableElimination engine
    """
    
    # Definir estructura DAG
    modelo = BayesianNetwork([
        ('Peligro_Deficit', 'Peligro'),
        ('Peligro_Termico', 'Peligro'),
        ('Peligro_Sequia', 'Peligro'),
        ('Peligro', 'Riesgo'),
        ('Exposicion', 'Riesgo'),
        ('Vulnerabilidad', 'Riesgo')
    ])
    
    # ─── CPT: Peligro_Deficit (nodo raíz) ────────────────────────────
    # Prior uniforme — se evidencia en inferencia
    cpd_deficit = TabularCPD(
        variable='Peligro_Deficit',
        variable_card=3,
        values=[[1/3], [1/3], [1/3]],
        state_names={'Peligro_Deficit': ['Bajo', 'Medio', 'Alto']}
    )
    
    # ─── CPT: Peligro_Termico (nodo raíz) ────────────────────────────
    cpd_termico = TabularCPD(
        variable='Peligro_Termico',
        variable_card=3,
        values=[[1/3], [1/3], [1/3]],
        state_names={'Peligro_Termico': ['Bajo', 'Medio', 'Alto']}
    )
    
    # ─── CPT: Peligro_Sequia (nodo raíz) ─────────────────────────────
    cpd_sequia = TabularCPD(
        variable='Peligro_Sequia',
        variable_card=3,
        values=[[1/3], [1/3], [1/3]],
        state_names={'Peligro_Sequia': ['Bajo', 'Medio', 'Alto']}
    )
    
    # ─── CPT: Exposicion (nodo raíz) ─────────────────────────────────
    cpd_exposicion = TabularCPD(
        variable='Exposicion',
        variable_card=3,
        values=[[1/3], [1/3], [1/3]],
        state_names={'Exposicion': ['Baja', 'Media', 'Alta']}
    )
    
    # ─── CPT: Vulnerabilidad (nodo raíz) ─────────────────────────────
    cpd_vulnerabilidad = TabularCPD(
        variable='Vulnerabilidad',
        variable_card=3,
        values=[[1/3], [1/3], [1/3]],
        state_names={'Vulnerabilidad': ['Baja', 'Media', 'Alta']}
    )
    
    # ─── CPT: Peligro (nodo intermedio) ──────────────────────────────
    # P(Peligro | Deficit, Termico, Sequia)
    # 3 padres × 3 estados cada uno = 27 columnas
    # Lógica: Peligro alto si CUALQUIER sub-peligro es alto (principio
    # de máximo daño). Peligro bajo solo si TODOS son bajos.
    # Ref: IPCC AR6 WG2 Cap. 5 - compound hazards
    
    peligro_values = np.zeros((3, 27))  # 3 estados × 27 combinaciones
    
    idx = 0
    for d in range(3):      # Deficit: 0=Bajo, 1=Medio, 2=Alto
        for t in range(3):  # Termico
            for s in range(3):  # Sequia
                max_peligro = max(d, t, s)
                media_peligro = (d + t + s) / 3.0
                
                if max_peligro == 0:
                    # Todos bajos → Peligro bajo dominante
                    peligro_values[0, idx] = 0.80
                    peligro_values[1, idx] = 0.15
                    peligro_values[2, idx] = 0.05
                elif max_peligro == 2:
                    # Al menos uno alto → Peligro alto probable
                    if media_peligro >= 1.5:
                        peligro_values[0, idx] = 0.05
                        peligro_values[1, idx] = 0.20
                        peligro_values[2, idx] = 0.75
                    else:
                        peligro_values[0, idx] = 0.10
                        peligro_values[1, idx] = 0.30
                        peligro_values[2, idx] = 0.60
                else:
                    # Combinación media
                    if media_peligro >= 0.67:
                        peligro_values[0, idx] = 0.15
                        peligro_values[1, idx] = 0.55
                        peligro_values[2, idx] = 0.30
                    else:
                        peligro_values[0, idx] = 0.40
                        peligro_values[1, idx] = 0.45
                        peligro_values[2, idx] = 0.15
                
                idx += 1
    
    cpd_peligro = TabularCPD(
        variable='Peligro',
        variable_card=3,
        values=peligro_values.tolist(),
        evidence=['Peligro_Deficit', 'Peligro_Termico', 'Peligro_Sequia'],
        evidence_card=[3, 3, 3],
        state_names={
            'Peligro': ['Bajo', 'Medio', 'Alto'],
            'Peligro_Deficit': ['Bajo', 'Medio', 'Alto'],
            'Peligro_Termico': ['Bajo', 'Medio', 'Alto'],
            'Peligro_Sequia': ['Bajo', 'Medio', 'Alto']
        }
    )
    
    # ─── CPT: Riesgo (nodo final) ────────────────────────────────────
    # P(Riesgo | Peligro, Exposicion, Vulnerabilidad)
    # 3 padres × 3 estados = 27 columnas
    # Lógica IPCC: Riesgo = Peligro × Exposición × Vulnerabilidad
    # Riesgo alto requiere al menos 2 de 3 componentes altos.
    
    riesgo_values = np.zeros((3, 27))
    
    idx = 0
    for p in range(3):      # Peligro
        for e in range(3):  # Exposicion
            for v in range(3):  # Vulnerabilidad
                score = (p + e + v)  # 0-6
                n_altos = sum([1 for x in [p, e, v] if x == 2])
                
                if score <= 1:
                    # Bajo: todo bajo o casi todo bajo
                    riesgo_values[0, idx] = 0.80
                    riesgo_values[1, idx] = 0.15
                    riesgo_values[2, idx] = 0.05
                elif score == 2:
                    riesgo_values[0, idx] = 0.55
                    riesgo_values[1, idx] = 0.35
                    riesgo_values[2, idx] = 0.10
                elif score == 3:
                    riesgo_values[0, idx] = 0.25
                    riesgo_values[1, idx] = 0.50
                    riesgo_values[2, idx] = 0.25
                elif score == 4:
                    if n_altos >= 2:
                        riesgo_values[0, idx] = 0.08
                        riesgo_values[1, idx] = 0.32
                        riesgo_values[2, idx] = 0.60
                    else:
                        riesgo_values[0, idx] = 0.12
                        riesgo_values[1, idx] = 0.43
                        riesgo_values[2, idx] = 0.45
                elif score == 5:
                    riesgo_values[0, idx] = 0.05
                    riesgo_values[1, idx] = 0.25
                    riesgo_values[2, idx] = 0.70
                else:  # score == 6, todo alto
                    riesgo_values[0, idx] = 0.02
                    riesgo_values[1, idx] = 0.13
                    riesgo_values[2, idx] = 0.85
                
                idx += 1
    
    cpd_riesgo = TabularCPD(
        variable='Riesgo',
        variable_card=3,
        values=riesgo_values.tolist(),
        evidence=['Peligro', 'Exposicion', 'Vulnerabilidad'],
        evidence_card=[3, 3, 3],
        state_names={
            'Riesgo': ['Bajo', 'Medio', 'Alto'],
            'Peligro': ['Bajo', 'Medio', 'Alto'],
            'Exposicion': ['Baja', 'Media', 'Alta'],
            'Vulnerabilidad': ['Baja', 'Media', 'Alta']
        }
    )
    
    # Agregar CPDs al modelo
    modelo.add_cpds(
        cpd_deficit, cpd_termico, cpd_sequia,
        cpd_exposicion, cpd_vulnerabilidad,
        cpd_peligro, cpd_riesgo
    )
    
    # Validar
    assert modelo.check_model(), "ERROR: La Red Bayesiana no es válida"
    
    # Motor de inferencia
    inferencia = VariableElimination(modelo)
    
    return modelo, inferencia


# =============================================================================
# CARGA DE DATOS
# =============================================================================

def cargar_vulnerabilidad():
    """Carga CSV de aptitud parroquial (Script 06C)."""
    csvs = sorted(VULN_DIR.glob("aptitud_parroquial_42parr_*.csv"))
    if not csvs:
        raise FileNotFoundError(f"No se encontró CSV de vulnerabilidad en {VULN_DIR}")
    
    df = pd.read_csv(csvs[-1])  # Más reciente
    print(f"  ✓ Vulnerabilidad: {csvs[-1].name}")
    print(f"    {len(df)} filas, {df['parroquia'].nunique()} parroquias")
    return df


def cargar_exposicion():
    """
    Carga CSV de exposición agrícola (Script 04C).
    
    Nota: Script 04C genera:
      - exposicion_resumen_*.csv  → papa, maíz, fréjol a nivel parroquial
      - quinua_provincial_*.csv   → quinua solo a nivel provincial (ESPAC)
    
    Para quinua se distribuye uniformemente entre parroquias como proxy,
    documentando la limitación (solo dato provincial disponible).
    """
    # Buscar CSV resumen
    csvs = sorted(EXPO_DIR.glob("exposicion_resumen_*.csv"))
    if not csvs:
        csvs = sorted(EXPO_DIR.glob("exposicion_parroquial_*.csv"))
    if not csvs:
        csvs = sorted(EXPO_DIR.glob("exposicion*.csv"))
    if not csvs:
        raise FileNotFoundError(f"No se encontró CSV de exposición en {EXPO_DIR}")
    
    df = pd.read_csv(csvs[-1])
    print(f"  ✓ Exposición: {csvs[-1].name}")
    print(f"    {len(df)} parroquias, columnas: {list(df.columns)}")
    
    # Quinua: cargar dato provincial y distribuir uniformemente
    csvs_q = sorted(EXPO_DIR.glob("quinua_provincial_*.csv"))
    if csvs_q:
        df_q = pd.read_csv(csvs_q[-1])
        ha_quinua_prov = df_q['ha_cosechada_espac'].iloc[0] if 'ha_cosechada_espac' in df_q.columns else 18.36
        # Distribución uniforme entre parroquias (limitación documentada)
        df['quinua'] = ha_quinua_prov / len(df)
        print(f"  ✓ Quinua provincial: {ha_quinua_prov:.2f} ha → {ha_quinua_prov/len(df):.2f} ha/parroquia (uniforme)")
        print(f"    ⚠ Limitación: quinua solo disponible a nivel provincial (ESPAC)")
    else:
        df['quinua'] = 0.0
        print(f"  ⚠ Quinua: archivo provincial no encontrado, asignando 0")
    
    print(f"    Cultivos disponibles: {[c for c in CULTIVOS if c in df.columns]}")
    return df


def extraer_peligro_parroquial(ssp, horizonte):
    """
    Extrae índices de peligro del NetCDF agregado para un SSP/horizonte,
    calcula ensemble multi-modelo, y agrega a nivel parroquial.
    
    Usa el mismo método de nearest neighbor del Script 06C para consistencia.
    
    Returns:
        dict: {parroquia: {deficit_mm, dias_estres_{cultivo}, cdd_max}}
    """
    yr_ini, yr_fin = HORIZONTES[horizonte]
    
    resultados_gcm = []
    
    for gcm in GCMS:
        nc_path = INDICES_DIR / ssp / gcm / "indices_agregados_anuales.nc"
        if not nc_path.exists():
            # Intentar sin subdirectorio de horizonte
            alt_paths = list((INDICES_DIR / ssp / gcm).glob("*.nc"))
            if alt_paths:
                nc_path = alt_paths[0]
            else:
                continue
        
        try:
            ds = xr.open_dataset(nc_path)
            
            # Filtrar años del horizonte
            if 'year' in ds.dims:
                ds_h = ds.sel(year=slice(yr_ini, yr_fin))
            elif 'time' in ds.dims:
                ds_h = ds.sel(time=slice(str(yr_ini), str(yr_fin)))
            else:
                # Sin dimensión temporal → asumir ya es el promedio del período
                ds_h = ds
            
            # Promediar temporalmente
            ds_mean = ds_h.mean(dim=[d for d in ds_h.dims if d not in ['lat', 'lon', 'latitude', 'longitude']])
            
            # Extraer variables relevantes
            data = {}
            for var in ['deficit_anual_mm', 'deficit_media_diaria', 'cdd_max',
                        'dias_estres_papa_anual', 'dias_estres_maiz_anual',
                        'dias_estres_frejol_anual', 'dias_estres_quinua_anual']:
                if var in ds_mean:
                    data[var] = ds_mean[var].values.astype(np.float64)
            
            if data:
                # Obtener coordenadas
                lat_name = 'lat' if 'lat' in ds_mean.coords else 'latitude'
                lon_name = 'lon' if 'lon' in ds_mean.coords else 'longitude'
                data['lats'] = ds_mean[lat_name].values
                data['lons'] = ds_mean[lon_name].values
                resultados_gcm.append(data)
            
            ds.close()
        except Exception as e:
            continue
    
    if not resultados_gcm:
        return None
    
    # Ensemble: media de GCMs para cada variable
    ensemble = {}
    for var in resultados_gcm[0]:
        if var in ('lats', 'lons'):
            ensemble[var] = resultados_gcm[0][var]
        else:
            arrays = [r[var] for r in resultados_gcm if var in r]
            if arrays:
                ensemble[var] = np.nanmean(np.stack(arrays, axis=0), axis=0)
    
    return ensemble


def agregar_peligro_a_parroquias(ensemble_data, gdf_parr):
    """
    Agrega datos de peligro del ensemble a nivel parroquial usando
    nearest neighbor (consistente con Script 06C).
    """
    if ensemble_data is None:
        return {}
    
    lats = ensemble_data['lats']
    lons = ensemble_data['lons']
    
    # Crear puntos de la grilla
    from shapely.geometry import Point
    puntos = []
    valores = defaultdict(list)
    
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            for var in ensemble_data:
                if var in ('lats', 'lons'):
                    continue
                val = ensemble_data[var]
                if val.ndim == 2:
                    v = float(val[i, j])
                elif val.ndim == 1:
                    v = float(val[i]) if len(val) > max(i, j) else np.nan
                else:
                    v = float(val)
                
                if not np.isnan(v):
                    if var not in valores:
                        valores[var] = {}
                    valores[var][(i, j)] = v
            
            puntos.append(((i, j), Point(lon, lat)))
    
    # Para cada parroquia: nearest neighbor
    resultado = {}
    for _, parr in gdf_parr.iterrows():
        nombre = parr.get('DPA_DESPAR', parr.get('parroquia', ''))
        centroide = parr.geometry.centroid
        
        # Encontrar punto más cercano
        min_dist = float('inf')
        best_ij = None
        for (i, j), pt in puntos:
            d = centroide.distance(pt)
            if d < min_dist:
                min_dist = d
                best_ij = (i, j)
        
        if best_ij:
            parr_data = {}
            for var in valores:
                if best_ij in valores[var]:
                    parr_data[var] = valores[var][best_ij]
            resultado[nombre] = parr_data
    
    return resultado


# =============================================================================
# INFERENCIA
# =============================================================================

def inferir_riesgo(modelo_inf, evidencia):
    """
    Realiza inferencia en la BN dada la evidencia observada.
    
    Args:
        modelo_inf: VariableElimination engine
        evidencia: dict con estados de nodos raíz
    
    Returns:
        dict: {estado: probabilidad} para el nodo Riesgo
    """
    try:
        result = modelo_inf.query(
            variables=['Riesgo'],
            evidence=evidencia,
            show_progress=False
        )
        probs = {
            'Bajo': float(result.values[0]),
            'Medio': float(result.values[1]),
            'Alto': float(result.values[2])
        }
        return probs
    except Exception as e:
        return {'Bajo': np.nan, 'Medio': np.nan, 'Alto': np.nan}


# =============================================================================
# MAIN
# =============================================================================

def main():
    t0 = datetime.now()
    
    print("╔" + "═"*68 + "╗")
    print("║  SCRIPT 07: RED BAYESIANA - RIESGO AGROCLIMÁTICO" + " "*19 + "║")
    print("║  IPCC AR6: Riesgo = f(Peligro × Exposición × Vulnerabilidad)" + " "*4 + "║")
    print("║  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " "*49 + "║")
    print("╚" + "═"*68 + "╝")
    
    # Crear directorios
    BN_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # ═══════════════════════════════════════════════════════════════════
    # [1/6] CARGAR DATOS
    # ═══════════════════════════════════════════════════════════════════
    print(f"\n[1/6] CARGA DE DATOS")
    print("─" * 60)
    
    # Vulnerabilidad (Script 06C)
    df_vuln = cargar_vulnerabilidad()
    
    # Exposición (Script 04C)
    df_expo = cargar_exposicion()
    
    # Parroquias
    gdf_parr = gpd.read_file(PARROQUIAS_PATH)
    print(f"  ✓ Parroquias: {len(gdf_parr)}")
    
    # Calcular umbrales de exposición por cultivo (terciles)
    umbrales_expo = {}
    for cult in CULTIVOS:
        if cult in df_expo.columns:
            vals = df_expo[cult].dropna()
            if len(vals) > 0:
                umbrales_expo[cult] = [
                    float(vals.quantile(0.33)),
                    float(vals.quantile(0.66))
                ]
            else:
                umbrales_expo[cult] = [0, 0]
        else:
            umbrales_expo[cult] = [0, 0]
    
    print(f"\n  Umbrales de exposición (terciles P33/P66):")
    for cult in CULTIVOS:
        print(f"    {cult}: {umbrales_expo[cult][0]:.1f} / {umbrales_expo[cult][1]:.1f} ha")
    
    # ═══════════════════════════════════════════════════════════════════
    # [2/6] CONSTRUIR RED BAYESIANA
    # ═══════════════════════════════════════════════════════════════════
    print(f"\n[2/6] CONSTRUCCIÓN DE RED BAYESIANA")
    print("─" * 60)
    
    modelo, inferencia = construir_red_bayesiana()
    
    print(f"  ✓ Estructura DAG validada")
    print(f"    Nodos: {modelo.nodes()}")
    print(f"    Aristas: {modelo.edges()}")
    print(f"    CPDs: {len(modelo.cpds)}")
    print(f"    check_model(): PASS")
    
    # Guardar modelo
    pkl_path = BN_DIR / f"modelo_bn_{TIMESTAMP}.pkl"
    with open(pkl_path, 'wb') as f:
        pickle.dump(modelo, f)
    print(f"  ✓ Modelo: {pkl_path.name}")
    
    # ═══════════════════════════════════════════════════════════════════
    # [3/6] INFERENCIA POR PARROQUIA × CULTIVO × SSP × HORIZONTE
    # ═══════════════════════════════════════════════════════════════════
    print(f"\n[3/6] INFERENCIA PROBABILÍSTICA")
    print("─" * 60)
    
    total = len(CULTIVOS) * len(SSPS) * len(HORIZONTES)
    print(f"  Combinaciones SSP × horizonte: {len(SSPS) * len(HORIZONTES)} = {total // len(CULTIVOS)}")
    print(f"  × {len(CULTIVOS)} cultivos × 42 parroquias")
    
    todos_resultados = []
    errores = []
    procesados = 0
    
    for ssp in SSPS:
        for horizonte in HORIZONTES:
            # Extraer peligro para esta combinación
            ensemble_peligro = extraer_peligro_parroquial(ssp, horizonte)
            peligro_parr = agregar_peligro_a_parroquias(ensemble_peligro, gdf_parr)
            
            for cultivo in CULTIVOS:
                procesados += 1
                
                # Filtrar vulnerabilidad para este cultivo/ssp/horizonte
                mask = (
                    (df_vuln['cultivo'] == cultivo) &
                    (df_vuln['ssp'] == ssp) &
                    (df_vuln['horizonte'] == horizonte)
                )
                df_vuln_filtro = df_vuln[mask]
                
                # Variable de estrés térmico específica del cultivo
                var_estres = f'dias_estres_{cultivo}_anual'
                
                for _, parr in gdf_parr.iterrows():
                    nombre_parr = parr.get('DPA_DESPAR', '')
                    canton = parr.get('DPA_DESCAN', '')
                    
                    try:
                        # ─── VULNERABILIDAD ───
                        vuln_row = df_vuln_filtro[
                            df_vuln_filtro['parroquia'] == nombre_parr
                        ]
                        if len(vuln_row) > 0:
                            aptitud = float(vuln_row.iloc[0]['aptitud_media'])
                        else:
                            aptitud = 0.5  # Valor por defecto si no hay dato
                        
                        estado_vuln = discretizar_vulnerabilidad(aptitud)
                        
                        # ─── EXPOSICIÓN ───
                        expo_row = df_expo[
                            df_expo['parroquia'].str.upper() == nombre_parr.upper()
                        ]
                        if len(expo_row) > 0 and cultivo in expo_row.columns:
                            ha = float(expo_row.iloc[0][cultivo])
                        else:
                            ha = 0.0
                        
                        estado_expo = discretizar_exposicion(ha, umbrales_expo.get(cultivo, [0, 0]))
                        
                        # ─── PELIGRO ───
                        parr_peligro = peligro_parr.get(nombre_parr, {})
                        
                        deficit = parr_peligro.get('deficit_anual_mm', -300)
                        estres = parr_peligro.get(var_estres, 15)
                        cdd = parr_peligro.get('cdd_max', 20)
                        
                        estado_deficit = discretizar_peligro_deficit(deficit)
                        estado_termico = discretizar_peligro_termico(estres)
                        estado_sequia = discretizar_peligro_sequia(cdd)
                        
                        # ─── INFERENCIA ───
                        estados_nombre = {0: 'Bajo', 1: 'Medio', 2: 'Alto'}
                        estados_expo_nombre = {0: 'Baja', 1: 'Media', 2: 'Alta'}
                        
                        evidencia = {
                            'Peligro_Deficit': estados_nombre[estado_deficit],
                            'Peligro_Termico': estados_nombre[estado_termico],
                            'Peligro_Sequia': estados_nombre[estado_sequia],
                            'Exposicion': estados_expo_nombre[estado_expo],
                            'Vulnerabilidad': estados_expo_nombre[estado_vuln]
                        }
                        
                        probs = inferir_riesgo(inferencia, evidencia)
                        
                        # Índice de riesgo compuesto: suma ponderada
                        # IR = 0×P(Bajo) + 0.5×P(Medio) + 1×P(Alto)
                        ir = 0.0 * probs['Bajo'] + 0.5 * probs['Medio'] + 1.0 * probs['Alto']
                        
                        todos_resultados.append({
                            'parroquia': nombre_parr,
                            'canton': canton,
                            'cultivo': cultivo,
                            'ssp': ssp,
                            'horizonte': horizonte,
                            'aptitud_rf': aptitud,
                            'superficie_ha': ha,
                            'deficit_mm': deficit,
                            'dias_estres': estres,
                            'cdd_max': cdd,
                            'estado_peligro_deficit': estados_nombre[estado_deficit],
                            'estado_peligro_termico': estados_nombre[estado_termico],
                            'estado_peligro_sequia': estados_nombre[estado_sequia],
                            'estado_exposicion': estados_expo_nombre[estado_expo],
                            'estado_vulnerabilidad': estados_expo_nombre[estado_vuln],
                            'prob_riesgo_bajo': probs['Bajo'],
                            'prob_riesgo_medio': probs['Medio'],
                            'prob_riesgo_alto': probs['Alto'],
                            'indice_riesgo': ir
                        })
                    
                    except Exception as e:
                        errores.append(f"{cultivo}/{ssp}/{horizonte}/{nombre_parr}: {e}")
                
                # Progreso
                pct = procesados / total * 100
                print(f"\r    {'█' * int(pct/3)}{'░' * (33-int(pct/3))} "
                      f"{pct:5.1f}% [{procesados}/{total}] "
                      f"✓ {cultivo}/{ssp}/{horizonte}", end='', flush=True)
    
    print()
    
    if not todos_resultados:
        print("  ❌ Sin resultados. Verificar datos de entrada.")
        return
    
    # ═══════════════════════════════════════════════════════════════════
    # [4/6] GUARDAR RESULTADOS
    # ═══════════════════════════════════════════════════════════════════
    print(f"\n[4/6] GUARDAR RESULTADOS")
    print("─" * 60)
    
    df_riesgo = pd.DataFrame(todos_resultados)
    
    # CSV completo
    csv_path = BN_DIR / f"riesgo_parroquial_{TIMESTAMP}.csv"
    df_riesgo.to_csv(csv_path, index=False, float_format='%.4f')
    print(f"  ✓ {csv_path.name}")
    print(f"    {len(df_riesgo)} filas ({df_riesgo['parroquia'].nunique()} parroquias)")
    
    # Pivote: parroquia × cultivo vs índice de riesgo
    pivote = df_riesgo.pivot_table(
        values='indice_riesgo',
        index=['parroquia', 'canton'],
        columns=['cultivo', 'ssp', 'horizonte'],
        aggfunc='mean'
    )
    csv_piv = BN_DIR / f"pivote_riesgo_{TIMESTAMP}.csv"
    pivote.to_csv(csv_piv, float_format='%.4f')
    print(f"  ✓ {csv_piv.name}")
    
    # ═══════════════════════════════════════════════════════════════════
    # [5/6] RESUMEN ESTADÍSTICO
    # ═══════════════════════════════════════════════════════════════════
    print(f"\n[5/6] RESUMEN ESTADÍSTICO")
    print("─" * 60)
    
    resumen = df_riesgo.groupby(['cultivo', 'ssp', 'horizonte']).agg(
        ir_media=('indice_riesgo', 'mean'),
        ir_min=('indice_riesgo', 'min'),
        ir_max=('indice_riesgo', 'max'),
        ir_std=('indice_riesgo', 'std'),
        prob_alto_media=('prob_riesgo_alto', 'mean')
    ).reset_index()
    
    print(f"\n  {'Cultivo':10s} {'SSP':8s} {'Horizonte':12s} {'IR media':>8s} {'IR min':>8s} "
          f"{'IR max':>8s} {'P(Alto)':>8s}")
    print(f"  {'─'*10} {'─'*8} {'─'*12} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")
    
    for _, r in resumen.sort_values(['cultivo', 'ssp', 'horizonte']).iterrows():
        print(f"  {r['cultivo']:10s} {r['ssp']:8s} {r['horizonte']:12s} "
              f"{r['ir_media']:8.4f} {r['ir_min']:8.4f} {r['ir_max']:8.4f} "
              f"{r['prob_alto_media']:8.4f}")
    
    # Top 5 parroquias de mayor riesgo (SSP585, 2061-2080)
    peor = df_riesgo[
        (df_riesgo['ssp'] == 'ssp585') & 
        (df_riesgo['horizonte'] == '2061-2080')
    ].groupby(['parroquia', 'canton']).agg(
        ir_media=('indice_riesgo', 'mean')
    ).reset_index().nlargest(10, 'ir_media')
    
    print(f"\n  TOP 10 parroquias mayor riesgo (SSP585, 2061-2080):")
    print(f"  {'Parroquia':30s} {'Cantón':20s} {'IR media':>8s}")
    print(f"  {'─'*30} {'─'*20} {'─'*8}")
    for _, r in peor.iterrows():
        print(f"  {r['parroquia']:30s} {r['canton']:20s} {r['ir_media']:8.4f}")
    
    # ═══════════════════════════════════════════════════════════════════
    # [6/6] REPORTE DE AUDITORÍA
    # ═══════════════════════════════════════════════════════════════════
    print(f"\n[6/6] REPORTE DE AUDITORÍA")
    print("─" * 60)
    
    rep_path = REPORTS_DIR / f"REPORTE_SCRIPT_07_{TIMESTAMP}.txt"
    with open(rep_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("REPORTE - SCRIPT 07: RED BAYESIANA\n")
        f.write("INTEGRACIÓN DE RIESGO AGROCLIMÁTICO (IPCC AR6)\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Fecha: {datetime.now()}\n")
        f.write(f"Autor: {AUTOR}\n\n")
        
        f.write("ESTRUCTURA DE LA RED BAYESIANA:\n")
        f.write(f"  Nodos: {list(modelo.nodes())}\n")
        f.write(f"  Aristas: {list(modelo.edges())}\n")
        f.write(f"  check_model(): PASS\n\n")
        
        f.write("MARCO TEÓRICO:\n")
        f.write("  RIESGO = f(Peligro × Exposición × Vulnerabilidad)\n")
        f.write("  Ref: IPCC AR6 WG2, Cap. 1 (Pörtner et al., 2022)\n\n")
        
        f.write("DISCRETIZACIÓN:\n")
        f.write("  Peligro_Deficit: < -200mm (Bajo) | -200 a -500mm (Medio) | > -500mm (Alto)\n")
        f.write("  Peligro_Termico: < 10 días (Bajo) | 10-30 (Medio) | > 30 (Alto)\n")
        f.write("  Peligro_Sequia:  < 15 CDD (Bajo) | 15-30 (Medio) | > 30 (Alto)\n")
        f.write("  Exposicion:      Terciles P33/P66 de superficie cultivada\n")
        f.write("  Vulnerabilidad:  aptitud > 0.7 (Baja) | 0.4-0.7 (Media) | < 0.4 (Alta)\n\n")
        
        f.write(f"RESULTADOS:\n")
        f.write(f"  Registros: {len(df_riesgo)}\n")
        f.write(f"  Parroquias: {df_riesgo['parroquia'].nunique()}\n")
        f.write(f"  Cultivos: {sorted(df_riesgo['cultivo'].unique())}\n")
        f.write(f"  SSPs: {sorted(df_riesgo['ssp'].unique())}\n")
        f.write(f"  Horizontes: {sorted(df_riesgo['horizonte'].unique())}\n")
        f.write(f"  Errores: {len(errores)}\n\n")
        
        if errores:
            f.write("ERRORES:\n")
            for e in errores[:20]:
                f.write(f"  - {e}\n")
            f.write("\n")
        
        f.write("RESUMEN POR CULTIVO × SSP × HORIZONTE:\n")
        f.write(f"{'Cultivo':12s} {'SSP':8s} {'Horiz':12s} {'IR media':>8s} {'P(Alto)':>8s}\n")
        for _, r in resumen.sort_values(['cultivo', 'ssp', 'horizonte']).iterrows():
            f.write(f"{r['cultivo']:12s} {r['ssp']:8s} {r['horizonte']:12s} "
                    f"{r['ir_media']:8.4f} {r['prob_alto_media']:8.4f}\n")
        
        f.write("\n" + "=" * 70 + "\n")
        f.write("ÍNDICE DE RIESGO COMPUESTO (IR):\n")
        f.write("  IR = 0×P(Bajo) + 0.5×P(Medio) + 1×P(Alto)\n")
        f.write("  Rango: [0, 1] donde 0 = sin riesgo, 1 = riesgo máximo\n\n")
        
        f.write("REFERENCIAS:\n")
        f.write("  IPCC (2022). AR6 WG2. Cambridge University Press.\n")
        f.write("  Pearl (1988). Probabilistic Reasoning. Morgan Kaufmann.\n")
        f.write("  Kjærulff & Madsen (2013). Bayesian Networks. Springer.\n")
        f.write("  Allen et al. (1998). FAO-56.\n")
        f.write("  Challinor et al. (2014). Nature Climate Change, 4, 287-291.\n")
        f.write("  McKee et al. (1993). 8th Conf. Applied Climatology.\n")
        f.write("=" * 70 + "\n")
    
    print(f"  ✓ {rep_path.name}")
    
    # ═══════════════════════════════════════════════════════════════════
    # RESUMEN FINAL
    # ═══════════════════════════════════════════════════════════════════
    t_total = datetime.now() - t0
    print()
    print("╔" + "═"*68 + "╗")
    print("║  ✓ SCRIPT 07 COMPLETADO" + " "*44 + "║")
    print("╚" + "═"*68 + "╝")
    print(f"\n  ⏱  Tiempo: {t_total}")
    print(f"  ✓  Registros: {len(df_riesgo)}")
    print(f"  ❌ Errores: {len(errores)}")
    print(f"\n  📁 {BN_DIR}")
    print(f"\n  🔜 Siguiente: Script 08 (Generación de mapas de riesgo)")
    print("═"*70)
    
    return df_riesgo, modelo


if __name__ == "__main__":
    df_riesgo, modelo = main()