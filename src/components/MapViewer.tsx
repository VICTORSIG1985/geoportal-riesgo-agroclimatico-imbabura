"use client";
import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { SERVICES, PRIORITY_COLORS } from "@/data/config";

async function fetchGeojson(url: string) {
  const params = new URLSearchParams({
    where: "1=1",
    outFields: "*",
    f: "geojson",
    outSR: "4326",
  });
  const res = await fetch(`${url}/query?${params}`);
  if (!res.ok) throw new Error("fetch FS failed");
  return res.json();
}

export default function MapViewer() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [selected, setSelected] = useState<any | null>(null);
  const [visible, setVisible] = useState({ prior: true, base: true });

  useEffect(() => {
    if (!containerRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {
          "osm-gray": {
            type: "raster",
            tiles: ["https://tiles.arcgis.com/tiles/mDHnw3YfXHXUryue/arcgis/rest/services/Light_Gray_Canvas_Base_WMTS/MapServer/tile/{z}/{y}/{x}"],
            tileSize: 256,
            attribution: "Light Gray Canvas — Esri"
          },
        },
        layers: [
          { id: "bg", type: "raster", source: "osm-gray" }
        ]
      },
      center: [-78.2, 0.35],
      zoom: 9.2,
      attributionControl: false,
    });
    map.addControl(new maplibregl.NavigationControl(), "top-left");
    map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    map.addControl(new maplibregl.AttributionControl({
      customAttribution: "Víctor Hugo Pinto Páez · USGP 2026 · DOI 10.5281/zenodo.19288559 · Datos: ArcGIS Online",
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
          paint: { "line-color": "#444", "line-width": 0.5, "line-opacity": 0.6 }
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
            "fill-opacity": 0.7
          }
        });
        map.addLayer({
          id: "prior-outline", type: "line", source: "prior",
          paint: { "line-color": "#222", "line-width": 0.4, "line-opacity": 0.7 }
        });
        map.addLayer({
          id: "prior-highlight", type: "line", source: "prior",
          paint: { "line-color": "#0A3558", "line-width": 3 },
          filter: ["==", "cod_parroq", ""]
        });

        map.on("click", "prior-fill", (e) => {
          if (!e.features?.length) return;
          const feat = e.features[0];
          const p = feat.properties;
          setSelected(p);
          map.setFilter("prior-highlight", ["==", "cod_parroq", p?.cod_parroq || ""]);
        });
        map.on("mouseenter", "prior-fill", () => map.getCanvas().style.cursor = "pointer");
        map.on("mouseleave", "prior-fill", () => map.getCanvas().style.cursor = "");
      } catch (err) {
        console.error("map load err", err);
      }
    });

    return () => { map.remove(); };
  }, []);

  useEffect(() => {
    const map = mapRef.current; if (!map || !map.getLayer("prior-fill")) return;
    map.setLayoutProperty("prior-fill", "visibility", visible.prior ? "visible" : "none");
    map.setLayoutProperty("prior-outline", "visibility", visible.prior ? "visible" : "none");
    map.setLayoutProperty("base-line", "visibility", visible.base ? "visible" : "none");
  }, [visible]);

  return (
    <div className="flex h-[calc(100vh-64px)]">
      <aside className="w-80 bg-white border-r border-[var(--border)] overflow-y-auto">
        <div className="p-5">
          <h2 className="text-xl mb-4">Visor Cartográfico</h2>
          <p className="text-sm text-[var(--text-muted)] mb-4">
            Priorización parroquial bajo <strong>SSP5-8.5 · 2061–2080</strong>. Haga clic sobre una parroquia para ver detalle.
          </p>

          <div className="mb-4">
            <h3 className="text-sm font-bold uppercase tracking-wider mb-2 text-[var(--text-muted)]">Capas</h3>
            <label className="flex items-center gap-2 text-sm py-1 cursor-pointer">
              <input type="checkbox" checked={visible.prior}
                onChange={e => setVisible(v => ({ ...v, prior: e.target.checked }))} />
              Priorización Final (42)
            </label>
            <label className="flex items-center gap-2 text-sm py-1 cursor-pointer">
              <input type="checkbox" checked={visible.base}
                onChange={e => setVisible(v => ({ ...v, base: e.target.checked }))} />
              Parroquias Base (líneas)
            </label>
          </div>

          <div className="mb-4">
            <h3 className="text-sm font-bold uppercase tracking-wider mb-2 text-[var(--text-muted)]">Leyenda</h3>
            {Object.entries(PRIORITY_COLORS).map(([k, v]) => (
              <div key={k} className="flex items-center gap-2 text-xs py-1">
                <span className="w-5 h-4 rounded" style={{ background: v.hex }}></span>
                <span>{v.label}</span>
              </div>
            ))}
          </div>

          {selected && (
            <div className="border-t pt-4 mt-4">
              <h3 className="text-lg font-bold">{selected.parroquia}</h3>
              <div className="text-sm text-[var(--text-muted)] mb-2">{selected.canton}</div>
              <div className="space-y-1 text-sm">
                <div>Ranking provincial: <strong>#{selected.ranking}</strong></div>
                <div>IR medio: <strong>{Number(selected.ir_medio_final).toFixed(3)}</strong></div>
                <div>IR máximo: <strong>{Number(selected.ir_max_final).toFixed(3)}</strong></div>
                <div>Cultivos en alto riesgo: <strong>{selected.n_cult_alto}</strong> / 4</div>
                <div>Exposición (ha): Papa {Number(selected.exp_pa_ha).toFixed(1)} · Maíz {Number(selected.exp_ma_ha).toFixed(1)} · Fréjol {Number(selected.exp_fr_ha).toFixed(1)} · Quinua {Number(selected.exp_qu_ha).toFixed(2)}</div>
                <div className="mt-2">
                  <span className="badge" style={{ background: PRIORITY_COLORS[selected.prioridad_final as keyof typeof PRIORITY_COLORS]?.hex, color: 'white' }}>
                    {selected.prioridad_final}
                  </span>
                </div>
                {selected.mensaje_priorizacion && (
                  <p className="text-xs mt-2 bg-[var(--bg)] p-2 rounded"><em>{selected.mensaje_priorizacion}</em></p>
                )}
                {selected.ficha_url && (
                  <a href={selected.ficha_url} target="_blank" className="btn-primary text-sm mt-3 inline-flex">
                    📄 Descargar ficha PDF
                  </a>
                )}
              </div>
            </div>
          )}
        </div>
      </aside>
      <div ref={containerRef} className="flex-1" />
    </div>
  );
}
