"use client";
import { useEffect, useState } from "react";
import { KB } from "@/data/kb";
import { Bot, Send, Sparkles, MessageCircle, Key, Lock, CheckCircle2, AlertCircle } from "lucide-react";

// RAG offline (fallback)
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
function retrieveContext(query: string, topK = 3) {
  const ranked = KB.map(e => ({ e, s: scoreEntry(query, e) })).sort((a, b) => b.s - a.s);
  return ranked.slice(0, topK).filter(r => r.s > 0).map(r => r.e);
}

interface Msg { role: "user" | "assistant"; text: string; sources?: string[]; provider?: "local" | "claude"; }

const SUGERENCIAS = [
  "¿Cuál es el hallazgo principal?",
  "¿Qué métricas tienen los modelos Random Forest?",
  "¿Cuáles son las parroquias prioritarias?",
  "¿Por qué la quinua es exploratoria?",
  "¿Cómo descargo los datos?",
  "¿Qué cultivo es más estable?",
];

const SYSTEM_PROMPT = `Eres el asistente científico del Geoportal Riesgo Agroclimático de Imbabura (Pinto Páez, 2026, USGP), manuscrito sometido a Natural Hazards (Springer). Respondes en español, con rigor académico y tono profesional. Tus respuestas se basan EXCLUSIVAMENTE en la información del manuscrito y del sistema. Si el contexto no contiene la respuesta, indica honestamente que no hay información y sugiere consultar la página Resultados o Datos Abiertos. Nunca inventes números ni referencias. Cita métricas textuales del manuscrito cuando estén disponibles.`;

async function askClaude(apiKey: string, model: string, query: string, context: typeof KB): Promise<string> {
  const ctxText = context.map((c, i) => `[Fragmento ${i+1}] ${c.q}\n${c.a}`).join("\n\n");
  const body = {
    model,
    max_tokens: 800,
    system: SYSTEM_PROMPT,
    messages: [
      { role: "user", content: `Contexto extraído de la base de conocimiento del manuscrito:\n\n${ctxText}\n\nPregunta del usuario: ${query}\n\nResponde en español, citando datos específicos cuando existan.` }
    ],
  };
  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
      "anthropic-dangerous-direct-browser-access": "true",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(`Claude API ${res.status}: ${t.slice(0, 200)}`);
  }
  const data = await res.json();
  return data.content?.[0]?.text || "(respuesta vacía)";
}

export default function AsistentePage() {
  const [q, setQ] = useState("");
  const [chat, setChat] = useState<Msg[]>([{
    role: "assistant",
    provider: "local",
    text: "Hola. Soy el asistente del Geoportal Riesgo Agroclimático de Imbabura. Respondo preguntas sobre la metodología, los cultivos, los escenarios, los resultados o cómo acceder a los datos. Todas mis respuestas se basan en el manuscrito sometido a Natural Hazards (Pinto Páez, 2026). Puedo responder en dos modos: (a) búsqueda local sobre 14 fragmentos pre-indexados (sin configuración, siempre disponible), o (b) generación con Claude API si configura su propia clave."
  }]);
  const [busy, setBusy] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("claude-haiku-4-5-20251001");
  const [showKeyUI, setShowKeyUI] = useState(false);
  const [keyStatus, setKeyStatus] = useState<"none" | "set" | "tested" | "failed">("none");

  useEffect(() => {
    const k = typeof window !== "undefined" ? window.localStorage.getItem("geoportal_anthropic_key") : null;
    const m = typeof window !== "undefined" ? window.localStorage.getItem("geoportal_anthropic_model") : null;
    if (k) { setApiKey(k); setKeyStatus("set"); }
    if (m) setModel(m);
  }, []);

  function saveKey() {
    window.localStorage.setItem("geoportal_anthropic_key", apiKey);
    window.localStorage.setItem("geoportal_anthropic_model", model);
    setKeyStatus(apiKey ? "set" : "none");
    setShowKeyUI(false);
  }
  function clearKey() {
    window.localStorage.removeItem("geoportal_anthropic_key");
    setApiKey(""); setKeyStatus("none");
  }

  async function send(text: string) {
    if (!text.trim() || busy) return;
    const userMsg: Msg = { role: "user", text };
    setChat(c => [...c, userMsg]);
    setQ("");
    setBusy(true);

    const ctx = retrieveContext(text, 3);

    if (apiKey && keyStatus !== "failed") {
      try {
        const answer = await askClaude(apiKey, model, text, ctx);
        setChat(c => [...c, { role: "assistant", text: answer, provider: "claude", sources: ctx.map(s => s.q) }]);
        setKeyStatus("tested");
      } catch (e: any) {
        setKeyStatus("failed");
        const fallback = ctx[0]?.a || "No hay coincidencias en la base de conocimiento local y la llamada a Claude falló. Consulte /resultados o /datos.";
        setChat(c => [...c, { role: "assistant", text: `⚠️ Claude API falló (${e.message}). Respuesta local:\n\n${fallback}`, provider: "local", sources: ctx.map(s => s.q) }]);
      } finally {
        setBusy(false);
      }
    } else {
      // Fallback: búsqueda local
      const answer = ctx[0]?.a || "No encontré una respuesta específica en la base de conocimiento. Puede revisar Resultados o Datos Abiertos. También puede configurar su clave de Claude (arriba) para respuestas generativas sobre cualquier tema del manuscrito.";
      setChat(c => [...c, { role: "assistant", text: answer, provider: "local", sources: ctx.map(s => s.q) }]);
      setBusy(false);
    }
  }

  return (
    <>
      <section className="bg-indigo-700 text-white py-14">
        <div className="container-prose">
          <div className="flex items-center gap-4">
            <Bot size={48} className="opacity-80"/>
            <div>
              <h1 className="text-white mb-2">Asistente IA del Geoportal</h1>
              <p className="text-xl opacity-90">Respuestas basadas en el manuscrito sometido a <em>Natural Hazards</em> (Pinto Páez, 2026).</p>
            </div>
          </div>
        </div>
      </section>

      <section className="container-prose py-10">
        <div className="max-w-3xl mx-auto">
          {/* Key config */}
          <div className="mb-5 card flex flex-wrap items-center gap-3">
            <Key size={18} className="text-indigo-600"/>
            <div className="text-sm flex-1">
              {keyStatus === "none" && <>Modo actual: <strong>búsqueda local</strong> (14 fragmentos pre-indexados).</>}
              {keyStatus === "set" && <>Modo: <strong>Claude API</strong> configurada. Listo para usar.</>}
              {keyStatus === "tested" && <><CheckCircle2 size={14} className="inline text-green-600"/> Claude respondiendo correctamente.</>}
              {keyStatus === "failed" && <><AlertCircle size={14} className="inline text-red-600"/> Claude falló — volviendo a modo local.</>}
            </div>
            <button onClick={() => setShowKeyUI(!showKeyUI)} className="btn-secondary text-sm">
              {apiKey ? "Cambiar clave" : "Configurar Claude API"}
            </button>
            {apiKey && <button onClick={clearKey} className="text-xs text-red-600 underline">Eliminar</button>}
          </div>
          {showKeyUI && (
            <div className="mb-5 card border-2 border-indigo-300 bg-indigo-50">
              <div className="flex items-center gap-2 mb-3 text-sm font-semibold"><Lock size={14}/> Configuración local (BYOK)</div>
              <p className="text-xs text-[var(--text-muted)] mb-3">
                La clave se guarda <strong>solo en tu navegador</strong> (localStorage), nunca se envía a nuestro servidor.
                Las peticiones van directo a <code>api.anthropic.com</code> desde tu browser. Obtén tu clave en {" "}
                <a href="https://console.anthropic.com/" target="_blank" rel="noopener" className="text-indigo-600 underline">console.anthropic.com</a>.
              </p>
              <div className="grid gap-3 text-sm">
                <label>
                  <span className="text-xs text-[var(--text-muted)] block mb-1">Anthropic API key</span>
                  <input type="password" value={apiKey} onChange={e => setApiKey(e.target.value)} placeholder="sk-ant-..."
                    className="w-full px-3 py-2 border border-[var(--border)] rounded text-sm font-mono"/>
                </label>
                <label>
                  <span className="text-xs text-[var(--text-muted)] block mb-1">Modelo</span>
                  <select value={model} onChange={e => setModel(e.target.value)} className="w-full px-3 py-2 border border-[var(--border)] rounded text-sm">
                    <option value="claude-haiku-4-5-20251001">Haiku 4.5 (rápido, económico)</option>
                    <option value="claude-sonnet-4-6">Sonnet 4.6 (balance)</option>
                    <option value="claude-opus-4-7">Opus 4.7 (máxima calidad)</option>
                  </select>
                </label>
                <div className="flex gap-2">
                  <button onClick={saveKey} className="btn-primary text-sm">Guardar localmente</button>
                  <button onClick={() => setShowKeyUI(false)} className="btn-secondary text-sm">Cancelar</button>
                </div>
              </div>
            </div>
          )}

          {/* Chat */}
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
                        {m.provider === "claude" && <span className="ml-2 bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded">Claude</span>}
                        {m.provider === "local" && <span className="ml-2 bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">Local RAG</span>}
                      </div>
                    )}
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{m.text}</p>
                    {m.sources && m.sources.length > 1 && (
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
              {busy && (
                <div className="flex justify-start">
                  <div className="bg-[var(--bg)] rounded-xl p-3 text-sm text-[var(--text-muted)] italic">pensando…</div>
                </div>
              )}
            </div>
            <div className="border-t border-[var(--border)] p-3 bg-white">
              <form onSubmit={e => { e.preventDefault(); send(q); }} className="flex gap-2">
                <input value={q} onChange={e => setQ(e.target.value)}
                  placeholder="Pregunta algo sobre el geoportal..." disabled={busy}
                  className="flex-1 px-4 py-3 border border-[var(--border)] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"/>
                <button type="submit" disabled={busy || !q.trim()} className="bg-indigo-600 text-white p-3 rounded-lg hover:bg-indigo-700 disabled:opacity-50">
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
                <button key={s} onClick={() => send(s)} disabled={busy}
                  className="text-sm border border-[var(--border)] rounded-full px-4 py-2 bg-white hover:bg-indigo-50 hover:border-indigo-300 transition disabled:opacity-50">
                  {s}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
