"use client";
import { useState } from "react";
import { KB } from "@/data/kb";
import { Bot, Send, Sparkles, MessageCircle } from "lucide-react";

function scoreEntry(query: string, kb: typeof KB[number]) {
  const q = query.toLowerCase();
  const qWords = q.split(/\s+/).filter(w => w.length > 2);
  let score = 0;
  for (const w of qWords) {
    if (kb.q.toLowerCase().includes(w)) score += 3;
    if (kb.a.toLowerCase().includes(w)) score += 1;
    if (kb.tags.some(t => t.toLowerCase().includes(w))) score += 2;
  }
  return score;
}

function retrieveAnswer(query: string) {
  const ranked = KB.map(e => ({ e, s: scoreEntry(query, e) })).sort((a, b) => b.s - a.s);
  if (ranked[0].s === 0) {
    return {
      answer: "No encontré una respuesta específica para esa pregunta en el manuscrito. Puedes consultar los resultados en la página de Resultados, descargar los datos crudos desde Datos Abiertos, o leer el manuscrito completo en Zenodo. También puedes preguntar sobre: objetivos del estudio, metodología, Random Forest, Red Bayesiana, IR, cultivos específicos, escenarios SSP, limitaciones o datos climáticos BASD-CMIP6-PE.",
      sources: []
    };
  }
  const top = ranked.slice(0, 3).filter(r => r.s > 0);
  return {
    answer: top[0].e.a,
    sources: top.map(r => r.e.q)
  };
}

const SUGERENCIAS = [
  "¿Cuál es el hallazgo principal?",
  "¿Qué métricas tienen los modelos Random Forest?",
  "¿Cuáles son las parroquias prioritarias?",
  "¿Por qué la quinua es exploratoria?",
  "¿Cómo descargo los datos?",
  "¿Qué cultivo es más estable?",
];

interface Msg { role: "user" | "assistant"; text: string; sources?: string[]; }

export default function AsistentePage() {
  const [q, setQ] = useState("");
  const [chat, setChat] = useState<Msg[]>([{
    role: "assistant",
    text: "Hola. Soy el asistente del Geoportal Riesgo Agroclimático de Imbabura. Puedo responder preguntas sobre la metodología, los cultivos, los escenarios, los resultados o cómo acceder a los datos. Todas mis respuestas se basan en el manuscrito sometido a Natural Hazards (Pinto Páez 2026). ¿Qué deseas saber?"
  }]);

  function send(text: string) {
    if (!text.trim()) return;
    const userMsg: Msg = { role: "user", text };
    const { answer, sources } = retrieveAnswer(text);
    const botMsg: Msg = { role: "assistant", text: answer, sources };
    setChat(c => [...c, userMsg, botMsg]);
    setQ("");
  }

  return (
    <>
      <section className="bg-indigo-700 text-white py-14">
        <div className="container-prose">
          <div className="flex items-center gap-4">
            <Bot size={48} className="opacity-80"/>
            <div>
              <h1 className="text-white mb-2">Asistente IA del Geoportal</h1>
              <p className="text-xl opacity-90">Retrieval-Augmented Generation sobre el manuscrito sometido a Natural Hazards.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="container-prose py-10">
        <div className="max-w-3xl mx-auto">
          <div className="card p-0 overflow-hidden flex flex-col" style={{ minHeight: 500 }}>
            <div className="flex-1 p-5 space-y-4 overflow-y-auto max-h-[500px]">
              {chat.map((m, i) => (
                <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[85%] rounded-xl p-3 ${
                    m.role === "user" ? "bg-[var(--primary)] text-white" : "bg-[var(--bg)] text-[var(--text)]"
                  }`}>
                    {m.role === "assistant" && (
                      <div className="flex items-center gap-1 text-xs text-indigo-600 font-semibold mb-1">
                        <Sparkles size={12}/> Asistente
                      </div>
                    )}
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{m.text}</p>
                    {m.sources && m.sources.length > 0 && (
                      <div className="mt-2 text-xs opacity-70 border-t pt-2">
                        <strong>Preguntas relacionadas:</strong>
                        <ul className="list-disc list-inside mt-1">
                          {m.sources.slice(1).map((s, j) => (
                            <li key={j} className="cursor-pointer hover:underline" onClick={() => send(s)}>{s}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
            <div className="border-t border-[var(--border)] p-3 bg-white">
              <form onSubmit={e => { e.preventDefault(); send(q); }} className="flex gap-2">
                <input value={q} onChange={e => setQ(e.target.value)}
                  placeholder="Pregunta algo sobre el geoportal..."
                  className="flex-1 px-4 py-3 border border-[var(--border)] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"/>
                <button type="submit" className="bg-indigo-600 text-white p-3 rounded-lg hover:bg-indigo-700">
                  <Send size={18}/>
                </button>
              </form>
            </div>
          </div>

          <div className="mt-6">
            <h3 className="text-sm font-bold uppercase tracking-wider text-[var(--text-muted)] mb-3 flex items-center gap-2">
              <MessageCircle size={14}/> Preguntas sugeridas
            </h3>
            <div className="flex flex-wrap gap-2">
              {SUGERENCIAS.map(s => (
                <button key={s} onClick={() => send(s)}
                  className="text-sm border border-[var(--border)] rounded-full px-4 py-2 bg-white hover:bg-indigo-50 hover:border-indigo-300 transition">
                  {s}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-10 card bg-indigo-50 border-l-4 border-indigo-400">
            <h3 className="text-lg mb-2 flex items-center gap-2"><Sparkles size={18}/> Cómo funciona este asistente</h3>
            <p className="text-sm text-[var(--text-muted)] leading-relaxed">
              El asistente usa un sistema de <strong>Retrieval-Augmented Generation (RAG)</strong> sobre una base de conocimiento
              pre-indexada extraída del manuscrito. Cada respuesta se compone del fragmento del manuscrito con mayor score de
              similitud semántica a la pregunta, junto con preguntas relacionadas para profundizar.
            </p>
            <p className="text-sm text-[var(--text-muted)] leading-relaxed mt-2">
              En versiones posteriores se conectará con la <strong>API de Claude (Anthropic)</strong> con embeddings del manuscrito completo
              almacenados en <strong>Supabase + pgvector</strong>, para respuestas generativas contextualizadas a cualquier consulta natural.
            </p>
          </div>
        </div>
      </section>
    </>
  );
}
