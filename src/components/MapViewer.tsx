"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { SERVICES, PRIORITY_COLORS } from "@/data/config";
import { Layers, Filter, X, FileText, Download } from "lucide-react";

type Cultivo = "papa" | "maiz" | "frejol" | "quinua";
type SSP = "ssp126" | "ssp370" | "ssp585";
type Horizonte = "2021-2040" | "2041-2060" | "2061-2080";

async function fetchGeojson(url: string, where = "1=1") {
  const params = new URLSearchParams({
    where,
    outFields: "*",
    f: "geojson",
    outSR: "4326",
  });
  const res = await fetch(`${url}/query?${params}`);
  if (!res.ok) throw new Error(`FS error ${res.status}`);
  return res.json();
}

function irColor(v: number): string {
  if (v == null || isNaN(v)) return "#CCCCCC";
  if (v >= 0.65) return "#B2182B";
  if (v >= 0.55) return "#EF8A62";
  if (v >= 0.45) return "#FDDBC7";
  if (v >= 0.40) return "#67A9CF";
  return "#2166AC";
}

export default function MapViewer() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [selected, setSelected] = useState<any | null>(null);
  const [capas, setCapas] = useState({
    prioridad: true,
    riesgoLong: false,
    base: true,
  });
  const [cultivo, setCultivo] = useState<Cultivo>("papa");
  const [ssp, setSsp] = useState<SSP>("ssp585");
  const [horiz, setHoriz] = useState<Horizonte>("2061-2080");
  const [loaded, setLoaded] = useState(false);
  const [panelFiltros, setPanelFiltros] = useState(true);

  useEffect(() => {
    if (!containerRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
      center: [-78.15, 0.35],
      zoom: 9,
      attributionControl: false,
      maxZoom: 14,
      minZoom: 6,
    });
    map.addControl(new maplibregl.NavigationControl(), "top-left");
    map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    map.addControl(new maplibregl.AttributionControl({
      customAttribution: "Víctor Hugo Pinto Páez · USGP 2026 · DOI 10.5281/zenodo.19288559 · © CartoDB · © OpenStreetMap",
    }), "bottom-right");

    mapRef.current = map;

    map.on("load", async () => {
      try {
        const [prior, base] = await Promise.all([
          fetchGeojson(SERVICES.flPrioridad.url),
          fetchGeojson(SERVICES.flParroquias.url),
        ]);

        map.addSource("base", { type: "geojson", data: base });
        map.addLayer({
          id: "base-line", type: "line", source: "base",
          paint: { "line-color": "#555", "line-width": 0.7, "line-opacity": 0.8 }
        });

        map.addSource("prior", { type: "geojson", data: prior });
        map.addLayer({
          id: "prior-fill", type: "fill", source: "prior",
          paint: {
            "fill-color": [
              "match", ["get", "prioridad_final"],
              "Muy Alta", PRIORITY_COLORS["Muy Alta"].hex,
              "Alta", PRIORITY_COLORS["Alta"].hex,
              "Alerta", PRIORITY_COLORS["Alerta"].hex,
              "Monitoreo", PRIORITY_COLORS["Monitoreo"].hex,
              "Favorable", PRIORITY_COLORS["Favorable"].hex,
              "#CCCCCC"
            ],
            "fill-opacity": 0.72
          }
        });
        map.addLayer({
          id: "prior-outline", type: "line", source: "prior",
          paint: { "line-color": "#222", "line-width": 0.5, "line-opacity": 0.8 }
        });
        map.addLayer({
          id: "prior-highlight", type: "line", source: "prior",
          paint: { "line-color": "#0A3558", "line-width": 3 },
          filter: ["==", ["get", "cod_parroq"], "___none___"]
        });

        // Riesgo Long — empieza oculto
        const riesgo = await fetchGeojson(SERVICES.flRiesgoLong.url, `cultivo='${cultivo}' AND ssp='${ssp}' AND horizonte='${horiz}'`);
        map.addSource("riesgo", { type: "geojson", data: riesgo });
        map.addLayer({
          id: "riesgo-fill", type: "fill", source: "riesgo",
          layout: { visibility: "none" },
          paint: {
            "fill-color": [
              "step", ["coalesce", ["get", "ir"], -1],
              "#CCCCCC",
              0.0, "#2166AC",
              0.40, "#67A9CF",
              0.45, "#FDDBC7",
              0.55, "#EF8A62",
              0.65, "#B2182B",
            ],
            "fill-opacity": 0.78
          }
        });
        map.addLayer({
          id: "riesgo-outline", type: "line", source: "riesgo",
          layout: { visibility: "none" },
          paint: { "line-color": "#222", "line-width": 0.5, "line-opacity": 0.8 }
        });

        // Zoom al extent
        try {
          let minx = 180, miny = 90, maxx = -180, maxy = -90;
          for (const f of base.features as any[]) {
            const coords = (f.geometry.coordinates as any[]).flat(3);
            for (let i = 0; i < coords.length; i += 2) {
              const x = coords[i], y = coords[i+1];
              if (x < minx) minx = x; if (x > maxx) maxx = x;
              if (y < miny) miny = y; if (y > maxy) maxy = y;
            }
          }
          map.fitBounds([[minx, miny], [maxx, maxy]], { padding: 40, duration: 0 });
        } catch {}

        // Click
        map.on("click", (e) => {
          const feats = map.queryRenderedFeatures(e.point, { layers: ["prior-fill", "riesgo-fill"] });
          if (!feats.length) { setSelected(null); map.setFilter("prior-highlight", ["==", ["get","cod_parroq"], "___none___"]); return; }
          const p = feats[0].properties as any;
          setSelected(p);
          map.setFilter("prior-highlight", ["==", ["get", "cod_parroq"], p?.cod_parroq || ""]);
        });
        map.on("mouseenter", "prior-fill", () => map.getCanvas().style.cursor = "pointer");
        map.on("mouseleave", "prior-fill", () => map.getCanvas().style.cursor = "");
        map.on("mouseenter", "riesgo-fill", () => map.getCanvas().style.cursor = "pointer");
        map.on("mouseleave", "riesgo-fill", () => map.getCanvas().style.cursor = "");

        // Disable interactions to protect from modification (panning/zoom still allowed via controls only if we leave them)
        // Users can still pan/zoom (read-only). No editing or adding features.
        setLoaded(true);
      } catch (err) {
        console.error("map load err", err);
      }
    });

    return () => { map.remove(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Toggle capas
  useEffect(() => {
    const m = mapRef.current; if (!m || !loaded) return;
    const vis = (id: string, show: boolean) => {
      if (m.getLayer(id)) m.setLayoutProperty(id, "visibility", show ? "visible" : "none");
    };
    vis("prior-fill", capas.prioridad);
    vis("prior-outline", capas.prioridad);
    vis("base-line", capas.base);
    vis("riesgo-fill", capas.riesgoLong);
    vis("riesgo-outline", capas.riesgoLong);
  }, [capas, loaded]);

  // Update Riesgo Long on filter change
  const refetchRiesgo = useCallback(async () => {
    const m = mapRef.current; if (!m || !loaded) return;
    try {
      const data = await fetchGeojson(SERVICES.flRiesgoLong.url, `cultivo='${cultivo}' AND ssp='${ssp}' AND horizonte='${horiz}'`);
      const src = m.getSource("riesgo") as maplibregl.GeoJSONSource | undefined;
      if (src) src.setData(data);
    } catch (err) {
      console.error("riesgo refetch err", err);
    }
  }, [cultivo, ssp, horiz, loaded]);

  useEffect(() => { refetchRiesgo(); }, [refetchRiesgo]);

  const cultLabel: Record<Cultivo, string> = { papa: "Papa", maiz: "Maíz", frejol: "Fréjol", quinua: "Quinua" };
  const sspLabel: Record<SSP, string> = { ssp126: "SSP1-2.6", ssp370: "SSP3-7.0", ssp585: "SSP5-8.5" };

  return (
    <div className="flex h-[calc(100vh-64px)]" onContextMenu={(e) => e.preventDefault()}>
      <aside className="w-96 bg-white border-r border-[var(--border)] overflow-y-auto flex-shrink-0">
        <div className="p-5">
          <h2 className="text-xl mb-2 flex items-center gap-2"><Layers size={20}/> Visor Cartográfico</h2>
          <div className="text-xs text-[var(--text-muted)] mb-4 bg-amber-50 border border-amber-200 rounded p-2">
            🔒 Visor en modo <strong>solo lectura</strong>. Haga clic en una parroquia para ver detalle y descargar la ficha PDF.
          </div>

          <div className="mb-4">
            <h3 className="text-xs font-bold uppercase tracking-wider mb-2 text-[var(--text-muted)]">Capas</h3>
            <label className="flex items-center gap-2 text-sm py-1 cursor-pointer">
              <input type="checkbox" checked={capas.prioridad} onChange={e => setCapas(v => ({ ...v, prioridad: e.target.checked }))}/>
              <span>Priorización Final (42)</span>
              <span className="text-xs text-[var(--text-muted)] ml-auto">por IR medio</span>
            </label>
            <label className="flex items-center gap-2 text-sm py-1 cursor-pointer">
              <input type="checkbox" checked={capas.riesgoLong} onChange={e => setCapas(v => ({ ...v, riesgoLong: e.target.checked }))}/>
              <span>Riesgo por Escenario</span>
              <span className="text-xs text-[var(--text-muted)] ml-auto">{cultLabel[cultivo]} · {sspLabel[ssp]} · {horiz}</span>
            </label>
            <label className="flex items-center gap-2 text-sm py-1 cursor-pointer">
              <input type="checkbox" checked={capas.base} onChange={e => setCapas(v => ({ ...v, base: e.target.checked }))}/>
              <span>Parroquias Base (líneas)</span>
            </label>
          </div>

          <div className="mb-4 border-t pt-3">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)] flex items-center gap-1"><Filter size={12}/> Filtros — capa Riesgo</h3>
              <button onClick={() => setPanelFiltros(!panelFiltros)} className="text-xs text-[var(--primary)] font-semibold">{panelFiltros ? "Ocultar" : "Mostrar"}</button>
            </div>
            {panelFiltros && (
              <div className="space-y-2 text-sm">
                <div>
                  <label className="text-xs text-[var(--text-muted)] block mb-1">Cultivo</label>
                  <div className="flex gap-1 flex-wrap">
                    {(Object.keys(cultLabel) as Cultivo[]).map(c => (
                      <button key={c} onClick={() => { setCultivo(c); setCapas(v => ({ ...v, riesgoLong: true })); }}
                        className={`px-2.5 py-1.5 text-xs rounded-full border ${cultivo===c?"bg-[var(--primary)] text-white border-[var(--primary)]":"bg-white text-[var(--text)] border-[var(--border)]"}`}>
                        {cultLabel[c]}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-xs text-[var(--text-muted)] block mb-1">Escenario climático (SSP)</label>
                  <div className="flex gap-1 flex-wrap">
                    {(Object.keys(sspLabel) as SSP[]).map(s => (
                      <button key={s} onClick={() => { setSsp(s); setCapas(v => ({ ...v, riesgoLong: true })); }}
                        className={`px-2.5 py-1.5 text-xs rounded-full border ${ssp===s?"bg-[var(--primary)] text-white border-[var(--primary)]":"bg-white text-[var(--text)] border-[var(--border)]"}`}>
                        {sspLabel[s]}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-xs text-[var(--text-muted)] block mb-1">Horizonte temporal</label>
                  <div className="flex gap-1 flex-wrap">
                    {(["2021-2040","2041-2060","2061-2080"] as Horizonte[]).map(h => (
                      <button key={h} onClick={() => { setHoriz(h); setCapas(v => ({ ...v, riesgoLong: true })); }}
                        className={`px-2.5 py-1.5 text-xs rounded-full border ${horiz===h?"bg-[var(--primary)] text-white border-[var(--primary)]":"bg-white text-[var(--text)] border-[var(--border)]"}`}>
                        {h}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="mb-4 border-t pt-3">
            <h3 className="text-xs font-bold uppercase tracking-wider mb-2 text-[var(--text-muted)]">Leyenda — IR / Prioridad</h3>
            {Object.entries(PRIORITY_COLORS).map(([k, v]) => (
              <div key={k} className="flex items-center gap-2 text-xs py-1">
                <span className="w-5 h-4 rounded" style={{ background: v.hex }}></span>
                <span>{v.label}</span>
              </div>
            ))}
          </div>

          {selected && (
            <div className="border-t pt-4 mt-4">
              <button onClick={() => { setSelected(null); mapRef.current?.setFilter("prior-highlight", ["==", ["get","cod_parroq"], "___none___"]); }}
                className="float-right text-[var(--text-muted)] hover:text-[var(--text)]"><X size={16}/></button>
              <h3 className="text-lg font-bold">{selected.parroquia}</h3>
              <div className="text-sm text-[var(--text-muted)] mb-2">{selected.canton}</div>
              <div className="space-y-1 text-sm">
                {selected.ranking && <div>Ranking provincial: <strong>#{selected.ranking}</strong></div>}
                {selected.ir_medio_final != null && <div>IR medio: <strong>{Number(selected.ir_medio_final).toFixed(3)}</strong></div>}
                {selected.ir_max_final != null && <div>IR máximo: <strong>{Number(selected.ir_max_final).toFixed(3)}</strong></div>}
                {selected.n_cult_alto != null && <div>Cultivos en alto riesgo: <strong>{selected.n_cult_alto}</strong> / 4</div>}
                {selected.ir != null && (
                  <div>IR ({cultLabel[cultivo]}, {sspLabel[ssp]}, {horiz}): <strong>{Number(selected.ir).toFixed(3)}</strong></div>
                )}
                {selected.exp_pa_ha != null && (
                  <div className="text-xs mt-1">Exposición (ha): Papa {Number(selected.exp_pa_ha).toFixed(1)} · Maíz {Number(selected.exp_ma_ha).toFixed(1)} · Fréjol {Number(selected.exp_fr_ha).toFixed(1)} · Quinua {Number(selected.exp_qu_ha).toFixed(2)}</div>
                )}
                {selected.prioridad_final && (
                  <div className="mt-2">
                    <span className="badge" style={{ background: PRIORITY_COLORS[selected.prioridad_final as keyof typeof PRIORITY_COLORS]?.hex, color: 'white' }}>
                      {selected.prioridad_final}
                    </span>
                  </div>
                )}
                {selected.mensaje_priorizacion && (
                  <p className="text-xs mt-2 bg-[var(--bg)] p-2 rounded"><em>{selected.mensaje_priorizacion}</em></p>
                )}
                {selected.ficha_url && (
                  <a href={selected.ficha_url} target="_blank" rel="noopener" className="btn-primary text-sm mt-3 inline-flex items-center gap-1">
                    <FileText size={14}/> Descargar ficha PDF
                  </a>
                )}
              </div>
            </div>
          )}
        </div>
      </aside>
      <div ref={containerRef} className="flex-1"/>
    </div>
  );
}
