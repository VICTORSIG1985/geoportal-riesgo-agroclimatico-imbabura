"use client";
import { useEffect, useMemo, useState } from "react";
import { KB, KB_CATEGORIES } from "@/data/kb";
import { Bot, Send, Sparkles, MessageCircle, Key, Lock, CheckCircle2, AlertCircle, Database, HelpCircle } from "lucide-react";
import PageHero from "@/components/PageHero";

function norm(s: string): string {
  return s.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

function tokenize(s: string): string[] {
  return norm(s).split(/[^a-z0-9ñ]+/).filter(w => w.length > 2);
}

function scoreEntry(queryTokens: string[], kb: typeof KB[number]): number {
  const qText = norm(kb.q);
  const aText = norm(kb.a);
  const tagsText = kb.tags.map(t => norm(t)).join(" ");
  let score = 0;
  for (const w of queryTokens) {
    if (qText.includes(w)) score += 5;
    if (tagsText.includes(w)) score += 3;
    if (aText.includes(w)) score += 1;
  }
  return score;
}

function retrieve(query: string, topK = 3) {
  const toks = tokenize(query);
  if (toks.length === 0) return [];
  const ranked = KB.map(e => ({ e, s: scoreEntry(toks, e) })).sort((a, b) => b.s - a.s);
  return ranked.filter(r => r.s >= 3).slice(0, topK);
}

const SYSTEM_PROMPT = `Eres el asistente científico del Geoportal Riesgo Agroclimático de Imbabura (Pinto Páez, 2026, USGP), manuscrito sometido a Natural Hazards (Springer). Respondes en español, con rigor académico y tono profesional. Tus respuestas se basan EXCLUSIVAMENTE en la información del manuscrito y del sistema. Si el contexto no contiene la respuesta, indica honestamente que no hay información y sugiere consultar la página Resultados o Datos Abiertos. Nunca inventes números ni referencias. Cita métricas textuales del manuscrito cuando estén disponibles.`;

async function askClaude(apiKey: string, model: string, query: string, context: typeof KB): Promise<string> {
  // Validación básica de la clave
  if (!apiKey || !apiKey.startsWith("sk-ant-")) {
    throw new Error("La clave de API no parece válida. Debe empezar con 'sk-ant-'. Obténgala en console.anthropic.com.");
  }

  const ctxText = context.map((c, i) => `[Fragmento ${i+1} · ${c.category}] ${c.q}\n${c.a}`).join("\n\n");
  const body = {
    model,
    max_tokens: 800,
    system: SYSTEM_PROMPT,
    messages: [
      { role: "user", content: `Contexto del manuscrito:\n\n${ctxText || "(sin contexto relevante)"}\n\nPregunta del usuario: ${query}\n\nResponde en español, citando datos específicos cuando existan en el contexto.` }
    ],
  };
  let res: Response;
  try {
    res = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
        "anthropic-dangerous-direct-browser-access": "true",
      },
      body: JSON.stringify(body),
    });
  } catch (netErr: any) {
    throw new Error(`No se pudo conectar con api.anthropic.com. Verifique su conexión a internet. (${netErr.message})`);
  }
  if (!res.ok) {
    const txt = await res.text();
    let detail = txt.slice(0, 300);
    try {
      const json = JSON.parse(txt);
      detail = json?.error?.message || detail;
    } catch {}
    if (res.status === 401) throw new Error(`Clave inválida o revocada. Revise console.anthropic.com.`);
    if (res.status === 429) throw new Error(`Límite de uso alcanzado o créditos insuficientes en su cuenta Anthropic.`);
    if (res.status === 400 && /model/i.test(detail)) throw new Error(`Modelo no disponible: ${model}. Pruebe con Haiku 4.5.`);
    throw new Error(`Claude API ${res.status}: ${detail}`);
  }
  const data = await res.json();
  // La respuesta puede tener múltiples bloques; concatenamos todos los de texto
  const blocks = Array.isArray(data?.content) ? data.content : [];
  const text = blocks.filter((b: any) => b?.type === "text").map((b: any) => b.text).join("\n").trim();
  return text || "(respuesta vacía — pruebe con otra pregunta o modelo)";
}

interface Msg {
  role: "user" | "assistant";
  text: string;
  related?: string[];
  provider?: "local" | "claude" | "nomatch";
  category?: string;
}

const NO_MATCH_LOCAL = `No encontré ninguna coincidencia para tu pregunta en la base de conocimiento local del geoportal.

El **modo local** responde solo a preguntas relacionadas con la investigación (objetivos, cultivos, escenarios climáticos, metodología, Red Bayesiana, Random Forest, resultados, exposición, fichas parroquiales, datos abiertos, limitaciones, reproducibilidad).

**Opciones:**
- Usa las **preguntas sugeridas** abajo, agrupadas por categoría.
- Configura tu **clave de Claude API** (arriba) para obtener respuestas generativas sobre cualquier tema del manuscrito.
- Consulta las secciones **Resultados**, **Metodología** o **Datos Abiertos** del geoportal.`;

export default function AsistentePage() {
  const [q, setQ] = useState("");
  const [chat, setChat] = useState<Msg[]>([{
    role: "assistant",
    provider: "local",
    text: `Hola. Soy el asistente del Geoportal Riesgo Agroclimático de Imbabura (Pinto Páez, 2026, USGP).

**Cómo funciono:**

🔹 **Modo local (por defecto):** respondo únicamente preguntas pre-indexadas sobre la investigación. Tengo ${KB.length} respuestas verificadas textualmente del manuscrito, organizadas en ${KB_CATEGORIES.length} categorías. Si preguntas algo fuera de la base, te lo indicaré.

🔹 **Modo Claude API (opcional):** si configuras tu clave de Anthropic, puedo responder preguntas libres usando los fragmentos como contexto. La clave se guarda solo en tu navegador.

Abajo tienes preguntas sugeridas por categoría para empezar.`
  }]);
  const [busy, setBusy] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("claude-haiku-4-5-20251001");
  const [showKeyUI, setShowKeyUI] = useState(false);
  const [keyStatus, setKeyStatus] = useState<"none" | "set" | "tested" | "failed">("none");
  const [filterCat, setFilterCat] = useState<string | null>(null);

  useEffect(() => {
    const k = typeof window !== "undefined" ? window.localStorage.getItem("geoportal_anthropic_key") : null;
    const m = typeof window !== "undefined" ? window.localStorage.getItem("geoportal_anthropic_model") : null;
    if (k) { setApiKey(k); setKeyStatus("set"); }
    if (m) setModel(m);
  }, []);

  const suggestedByCategory = useMemo(() => {
    const byCat: Record<string, typeof KB> = {};
    for (const e of KB) {
      const c = e.category || "Otros";
      (byCat[c] ||= []).push(e);
    }
    return byCat;
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

    const hits = retrieve(text, 3);

    // Modo Claude
    if (apiKey && keyStatus !== "failed") {
      try {
        const answer = await askClaude(apiKey, model, text, hits.map(h => h.e));
        setChat(c => [...c, { role: "assistant", text: answer, provider: "claude", related: hits.map(h => h.e.q) }]);
        setKeyStatus("tested");
      } catch (e: any) {
        setKeyStatus("failed");
        const fallback = hits[0]?.e.a || NO_MATCH_LOCAL;
        setChat(c => [...c, { role: "assistant", text: `⚠️ La llamada a Claude API falló (${e.message}). Respuesta del modo local:\n\n${fallback}`, provider: "local", related: hits.map(h => h.e.q) }]);
      } finally {
        setBusy(false);
      }
      return;
    }

    // Modo local estricto
    if (hits.length > 0) {
      const best = hits[0].e;
      setChat(c => [...c, {
        role: "assistant",
        text: best.a,
        provider: "local",
        category: best.category,
        related: hits.slice(1).map(h => h.e.q)
      }]);
    } else {
      setChat(c => [...c, { role: "assistant", text: NO_MATCH_LOCAL, provider: "nomatch" }]);
    }
    setBusy(false);
  }

  const categories = KB_CATEGORIES.filter(c => suggestedByCategory[c]?.length);
  const shownQuestions = filterCat ? (suggestedByCategory[filterCat] || []) : KB.slice(0, 12);

  return (
    <>
      <PageHero
        title="Asistente IA del Geoportal"
        subtitle="Respuestas basadas en el manuscrito sometido a Natural Hazards (Pinto Páez, 2026). Modo local con 30+ preguntas pre-indexadas o generación con Claude API."
        image="wm_cayambe.jpg"
        overlayColor="rgba(79,70,229,0.38)"
        credit="Imagen: Nevado Cayambe desde Imbabura — Wikimedia Commons · CC BY-SA"
      />

      <section className="container-prose py-10">
        <div className="max-w-3xl mx-auto">
          {/* Key config */}
          <div className="mb-5 card flex flex-wrap items-center gap-3">
            <Key size={18} className="text-indigo-600"/>
            <div className="text-sm flex-1">
              {keyStatus === "none" && <>Modo actual: <strong>búsqueda local</strong> ({KB.length} preguntas pre-indexadas).</>}
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
              <div className="flex items-center gap-2 mb-3 text-sm font-semibold"><Lock size={14}/> Configuración local (BYOK · Bring Your Own Key)</div>
              <p className="text-xs text-[var(--text-muted)] mb-3">
                La clave se guarda <strong>solo en tu navegador</strong> (localStorage), nunca se envía a nuestro servidor.
                Las peticiones van directo a <code>api.anthropic.com</code> desde tu browser. Obtén tu clave en{" "}
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
                  <div className={`max-w-[88%] rounded-xl p-3 ${
                    m.role === "user" ? "bg-[var(--primary)] text-white" : "bg-[var(--bg)] text-[var(--text)]"
                  }`}>
                    {m.role === "assistant" && (
                      <div className="flex items-center gap-1 text-xs font-semibold mb-1 flex-wrap">
                        <Sparkles size={12} className="text-indigo-600"/>
                        <span className="text-indigo-600">Asistente</span>
                        {m.provider === "claude" && <span className="bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded">Claude API</span>}
                        {m.provider === "local" && <span className="bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">Local RAG</span>}
                        {m.provider === "nomatch" && <span className="bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded">Sin coincidencia</span>}
                        {m.category && <span className="bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded">{m.category}</span>}
                      </div>
                    )}
                    <div className="text-sm leading-relaxed whitespace-pre-wrap">{m.text}</div>
                    {m.related && m.related.length > 0 && (
                      <div className="mt-2 text-xs opacity-70 border-t pt-2">
                        <strong>Relacionadas:</strong>
                        <ul className="mt-1 space-y-0.5">
                          {m.related.map((s, j) => (
                            <li key={j} className="cursor-pointer hover:underline flex items-start gap-1" onClick={() => send(s)}>
                              <span>→</span><span>{s}</span>
                            </li>
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
                  placeholder={apiKey ? "Pregunta lo que quieras sobre el geoportal o manuscrito..." : "Usa las preguntas sugeridas o pregunta sobre el manuscrito..."}
                  disabled={busy}
                  className="flex-1 px-4 py-3 border border-[var(--border)] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"/>
                <button type="submit" disabled={busy || !q.trim()} className="bg-indigo-600 text-white p-3 rounded-lg hover:bg-indigo-700 disabled:opacity-50" aria-label="enviar">
                  <Send size={18}/>
                </button>
              </form>
            </div>
          </div>

          {/* Explicación del modo local */}
          {!apiKey && (
            <div className="mt-5 card bg-amber-50 border-l-4 border-amber-400">
              <h3 className="text-sm font-bold mb-1 flex items-center gap-2"><HelpCircle size={14}/> ¿Por qué solo respuestas pre-indexadas?</h3>
              <p className="text-xs text-[var(--text-muted)] leading-relaxed">
                El modo local garantiza <strong>exactitud 100%</strong>: cada respuesta es texto literal verificado del manuscrito.
                Es adecuado para consultas frecuentes sobre metodología, resultados y datos. Si necesitas preguntas libres,
                configura tu clave de Claude API (arriba) para generación abierta con el manuscrito como contexto.
              </p>
            </div>
          )}

          {/* Preguntas sugeridas — selector de categoría */}
          <div className="mt-8">
            <h3 className="text-sm font-bold uppercase tracking-wider text-[var(--text-muted)] mb-3 flex items-center gap-2">
              <Database size={14}/> Preguntas pre-indexadas ({KB.length} disponibles)
            </h3>
            <div className="flex flex-wrap gap-2 mb-4">
              <button onClick={() => setFilterCat(null)}
                className={`text-xs px-3 py-1.5 rounded-full border ${filterCat===null?"bg-indigo-600 text-white border-indigo-600":"bg-white text-[var(--primary)] border-[var(--border)]"}`}>
                Todas
              </button>
              {categories.map(c => (
                <button key={c} onClick={() => setFilterCat(c)}
                  className={`text-xs px-3 py-1.5 rounded-full border ${filterCat===c?"bg-indigo-600 text-white border-indigo-600":"bg-white text-[var(--primary)] border-[var(--border)]"}`}>
                  {c} ({suggestedByCategory[c]?.length ?? 0})
                </button>
              ))}
            </div>
            <div className="grid md:grid-cols-2 gap-2">
              {shownQuestions.map((e, i) => (
                <button key={i} onClick={() => send(e.q)} disabled={busy}
                  className="text-left text-sm border border-[var(--border)] rounded-lg px-4 py-3 bg-white hover:bg-indigo-50 hover:border-indigo-300 transition disabled:opacity-50">
                  <div className="text-[10px] uppercase tracking-wider text-indigo-600 font-bold mb-0.5">{e.category}</div>
                  <div>{e.q}</div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
