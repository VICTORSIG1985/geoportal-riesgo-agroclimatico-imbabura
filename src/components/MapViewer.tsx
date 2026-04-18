"use client";
import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { SERVICES, PRIORITY_COLORS } from "@/data/config";
import { Layers, Filter, X, FileText, Search, Bookmark, Table, Info, Lock, Loader2, RefreshCw, Share2 } from "lucide-react";
import RegisterModal from "./RegisterModal";
import { getRegistro, submitRegistro } from "@/lib/registro";

type Cultivo = "papa" | "maiz" | "frejol" | "quinua";
/** Los valores REALES en el FS son 'SSP1-2.6', 'SSP3-7.0', 'SSP5-8.5' (con mayúsculas/puntuación). */
type SSP = "SSP1-2.6" | "SSP3-7.0" | "SSP5-8.5";
type Horizonte = "2021-2040" | "2041-2060" | "2061-2080";
type Modo = "priorizacion" | "analisis";

const BOOKMARKS: { id: string; name: string; bounds: [[number, number], [number, number]]; desc: string }[] = [
  { id: "prov", name: "Vista provincial — Imbabura", bounds: [[-79.4, 0.05], [-77.7, 0.95]], desc: "Extensión completa de las 42 parroquias." },
  { id: "intag", name: "Intag — Cotacachi occidental", bounds: [[-78.9, 0.2], [-78.5, 0.55]], desc: "Zona de mayor priorización: García Moreno, Cuellaje, Peñaherrera." },
  { id: "ibarra_aa", name: "Eje Ibarra — Antonio Ante", bounds: [[-78.3, 0.2], [-78.05, 0.45]], desc: "Corredor urbano-rural, mayor exposición poblacional." },
  { id: "otavalo", name: "Otavalo — Mojanda", bounds: [[-78.4, 0.05], [-78.15, 0.3]], desc: "Valles con cultivos andinos tradicionales." },
  { id: "chota", name: "Cuenca del Chota — Pimampiro", bounds: [[-78.1, 0.3], [-77.75, 0.55]], desc: "Valle semiárido con exposición agroclimática alta." },
  { id: "urcuqui", name: "San Miguel de Urcuquí", bounds: [[-78.35, 0.3], [-78.05, 0.55]], desc: "Transición a la cuenca del Chota, 6 parroquias rurales." },
];

async function fetchGeojson(url: string, where = "1=1") {
  const params = new URLSearchParams({
    where, outFields: "*", f: "geojson", outSR: "4326",
  });
  // AbortController para evitar colgarse si el servicio demora
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 30_000);
  try {
    const res = await fetch(`${url}/query?${params}`, { signal: ctrl.signal });
    if (!res.ok) throw new Error(`FS ${res.status}`);
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

const SSPLABEL: Record<SSP, string> = { "SSP1-2.6": "SSP1-2.6", "SSP3-7.0": "SSP3-7.0", "SSP5-8.5": "SSP5-8.5" };
const CULTLABEL: Record<Cultivo, string> = { papa: "Papa", maiz: "Maíz", frejol: "Fréjol", quinua: "Quinua" };

export default function MapViewer() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  // Cache de resultados por combinación (key = "cultivo|ssp|horiz"); cada uno tiene 42 features.
  // Evita pedir los 1.512 de una vez (timeout 504 en AGO) y el segundo acceso a la misma combinación es instantáneo.
  const riesgoCacheRef = useRef<Map<string, any>>(new Map());

  // Leer estado inicial desde URL (si existe)
  const initFromUrl = (() => {
    if (typeof window === "undefined") return {};
    const params = new URLSearchParams(window.location.search);
    // Compatibilidad con URLs antiguas: 'ssp126' → 'SSP1-2.6', etc.
    const rawSsp = params.get("ssp");
    const sspMap: Record<string, SSP> = {
      "ssp126": "SSP1-2.6", "ssp370": "SSP3-7.0", "ssp585": "SSP5-8.5",
      "SSP1-2.6": "SSP1-2.6", "SSP3-7.0": "SSP3-7.0", "SSP5-8.5": "SSP5-8.5",
    };
    return {
      modo: (params.get("modo") as Modo) || undefined,
      cultivo: (params.get("cultivo") as Cultivo) || undefined,
      ssp: (rawSsp && sspMap[rawSsp]) || undefined,
      horiz: (params.get("horiz") as Horizonte) || undefined,
      codp: params.get("p") || undefined,
    };
  })();

  const [selected, setSelected] = useState<any | null>(null);
  const [regOpen, setRegOpen] = useState(false);
  const [pendingFicha, setPendingFicha] = useState<{ url: string; name: string } | null>(null);
  const [modo, setModo] = useState<Modo>(initFromUrl.modo || "priorizacion");
  const [cultivo, setCultivo] = useState<Cultivo>(initFromUrl.cultivo || "papa");
  const [ssp, setSsp] = useState<SSP>(initFromUrl.ssp || "SSP5-8.5");
  const [horiz, setHoriz] = useState<Horizonte>(initFromUrl.horiz || "2061-2080");
  const [opacidad, setOpacidad] = useState(0.78);
  const [copied, setCopied] = useState(false);

  const [priorData, setPriorData] = useState<any | null>(null);
  const [riesgoData, setRiesgoData] = useState<any | null>(null);
  const [baseData, setBaseData] = useState<any | null>(null);

  const [loading, setLoading] = useState<string | null>("Iniciando visor...");
  const [error, setError] = useState<string | null>(null);

  const [searchTerm, setSearchTerm] = useState("");

  // Init map + base layers
  useEffect(() => {
    if (!containerRef.current) return;
    setLoading("Cargando basemap...");
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
      center: [-78.2, 0.35], zoom: 9, maxZoom: 14, minZoom: 6,
      attributionControl: false,
      dragRotate: false, touchZoomRotate: false, // modo solo lectura (no rotación)
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");
    map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    map.addControl(new maplibregl.AttributionControl({
      customAttribution: "Víctor Hugo Pinto Páez · USGP 2026 · DOI 10.5281/zenodo.19288559 · © CartoDB · © OpenStreetMap",
    }), "bottom-right");
    mapRef.current = map;

    map.on("load", async () => {
      try {
        setLoading("Cargando 42 parroquias...");
        const [prior, base] = await Promise.all([
          fetchGeojson(SERVICES.flPrioridad.url),
          fetchGeojson(SERVICES.flParroquias.url),
        ]);
        setPriorData(prior); setBaseData(base);

        map.addSource("base", { type: "geojson", data: base });
        map.addLayer({ id: "base-line", type: "line", source: "base",
          paint: { "line-color": "#555", "line-width": 0.7, "line-opacity": 0.7 } });

        map.addSource("prior", { type: "geojson", data: prior });
        map.addLayer({ id: "prior-fill", type: "fill", source: "prior",
          paint: {
            "fill-color": ["match", ["get", "prioridad_final"],
              "Muy Alta", PRIORITY_COLORS["Muy Alta"].hex,
              "Alta", PRIORITY_COLORS["Alta"].hex,
              "Alerta", PRIORITY_COLORS["Alerta"].hex,
              "Monitoreo", PRIORITY_COLORS["Monitoreo"].hex,
              "Favorable", PRIORITY_COLORS["Favorable"].hex,
              "#CCCCCC"],
            "fill-opacity": 0.78
          }});
        map.addLayer({ id: "prior-outline", type: "line", source: "prior",
          paint: { "line-color": "#222", "line-width": 0.5, "line-opacity": 0.85 } });
        map.addLayer({ id: "prior-highlight", type: "line", source: "prior",
          paint: { "line-color": "#0A3558", "line-width": 3 },
          filter: ["==", ["get", "cod_parroq"], "___none___"] });

        // Capa analítica: empezamos vacía; los datos se piden por combinación (cultivo×SSP×horizonte)
        // sólo cuando el usuario entra al modo Análisis. Esto evita el timeout 504 al pedir los 1.512.
        const emptyFC: any = { type: "FeatureCollection", features: [] };
        setRiesgoData(emptyFC);
        map.addSource("riesgo", { type: "geojson", data: emptyFC });
        map.addLayer({ id: "riesgo-fill", type: "fill", source: "riesgo",
          layout: { visibility: "none" },
          paint: {
            "fill-color": ["step", ["coalesce", ["get", "ir"], -1],
              "#CCCCCC",
              0.0, "#2166AC", 0.40, "#67A9CF", 0.45, "#FDDBC7", 0.55, "#EF8A62", 0.65, "#B2182B"],
            "fill-opacity": 0.78
          }});
        map.addLayer({ id: "riesgo-outline", type: "line", source: "riesgo",
          layout: { visibility: "none" },
          paint: { "line-color": "#222", "line-width": 0.5, "line-opacity": 0.85 } });

        // Fit bounds
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
          map.fitBounds([[minx, miny], [maxx, maxy]], { padding: 50, duration: 0 });
        } catch {}

        // Click → selección
        map.on("click", (e) => {
          const feats = map.queryRenderedFeatures(e.point, { layers: ["prior-fill", "riesgo-fill"] });
          if (!feats.length) { clearSelection(); return; }
          const p = feats[0].properties as any;
          selectFeature(p);
        });

        // Tooltip hover
        popupRef.current = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 6 });
        const bindHover = (layer: string, field: string) => {
          map.on("mousemove", layer, (e) => {
            map.getCanvas().style.cursor = "pointer";
            if (!e.features?.length || !popupRef.current) return;
            const p = e.features[0].properties as any;
            const label = p[field] ?? p.parroquia;
            const extra = layer === "prior-fill" ? `<br><em>${p.prioridad_final} · IR ${Number(p.ir_medio_final).toFixed(3)}</em>` :
                          `<br><em>IR ${Number(p.ir).toFixed(3)}</em>`;
            popupRef.current.setLngLat(e.lngLat).setHTML(
              `<div style="font-size:12px;font-weight:600">${label}${extra}</div>`
            ).addTo(map);
          });
          map.on("mouseleave", layer, () => {
            map.getCanvas().style.cursor = "";
            popupRef.current?.remove();
          });
        };
        bindHover("prior-fill", "parroquia");
        bindHover("riesgo-fill", "parroquia");

        setLoading(null);
      } catch (err: any) {
        console.error("map load err", err);
        setError(`No se pudieron cargar los datos: ${err.message || err}. Verifique su conexión.`);
        setLoading(null);
      }
    });

    return () => { map.remove(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function clearSelection() {
    setSelected(null);
    mapRef.current?.setFilter("prior-highlight", ["==", ["get", "cod_parroq"], "___none___"]);
  }
  function selectFeature(p: any) {
    setSelected(p);
    mapRef.current?.setFilter("prior-highlight", ["==", ["get", "cod_parroq"], p?.cod_parroq || ""]);
  }

  // Cambio de modo
  useEffect(() => {
    const m = mapRef.current; if (!m || !m.getLayer("prior-fill")) return;
    const priorVis = modo === "priorizacion";
    m.setLayoutProperty("prior-fill", "visibility", priorVis ? "visible" : "none");
    m.setLayoutProperty("prior-outline", "visibility", priorVis ? "visible" : "none");
    m.setLayoutProperty("riesgo-fill", "visibility", priorVis ? "none" : "visible");
    m.setLayoutProperty("riesgo-outline", "visibility", priorVis ? "none" : "visible");
  }, [modo]);

  // Opacidad
  useEffect(() => {
    const m = mapRef.current; if (!m || !m.getLayer("prior-fill")) return;
    m.setPaintProperty("prior-fill", "fill-opacity", opacidad);
    m.setPaintProperty("riesgo-fill", "fill-opacity", opacidad);
  }, [opacidad]);

  // Sincronizar estado → URL (sin recargar)
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams();
    params.set("modo", modo);
    if (modo === "analisis") {
      params.set("cultivo", cultivo);
      params.set("ssp", ssp);
      params.set("horiz", horiz);
    }
    if (selected?.cod_parroq) params.set("p", selected.cod_parroq);
    const newUrl = `${window.location.pathname}?${params.toString()}`;
    window.history.replaceState({}, "", newUrl);
  }, [modo, cultivo, ssp, horiz, selected]);

  // Aplicar parroquia desde URL cuando cargan los datos
  useEffect(() => {
    if (!priorData || !initFromUrl.codp) return;
    const f = (priorData.features as any[]).find(f => f.properties.cod_parroq === initFromUrl.codp);
    if (f) zoomToParroquia(initFromUrl.codp);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [priorData]);

  async function copyShareLink() {
    if (typeof window === "undefined") return;
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  }

  // Carga los datos de riesgo filtrados por cultivo×SSP×horizonte (42 features por combinación).
  // Usa caché en memoria para que la segunda visita a la misma combinación sea instantánea.
  const applyFilters = useCallback(async () => {
    const m = mapRef.current; if (!m || !m.getSource("riesgo")) return;
    const key = `${cultivo}|${ssp}|${horiz}`;
    const cached = riesgoCacheRef.current.get(key);
    if (cached) {
      setRiesgoData(cached);
      (m.getSource("riesgo") as maplibregl.GeoJSONSource).setData(cached);
      setError(null);
      return;
    }
    setError(null);
    setLoading(`Cargando ${cultivo} · ${ssp} · ${horiz}...`);
    try {
      const where = `cultivo='${cultivo}' AND ssp='${ssp}' AND horizonte='${horiz}'`;
      const data = await fetchGeojson(SERVICES.flRiesgoLong.url, where);
      riesgoCacheRef.current.set(key, data);
      setRiesgoData(data);
      (m.getSource("riesgo") as maplibregl.GeoJSONSource).setData(data);
      setLoading(null);
    } catch (err: any) {
      setLoading(null);
      const msg = err?.name === "AbortError"
        ? "El servicio cartográfico tardó demasiado. Intente nuevamente en unos segundos."
        : `No se pudo cargar la capa analítica: ${err.message || err}`;
      setError(msg);
    }
  }, [cultivo, ssp, horiz]);
  useEffect(() => { if (modo === "analisis") applyFilters(); }, [cultivo, ssp, horiz, modo, applyFilters]);

  // Bookmarks
  function goTo(bm: typeof BOOKMARKS[number]) {
    mapRef.current?.fitBounds(bm.bounds, { padding: 40, duration: 600 });
  }

  // Búsqueda por parroquia
  const parroquiaMatches = useMemo(() => {
    if (!searchTerm || !priorData) return [];
    const t = searchTerm.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    return (priorData.features as any[])
      .filter(f => {
        const p = f.properties;
        const name = (p.parroquia || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
        return name.includes(t);
      })
      .slice(0, 6)
      .map(f => f.properties);
  }, [searchTerm, priorData]);

  function zoomToParroquia(cod: string) {
    if (!priorData || !mapRef.current) return;
    const feat = (priorData.features as any[]).find(f => f.properties.cod_parroq === cod);
    if (!feat) return;
    try {
      let minx = 180, miny = 90, maxx = -180, maxy = -90;
      const coords = (feat.geometry.coordinates as any[]).flat(3);
      for (let i = 0; i < coords.length; i += 2) {
        const x = coords[i], y = coords[i+1];
        if (x < minx) minx = x; if (x > maxx) maxx = x;
        if (y < miny) miny = y; if (y > maxy) maxy = y;
      }
      mapRef.current.fitBounds([[minx, miny], [maxx, maxy]], { padding: 80, duration: 700 });
      selectFeature(feat.properties);
      setSearchTerm("");
    } catch {}
  }

  // Tabla resumen sincronizada
  const resumen = useMemo(() => {
    if (modo === "priorizacion") {
      if (!priorData) return null;
      const feats = (priorData.features as any[]).map(f => f.properties);
      const byPrio: Record<string, number> = {};
      feats.forEach(f => byPrio[f.prioridad_final] = (byPrio[f.prioridad_final] || 0) + 1);
      const vals = feats.map(f => Number(f.ir_medio_final)).filter(v => !isNaN(v));
      return {
        titulo: "Distribución provincial (IR medio final)",
        indicadores: [
          { k: "Parroquias", v: feats.length },
          { k: "IR mín", v: Math.min(...vals).toFixed(3) },
          { k: "IR med", v: (vals.reduce((a,b)=>a+b,0)/vals.length).toFixed(3) },
          { k: "IR máx", v: Math.max(...vals).toFixed(3) },
        ],
        categorias: Object.entries(byPrio).sort((a,b) => {
          const order = ["Muy Alta","Alta","Alerta","Monitoreo","Favorable"];
          return order.indexOf(a[0]) - order.indexOf(b[0]);
        }),
        top: feats.sort((a,b) => Number(b.ir_medio_final) - Number(a.ir_medio_final)).slice(0, 5),
      };
    } else {
      if (!riesgoData) return null;
      const feats = (riesgoData.features as any[]).map(f => f.properties);
      const vals = feats.map(f => Number(f.ir)).filter(v => !isNaN(v));
      return {
        titulo: `${CULTLABEL[cultivo]} · ${SSPLABEL[ssp]} · ${horiz}`,
        indicadores: [
          { k: "Parroquias", v: feats.length },
          { k: "IR mín", v: Math.min(...vals).toFixed(3) },
          { k: "IR med", v: (vals.reduce((a,b)=>a+b,0)/vals.length).toFixed(3) },
          { k: "IR máx", v: Math.max(...vals).toFixed(3) },
        ],
        categorias: null,
        top: feats.sort((a,b) => Number(b.ir) - Number(a.ir)).slice(0, 5),
      };
    }
  }, [modo, priorData, riesgoData, cultivo, ssp, horiz]);

  function doFichaDownload(url: string, name: string) {
    const a = document.createElement("a");
    a.href = url; a.download = name; a.target = "_blank"; a.rel = "noopener";
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
  }
  function handleFichaDownload(url: string, name: string) {
    const reg = getRegistro();
    if (reg) {
      submitRegistro(reg, "ficha", name).catch(() => {});
      doFichaDownload(url, name);
      return;
    }
    setPendingFicha({ url, name });
    setRegOpen(true);
  }

  return (
    <div className="flex h-[calc(100vh-64px)]" onContextMenu={(e) => e.preventDefault()}>
      <aside className="w-[380px] bg-white border-r border-[var(--border)] overflow-y-auto flex-shrink-0">
        <div className="p-5 space-y-4">
          <div>
            <h2 className="text-xl mb-1 flex items-center gap-2"><Layers size={20}/> Visor Cartográfico</h2>
            <details className="text-xs bg-indigo-50 border border-indigo-200 rounded p-2 mb-1" open>
              <summary className="cursor-pointer font-semibold text-indigo-800">📘 ¿Cómo usar este visor?</summary>
              <div className="mt-2 text-[var(--text-muted)] space-y-1">
                <p><strong>Modo Priorización</strong>: muestra la clasificación final de cada parroquia (Muy Alta / Alta / Alerta / Monitoreo / Favorable). Ideal para lectura rápida.</p>
                <p><strong>Modo Análisis</strong>: permite filtrar por cultivo (papa, maíz, fréjol, quinua), escenario climático (SSP) y periodo de tiempo (horizonte) para ver el riesgo específico.</p>
                <p><strong>Hover</strong> sobre un polígono: tooltip breve. <strong>Click</strong>: abre ficha con datos completos y descarga del PDF.</p>
                <p><strong>Zonas de interés</strong>: accesos directos a Intag, Ibarra, Otavalo, Chota, Urcuquí.</p>
              </div>
            </details>
            <div className="text-xs text-[var(--text-muted)] bg-amber-50 border border-amber-200 rounded p-2 flex gap-1 items-start">
              <Lock size={12} className="mt-0.5 flex-shrink-0"/>
              <span>Modo <strong>solo lectura</strong>. El mapa no se puede editar.</span>
            </div>
          </div>

          {/* Modo dual */}
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)] mb-2">Modo</div>
            <div className="grid grid-cols-2 gap-1 p-1 bg-[var(--bg)] rounded">
              <button onClick={() => setModo("priorizacion")}
                className={`text-xs py-2 rounded font-semibold ${modo==="priorizacion"?"bg-white shadow text-[var(--primary)]":"text-[var(--text-muted)]"}`}>
                Priorización
              </button>
              <button onClick={() => setModo("analisis")}
                className={`text-xs py-2 rounded font-semibold ${modo==="analisis"?"bg-white shadow text-[var(--primary)]":"text-[var(--text-muted)]"}`}>
                Análisis
              </button>
            </div>
            <div className="text-[10px] text-[var(--text-muted)] mt-1">
              {modo === "priorizacion" ? "Lectura ejecutiva: prioridad final por parroquia." : "Exploración por cultivo × SSP × horizonte (1.512 inferencias)."}
            </div>
          </div>

          {/* Filtros modo análisis */}
          {modo === "analisis" && (
            <div className="space-y-2 pt-2 border-t border-[var(--border)]">
              <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)] mb-1 flex items-center gap-1"><Filter size={11}/> Filtros</div>
              <div>
                <label className="text-[10px] uppercase tracking-wider text-[var(--text-muted)] block mb-1">Cultivo</label>
                <div className="flex gap-1 flex-wrap">
                  {(Object.keys(CULTLABEL) as Cultivo[]).map(c => (
                    <button key={c} onClick={() => setCultivo(c)}
                      className={`px-2 py-1 text-[11px] rounded-full border ${cultivo===c?"bg-[var(--primary)] text-white border-[var(--primary)]":"bg-white text-[var(--text)] border-[var(--border)]"}`}>
                      {CULTLABEL[c]}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-[10px] uppercase tracking-wider text-[var(--text-muted)] block mb-1">Escenario SSP</label>
                <div className="flex gap-1 flex-wrap">
                  {(Object.keys(SSPLABEL) as SSP[]).map(s => (
                    <button key={s} onClick={() => setSsp(s)}
                      className={`px-2 py-1 text-[11px] rounded-full border ${ssp===s?"bg-[var(--primary)] text-white border-[var(--primary)]":"bg-white text-[var(--text)] border-[var(--border)]"}`}>
                      {SSPLABEL[s]}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-[10px] uppercase tracking-wider text-[var(--text-muted)] block mb-1">Horizonte</label>
                <div className="flex gap-1 flex-wrap">
                  {(["2021-2040","2041-2060","2061-2080"] as Horizonte[]).map(h => (
                    <button key={h} onClick={() => setHoriz(h)}
                      className={`px-2 py-1 text-[11px] rounded-full border ${horiz===h?"bg-[var(--primary)] text-white border-[var(--primary)]":"bg-white text-[var(--text)] border-[var(--border)]"}`}>
                      {h}
                    </button>
                  ))}
                </div>
              </div>
              <button onClick={() => { setCultivo("papa"); setSsp("SSP5-8.5"); setHoriz("2061-2080"); }}
                className="text-[10px] text-[var(--primary)] font-semibold hover:underline flex items-center gap-1">
                <RefreshCw size={10}/> Restablecer filtros
              </button>
            </div>
          )}

          {/* Búsqueda */}
          <div className="pt-2 border-t border-[var(--border)]">
            <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)] mb-1 flex items-center gap-1"><Search size={11}/> Buscar parroquia</div>
            <div className="relative">
              <input value={searchTerm} onChange={e => setSearchTerm(e.target.value)}
                placeholder="Ej. García Moreno, Lita..."
                className="w-full pl-3 pr-8 py-2 text-sm border border-[var(--border)] rounded"/>
              {searchTerm && <button onClick={() => setSearchTerm("")} className="absolute right-2 top-1/2 -translate-y-1/2 text-[var(--text-muted)]"><X size={14}/></button>}
            </div>
            {parroquiaMatches.length > 0 && (
              <div className="mt-1 bg-white border border-[var(--border)] rounded shadow-sm max-h-40 overflow-y-auto">
                {parroquiaMatches.map(p => (
                  <button key={p.cod_parroq} onClick={() => zoomToParroquia(p.cod_parroq)}
                    className="w-full text-left text-sm px-3 py-1.5 hover:bg-[var(--bg)] border-b last:border-b-0">
                    <div className="font-semibold text-xs">{p.parroquia}</div>
                    <div className="text-[10px] text-[var(--text-muted)]">{p.canton}</div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Bookmarks */}
          <div className="pt-2 border-t border-[var(--border)]">
            <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)] mb-1 flex items-center gap-1"><Bookmark size={11}/> Zonas de interés</div>
            <div className="grid grid-cols-2 gap-1">
              {BOOKMARKS.map(b => (
                <button key={b.id} onClick={() => goTo(b)} title={b.desc}
                  className="text-[11px] py-1.5 px-2 rounded border border-[var(--border)] bg-white hover:bg-[var(--bg)] text-left">
                  {b.name.split(" — ")[0]}
                </button>
              ))}
            </div>
          </div>

          {/* Opacidad */}
          <div className="pt-2 border-t border-[var(--border)]">
            <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)] mb-1">Opacidad ({Math.round(opacidad*100)}%)</div>
            <input type="range" min={0.3} max={1} step={0.05} value={opacidad} onChange={e => setOpacidad(Number(e.target.value))} className="w-full"/>
          </div>

          {/* Leyenda dinámica — rampa continua IR en modo análisis */}
          <div className="pt-2 border-t border-[var(--border)]">
            <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)] mb-1">
              Leyenda {modo==="priorizacion"?"· Prioridad final":"· Índice de Riesgo (IR)"}
            </div>
            {modo === "priorizacion" ? (
              Object.entries(PRIORITY_COLORS).map(([k, v]) => (
                <div key={k} className="flex items-center gap-2 text-[11px] py-0.5">
                  <span className="w-5 h-4 rounded inline-block" style={{ background: v.hex, opacity: opacidad }}></span>
                  <span>{v.label}</span>
                </div>
              ))
            ) : (
              <div>
                <div className="h-4 rounded mb-1" style={{
                  background: "linear-gradient(90deg, #2166AC 0%, #67A9CF 33%, #FDDBC7 55%, #EF8A62 75%, #B2182B 100%)",
                  opacity: opacidad
                }}/>
                <div className="flex justify-between text-[10px] text-[var(--text-muted)]">
                  <span>0.0</span><span>0.40</span><span>0.45</span><span>0.55</span><span>0.65</span><span>1.0</span>
                </div>
                <div className="text-[10px] text-[var(--text-muted)] mt-1">
                  IR para <strong>{CULTLABEL[cultivo]}</strong> · {SSPLABEL[ssp]} · {horiz}
                </div>
              </div>
            )}
          </div>

          {/* Tabla resumen sincronizada */}
          {resumen && (
            <div className="pt-2 border-t border-[var(--border)]">
              <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)] mb-1 flex items-center gap-1"><Table size={11}/> Resumen</div>
              <div className="text-[11px] text-[var(--text-muted)] mb-1">{resumen.titulo}</div>
              <div className="grid grid-cols-4 gap-1 text-[10px] mb-2">
                {resumen.indicadores.map(i => (
                  <div key={i.k} className="text-center bg-[var(--bg)] rounded p-1">
                    <div className="font-bold text-[var(--primary)] text-xs">{i.v}</div>
                    <div className="text-[9px] text-[var(--text-muted)] uppercase">{i.k}</div>
                  </div>
                ))}
              </div>
              <div className="text-[10px] uppercase tracking-wider text-[var(--text-muted)] mb-0.5">Top 5 parroquias</div>
              <ul className="text-[11px] space-y-0.5">
                {resumen.top.map((p: any, i: number) => {
                  const v = modo==="priorizacion" ? p.ir_medio_final : p.ir;
                  return (
                    <li key={p.cod_parroq || i} className="flex justify-between cursor-pointer hover:bg-[var(--bg)] px-1 rounded"
                      onClick={() => { if (p.cod_parroq) zoomToParroquia(p.cod_parroq); else selectFeature(p); }}>
                      <span className="truncate mr-1">{i+1}. {p.parroquia}</span>
                      <span className="font-mono font-semibold">{Number(v).toFixed(3)}</span>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          {/* Compartir vista (URL con estado) */}
          <div className="pt-2 border-t border-[var(--border)]">
            <button onClick={copyShareLink}
              className="w-full inline-flex items-center justify-center gap-1 text-xs bg-[var(--primary)] text-white px-3 py-2 rounded font-semibold hover:bg-[var(--primary-dark)]">
              <Share2 size={12}/> {copied ? "Enlace copiado ✓" : "Compartir vista actual"}
            </button>
            <div className="text-[10px] text-[var(--text-muted)] mt-1 text-center">
              URL con modo, filtros y parroquia seleccionada
            </div>
          </div>

          {/* Metadatos del visor */}
          <div className="pt-2 border-t border-[var(--border)] text-[10px] text-[var(--text-muted)] space-y-0.5">
            <div className="flex items-center gap-1 font-semibold text-[11px] mb-1"><Info size={11}/> Metadatos</div>
            <div>Fuente: ArcGIS Online USGP-EC · 3 Feature Services REST</div>
            <div>Variable: IR = 0·P(Bajo) + 0,5·P(Medio) + 1·P(Alto)</div>
            <div>SRS: WGS84 (EPSG:4326)</div>
            <div>Resolución: parroquial (~10 km raster climático)</div>
            <div>Actualización: 2026-03 · DOI 10.5281/zenodo.19288559</div>
          </div>

          {/* Selección detallada */}
          {selected && (
            <div className="pt-3 border-t-2 border-[var(--primary)]">
              <div className="flex justify-between items-start mb-1">
                <div>
                  <div className="text-[10px] uppercase tracking-wider text-[var(--text-muted)]">{selected.canton}</div>
                  <h3 className="text-base font-bold">{selected.parroquia}</h3>
                </div>
                <button onClick={clearSelection} className="text-[var(--text-muted)] hover:text-[var(--text)]"><X size={14}/></button>
              </div>
              <div className="space-y-1 text-xs">
                {selected.ranking && <div>Ranking: <strong>#{selected.ranking}</strong></div>}
                {selected.ir_medio_final != null && <div>IR medio final: <strong>{Number(selected.ir_medio_final).toFixed(3)}</strong></div>}
                {selected.ir_max_final != null && <div>IR máximo: <strong>{Number(selected.ir_max_final).toFixed(3)}</strong></div>}
                {selected.n_cult_alto != null && <div>Cultivos en alto riesgo: <strong>{selected.n_cult_alto}</strong>/4</div>}
                {selected.ir != null && (
                  <div>IR ({CULTLABEL[cultivo]}, {SSPLABEL[ssp]}, {horiz}): <strong>{Number(selected.ir).toFixed(3)}</strong></div>
                )}
                {selected.prioridad_final && (
                  <div className="mt-1">
                    <span className="badge" style={{ background: PRIORITY_COLORS[selected.prioridad_final as keyof typeof PRIORITY_COLORS]?.hex, color: "white" }}>
                      {selected.prioridad_final}
                    </span>
                  </div>
                )}
                {selected.mensaje_priorizacion && (
                  <p className="text-[11px] mt-1 bg-[var(--bg)] p-2 rounded"><em>{selected.mensaje_priorizacion}</em></p>
                )}
                {selected.ficha_url && (
                  <button onClick={() => handleFichaDownload(selected.ficha_url, `Ficha_${selected.parroquia || "parroquia"}.pdf`)}
                    className="btn-primary text-xs mt-2 inline-flex items-center gap-1">
                    <Lock size={10} className="opacity-70"/> <FileText size={12}/> Descargar ficha PDF
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </aside>

      <div className="flex-1 relative">
        <div ref={containerRef} className="w-full h-full"/>
        {loading && (
          <div className="absolute top-3 right-3 bg-white/95 border border-[var(--border)] rounded-lg shadow px-3 py-2 text-xs flex items-center gap-2">
            <Loader2 size={14} className="animate-spin text-[var(--primary)]"/> {loading}
          </div>
        )}
        {error && (
          <div className="absolute bottom-16 left-1/2 -translate-x-1/2 bg-red-50 border border-red-300 rounded-lg shadow-lg px-4 py-3 max-w-md">
            <div className="text-sm font-semibold text-red-700 mb-1 flex items-center gap-1"><AlertCircle size={14}/> Error al cargar datos</div>
            <div className="text-xs text-red-600 mb-2">{error}</div>
            <button onClick={() => window.location.reload()} className="text-xs text-red-700 underline">Recargar</button>
          </div>
        )}
      </div>

      <RegisterModal
        open={regOpen}
        onClose={() => { setRegOpen(false); setPendingFicha(null); }}
        onCompleted={() => {
          setRegOpen(false);
          if (pendingFicha) doFichaDownload(pendingFicha.url, pendingFicha.name);
          setPendingFicha(null);
        }}
        pending={pendingFicha ? { tipo: "ficha", name: pendingFicha.name } : null}
      />
    </div>
  );
}

function AlertCircle(props: any) {
  // stub re-import; keep icon available via lucide-react
  const { size = 16, ...rest } = props;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...rest}>
      <circle cx="12" cy="12" r="10"/>
      <line x1="12" y1="8" x2="12" y2="12"/>
      <line x1="12" y1="16" x2="12.01" y2="16"/>
    </svg>
  );
}
