"use client";
import { useMemo, useState } from "react";
import { TOP10, EXPOSICION, PERDIDA_APTITUD, CULTIVOS } from "@/data/ranking";
import { PRIORITY_COLORS } from "@/data/config";
import IRChart from "@/components/IRChart";
import { TrendingUp, Target, Wheat, Download } from "lucide-react";

export default function ResultadosPage() {
  const [cultSel, setCultSel] = useState("papa");
  const expTotal = EXPOSICION.papa + EXPOSICION.maiz + EXPOSICION.frejol;

  return (
    <>
      <section className="bg-[var(--accent-3)] text-white py-14">
        <div className="container-prose">
          <h1 className="text-white mb-3">Resultados</h1>
          <p className="text-xl opacity-90 max-w-3xl">
            Principales hallazgos de la investigación: ranking parroquial, IR por cultivo y escenario, exposición agrícola
            y pérdida de aptitud climática.
          </p>
        </div>
      </section>

      <section className="container-prose py-10">
        <div className="grid md:grid-cols-4 gap-4">
          <div className="card border-l-4 border-[var(--accent)]">
            <div className="text-xs uppercase tracking-wider text-[var(--text-muted)]">Rango de IR</div>
            <div className="text-3xl font-bold">0,350 – 0,689</div>
            <div className="text-sm mt-1">Imbaya → García Moreno</div>
          </div>
          <div className="card border-l-4 border-[var(--accent)]">
            <div className="text-xs uppercase tracking-wider text-[var(--text-muted)]">Factor</div>
            <div className="text-3xl font-bold text-[var(--accent)]">1,97×</div>
            <div className="text-sm mt-1">Diferencia entre extremos</div>
          </div>
          <div className="card border-l-4 border-[var(--accent-2)]">
            <div className="text-xs uppercase tracking-wider text-[var(--text-muted)]">Exposición total</div>
            <div className="text-3xl font-bold">{expTotal.toLocaleString('es')} ha</div>
            <div className="text-sm mt-1">Papa + Maíz + Fréjol</div>
          </div>
          <div className="card border-l-4 border-[var(--primary)]">
            <div className="text-xs uppercase tracking-wider text-[var(--text-muted)]">Inferencias</div>
            <div className="text-3xl font-bold">1.512 / 1.512</div>
            <div className="text-sm mt-1">Sin valores nulos</div>
          </div>
        </div>
      </section>

      <section className="container-prose py-10">
        <h2 className="mb-6 flex items-center gap-3"><TrendingUp className="text-[var(--primary)]"/> IR medio provincial por cultivo, escenario y horizonte</h2>
        <div className="flex flex-wrap gap-2 mb-6">
          {CULTIVOS.map(c => (
            <button key={c} onClick={() => setCultSel(c)}
              className={`px-4 py-2 rounded-full text-sm font-semibold border transition ${
                cultSel === c ? "bg-[var(--primary)] text-white border-[var(--primary)]" : "bg-white text-[var(--primary)] border-[var(--border)] hover:bg-gray-50"
              }`}>
              {c.charAt(0).toUpperCase() + c.slice(1)}
            </button>
          ))}
        </div>
        <div className="card">
          <IRChart cultivo={cultSel}/>
        </div>
        <p className="text-sm text-[var(--text-muted)] mt-3">
          Fuente: Tabla 5 del manuscrito. IR = 0·P(Bajo) + 0,5·P(Medio) + 1·P(Alto). Valores medios provinciales (42 parroquias).
          <strong> Fréjol</strong> es el cultivo más estable (ΔIR ≤ +0,5%). <strong>Quinua</strong> muestra el mayor incremento relativo (+49,3%)
          pero es estimación exploratoria provincial.
        </p>
      </section>

      <section className="container-prose py-10">
        <h2 className="mb-6 flex items-center gap-3"><Target className="text-[var(--primary)]"/> Top 10 parroquias — Ranking de priorización</h2>
        <div className="card p-0 overflow-x-auto">
          <table className="data">
            <thead>
              <tr>
                <th>#</th><th>Parroquia</th><th>Cantón</th>
                <th>IR medio</th><th>IR máx</th><th>Cultivos alto</th><th>Prioridad</th>
              </tr>
            </thead>
            <tbody>
              {TOP10.map(r => (
                <tr key={r.rank}>
                  <td className="font-bold">{r.rank}</td>
                  <td className="font-semibold">{r.parroquia}</td>
                  <td>{r.canton}</td>
                  <td>{r.ir_medio.toFixed(3)}</td>
                  <td>{r.ir_max.toFixed(3)}</td>
                  <td className="text-center">{r.n_cult_alto} / 4</td>
                  <td>
                    <span className="badge" style={{ background: PRIORITY_COLORS[r.prioridad].hex, color: 'white' }}>
                      {r.prioridad}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-sm text-[var(--text-muted)] mt-3">
          Fuente: Tabla 7 del manuscrito. <strong>Cotacachi</strong> concentra 6 de las 10 parroquias prioritarias (zona de Intag).
          Solo en <strong>García Moreno</strong> los 4 cultivos entran simultáneamente en categoría Alto.
          Para el ranking completo de las 42 parroquias, use el <a href="/visor" className="text-[var(--primary)] font-semibold">Visor Cartográfico</a>.
        </p>
      </section>

      <section className="container-prose py-10">
        <h2 className="mb-6 flex items-center gap-3"><Wheat className="text-[var(--primary)]"/> Exposición agrícola (MapSPAM 2020)</h2>
        <div className="grid md:grid-cols-4 gap-4 mb-6">
          <div className="card text-center">
            <div className="text-4xl font-bold text-[var(--accent-3)]">{EXPOSICION.maiz.toLocaleString('es')}</div>
            <div className="text-sm text-[var(--text-muted)] mt-1">ha · Maíz (71,7%)</div>
          </div>
          <div className="card text-center">
            <div className="text-4xl font-bold text-[var(--accent-2)]">{EXPOSICION.frejol.toLocaleString('es')}</div>
            <div className="text-sm text-[var(--text-muted)] mt-1">ha · Fréjol (21,6%)</div>
          </div>
          <div className="card text-center">
            <div className="text-4xl font-bold text-[var(--primary)]">{EXPOSICION.papa.toLocaleString('es')}</div>
            <div className="text-sm text-[var(--text-muted)] mt-1">ha · Papa (6,6%)</div>
          </div>
          <div className="card text-center border-l-4 border-amber-400">
            <div className="text-4xl font-bold text-amber-500">{EXPOSICION.quinua}</div>
            <div className="text-sm text-[var(--text-muted)] mt-1">ha · Quinua (ESPAC)</div>
          </div>
        </div>
        <div className="card bg-amber-50 border-l-4 border-amber-400">
          <strong>Advertencia quinua:</strong> ESPAC 2024 reporta apenas 18,36 ha distribuidas uniformemente entre las 42 parroquias.
          Los IR de quinua reflejan variación en peligro y susceptibilidad, pero <strong>no diferencias reales de exposición</strong>.
          Tratar como estimación exploratoria a escala provincial.
        </div>
      </section>

      <section className="container-prose py-10">
        <h2 className="mb-6">Pérdida de aptitud climática — SSP5-8.5 · 2061-2080</h2>
        <div className="grid md:grid-cols-4 gap-4">
          {Object.entries(PERDIDA_APTITUD).map(([cult, val]) => (
            <div key={cult} className="card">
              <div className="text-xs uppercase tracking-wider text-[var(--text-muted)]">{cult}</div>
              <div className="text-3xl font-bold text-[var(--accent)]">{val}%</div>
              <div className="text-sm text-[var(--text-muted)] mt-1">Caída vs. histórico</div>
            </div>
          ))}
        </div>
        <p className="text-sm text-[var(--text-muted)] mt-3">
          Orden de pérdida: quinua &gt; papa &gt; maíz &gt; fréjol. Bajo SSP1-2.6 ningún cultivo supera −3,4%.
        </p>
      </section>

      <section className="container-prose py-10">
        <div className="card bg-gradient-to-br from-[var(--primary)] to-[var(--primary-dark)] text-white">
          <h3 className="text-white text-2xl mb-3 flex items-center gap-2"><Download/> Descarga los datos completos</h3>
          <p className="opacity-90 mb-4">
            Acceso vía REST a las 1.512 inferencias por parroquia × cultivo × SSP × horizonte, además del ranking final y la
            capa de priorización ejecutiva.
          </p>
          <div className="flex flex-wrap gap-2">
            <a href="/datos" className="btn-primary bg-white text-[var(--primary)] hover:bg-gray-100">Datos abiertos</a>
            <a href="/visor" className="btn-secondary border-white text-white hover:bg-white hover:text-[var(--primary)]">Visor cartográfico</a>
          </div>
        </div>
      </section>
    </>
  );
}
