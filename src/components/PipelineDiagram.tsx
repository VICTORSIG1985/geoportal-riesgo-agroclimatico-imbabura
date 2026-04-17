// Organizador gráfico nativo — Pipeline 5 fases (Pinto Páez 2026)
// Reemplaza la imagen estática para mantener resolución en cualquier tamaño.

const FASES = [
  { n: 1, t: "Preparación climática", scripts: "00 · 01 · 01B · 02",
    items: ["Descarga BASD-CMIP6-PE", "10 MCG × 3 SSP × 3 horizontes", "Recorte espacial Imbabura"],
    color: "#2166AC"
  },
  { n: 2, t: "Índices agroclimáticos", scripts: "03A · 03B · 03C · 03D · 03E · 03F",
    items: ["ET₀ Hargreaves-Samani", "P − ET₀ déficit hídrico", "Estrés térmico / cultivo", "CDD, heladas, agregación"],
    color: "#67A9CF"
  },
  { n: 3, t: "Exposición agrícola", scripts: "04B · 04C",
    items: ["MapSPAM 2020 v2r0", "ESPAC 2024 (INEC)", "Desagregación parroquial exactextract"],
    color: "#228B6E"
  },
  { n: 4, t: "SDM con Random Forest", scripts: "05A · 05B · 05C · 06 · 06B · 06C",
    items: ["2.681 registros GBIF", "16 variables predictoras", "RF k=5 validación espacial", "Proyección a 9 escenarios"],
    color: "#EF8A62"
  },
  { n: 5, t: "Integración bayesiana", scripts: "07 · 08 · 09 · 10",
    items: ["Red Bayesiana 7 nodos", "1.512 inferencias IR", "Mapas + 42 fichas PDF", "Validación ISO 19115"],
    color: "#B2182B"
  },
];

export default function PipelineDiagram() {
  return (
    <div className="w-full">
      <div className="grid md:grid-cols-5 gap-3 relative">
        {FASES.map((f, i) => (
          <div key={f.n} className="relative">
            <div className="rounded-xl overflow-hidden shadow border border-[var(--border)] bg-white h-full flex flex-col">
              <div className="px-4 py-3 text-white flex items-center gap-2" style={{ background: f.color }}>
                <div className="w-8 h-8 rounded-full bg-white/25 flex items-center justify-center text-sm font-bold">{f.n}</div>
                <div className="font-bold text-sm">{f.t}</div>
              </div>
              <div className="p-3 text-xs flex-1 flex flex-col">
                <div className="text-[10px] uppercase tracking-wider font-bold text-[var(--text-muted)] mb-1">Scripts</div>
                <div className="text-xs font-mono text-[var(--text-muted)] mb-2">{f.scripts}</div>
                <ul className="space-y-1 text-[var(--text-muted)] list-disc list-inside mt-auto">
                  {f.items.map((it, j) => <li key={j}>{it}</li>)}
                </ul>
              </div>
            </div>
            {i < FASES.length - 1 && (
              <div className="hidden md:flex absolute top-1/2 -right-2 -translate-y-1/2 z-10 text-[var(--text-muted)] text-lg pointer-events-none">
                ▶
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="mt-4 rounded-lg bg-[var(--bg)] border-l-4 border-[var(--primary)] p-3 text-sm text-[var(--text-muted)]">
        <strong className="text-[var(--primary)]">Entrada:</strong> BASD-CMIP6-PE (Fernandez-Palomino et al. 2024) ·
        GBIF · MapSPAM · ESPAC · CONALI.
        <br/>
        <strong className="text-[var(--primary)]">Salida:</strong> 1.512 IR parroquial × cultivo × escenario · 42 fichas PDF ·
        60 mapas · ISO 19115.
      </div>
    </div>
  );
}
