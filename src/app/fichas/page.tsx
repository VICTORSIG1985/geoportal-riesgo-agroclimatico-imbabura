"use client";
import { useMemo, useState } from "react";
import { FICHAS, fichaDownloadUrl, fichaItemUrl } from "@/data/fichas";
import { Download, ExternalLink, Search, FileText } from "lucide-react";

export default function FichasPage() {
  const [q, setQ] = useState("");
  const [canton, setCanton] = useState("Todos");
  const cantones = useMemo(() => ["Todos", ...Array.from(new Set(FICHAS.map(f => f.canton)))], []);
  const filtered = useMemo(() =>
    FICHAS.filter(f =>
      (canton === "Todos" || f.canton === canton) &&
      (q === "" || f.parroquia.toLowerCase().includes(q.toLowerCase()) || f.canton.toLowerCase().includes(q.toLowerCase()))
    ).sort((a, b) => (a.canton + a.parroquia).localeCompare(b.canton + b.parroquia))
  , [q, canton]);

  return (
    <>
      <section className="bg-[var(--accent-2)] text-white py-14">
        <div className="container-prose">
          <h1 className="text-white mb-3">Fichas Parroquiales</h1>
          <p className="text-xl opacity-90 max-w-3xl">
            42 fichas PDF (una por parroquia) con IR medio y máximo bajo los 9 escenarios, cultivo más vulnerable,
            mensaje de priorización y recomendación operativa para los GADs.
          </p>
        </div>
      </section>

      <section className="container-prose py-6 sticky top-[64px] bg-[var(--bg)] z-10 border-b border-[var(--border)]">
        <div className="flex flex-wrap gap-3 items-center">
          <div className="flex-1 min-w-[200px] relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]"/>
            <input value={q} onChange={e => setQ(e.target.value)}
              placeholder="Buscar por parroquia o cantón..."
              className="w-full pl-10 pr-4 py-2 border border-[var(--border)] rounded-lg text-sm"/>
          </div>
          <select value={canton} onChange={e => setCanton(e.target.value)}
            className="px-4 py-2 border border-[var(--border)] rounded-lg text-sm">
            {cantones.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <div className="text-sm text-[var(--text-muted)]">
            <strong>{filtered.length}</strong> / {FICHAS.length} fichas
          </div>
        </div>
      </section>

      <section className="container-prose py-10">
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(f => (
            <div key={f.id} className="card flex flex-col">
              <div className="flex items-start gap-3 mb-3">
                <div className="w-10 h-10 rounded bg-[var(--accent-2)] text-white flex items-center justify-center flex-shrink-0">
                  <FileText size={20}/>
                </div>
                <div className="min-w-0">
                  <div className="text-xs uppercase tracking-wider text-[var(--text-muted)] font-semibold">{f.canton}</div>
                  <div className="font-bold leading-tight">{f.parroquia}</div>
                </div>
              </div>
              <div className="flex gap-2 mt-auto">
                <a href={fichaDownloadUrl(f.id)} download={`Ficha_${f.parroquia}.pdf`} target="_blank"
                  className="flex-1 inline-flex items-center justify-center gap-1 bg-[var(--accent-2)] text-white px-3 py-2 rounded text-sm font-semibold hover:bg-emerald-700">
                  <Download size={14}/> PDF
                </a>
                <a href={fichaItemUrl(f.id)} target="_blank"
                  className="inline-flex items-center justify-center gap-1 border border-[var(--accent-2)] text-[var(--accent-2)] px-3 py-2 rounded text-sm font-semibold hover:bg-[var(--accent-2)] hover:text-white">
                  <ExternalLink size={14}/>
                </a>
              </div>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
