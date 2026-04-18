"use client";
import { useState } from "react";
import { FIGURES, GROUPS, figureUrl, Figure } from "@/data/figures";
import { X, Download, Lock } from "lucide-react";
import PageHero from "@/components/PageHero";
import RegisterModal from "@/components/RegisterModal";
import { getRegistro, submitRegistro } from "@/lib/registro";

export default function Galeria() {
  const [group, setGroup] = useState<string>("Todos");
  const [lightbox, setLightbox] = useState<Figure | null>(null);
  const [regOpen, setRegOpen] = useState(false);
  const [pendingFig, setPendingFig] = useState<Figure | null>(null);
  const shown = group === "Todos" ? FIGURES : FIGURES.filter(f => f.group === group);

  function doDownload(fig: Figure) {
    const a = document.createElement("a");
    a.href = figureUrl(fig);
    a.download = fig.file;
    a.target = "_blank"; a.rel = "noopener";
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
  }
  function handleDownload(fig: Figure, e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    const reg = getRegistro();
    if (reg) {
      submitRegistro(reg, "ficha", fig.file).catch(() => {});
      doDownload(fig);
      return;
    }
    setPendingFig(fig);
    setRegOpen(true);
  }
  return (
    <>
      <PageHero
        title="Galería Científica"
        subtitle="60 figuras cartográficas derivadas de la investigación, organizadas por 6 grupos temáticos. Todas públicas en ArcGIS Online."
        image="imbabura_geoparque_slide2.png"
        overlayColor="rgba(107,78,155,0.35)"
        credit="Imagen: Geoparque Mundial UNESCO Imbabura · Fuente: geoparque.imbabura.gob.ec · Elaboración: Prefectura de Imbabura"
      />

      <section className="container-prose py-6 sticky top-[64px] bg-[var(--bg)] z-10 border-b border-[var(--border)]">
        <div className="flex flex-wrap gap-2">
          {["Todos", ...GROUPS].map(g => (
            <button key={g} onClick={() => setGroup(g)}
              className={`px-4 py-2 rounded-full text-sm font-semibold border transition ${
                group === g ? "bg-[var(--primary)] text-white border-[var(--primary)]" : "bg-white text-[var(--primary)] border-[var(--border)] hover:bg-gray-50"
              }`}>
              {g}{g !== "Todos" && ` (${FIGURES.filter(f => f.group === g).length})`}
            </button>
          ))}
        </div>
      </section>

      <section className="container-prose py-10">
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {shown.map((fig, i) => (
            <div key={i} className="card p-0 overflow-hidden cursor-pointer group" onClick={() => setLightbox(fig)}>
              <div className="aspect-video bg-[var(--bg)] overflow-hidden">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={figureUrl(fig)} alt={fig.title}
                  className="w-full h-full object-contain group-hover:scale-105 transition-transform"/>
              </div>
              <div className="p-4">
                <div className="text-xs uppercase tracking-wider text-[var(--text-muted)] font-semibold mb-1">{fig.group}</div>
                <div className="font-bold text-sm mb-1">{fig.title}</div>
                <div className="text-xs text-[var(--text-muted)] line-clamp-2">{fig.caption}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {lightbox && (
        <div className="fixed inset-0 bg-black/90 z-50 flex flex-col items-center justify-center p-4" onClick={() => setLightbox(null)}>
          <button onClick={() => setLightbox(null)} className="absolute top-4 right-4 text-white p-2 hover:bg-white/10 rounded">
            <X size={28}/>
          </button>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={figureUrl(lightbox)} alt={lightbox.title}
            className="max-h-[80vh] max-w-[90vw] object-contain bg-white rounded shadow-2xl"/>
          <div className="bg-white/10 text-white p-5 max-w-3xl w-full rounded mt-4" onClick={e => e.stopPropagation()}>
            <div className="text-xs uppercase tracking-wider opacity-70">{lightbox.group}</div>
            <h3 className="text-xl font-bold text-white">{lightbox.title}</h3>
            <p className="opacity-90 my-2">{lightbox.caption}</p>
            <button onClick={(e) => handleDownload(lightbox, e)}
              className="inline-flex items-center gap-2 bg-white text-[var(--primary)] px-4 py-2 rounded-lg font-semibold mt-2 hover:bg-gray-100">
              <Lock size={12} className="opacity-70"/> <Download size={16}/> Descargar PNG
            </button>
            <p className="text-[11px] text-white/70 mt-2">🔒 Descarga sujeta a registro único (LOPDP Ecuador)</p>
          </div>
        </div>
      )}

      <RegisterModal
        open={regOpen}
        onClose={() => { setRegOpen(false); setPendingFig(null); }}
        onCompleted={() => {
          setRegOpen(false);
          if (pendingFig) doDownload(pendingFig);
          setPendingFig(null);
        }}
        pending={pendingFig ? { tipo: "ficha", name: pendingFig.file } : null}
      />
    </>
  );
}
