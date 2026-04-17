"""
Script publicado como parte del Geoportal Riesgo Agroclimático — Imbabura, Ecuador
Pinto Páez, V. H. (2026). https://doi.org/10.5281/zenodo.19288559
Licencia: CC BY 4.0

NOTA: este archivo fue sanitizado para publicación pública.
- Credenciales (API keys, tokens, service accounts) removidas → <REDACTED_*>
- Rutas absolutas locales sustituidas por <RUTA_LOCAL>
Antes de ejecutar, configure sus propias rutas de entrada/salida y credenciales.

Archivo original: SCRIPT 06 ENTRENAMIENTO DE RANDOM FOREST + ANÁLISIS SHAP.py
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
SCRIPT 06: ENTRENAMIENTO DE RANDOM FOREST + ANÁLISIS SHAP
===============================================================================
Versión: 1.1.0
Fecha: 2026-02-26
Autor: Víctor Hugo Pinto Páez

Tesis: Riesgo agroclimático de cultivos andinos bajo escenarios CMIP6
       en la provincia de Imbabura: modelamiento de distribución de
       especies para la gestión territorial

Universidad: San Gregorio de Portoviejo
Programa: Maestría en Prevención y Gestión de Riesgos

===============================================================================

1. VARIABLES PREDICTORAS: El Script 03C generó una variable de estrés
   térmico ESPECÍFICA por cultivo (dias_estres_{cultivo}_anual), porque
   cada cultivo tiene un umbral térmico distinto:
     - Papa: Tmax > 25°C (CIP, 2020)
     - Maíz: Tmax > 35°C (FAO-56)
     - Fréjol: Tmax > 30°C (CIAT)
     - Quinua: Tmax > 32°C (Jacobsen, 2003)
   
   El modelo de cada cultivo usa SU variable de estrés correspondiente.
   Total: 12 variables comunes + 1 específica = 13 predictores por modelo.

2. VARIABLES TÉRMICAS AGREGADAS: El Script 05C calculó 3 variables
   térmicas adicionales desde datos diarios BASD-CMIP6-PE:
     - tmax_media_anual: régimen térmico máximo
     - tmin_media_anual: limitante altitudinal (Hijmans et al., 2003)
     - rango_termico_diurno: ≡ bio02 WorldClim, fotosíntesis/respiración
   
   Total final: 15 comunes + 1 específica = 16 predictores por modelo.

3. VARIABLES ELIMINADAS: La variable genérica 'dias_estres_termico_anual'
   no existe en los datasets; fue reemplazada por las específicas por cultivo.

4. SHAP: Corregido error de compatibilidad "Per-column arrays must each
   be 1-dimensional" convirtiendo datos a numpy float64 explícito.

===============================================================================
JUSTIFICACIÓN CIENTÍFICA DE PARÁMETROS
===============================================================================

n_estimators = 500
    Probst & Boulesteix (2018): convergencia de importancia de variables.
    Estándar en SDM (Cutler et al., 2007; Mi et al., 2017).

max_features = 'sqrt'
    √p candidatas por split. Recomendación de Breiman (2001) para
    clasificación. Con p=16, selecciona 4 variables por split.

min_samples_leaf = 5
    Previene sobreajuste. Estándar en SDM (Cutler et al., 2007).

class_weight = 'balanced'
    Compensa ratio ~1.5:1. Robusto según Barbet-Massin et al. (2012).

Validación cruzada espacial (k=5, bloques de 2°)
    Roberts et al. (2017), Valavi et al. (2019): evita inflación de
    métricas por autocorrelación espacial.

SHAP TreeExplainer
    Lundberg & Lee (2017), Lundberg et al. (2020): atribuciones
    consistentes basadas en valores de Shapley.

===============================================================================
REFERENCIAS
===============================================================================

Breiman, L. (2001). Random Forests. Machine Learning, 45(1), 5-32.
Cutler, D.R., et al. (2007). Ecology, 88(11), 2783-2792.
King, G., & Zeng, L. (2001). Political Analysis, 9(2), 137-163.
Lundberg, S.M., & Lee, S.I. (2017). NeurIPS 30.
Lundberg, S.M., et al. (2020). Nature Machine Intelligence, 2(1), 56-67.
Mi, C., et al. (2017). Ecological Informatics, 38, 13-18.
Probst, P., & Boulesteix, A.L. (2018). JMLR, 18, 1-18.
Roberts, D.R., et al. (2017). Ecography, 40(8), 913-929.
Valavi, R., et al. (2019). Methods in Ecology and Evolution, 10(2), 225-232.

===============================================================================
"""

import os
import sys
import json
import warnings
import hashlib
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
import traceback

warnings.filterwarnings('ignore')

# =============================================================================
# IMPORTACIÓN DE LIBRERÍAS
# =============================================================================

try:
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import (
        roc_auc_score, accuracy_score, cohen_kappa_score,
        confusion_matrix, roc_curve, brier_score_loss
    )
    from sklearn.inspection import permutation_importance
    import joblib
    LIBS_OK = True
except ImportError as e:
    print(f"Error de importación: {e}")
    print("Ejecute: pip install numpy pandas scikit-learn joblib")
    sys.exit(1)

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    print("⚠ SHAP no disponible. Instalarlo con: pip install shap")
    print("  Se usará importancia por permutación como alternativa.")


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

@dataclass
class Config:
    """Configuración centralizada con trazabilidad científica."""

    VERSION: str = "1.1.0"
    AUTOR: str = "Víctor Hugo Pinto Páez"
    UNIVERSIDAD: str = "Universidad San Gregorio de Portoviejo"
    TITULO_TESIS: str = (
        "Riesgo agroclimático de cultivos andinos bajo escenarios CMIP6 "
        "en la provincia de Imbabura: modelamiento de distribución de "
        "especies para la gestión territorial"
    )

    # --- Rutas ---
    BASE_DIR: Path = Path(r"D:/POSGRADOS/TESIS/Prevención_de_Riesgos")
    DATASETS_DIR: Path = field(default=None)
    OUTPUT_DIR: Path = field(default=None)
    REPORTES_DIR: Path = field(default=None)

    # --- Cultivos ---
    CULTIVOS: List[str] = field(default_factory=lambda: [
        'papa', 'maiz', 'frejol', 'quinua'
    ])

    NOMBRES_CIENTIFICOS: Dict[str, str] = field(default_factory=lambda: {
        'papa': 'Solanum tuberosum L.',
        'maiz': 'Zea mays L.',
        'frejol': 'Phaseolus vulgaris L.',
        'quinua': 'Chenopodium quinoa Willd.'
    })

    # --- Parámetros Random Forest ---
    N_ESTIMATORS: int = 500          # Probst & Boulesteix (2018)
    MAX_FEATURES: str = 'sqrt'       # Breiman (2001)
    MIN_SAMPLES_SPLIT: int = 10
    MIN_SAMPLES_LEAF: int = 5        # Cutler et al. (2007)
    MAX_DEPTH: int = None
    CLASS_WEIGHT: str = 'balanced'   # King & Zeng (2001)
    RANDOM_STATE: int = 42
    N_JOBS: int = -1
    OOB_SCORE: bool = True

    # --- Validación cruzada espacial ---
    N_FOLDS: int = 5
    BLOCK_SIZE_DEG: float = 2.0      # Roberts et al. (2017)

    # --- Umbrales de aceptación (Protocolo Metodológico) ---
    UMBRAL_AUC: float = 0.75
    UMBRAL_TSS: float = 0.50
    UMBRAL_KAPPA: float = 0.40
    UMBRAL_OOB_ERROR: float = 0.30

    # --- Variables predictoras ---
    # 15 variables COMUNES a todos los cultivos
    VARIABLES_COMUNES: List[str] = field(default_factory=lambda: [
        'ET0_media_diaria',       # Hargreaves & Samani (1985) - Script 03A
        'ET0_anual_mm',           # Hargreaves & Samani (1985) - Script 03A
        'deficit_media_diaria',   # FAO-56 (Allen et al., 1998) - Script 03B
        'deficit_anual_mm',       # FAO-56 - Script 03B
        'pct_dias_deficit',       # FAO-56 - Script 03B
        'dias_secos_anual',       # Zhang et al. (2011) - Script 03D
        'cdd_max',                # ETCCDI (Frich et al., 2002) - Script 03D
        'eventos_sequia_7d',      # Script 03D
        'eventos_sequia_15d',     # Script 03D
        'dias_helada_anual',      # Snyder & Melo-Abreu (2005) - Script 03E
        'pr_anual_mm',            # Script 03F
        'indice_aridez',          # UNEP (1992) - Script 03F
        'tmax_media_anual',       # Régimen térmico máximo - Script 05C
        'tmin_media_anual',       # Limitante altitudinal (Hijmans et al., 2003) - Script 05C
        'rango_termico_diurno',   # ≡ bio02 WorldClim, tuberización papa (CIP, 2020) - Script 05C
    ])

    # Variable ESPECÍFICA por cultivo (Script 03C)
    # Cada cultivo tiene su propio umbral de estrés térmico:
    #   Papa: Tmax > 25°C (CIP, 2020)
    #   Maíz: Tmax > 35°C (FAO-56)
    #   Fréjol: Tmax > 30°C (CIAT)
    #   Quinua: Tmax > 32°C (Jacobsen, 2003)
    VARIABLE_ESTRES_CULTIVO: Dict[str, str] = field(default_factory=lambda: {
        'papa': 'dias_estres_papa_anual',
        'maiz': 'dias_estres_maiz_anual',
        'frejol': 'dias_estres_frejol_anual',
        'quinua': 'dias_estres_quinua_anual',
    })

    TIMESTAMP: str = field(default_factory=lambda: datetime.now().strftime('%Y%m%d_%H%M%S'))

    def __post_init__(self):
        if self.DATASETS_DIR is None:
            self.DATASETS_DIR = Path(r"D:/POSGRADOS/TESIS/02_DATOS/sdm_training")
        if self.OUTPUT_DIR is None:
            self.OUTPUT_DIR = self.BASE_DIR / "04_RESULTADOS" / "fase4_modelamiento" / "random_forest"
        if self.REPORTES_DIR is None:
            self.REPORTES_DIR = self.BASE_DIR / "05_DOCUMENTACION" / "reportes_auditoria"

        for subdir in ['modelos', 'metricas', 'shap', 'auditoria']:
            (self.OUTPUT_DIR / subdir).mkdir(parents=True, exist_ok=True)
        self.REPORTES_DIR.mkdir(parents=True, exist_ok=True)

    def get_variables_cultivo(self, cultivo: str) -> List[str]:
        """
        Retorna las 16 variables para un cultivo específico:
        15 comunes + 1 de estrés térmico específica del cultivo.
        """
        variables = self.VARIABLES_COMUNES.copy()
        var_estres = self.VARIABLE_ESTRES_CULTIVO.get(cultivo)
        if var_estres:
            variables.append(var_estres)
        return variables


# =============================================================================
# FUNCIONES DE CARGA
# =============================================================================

def buscar_dataset(config: Config, cultivo: str) -> Optional[Path]:
    """Busca el dataset más reciente para un cultivo."""
    patron = f"dataset_rf_{cultivo}_*.csv"
    archivos = sorted(config.DATASETS_DIR.glob(patron))
    if not archivos:
        return None
    return archivos[-1]


def cargar_dataset(filepath: Path, variables: List[str]) -> pd.DataFrame:
    """Carga y valida un dataset."""
    df = pd.read_csv(filepath)

    # Verificar que todas las variables existen
    faltantes = [v for v in variables if v not in df.columns]
    if faltantes:
        raise ValueError(f"Variables faltantes en {filepath.name}: {faltantes}")

    if 'presencia' not in df.columns:
        raise ValueError("Columna 'presencia' no encontrada")

    # Eliminar NaN
    n_antes = len(df)
    df = df.dropna(subset=variables + ['presencia'])
    n_despues = len(df)
    if n_antes != n_despues:
        print(f"  ⚠ Eliminados {n_antes - n_despues} registros con NaN "
              f"({(n_antes-n_despues)/n_antes*100:.1f}%)")

    return df


# =============================================================================
# VALIDACIÓN CRUZADA ESPACIAL
# =============================================================================

def crear_folds_espaciales(df: pd.DataFrame, n_folds: int,
                           block_size: float) -> List[Tuple[np.ndarray, np.ndarray]]:
    """
    Folds de CV basados en bloques espaciales de latitud.
    
    Referencia: Valavi et al. (2019), Roberts et al. (2017).
    """
    if 'lat' not in df.columns:
        print("  ⚠ Columna 'lat' no encontrada. Usando CV estratificada.")
        from sklearn.model_selection import StratifiedKFold
        skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)
        return list(skf.split(df, df['presencia']))

    lat_min = df['lat'].min()
    lat_max = df['lat'].max()

    n_blocks = max(n_folds, int(np.ceil((lat_max - lat_min) / block_size)))
    block_edges = np.linspace(lat_min, lat_max + 0.001, n_blocks + 1)
    block_ids = np.digitize(df['lat'].values, block_edges) - 1
    block_ids = np.clip(block_ids, 0, n_blocks - 1)

    unique_blocks = np.unique(block_ids)
    np.random.seed(42)
    np.random.shuffle(unique_blocks)

    fold_assignments = np.zeros(len(df), dtype=int)
    for i, block in enumerate(unique_blocks):
        fold_assignments[block_ids == block] = i % n_folds

    folds = []
    for fold_i in range(n_folds):
        test_mask = fold_assignments == fold_i
        train_mask = ~test_mask

        train_classes = df.iloc[np.where(train_mask)[0]]['presencia'].unique()
        test_classes = df.iloc[np.where(test_mask)[0]]['presencia'].unique()

        if len(train_classes) < 2 or len(test_classes) < 2:
            continue

        folds.append((np.where(train_mask)[0], np.where(test_mask)[0]))

    if len(folds) < 3:
        print("  ⚠ Bloques espaciales insuficientes. Usando CV estratificada.")
        from sklearn.model_selection import StratifiedKFold
        skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)
        folds = list(skf.split(df, df['presencia']))

    return folds


# =============================================================================
# MÉTRICAS
# =============================================================================

def calcular_tss(y_true, y_pred):
    """TSS = Sensibilidad + Especificidad - 1 (Allouche et al., 2006)."""
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    sens = tp / (tp + fn) if (tp + fn) > 0 else 0
    spec = tn / (tn + fp) if (tn + fp) > 0 else 0
    return sens + spec - 1


def calcular_umbral_optimo(y_true, y_prob):
    """Umbral que maximiza TSS (Liu et al., 2013)."""
    fpr, tpr, thresholds = roc_curve(y_true, y_prob)
    tss_vals = tpr - fpr
    return thresholds[np.argmax(tss_vals)]


def calcular_metricas(y_true, y_prob, umbral=None):
    """Métricas completas de evaluación."""
    auc = roc_auc_score(y_true, y_prob)
    if umbral is None:
        umbral = calcular_umbral_optimo(y_true, y_prob)

    y_pred = (y_prob >= umbral).astype(int)
    tss = calcular_tss(y_true, y_pred)
    kappa = cohen_kappa_score(y_true, y_pred)
    acc = accuracy_score(y_true, y_pred)
    brier = brier_score_loss(y_true, y_prob)

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    sens = tp / (tp + fn) if (tp + fn) > 0 else 0
    spec = tn / (tn + fp) if (tn + fp) > 0 else 0

    return {
        'AUC_ROC': round(auc, 4), 'TSS': round(tss, 4),
        'Kappa': round(kappa, 4), 'Accuracy': round(acc, 4),
        'Sensitivity': round(sens, 4), 'Specificity': round(spec, 4),
        'Brier_Score': round(brier, 4), 'Umbral_optimo': round(umbral, 4),
        'TP': int(tp), 'TN': int(tn), 'FP': int(fp), 'FN': int(fn)
    }


# =============================================================================
# ENTRENAMIENTO Y EVALUACIÓN
# =============================================================================

def entrenar_evaluar_cultivo(df, variables, cultivo, config):
    """Pipeline completo para un cultivo."""

    print(f"\n{'='*70}")
    print(f"  CULTIVO: {cultivo.upper()} ({config.NOMBRES_CIENTIFICOS[cultivo]})")
    print(f"{'='*70}")

    X = df[variables].values.astype(np.float64)
    y = df['presencia'].values.astype(np.int32)

    n_pres = int(y.sum())
    n_aus = len(y) - n_pres
    ratio = n_aus / n_pres if n_pres > 0 else 0

    print(f"  Presencias: {n_pres}")
    print(f"  Pseudo-ausencias: {n_aus}")
    print(f"  Ratio: {ratio:.2f}:1")
    print(f"  Variables predictoras: {len(variables)}")
    for v in variables:
        marcador = " ← específica" if "estres" in v and cultivo in v else ""
        print(f"    • {v}{marcador}")

    # -----------------------------------------------------------------
    # 1. VALIDACIÓN CRUZADA ESPACIAL
    # -----------------------------------------------------------------
    print(f"\n  [1/5] Validación cruzada espacial ({config.N_FOLDS} folds, "
          f"bloques de {config.BLOCK_SIZE_DEG}°)...")

    folds = crear_folds_espaciales(df, config.N_FOLDS, config.BLOCK_SIZE_DEG)
    print(f"        Folds generados: {len(folds)}")

    metricas_folds = []
    y_prob_cv = np.zeros(len(y))
    fold_assignments = np.full(len(y), -1, dtype=int)

    for fold_i, (train_idx, test_idx) in enumerate(folds):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        rf_fold = RandomForestClassifier(
            n_estimators=config.N_ESTIMATORS,
            max_features=config.MAX_FEATURES,
            min_samples_split=config.MIN_SAMPLES_SPLIT,
            min_samples_leaf=config.MIN_SAMPLES_LEAF,
            max_depth=config.MAX_DEPTH,
            class_weight=config.CLASS_WEIGHT,
            random_state=config.RANDOM_STATE,
            n_jobs=config.N_JOBS,
            oob_score=False
        )
        rf_fold.fit(X_train, y_train)

        y_prob_test = rf_fold.predict_proba(X_test)[:, 1]
        y_prob_cv[test_idx] = y_prob_test
        fold_assignments[test_idx] = fold_i

        m_fold = calcular_metricas(y_test, y_prob_test)
        m_fold['fold'] = fold_i + 1
        m_fold['n_train'] = len(train_idx)
        m_fold['n_test'] = len(test_idx)
        metricas_folds.append(m_fold)

        print(f"        Fold {fold_i+1}: AUC={m_fold['AUC_ROC']:.3f}, "
              f"TSS={m_fold['TSS']:.3f}, Kappa={m_fold['Kappa']:.3f} "
              f"(train={len(train_idx)}, test={len(test_idx)})")

    evaluated = fold_assignments >= 0
    metricas_cv = calcular_metricas(y[evaluated], y_prob_cv[evaluated])

    aucs = [m['AUC_ROC'] for m in metricas_folds]
    tsss = [m['TSS'] for m in metricas_folds]

    print(f"\n        --- MÉTRICAS CV CONSOLIDADAS ---")
    print(f"        AUC-ROC:  {metricas_cv['AUC_ROC']:.4f} (σ={np.std(aucs):.4f})")
    print(f"        TSS:      {metricas_cv['TSS']:.4f} (σ={np.std(tsss):.4f})")
    print(f"        Kappa:    {metricas_cv['Kappa']:.4f}")
    print(f"        Accuracy: {metricas_cv['Accuracy']:.4f}")

    # -----------------------------------------------------------------
    # 2. MODELO FINAL
    # -----------------------------------------------------------------
    print(f"\n  [2/5] Entrenando modelo final (n={len(y)})...")

    rf_final = RandomForestClassifier(
        n_estimators=config.N_ESTIMATORS,
        max_features=config.MAX_FEATURES,
        min_samples_split=config.MIN_SAMPLES_SPLIT,
        min_samples_leaf=config.MIN_SAMPLES_LEAF,
        max_depth=config.MAX_DEPTH,
        class_weight=config.CLASS_WEIGHT,
        random_state=config.RANDOM_STATE,
        n_jobs=config.N_JOBS,
        oob_score=config.OOB_SCORE
    )
    rf_final.fit(X, y)

    oob_error = 1 - rf_final.oob_score_
    print(f"        OOB Score: {rf_final.oob_score_:.4f}")
    print(f"        OOB Error: {oob_error:.4f}")

    # -----------------------------------------------------------------
    # 3. IMPORTANCIA POR PERMUTACIÓN
    # -----------------------------------------------------------------
    print(f"\n  [3/5] Calculando importancia de variables (permutación)...")

    perm_imp = permutation_importance(
        rf_final, X, y,
        n_repeats=30, random_state=config.RANDOM_STATE,
        n_jobs=config.N_JOBS, scoring='roc_auc'
    )

    gini_imp = rf_final.feature_importances_

    df_importancia = pd.DataFrame({
        'variable': variables,
        'importancia_gini': np.round(gini_imp, 6),
        'importancia_gini_pct': np.round(gini_imp / gini_imp.sum() * 100, 2),
        'importancia_permutacion_mean': np.round(perm_imp.importances_mean, 6),
        'importancia_permutacion_std': np.round(perm_imp.importances_std, 6),
    }).sort_values('importancia_permutacion_mean', ascending=False)
    df_importancia['ranking'] = range(1, len(variables) + 1)

    print(f"\n        Top 5 variables (permutación):")
    for _, row in df_importancia.head(5).iterrows():
        print(f"          {int(row['ranking'])}. {row['variable']}: "
              f"{row['importancia_permutacion_mean']:.4f} "
              f"(±{row['importancia_permutacion_std']:.4f})")

    # -----------------------------------------------------------------
    # 4. SHAP VALUES
    # -----------------------------------------------------------------
    print(f"\n  [4/5] Calculando SHAP values...")

    df_shap = None

    if SHAP_AVAILABLE:
        try:
            # FIX: Usar DataFrame con dtypes explícitos para evitar
            # error "Per-column arrays must each be 1-dimensional"
            X_df = pd.DataFrame(X, columns=variables).astype(np.float64)

            # Submuestra si dataset grande
            if len(X_df) > 5000:
                X_shap = X_df.sample(n=5000, random_state=42)
            else:
                X_shap = X_df

            explainer = shap.TreeExplainer(rf_final)
            shap_values_raw = explainer.shap_values(X_shap)

            # Clase positiva (presencia)
            if isinstance(shap_values_raw, list):
                shap_array = np.array(shap_values_raw[1], dtype=np.float64)
            else:
                shap_array = np.array(shap_values_raw, dtype=np.float64)

            mean_abs_shap = np.abs(shap_array).mean(axis=0)

            df_shap = pd.DataFrame({
                'variable': variables,
                'mean_abs_shap': np.round(mean_abs_shap, 6),
                'mean_abs_shap_pct': np.round(
                    mean_abs_shap / mean_abs_shap.sum() * 100, 2
                )
            }).sort_values('mean_abs_shap', ascending=False)
            df_shap['ranking_shap'] = range(1, len(variables) + 1)

            print(f"        ✓ SHAP calculado exitosamente")
            print(f"        Top 5 variables (SHAP):")
            for _, row in df_shap.head(5).iterrows():
                print(f"          {int(row['ranking_shap'])}. {row['variable']}: "
                      f"|SHAP|={row['mean_abs_shap']:.4f} "
                      f"({row['mean_abs_shap_pct']:.1f}%)")

        except Exception as e:
            print(f"        ⚠ Error en SHAP: {e}")
            print(f"        Usando importancia por permutación como respaldo.")
    else:
        print(f"        SHAP no disponible. Usando permutación.")

    # -----------------------------------------------------------------
    # 5. GUARDAR
    # -----------------------------------------------------------------
    print(f"\n  [5/5] Guardando modelo y resultados...")

    modelo_path = (config.OUTPUT_DIR / "modelos" /
                   f"rf_{cultivo}_{config.TIMESTAMP}.joblib")
    joblib.dump(rf_final, modelo_path)
    print(f"        Modelo: {modelo_path.name}")

    # Metadatos
    meta = {
        'cultivo': cultivo,
        'especie': config.NOMBRES_CIENTIFICOS[cultivo],
        'version_script': config.VERSION,
        'n_presencias': n_pres,
        'n_ausencias': n_aus,
        'ratio': round(ratio, 2),
        'variables': variables,
        'n_variables': len(variables),
        'variable_estres_especifica': config.VARIABLE_ESTRES_CULTIVO[cultivo],
        'parametros_rf': {
            'n_estimators': config.N_ESTIMATORS,
            'max_features': config.MAX_FEATURES,
            'min_samples_split': config.MIN_SAMPLES_SPLIT,
            'min_samples_leaf': config.MIN_SAMPLES_LEAF,
            'max_depth': str(config.MAX_DEPTH),
            'class_weight': config.CLASS_WEIGHT,
            'random_state': config.RANDOM_STATE
        },
        'metricas_cv': metricas_cv,
        'oob_error': round(oob_error, 4),
        'oob_score': round(rf_final.oob_score_, 4),
        'n_folds': len(folds),
        'block_size_deg': config.BLOCK_SIZE_DEG,
        'umbral_optimo': metricas_cv['Umbral_optimo'],
        'timestamp': config.TIMESTAMP
    }
    meta_path = (config.OUTPUT_DIR / "modelos" /
                 f"rf_{cultivo}_{config.TIMESTAMP}_meta.json")
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    # Importancias
    imp_path = (config.OUTPUT_DIR / "shap" /
                f"importancia_{cultivo}_{config.TIMESTAMP}.csv")
    df_importancia.to_csv(imp_path, index=False)

    # SHAP
    if df_shap is not None:
        shap_path = (config.OUTPUT_DIR / "shap" /
                     f"shap_{cultivo}_{config.TIMESTAMP}.csv")
        df_shap.to_csv(shap_path, index=False)

    return {
        'cultivo': cultivo,
        'modelo': rf_final,
        'metricas_cv': metricas_cv,
        'metricas_folds': metricas_folds,
        'oob_error': oob_error,
        'importancia': df_importancia,
        'shap': df_shap,
        'umbral_optimo': metricas_cv['Umbral_optimo'],
        'modelo_path': modelo_path,
        'variables': variables
    }


# =============================================================================
# REPORTE DE AUDITORÍA
# =============================================================================

def generar_reporte(resultados, config):
    """Genera reporte de auditoría completo."""

    reporte_path = (config.REPORTES_DIR /
                    f"REPORTE_SCRIPT_06_{config.TIMESTAMP}.txt")

    with open(reporte_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("REPORTE DE AUDITORÍA - SCRIPT 06 v1.1.0\n")
        f.write("ENTRENAMIENTO DE RANDOM FOREST + ANÁLISIS SHAP\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Versión: {config.VERSION}\n")
        f.write(f"Autor: {config.AUTOR}\n\n")

        # Corrección documentada
        f.write("-" * 70 + "\n")
        f.write("CORRECCIÓN v1.1.0\n")
        f.write("-" * 70 + "\n")
        f.write("  v1.0.0 usó 12 variables porque 'dias_estres_termico_anual'\n")
        f.write("  no existe. El Script 03C generó variables ESPECÍFICAS por\n")
        f.write("  cultivo: dias_estres_{cultivo}_anual. Además, Script 05C\n")
        f.write("  calculó 3 variables térmicas adicionales (tmax_media_anual,\n")
        f.write("  tmin_media_anual, rango_termico_diurno) desde datos diarios\n")
        f.write("  BASD-CMIP6-PE. v1.1.0 usa 15 comunes + 1 específica = 16.\n\n")

        # Parámetros
        f.write("-" * 70 + "\n")
        f.write("PARÁMETROS DEL MODELO\n")
        f.write("-" * 70 + "\n")
        f.write(f"  n_estimators:      {config.N_ESTIMATORS} (Probst & Boulesteix, 2018)\n")
        f.write(f"  max_features:      {config.MAX_FEATURES} (Breiman, 2001)\n")
        f.write(f"  min_samples_split: {config.MIN_SAMPLES_SPLIT}\n")
        f.write(f"  min_samples_leaf:  {config.MIN_SAMPLES_LEAF} (Cutler et al., 2007)\n")
        f.write(f"  max_depth:         {config.MAX_DEPTH}\n")
        f.write(f"  class_weight:      {config.CLASS_WEIGHT} (King & Zeng, 2001)\n")
        f.write(f"  random_state:      {config.RANDOM_STATE}\n\n")
        f.write(f"  Validación:        CV espacial {config.N_FOLDS}-fold\n")
        f.write(f"  Tamaño de bloque:  {config.BLOCK_SIZE_DEG}° "
                f"(Roberts et al., 2017)\n\n")

        # Variables
        f.write("-" * 70 + "\n")
        f.write("VARIABLES PREDICTORAS\n")
        f.write("-" * 70 + "\n")
        f.write("  Variables comunes (15):\n")
        for v in config.VARIABLES_COMUNES:
            f.write(f"    • {v}\n")
        f.write("\n  Variables específicas por cultivo (1 cada uno):\n")
        for cult, var in config.VARIABLE_ESTRES_CULTIVO.items():
            f.write(f"    • {cult}: {var}\n")
        f.write(f"\n  Total por modelo: 16 variables\n\n")

        # Resultados por cultivo
        f.write("-" * 70 + "\n")
        f.write("RESULTADOS POR CULTIVO\n")
        f.write("-" * 70 + "\n\n")

        for res in resultados:
            cultivo = res['cultivo']
            m = res['metricas_cv']

            f.write(f"  {cultivo.upper()} ({config.NOMBRES_CIENTIFICOS[cultivo]})\n")
            f.write(f"  {'─'*50}\n")
            f.write(f"  Variable estrés: {config.VARIABLE_ESTRES_CULTIVO[cultivo]}\n")
            f.write(f"  AUC-ROC:      {m['AUC_ROC']:.4f}  "
                    f"{'✓' if m['AUC_ROC'] >= config.UMBRAL_AUC else '✗'} "
                    f"(≥ {config.UMBRAL_AUC})\n")
            f.write(f"  TSS:          {m['TSS']:.4f}  "
                    f"{'✓' if m['TSS'] >= config.UMBRAL_TSS else '✗'} "
                    f"(≥ {config.UMBRAL_TSS})\n")
            f.write(f"  Kappa:        {m['Kappa']:.4f}  "
                    f"{'✓' if m['Kappa'] >= config.UMBRAL_KAPPA else '✗'} "
                    f"(≥ {config.UMBRAL_KAPPA})\n")
            f.write(f"  OOB Error:    {res['oob_error']:.4f}  "
                    f"{'✓' if res['oob_error'] <= config.UMBRAL_OOB_ERROR else '✗'} "
                    f"(≤ {config.UMBRAL_OOB_ERROR})\n")
            f.write(f"  Accuracy:     {m['Accuracy']:.4f}\n")
            f.write(f"  Sensibilidad: {m['Sensitivity']:.4f}\n")
            f.write(f"  Especificidad:{m['Specificity']:.4f}\n")
            f.write(f"  Brier Score:  {m['Brier_Score']:.4f}\n")
            f.write(f"  Modelo:       {res['modelo_path'].name}\n\n")

            f.write(f"  Top 5 variables (permutación):\n")
            for _, row in res['importancia'].head(5).iterrows():
                f.write(f"    {int(row['ranking'])}. {row['variable']}: "
                        f"{row['importancia_permutacion_mean']:.4f} "
                        f"(±{row['importancia_permutacion_std']:.4f})\n")

            if res['shap'] is not None:
                f.write(f"\n  Top 5 variables (SHAP):\n")
                for _, row in res['shap'].head(5).iterrows():
                    f.write(f"    {int(row['ranking_shap'])}. {row['variable']}: "
                            f"|SHAP|={row['mean_abs_shap']:.4f} "
                            f"({row['mean_abs_shap_pct']:.1f}%)\n")
            f.write("\n")

        # Tabla resumen
        f.write("-" * 70 + "\n")
        f.write("TABLA RESUMEN\n")
        f.write("-" * 70 + "\n\n")
        f.write(f"{'Cultivo':<12} {'AUC':>8} {'TSS':>8} {'Kappa':>8} "
                f"{'OOB Err':>8} {'Vars':>6} {'Estado':>10}\n")
        f.write(f"{'─'*12} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*6} {'─'*10}\n")

        todos_aprobados = True
        for res in resultados:
            m = res['metricas_cv']
            aprobado = (
                m['AUC_ROC'] >= config.UMBRAL_AUC and
                m['TSS'] >= config.UMBRAL_TSS and
                m['Kappa'] >= config.UMBRAL_KAPPA and
                res['oob_error'] <= config.UMBRAL_OOB_ERROR
            )
            if not aprobado:
                todos_aprobados = False
            estado = "APROBADO" if aprobado else "REVISIÓN"
            f.write(f"{res['cultivo']:<12} {m['AUC_ROC']:>8.4f} "
                    f"{m['TSS']:>8.4f} {m['Kappa']:>8.4f} "
                    f"{res['oob_error']:>8.4f} {len(res['variables']):>6} "
                    f"{estado:>10}\n")

        # Decisión
        f.write(f"\n{'='*70}\n")
        if todos_aprobados:
            f.write("DECISIÓN: APROBADO\n")
            f.write("Todos los modelos cumplen los criterios del Protocolo.\n")
        else:
            f.write("DECISIÓN: REVISIÓN REQUERIDA\n")
        f.write(f"{'='*70}\n\n")

        # Referencias
        f.write("-" * 70 + "\n")
        f.write("REFERENCIAS\n")
        f.write("-" * 70 + "\n")
        f.write("Allouche, O., et al. (2006). J. Applied Ecology, 43(6), 1223-1232.\n")
        f.write("Breiman, L. (2001). Machine Learning, 45(1), 5-32.\n")
        f.write("Cutler, D.R., et al. (2007). Ecology, 88(11), 2783-2792.\n")
        f.write("King, G., & Zeng, L. (2001). Political Analysis, 9(2), 137-163.\n")
        f.write("Liu, C., et al. (2013). J. Biogeography, 40(4), 778-789.\n")
        f.write("Lundberg, S.M., & Lee, S.I. (2017). NeurIPS 30.\n")
        f.write("Probst, P., & Boulesteix, A.L. (2018). JMLR, 18, 1-18.\n")
        f.write("Roberts, D.R., et al. (2017). Ecography, 40(8), 913-929.\n")
        f.write("Valavi, R., et al. (2019). MEE, 10(2), 225-232.\n")

    return reporte_path


# =============================================================================
# EJECUCIÓN PRINCIPAL
# =============================================================================

def main():
    print("\n" + "╔" + "═"*68 + "╗")
    print("║" + " SCRIPT 06 v1.1.0: RANDOM FOREST + ANÁLISIS SHAP".center(68) + "║")
    print("║" + " Corregido: 16 variables por cultivo (15 comunes + 1 estrés)".center(68) + "║")
    print("║" + f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(68) + "║")
    print("╚" + "═"*68 + "╝")

    config = Config()

    print(f"\n[0] Verificando datos de entrada...")
    print(f"    Directorio: {config.DATASETS_DIR}")

    if not config.DATASETS_DIR.exists():
        print(f"    ✗ No se encontró: {config.DATASETS_DIR}")
        sys.exit(1)

    resultados_todos = []
    t_inicio = datetime.now()

    for cultivo in config.CULTIVOS:
        print(f"\n{'─'*70}")
        print(f"  Buscando dataset: {cultivo}...")

        filepath = buscar_dataset(config, cultivo)
        if filepath is None:
            print(f"  ✗ Dataset no encontrado para {cultivo}. Saltando.")
            continue

        print(f"  ✓ Archivo: {filepath.name}")

        # Obtener las 13 variables específicas para este cultivo
        variables = config.get_variables_cultivo(cultivo)
        print(f"  Variables: {len(variables)} (15 comunes + "
              f"{config.VARIABLE_ESTRES_CULTIVO[cultivo]})")

        try:
            df = cargar_dataset(filepath, variables)
            resultado = entrenar_evaluar_cultivo(df, variables, cultivo, config)
            resultados_todos.append(resultado)
        except Exception as e:
            print(f"  ✗ Error: {e}")
            traceback.print_exc()
            continue

    if not resultados_todos:
        print("\n✗ No se pudieron entrenar modelos.")
        sys.exit(1)

    # GUARDAR CONSOLIDADOS
    print(f"\n{'='*70}")
    print("  GUARDANDO RESULTADOS CONSOLIDADOS")
    print(f"{'='*70}")

    # Métricas
    rows = []
    for res in resultados_todos:
        row = {'cultivo': res['cultivo'], 'n_variables': len(res['variables'])}
        row.update(res['metricas_cv'])
        row['OOB_Error'] = res['oob_error']
        rows.append(row)
    df_met = pd.DataFrame(rows)
    met_path = config.OUTPUT_DIR / "metricas" / f"metricas_rf_{config.TIMESTAMP}.csv"
    df_met.to_csv(met_path, index=False)
    print(f"  ✓ Métricas: {met_path.name}")

    # Por fold
    frows = []
    for res in resultados_todos:
        for mf in res['metricas_folds']:
            row = {'cultivo': res['cultivo']}
            row.update(mf)
            frows.append(row)
    df_folds = pd.DataFrame(frows)
    folds_path = config.OUTPUT_DIR / "metricas" / f"metricas_por_fold_{config.TIMESTAMP}.csv"
    df_folds.to_csv(folds_path, index=False)
    print(f"  ✓ Métricas por fold: {folds_path.name}")

    # Importancias consolidadas
    imp_rows = []
    for res in resultados_todos:
        df_imp = res['importancia'].copy()
        df_imp['cultivo'] = res['cultivo']
        imp_rows.append(df_imp)
    df_imp_all = pd.concat(imp_rows, ignore_index=True)
    imp_path = config.OUTPUT_DIR / "shap" / f"importancia_consolidada_{config.TIMESTAMP}.csv"
    df_imp_all.to_csv(imp_path, index=False)
    print(f"  ✓ Importancias: {imp_path.name}")

    # SHAP consolidado
    shap_rows = []
    for res in resultados_todos:
        if res['shap'] is not None:
            df_s = res['shap'].copy()
            df_s['cultivo'] = res['cultivo']
            shap_rows.append(df_s)
    if shap_rows:
        df_shap_all = pd.concat(shap_rows, ignore_index=True)
        shap_path = config.OUTPUT_DIR / "shap" / f"shap_consolidado_{config.TIMESTAMP}.csv"
        df_shap_all.to_csv(shap_path, index=False)
        print(f"  ✓ SHAP consolidado: {shap_path.name}")

    # Reporte
    reporte_path = generar_reporte(resultados_todos, config)
    print(f"  ✓ Reporte: {reporte_path.name}")

    # RESUMEN FINAL
    t_fin = datetime.now()

    print(f"\n{'═'*70}")
    print(f"  RESUMEN FINAL (v1.1.0 — 16 variables por modelo)")
    print(f"{'═'*70}")

    print(f"\n  {'Cultivo':<12} {'AUC':>8} {'TSS':>8} {'Kappa':>8} "
          f"{'OOB Err':>8} {'Vars':>6} {'Estado':>10}")
    print(f"  {'─'*12} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*6} {'─'*10}")

    for res in resultados_todos:
        m = res['metricas_cv']
        aprobado = (
            m['AUC_ROC'] >= config.UMBRAL_AUC and
            m['TSS'] >= config.UMBRAL_TSS and
            m['Kappa'] >= config.UMBRAL_KAPPA and
            res['oob_error'] <= config.UMBRAL_OOB_ERROR
        )
        estado = "✓ APROBADO" if aprobado else "✗ REVISIÓN"
        print(f"  {res['cultivo']:<12} {m['AUC_ROC']:>8.4f} "
              f"{m['TSS']:>8.4f} {m['Kappa']:>8.4f} "
              f"{res['oob_error']:>8.4f} {len(res['variables']):>6} "
              f"{estado:>10}")

    print(f"\n  Tiempo total: {t_fin - t_inicio}")
    print(f"  Archivos en: {config.OUTPUT_DIR}")

    print(f"\n{'═'*70}")
    print(f"  ✓ SCRIPT 06 v1.1.0 COMPLETADO")
    print(f"  Siguiente paso: Script 07 (Red Bayesiana) o")
    print(f"  Script de proyección RF a escenarios CMIP6")
    print(f"{'═'*70}\n")

    return resultados_todos


if __name__ == "__main__":
    resultados = main()