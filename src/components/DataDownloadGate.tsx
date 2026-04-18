"use client";
import { useState } from "react";
import RegisterModal from "./RegisterModal";
import { getRegistro, submitRegistro } from "@/lib/registro";
import { Lock, Loader2, AlertCircle } from "lucide-react";

interface Props {
  /** URL de la que se descarga (GeoJSON, JSON, etc.). La respuesta se re-serializa formateada. */
  sourceUrl: string;
  /** Nombre de archivo final que verá el usuario. Incluya extensión: .geojson, .json, .md, etc. */
  fileName: string;
  /** Formato para el blob: geojson / json / md / csv. Controla cómo se formatea el contenido. */
  format?: "geojson" | "json" | "md" | "csv";
  /** MIME type (opcional, se infiere del format). */
  mimeType?: string;
  /** Tipo de descarga para tracking/registro. */
  tipo?: "geojson" | "script" | "ficha" | "api";
  className?: string;
  children: React.ReactNode;
  ariaLabel?: string;
  /** Título para la conversión Markdown. */
  mdTitle?: string;
}

function jsonToPretty(text: string): string {
  try { return JSON.stringify(JSON.parse(text), null, 2); } catch { return text; }
}

// Escapa un valor para tabla Markdown
function mdEscape(v: any): string {
  if (v == null) return "";
  let s = String(v);
  s = s.replace(/\r?\n/g, " ").replace(/\|/g, "\\|").replace(/\t/g, " ");
  return s.length > 80 ? s.slice(0, 80) + "…" : s;
}

function geojsonToMd(text: string, title: string): string {
  try {
    const gj = JSON.parse(text);
    const feats = gj.features || [];
    const lines: string[] = [];
    // Título
    lines.push(`# ${title}`, "");
    // Metadatos en formato simple (sin HTML, sin caracteres problemáticos)
    lines.push(`- Fuente: Geoportal Riesgo Agroclimatico — Imbabura · USGP 2026`);
    lines.push(`- Cita APA: Pinto Paez, V. H. (2026). Geoportal riesgo agroclimatico — Imbabura, Ecuador [Geoportal]. Zenodo. https://doi.org/10.5281/zenodo.19288559`);
    lines.push(`- Fecha de exportacion: ${new Date().toISOString()}`);
    lines.push(`- Registros: ${feats.length}`);
    lines.push(`- Licencia: CC BY 4.0`);
    lines.push("");
    // Tabla atributos (sin emojis ni caracteres Unicode raros)
    if (feats.length) {
      const cols = Object.keys(feats[0].properties || {});
      lines.push("| # | " + cols.join(" | ") + " |");
      lines.push("|---|" + cols.map(() => "---").join("|") + "|");
      feats.forEach((f: any, i: number) => {
        const row = cols.map(c => mdEscape(f.properties?.[c]));
        lines.push(`| ${i+1} | ${row.join(" | ")} |`);
      });
    } else {
      lines.push("_Sin registros._");
    }
    lines.push("");
    lines.push("Nota: el formato Markdown contiene solo atributos tabulados. Para geometrias completas descargue el GeoJSON.");
    return lines.join("\n");
  } catch {
    return `# ${title}\n\nError al procesar el contenido.\n`;
  }
}

function geojsonToCsv(text: string): string {
  try {
    const gj = JSON.parse(text);
    const feats = gj.features || [];
    if (!feats.length) return "\ufeff(Sin registros)\n";
    const cols = Object.keys(feats[0].properties || {});
    const esc = (v: any) => {
      if (v == null) return "";
      const s = String(v).replace(/"/g, '""');
      return /[,";\n\r]/.test(s) ? `"${s}"` : s;
    };
    const rows = [cols.join(",")];
    for (const f of feats) rows.push(cols.map(c => esc(f.properties?.[c])).join(","));
    return "\ufeff" + rows.join("\n"); // BOM para que Excel lo abra con UTF-8
  } catch {
    return "\ufeffError\n";
  }
}

export default function DataDownloadGate({
  sourceUrl, fileName, format = "geojson", mimeType,
  tipo = "geojson", className, children, ariaLabel, mdTitle,
}: Props) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function triggerDownload() {
    setErr(null); setBusy(true);
    try {
      const res = await fetch(sourceUrl);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const raw = await res.text();
      let content = raw;
      let mime = mimeType;
      if (format === "geojson") {
        content = jsonToPretty(raw);
        mime = mime || "application/geo+json";
      } else if (format === "json") {
        content = jsonToPretty(raw);
        mime = mime || "application/json";
      } else if (format === "md") {
        content = geojsonToMd(raw, mdTitle || fileName);
        mime = mime || "text/markdown; charset=utf-8";
      } else if (format === "csv") {
        content = geojsonToCsv(raw);
        mime = mime || "text/csv; charset=utf-8";
      }
      const blob = new Blob([content], { type: mime || "application/octet-stream" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = fileName;
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch (e: any) {
      setErr(`No se pudo descargar: ${e.message || e}`);
    } finally {
      setBusy(false);
    }
  }

  async function handleClick(e: React.MouseEvent) {
    e.preventDefault();
    const reg = getRegistro();
    if (reg) {
      // Ya registrado: registrar silenciosamente y descargar
      submitRegistro(reg, tipo, fileName).catch(() => {});
      await triggerDownload();
      return;
    }
    setOpen(true);
  }

  return (
    <>
      <button
        onClick={handleClick}
        disabled={busy}
        aria-label={ariaLabel}
        className={`${className || ""} ${busy ? "opacity-70 cursor-wait" : ""}`}
      >
        {busy ? <Loader2 size={14} className="inline animate-spin mr-1"/> : <Lock size={11} className="inline mr-0.5 opacity-70" aria-hidden="true"/>}
        {children}
      </button>
      {err && (
        <div className="text-xs text-red-600 mt-1 flex items-center gap-1">
          <AlertCircle size={12}/> {err}
        </div>
      )}
      <RegisterModal
        open={open}
        onClose={() => setOpen(false)}
        onCompleted={() => { setOpen(false); triggerDownload(); }}
        pending={{ tipo: tipo === "geojson" ? "script" : (tipo as any), name: fileName }}
      />
    </>
  );
}
