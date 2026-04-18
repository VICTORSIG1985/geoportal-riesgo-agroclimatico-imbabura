"""
Script publicado como parte del Geoportal Riesgo Agroclimático — Imbabura, Ecuador
Pinto Páez, V. H. (2026). https://doi.org/10.5281/zenodo.19288559
Licencia: CC BY 4.0

NOTA: este archivo fue sanitizado para publicación pública.
- Credenciales (API keys, tokens, service accounts) removidas → <REDACTED_*>
- Rutas absolutas locales sustituidas por <RUTA_LOCAL>
Antes de ejecutar, configure sus propias rutas de entrada/salida y credenciales.

Archivo original: SCRIPT 06B v1.4 PROYECCIÓN DE RANDOM FOREST A ESCENARIOS CMIP6.py
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
SCRIPT 06B v1.4: PROYECCIÓN DE RANDOM FOREST A ESCENARIOS CMIP6
===============================================================================
Autor:   Víctor Hugo Pinto Páez
Versión: 1.4.0 | 2026-02-26

FIX v1.4: Conversión explícita a float64 de todas las variables NetCDF
          (algunas se almacenan como int32, causando error en np.isnan).
          Ruta de parroquias incluida directamente.
===============================================================================
"""

import os, sys, glob, warnings, time
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd

try:
    import xarray as xr
except ImportError:
    sys.exit("ERROR: pip install xarray netcdf4")
try:
    import rasterio
    from rasterio.transform import from_bounds
    from rasterio.crs import CRS
except ImportError:
    sys.exit("ERROR: pip install rasterio")
try:
    import geopandas as gpd
    from shapely.geometry import Point
except ImportError:
    sys.exit("ERROR: pip install geopandas")
try:
    import joblib
except ImportError:
    sys.exit("ERROR: pip install joblib")

warnings.filterwarnings('ignore')


# =============================================================================
# PROGRESO
# =============================================================================

class Progreso:
    def __init__(self, total: int):
        self.total = total
        self.actual = 0
        self.t0 = time.time()
        self.errores_recientes = []

    def avanzar(self, detalle: str = "", ok: bool = True):
        self.actual += 1
        pct = self.actual / self.total * 100
        elapsed = time.time() - self.t0
        eta = elapsed / self.actual * (self.total - self.actual) if self.actual > 0 else 0
        eta_s = str(timedelta(seconds=int(eta)))
        n = 30
        filled = int(n * self.actual / self.total)
        bar = "█" * filled + "░" * (n - filled)
        sym = "✓" if ok else "✗"
        print(f"\r    {bar} {pct:5.1f}% [{self.actual}/{self.total}] "
              f"ETA:{eta_s} {sym} {detalle:35s}", end="", flush=True)

    def fin(self):
        elapsed = time.time() - self.t0
        print(f"\r    {'█'*30} 100.0% [{self.total}/{self.total}] "
              f"Completado en {timedelta(seconds=int(elapsed))}          ")


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

@dataclass
class Config:
    VERSION: str = "1.4.0"
    AUTOR: str = "Víctor Hugo Pinto Páez"
    TIMESTAMP: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))

    BASE_DIR: Path = field(init=False)
    BASE_PREV: Path = field(init=False)
    MODELOS_DIR: Path = field(init=False)
    INDICES_DIR: Path = field(init=False)
    RECORTADOS_DIR: Path = field(init=False)
    OUTPUT_DIR: Path = field(init=False)
    OUTPUT_PARROQUIAL: Path = field(init=False)
    REPORTS_DIR: Path = field(init=False)
    PARROQUIAS_PATH: Path = field(init=False)

    SSPS: List[str] = field(default_factory=lambda: ['ssp126', 'ssp370', 'ssp585'])
    HORIZONTES: Dict[str, Tuple[int, int]] = field(default_factory=lambda: {
        '2021-2040': (2021, 2040),
        '2041-2060': (2041, 2060),
        '2061-2080': (2061, 2080),
    })
    CULTIVOS: List[str] = field(default_factory=lambda: ['papa', 'maiz', 'frejol', 'quinua'])

    def __post_init__(self):
        for c in [Path(r"<RUTA_LOCAL>"), Path(r"<RUTA_LOCAL>")]:
            if (c / "02_DATOS").exists():
                self.BASE_DIR = c
                break
        else:
            self.BASE_DIR = Path(r"<RUTA_LOCAL>")

        for c in [Path(r"<RUTA_LOCAL>"),
                   Path(r"<RUTA_LOCAL>"),
                   self.BASE_DIR]:
            if (c / "04_RESULTADOS").exists():
                self.BASE_PREV = c
                break
        else:
            self.BASE_PREV = self.BASE_DIR

        self.INDICES_DIR = self.BASE_DIR / "02_DATOS" / "climaticos" / "indices" / "agregados"
        self.RECORTADOS_DIR = self.BASE_DIR / "02_DATOS" / "climaticos" / "BASD_CMIP6_PE" / "recortados"
        self.MODELOS_DIR = self._encontrar_modelos()
        self.OUTPUT_DIR = self.BASE_PREV / "04_RESULTADOS" / "fase4_modelamiento" / "random_forest" / "proyecciones"
        self.OUTPUT_PARROQUIAL = self.OUTPUT_DIR / "parroquial"
        self.REPORTS_DIR = self.BASE_PREV / "05_DOCUMENTACION" / "reportes_auditoria"
        if not self.REPORTS_DIR.parent.exists():
            self.REPORTS_DIR = self.BASE_DIR / "05_DOCUMENTACION" / "reportes_auditoria"

        # Parroquias: ruta directa
        for p in [
            self.BASE_DIR / "Imbabura_Parroquia.gpkg",
            self.BASE_DIR / "02_DATOS" / "limites" / "Imbabura_Parroquia.gpkg",
            self.BASE_DIR / "02_DATOS" / "limites" / "gadm41_ECU.gpkg",
        ]:
            if p.exists():
                self.PARROQUIAS_PATH = p
                break
        else:
            self.PARROQUIAS_PATH = self.BASE_DIR / "Imbabura_Parroquia.gpkg"

    def _encontrar_modelos(self) -> Path:
        for c in [
            self.BASE_PREV / "04_RESULTADOS" / "fase4_modelamiento" / "random_forest" / "modelos",
            self.BASE_PREV / "04_RESULTADOS" / "fase4_modelamiento" / "random_forest",
            self.BASE_DIR / "04_RESULTADOS" / "fase4_modelamiento" / "random_forest" / "modelos",
            self.BASE_DIR / "04_RESULTADOS" / "fase4_modelamiento" / "random_forest",
        ]:
            if c.exists() and list(c.glob("rf_*.joblib")):
                return c
        for base in [self.BASE_PREV, self.BASE_DIR]:
            for jl in base.rglob("rf_papa_*.joblib"):
                return jl.parent
        return self.BASE_PREV / "04_RESULTADOS" / "fase4_modelamiento" / "random_forest"

    def var_estres(self, cultivo: str) -> str:
        return f"dias_estres_{cultivo}_anual"


# =============================================================================
# FUNCIONES DE DATOS
# =============================================================================

def detectar_gcms(config: Config) -> List[str]:
    gcms = set()
    for ssp in config.SSPS:
        d = config.INDICES_DIR / ssp
        if d.exists():
            for sub in d.iterdir():
                if sub.is_dir():
                    gcms.add(sub.name)
    return sorted(gcms)


def encontrar_ncs(directorio: Path, año_ini: int, año_fin: int) -> List[Path]:
    if not directorio.exists():
        return []
    result = []
    for nc in sorted(directorio.glob("*.nc")):
        nums = [int(p) for p in nc.stem.split('_') if p.isdigit() and len(p) == 4]
        if len(nums) >= 2 and nums[-1] >= año_ini and nums[-2] <= año_fin:
            result.append(nc)
    return result


def encontrar_ncs_var(directorio: Path, variable: str,
                       año_ini: int, año_fin: int) -> List[Path]:
    if not directorio.exists():
        return []
    result = []
    for nc in sorted(directorio.glob(f"*_{variable}_*.nc")):
        nums = [int(p) for p in nc.stem.split('_') if p.isdigit() and len(p) == 4]
        if len(nums) >= 2 and nums[-1] >= año_ini and nums[-2] <= año_fin:
            result.append(nc)
    return result


def cargar_indices(config: Config, ssp: str, gcm: str,
                   horizonte: str) -> Optional[xr.Dataset]:
    """Carga 13 variables del NetCDF agregado. Convierte todo a float64."""
    y1, y2 = config.HORIZONTES[horizonte]
    archivos = encontrar_ncs(config.INDICES_DIR / ssp / gcm, y1, y2)
    if not archivos:
        return None

    dss = []
    for f in archivos:
        try:
            ds = xr.open_dataset(f)
            # CONVERSIÓN A FLOAT64 para evitar error isnan con int32
            for var in ds.data_vars:
                if ds[var].dtype != np.float64:
                    ds[var] = ds[var].astype(np.float64)
            dss.append(ds)
        except Exception:
            pass

    if not dss:
        return None
    if len(dss) == 1:
        return dss[0]

    try:
        return xr.concat(dss, dim='_d').mean(dim='_d')
    except Exception:
        r = dss[0].copy(deep=True)
        for v in r.data_vars:
            arrs = [d[v].values.astype(np.float64) for d in dss if v in d]
            if len(arrs) > 1:
                r[v].values = np.nanmean(np.stack(arrs), axis=0)
        return r


def calcular_termicas(config: Config, ssp: str, gcm: str,
                       horizonte: str,
                       lats_target: np.ndarray,
                       lons_target: np.ndarray) -> Dict[str, np.ndarray]:
    """
    Calcula 3 térmicas desde datos diarios tasmax/tasmin.
    Grilla ~170 píxeles → toma segundos.
    """
    y1, y2 = config.HORIZONTES[horizonte]
    gcm_dir = config.RECORTADOS_DIR / ssp / gcm

    tmax_files = encontrar_ncs_var(gcm_dir, 'tasmax', y1, y2)
    tmin_files = encontrar_ncs_var(gcm_dir, 'tasmin', y1, y2)

    if not tmax_files or not tmin_files:
        return {}

    try:
        ds_tmax = xr.open_mfdataset(tmax_files, combine='by_coords')
        ds_tmin = xr.open_mfdataset(tmin_files, combine='by_coords')

        if 'time' in ds_tmax.dims:
            ds_tmax = ds_tmax.sel(time=slice(f"{y1}-01-01", f"{y2}-12-31"))
            ds_tmin = ds_tmin.sel(time=slice(f"{y1}-01-01", f"{y2}-12-31"))

        tmax_var = list(ds_tmax.data_vars)[0]
        tmin_var = list(ds_tmin.data_vars)[0]

        tmax = ds_tmax[tmax_var].astype(np.float64)
        tmin = ds_tmin[tmin_var].astype(np.float64)

        tmax_mean = tmax.mean(dim='time').values
        tmin_mean = tmin.mean(dim='time').values
        rango_mean = (tmax - tmin).mean(dim='time').values

        lat_d = 'lat' if 'lat' in ds_tmax.dims else 'latitude'
        lon_d = 'lon' if 'lon' in ds_tmax.dims else 'longitude'
        lats_d = ds_tmax[lat_d].values
        lons_d = ds_tmax[lon_d].values

        ds_tmax.close()
        ds_tmin.close()

        # Interpolar si grillas difieren
        if not (np.array_equal(lats_d, lats_target) and np.array_equal(lons_d, lons_target)):
            tmax_mean = _interpolar(tmax_mean, lats_d, lons_d, lats_target, lons_target)
            tmin_mean = _interpolar(tmin_mean, lats_d, lons_d, lats_target, lons_target)
            rango_mean = _interpolar(rango_mean, lats_d, lons_d, lats_target, lons_target)

        return {
            'tmax_media_anual': tmax_mean.astype(np.float64),
            'tmin_media_anual': tmin_mean.astype(np.float64),
            'rango_termico_diurno': rango_mean.astype(np.float64),
        }

    except Exception as e:
        return {}


def _interpolar(data, lats_src, lons_src, lats_dst, lons_dst):
    """Nearest-neighbor entre grillas."""
    try:
        from scipy.interpolate import RegularGridInterpolator
        if lats_src[0] > lats_src[-1]:
            lats_src = lats_src[::-1]
            data = data[::-1, :]
        interp = RegularGridInterpolator(
            (lats_src, lons_src), data.astype(np.float64),
            method='nearest', bounds_error=False, fill_value=np.nan
        )
        lon_g, lat_g = np.meshgrid(lons_dst, lats_dst)
        return interp(np.column_stack([lat_g.ravel(), lon_g.ravel()])).reshape(len(lats_dst), len(lons_dst))
    except Exception:
        return data


# =============================================================================
# PREDICCIÓN
# =============================================================================

def construir_dataframe(ds: xr.Dataset, termicas: Dict[str, np.ndarray],
                         modelo, cultivo: str, config: Config):
    """
    Construye DataFrame con 16 variables (float64):
    13 del NetCDF + 3 térmicas desde daily.
    """
    lat_n = 'lat' if 'lat' in ds.dims else 'latitude'
    lon_n = 'lon' if 'lon' in ds.dims else 'longitude'
    lats = ds[lat_n].values
    lons = ds[lon_n].values
    lon_g, lat_g = np.meshgrid(lons, lats)

    df = pd.DataFrame({'lat': lat_g.ravel(), 'lon': lon_g.ravel()})

    # Nombres del modelo
    if hasattr(modelo, 'feature_names_in_'):
        model_vars = list(modelo.feature_names_in_)
    else:
        model_vars = [
            'ET0_media_diaria', 'ET0_anual_mm', 'deficit_media_diaria',
            'deficit_anual_mm', 'pct_dias_deficit', 'dias_secos_anual',
            'cdd_max', 'eventos_sequia_7d', 'eventos_sequia_15d',
            'dias_helada_anual', 'pr_anual_mm', 'indice_aridez',
            'tmax_media_anual', 'tmin_media_anual', 'rango_termico_diurno',
            config.var_estres(cultivo),
        ]

    nc_vars = list(ds.data_vars)
    nc_lower = {v.lower(): v for v in nc_vars}

    for mv in model_vars:
        # Térmica calculada?
        if mv in termicas:
            df[mv] = termicas[mv].ravel().astype(np.float64)
            continue

        # Buscar en NetCDF
        nc_match = None
        if mv in nc_vars:
            nc_match = mv
        elif mv.lower() in nc_lower:
            nc_match = nc_lower[mv.lower()]
        else:
            for nv in nc_vars:
                if mv.lower() in nv.lower() or nv.lower() in mv.lower():
                    nc_match = nv
                    break

        if nc_match:
            vals = ds[nc_match].values.astype(np.float64)
            df[mv] = vals.ravel() if vals.ndim == 2 else np.nanmean(vals, axis=0).ravel()
        else:
            df[mv] = np.nan

    # FORZAR float64 en TODAS las columnas de predictores
    for mv in model_vars:
        if mv in df.columns:
            df[mv] = pd.to_numeric(df[mv], errors='coerce').astype(np.float64)

    df_valid = df.dropna(subset=model_vars, how='all').copy()
    return df_valid, lats, lons, model_vars


def predecir(modelo, df: pd.DataFrame, model_vars: List[str]) -> np.ndarray:
    X = df[model_vars].values.astype(np.float64)
    for j in range(X.shape[1]):
        col = X[:, j]
        m = np.isnan(col)
        if m.any():
            med = np.nanmedian(col)
            col[m] = med if not np.isnan(med) else 0.0
    return modelo.predict_proba(X)[:, 1]


def raster_desde_df(proba, df, lats, lons):
    grid = np.full((len(lats), len(lons)), np.nan, dtype=np.float32)
    lat_idx = {float(lat): i for i, lat in enumerate(lats)}
    lon_idx = {float(lon): j for j, lon in enumerate(lons)}
    for k, (_, row) in enumerate(df.iterrows()):
        i = lat_idx.get(float(row['lat']))
        j = lon_idx.get(float(row['lon']))
        if i is not None and j is not None:
            grid[i, j] = proba[k]
    return grid


def guardar_tiff(grid, lats, lons, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    rl = abs(float(lats[1] - lats[0])) if len(lats) > 1 else 0.1
    ro = abs(float(lons[1] - lons[0])) if len(lons) > 1 else 0.1
    transform = from_bounds(
        float(lons.min())-ro/2, float(lats.min())-rl/2,
        float(lons.max())+ro/2, float(lats.max())+rl/2,
        len(lons), len(lats)
    )
    g = grid.astype(np.float32).copy()
    g[np.isnan(g)] = -9999.0
    with rasterio.open(str(path), 'w', driver='GTiff',
                       height=g.shape[0], width=g.shape[1], count=1,
                       dtype='float32', crs=CRS.from_epsg(4326),
                       transform=transform, nodata=-9999.0, compress='lzw') as dst:
        dst.write(g, 1)


# =============================================================================
# PARROQUIAS
# =============================================================================

def cargar_parroquias(config: Config) -> Optional[gpd.GeoDataFrame]:
    p = config.PARROQUIAS_PATH
    if not p.exists():
        print(f"  ⚠ No existe: {p}")
        return None

    try:
        # Intentar como GeoPackage con layers
        layers = gpd.list_layers(p) if hasattr(gpd, 'list_layers') else None
        if layers is not None and len(layers) > 0:
            print(f"  Capas en {p.name}: {list(layers['name'])}")

        gdf = gpd.read_file(p)
        print(f"  ✓ Parroquias: {p.name} ({len(gdf)} features)")
        print(f"    Columnas: {list(gdf.columns)[:8]}")

        # Filtrar Imbabura si es dataset nacional
        if len(gdf) > 50:
            for col in gdf.columns:
                if gdf[col].dtype == 'object':
                    mask = gdf[col].str.contains('Imbabura', case=False, na=False)
                    if mask.any():
                        gdf = gdf[mask]
                        print(f"    Filtrado a Imbabura: {len(gdf)} features")
                        break

        return gdf

    except Exception as e:
        print(f"  ⚠ Error leyendo parroquias: {e}")
        return None


def zonal_stats(grid, lats, lons, parroquias):
    lon_g, lat_g = np.meshgrid(lons, lats)
    m = ~np.isnan(grid)
    if not m.any():
        return pd.DataFrame()

    pts = gpd.GeoDataFrame(
        {'aptitud': grid[m].astype(float)},
        geometry=[Point(float(x), float(y)) for x, y in zip(lon_g[m], lat_g[m])],
        crs="EPSG:4326"
    )
    if parroquias.crs and parroquias.crs != pts.crs:
        parroquias = parroquias.to_crs("EPSG:4326")

    joined = gpd.sjoin(pts, parroquias, how='inner', predicate='within')

    # Detectar columna de nombre
    for c in ['NAME_3', 'ADM3_ES', 'DPA_PARROQ', 'parroquia', 'PARROQUIA',
              'DPA_DESPAR', 'NOM_PARROQ', 'nombre']:
        if c in joined.columns:
            nc = c
            break
    else:
        for c in parroquias.columns:
            if parroquias[c].dtype == 'object' and c not in ['geometry']:
                nc = c
                break
        else:
            return pd.DataFrame()

    return joined.groupby(nc)['aptitud'].agg(
        aptitud_media='mean', aptitud_mediana='median', aptitud_sd='std',
        aptitud_min='min', aptitud_max='max', n_pixeles='count'
    ).reset_index().rename(columns={nc: 'parroquia'})


# =============================================================================
# MAIN
# =============================================================================

def main():
    config = Config()
    t0 = datetime.now()

    print("╔" + "═"*68 + "╗")
    print("║  SCRIPT 06B v1.4: PROYECCIÓN RF A ESCENARIOS CMIP6" + " "*17 + "║")
    print("║  13 NetCDF + 3 térmicas (daily) = 16 vars | float64 fix      ║")
    print("║  " + t0.strftime('%Y-%m-%d %H:%M:%S') + " "*45 + "║")
    print("╚" + "═"*68 + "╝")

    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    config.OUTPUT_PARROQUIAL.mkdir(parents=True, exist_ok=True)
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # ═══════════════════════════════════════════════════════════════════
    print("\n[1/6] VERIFICACIÓN DE ENTRADAS")
    print("─"*60)
    print(f"  MODELOS:     {config.MODELOS_DIR}")
    print(f"  INDICES:     {config.INDICES_DIR}")
    print(f"  RECORTADOS:  {config.RECORTADOS_DIR}")
    print(f"  PARROQUIAS:  {config.PARROQUIAS_PATH}")
    print(f"  OUTPUT:      {config.OUTPUT_DIR}")

    # Modelos
    modelos = {}
    for cultivo in config.CULTIVOS:
        archivos = sorted(glob.glob(str(config.MODELOS_DIR / f"rf_{cultivo}_*.joblib")))
        if archivos:
            modelos[cultivo] = joblib.load(archivos[-1])
            feat = modelos[cultivo].feature_names_in_ if hasattr(modelos[cultivo], 'feature_names_in_') else None
            n = len(feat) if feat is not None else '?'
            print(f"  ✓ {cultivo:8s}: {Path(archivos[-1]).name} ({n} vars)")
            if feat is not None and cultivo == config.CULTIVOS[0]:
                print(f"    Variables del modelo:")
                for f in feat:
                    print(f"      • {f}")
        else:
            print(f"  ✗ {cultivo}: NO ENCONTRADO")

    if not modelos:
        print("\n  ❌ Sin modelos. Abortando.")
        return None, None

    # GCMs
    gcms = detectar_gcms(config)
    print(f"\n  GCMs: {len(gcms)} → {', '.join(gcms)}")
    if not gcms:
        print("  ❌ Sin GCMs. Abortando.")
        return None, None

    # Test rápido de un archivo
    ds_test = cargar_indices(config, config.SSPS[0], gcms[0],
                              list(config.HORIZONTES.keys())[0])
    if ds_test:
        print(f"\n  NetCDF test ({len(ds_test.data_vars)} vars, todas float64):")
        for v in sorted(ds_test.data_vars):
            print(f"    • {v}: {ds_test[v].dtype}, shape={ds_test[v].shape}")
        ds_test.close()

    # Parroquias
    print()
    parroquias = cargar_parroquias(config)

    n_total = len(config.SSPS) * len(gcms) * len(config.HORIZONTES) * len(modelos)
    print(f"\n  📊 Proyecciones: {n_total}")
    print(f"     {len(config.SSPS)} SSP × {len(gcms)} GCM × "
          f"{len(config.HORIZONTES)} horiz × {len(modelos)} cultivos")

    # ═══════════════════════════════════════════════════════════════════
    print(f"\n[2/6] PROYECCIÓN ({n_total} combinaciones)")
    print("─"*60)

    resultado_ens = {}
    resultado_parr = []
    errores = []
    procesados = 0
    prog = Progreso(n_total)

    for ssp in config.SSPS:
        for horizonte in config.HORIZONTES:
            grids_cultivo = {c: [] for c in modelos}
            lats_ref, lons_ref = None, None

            for gcm in gcms:
                # A: Cargar 13 vars (float64)
                ds = cargar_indices(config, ssp, gcm, horizonte)
                if ds is None:
                    for c in modelos:
                        prog.avanzar(f"⚠ sin datos {gcm[:15]}", ok=False)
                    errores.append(f"Sin índices: {ssp}/{gcm}/{horizonte}")
                    continue

                lat_n = 'lat' if 'lat' in ds.dims else 'latitude'
                lon_n = 'lon' if 'lon' in ds.dims else 'longitude'
                lats = ds[lat_n].values
                lons = ds[lon_n].values
                if lats_ref is None:
                    lats_ref, lons_ref = lats, lons

                # B: Calcular 3 térmicas
                termicas = calcular_termicas(config, ssp, gcm, horizonte, lats, lons)

                # C: Aplicar RF por cultivo
                for cultivo, modelo in modelos.items():
                    try:
                        df, _, _, mvars = construir_dataframe(
                            ds, termicas, modelo, cultivo, config
                        )
                        if len(df) == 0:
                            errores.append(f"Vacío: {cultivo}/{ssp}/{gcm}/{horizonte}")
                            prog.avanzar(f"⚠ vacío {cultivo}/{gcm[:10]}", ok=False)
                            continue

                        proba = predecir(modelo, df, mvars)
                        grid = raster_desde_df(proba, df, lats, lons)

                        p = (config.OUTPUT_DIR / "por_gcm" / cultivo / ssp /
                             horizonte / f"aptitud_{cultivo}_{gcm}.tif")
                        guardar_tiff(grid, lats, lons, p)

                        grids_cultivo[cultivo].append(grid)
                        procesados += 1
                        prog.avanzar(f"{cultivo}/{ssp}/{gcm[:12]}", ok=True)

                    except Exception as e:
                        err_msg = str(e)[:80]
                        errores.append(f"{cultivo}/{ssp}/{gcm}/{horizonte}: {err_msg}")
                        prog.avanzar(f"✗ {cultivo}/{gcm[:10]}", ok=False)

                ds.close()

            # Ensemble
            for cultivo in modelos:
                grids = grids_cultivo[cultivo]
                if len(grids) < 2:
                    continue

                stack = np.stack(grids, axis=0).astype(np.float64)
                ens_mean = np.nanmean(stack, axis=0).astype(np.float32)
                ens_sd = np.nanstd(stack, axis=0).astype(np.float32)

                bp = config.OUTPUT_DIR / "ensemble" / cultivo / ssp / horizonte
                guardar_tiff(ens_mean, lats_ref, lons_ref, bp / f"aptitud_{cultivo}_mean.tif")
                guardar_tiff(ens_sd, lats_ref, lons_ref, bp / f"aptitud_{cultivo}_sd.tif")

                mv = float(np.nanmean(ens_mean))
                sv = float(np.nanmean(ens_sd))
                resultado_ens[(cultivo, ssp, horizonte)] = {
                    'n_gcms': len(grids), 'aptitud_media': mv, 'incertidumbre_sd': sv
                }

                if parroquias is not None and lats_ref is not None:
                    st = zonal_stats(ens_mean, lats_ref, lons_ref, parroquias)
                    if not st.empty:
                        st['cultivo'] = cultivo
                        st['ssp'] = ssp
                        st['horizonte'] = horizonte
                        st['n_gcms'] = len(grids)
                        resultado_parr.append(st)

    prog.fin()

    # ═══════════════════════════════════════════════════════════════════
    print(f"\n[3/6] AGREGACIÓN PARROQUIAL")
    print("─"*60)

    df_parr = None
    if resultado_parr:
        df_parr = pd.concat(resultado_parr, ignore_index=True)
        csv = config.OUTPUT_PARROQUIAL / f"aptitud_parroquial_{config.TIMESTAMP}.csv"
        df_parr.to_csv(csv, index=False, float_format='%.4f')
        print(f"  ✓ {csv.name}")
        print(f"    {len(df_parr)} filas, {df_parr['parroquia'].nunique()} parroquias")
    else:
        print("  ⚠ Sin resultados parroquiales")

    # ═══════════════════════════════════════════════════════════════════
    print(f"\n[4/6] RESUMEN")
    print("─"*60)

    rows = []
    for (c, s, h), v in sorted(resultado_ens.items()):
        rows.append({'cultivo': c, 'ssp': s, 'horizonte': h,
                     'n_gcms': v['n_gcms'], 'aptitud_media': v['aptitud_media'],
                     'incertidumbre_sd': v['incertidumbre_sd']})

    df_res = None
    if rows:
        df_res = pd.DataFrame(rows)
        rp = config.OUTPUT_DIR / f"resumen_proyecciones_{config.TIMESTAMP}.csv"
        df_res.to_csv(rp, index=False, float_format='%.4f')
        print(f"  ✓ {rp.name}\n")

        print(f"  {'Cultivo':10s} {'SSP':8s} {'Horizonte':12s} {'Media':>8s} {'±SD':>8s} {'GCMs':>5s}")
        print(f"  {'─'*10} {'─'*8} {'─'*12} {'─'*8} {'─'*8} {'─'*5}")
        for r in rows:
            print(f"  {r['cultivo']:10s} {r['ssp']:8s} {r['horizonte']:12s} "
                  f"{r['aptitud_media']:8.4f} {r['incertidumbre_sd']:8.4f} {r['n_gcms']:5d}")
    else:
        print("  ⚠ Sin resultados de ensemble")

    # ═══════════════════════════════════════════════════════════════════
    print(f"\n[5/6] REPORTE DE AUDITORÍA")
    print("─"*60)

    rep = config.REPORTS_DIR / f"REPORTE_SCRIPT_06B_{config.TIMESTAMP}.txt"
    try:
        with open(rep, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("REPORTE - SCRIPT 06B v1.4\n")
            f.write("PROYECCIÓN RF A ESCENARIOS CMIP6\n")
            f.write("="*70 + "\n\n")
            f.write(f"Fecha: {datetime.now()}\nAutor: {config.AUTOR}\n\n")
            f.write("MÉTODO:\n")
            f.write("  13 vars del NetCDF agregado (Scripts 03A-03F)\n")
            f.write("  + 3 vars térmicas de datos diarios (réplica Script 05C):\n")
            f.write("    tmax_media_anual = mean(tasmax)\n")
            f.write("    tmin_media_anual = mean(tasmin)\n")
            f.write("    rango_termico_diurno = mean(tasmax - tasmin)\n")
            f.write("  FIX: Conversión float64 para todas las variables NetCDF\n\n")
            f.write(f"SSPs: {config.SSPS}\nGCMs: {gcms}\n")
            f.write(f"Horizontes: {list(config.HORIZONTES.keys())}\n")
            f.write(f"Cultivos: {list(modelos.keys())}\n\n")
            f.write(f"Proyecciones OK: {procesados}/{n_total}\n")
            f.write(f"Ensembles: {len(resultado_ens)}\n")
            f.write(f"Errores: {len(errores)}\n\n")
            if errores:
                f.write("ERRORES:\n")
                for e in errores[:50]:
                    f.write(f"  - {e}\n")
                f.write("\n")
            if rows:
                f.write("RESUMEN:\n")
                f.write(f"{'Cultivo':12s} {'SSP':8s} {'Horiz':12s} {'Media':>8s} {'SD':>8s} {'N':>4s}\n")
                f.write("-"*50 + "\n")
                for r in rows:
                    f.write(f"{r['cultivo']:12s} {r['ssp']:8s} {r['horizonte']:12s} "
                            f"{r['aptitud_media']:8.4f} {r['incertidumbre_sd']:8.4f} {r['n_gcms']:4d}\n")
            f.write("\n" + "="*70 + "\n")
            f.write("REFERENCIAS:\n")
            f.write("  Knutti et al. (2010). J. Climate, 23(10), 2739-2758.\n")
            f.write("  Hargreaves & Samani (1985). Appl. Eng. Agric., 1(2), 96-99.\n")
            f.write("  Allen et al. (1998). FAO-56.\n")
            f.write("  Fernandez-Palomino et al. (2024). Sci. Data, 11, 34.\n")
            f.write("  IPCC (2022). AR6 WG2.\n")
            f.write("="*70 + "\n")
        print(f"  ✓ {rep.name}")
    except Exception as e:
        print(f"  ⚠ {e}")

    # ═══════════════════════════════════════════════════════════════════
    t_total = datetime.now() - t0
    print()
    print("╔" + "═"*68 + "╗")
    print("║  ✓ SCRIPT 06B v1.4 COMPLETADO" + " "*38 + "║")
    print("╚" + "═"*68 + "╝")
    print(f"\n  ⏱  Tiempo: {t_total}")
    print(f"  ✓  OK:      {procesados}/{n_total}")
    print(f"  ❌ Errores: {len(errores)}")
    if resultado_ens:
        print(f"  📊 Ensembles: {len(resultado_ens)}")
    if df_parr is not None:
        print(f"  🗺  Parroquias: {df_parr['parroquia'].nunique()}")
    print(f"\n  📁 {config.OUTPUT_DIR}")
    print(f"\n  🔜 Siguiente: Script 07 (Red Bayesiana)")
    print("═"*70)

    return resultado_ens, df_res


if __name__ == "__main__":
    resultados, resumen = main()