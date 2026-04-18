"use client";
import { useState } from "react";
import { AVISO_LEGAL_V1, CONSENT_VERSION, getRegistro, submitRegistro, setRegistro, uuid, isValidEmail } from "@/lib/registro";
import { X, Mail, Shield, Loader2, AlertCircle, ExternalLink } from "lucide-react";

interface Props {
  href: string;
  className?: string;
  children: React.ReactNode;
  // etiqueta humana para el tracking
  label?: string;
}

/**
 * Enlace externo con exit-intent:
 * - Si el usuario ya se registró, abre directo.
 * - Si no se registró, abre modal ligero que pide solo email + consentimiento
 *   (uso del geoportal sin descarga, conforme LOPDP Ecuador).
 */
export default function ExternalLinkGate({ href, className, children, label }: Props) {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  function proceed() {
    window.open(href, "_blank", "noopener");
  }

  function handleClick(e: React.MouseEvent) {
    e.preventDefault();
    const reg = getRegistro();
    if (reg) {
      submitRegistro(reg, "api", label || href).catch(() => {});
      proceed();
      return;
    }
    setOpen(true);
  }

  async function submit() {
    setErr(null);
    if (!isValidEmail(email)) { setErr("Correo electrónico no válido."); return; }
    if (!consent) { setErr("Debe aceptar el aviso de privacidad para continuar."); return; }
    setBusy(true);
    const reg = {
      nombre: "Uso del geoportal (solo navegación)",
      email: email.trim().toLowerCase(),
      lat: 0, lon: 0, // sin geolocalización
      ubicacion_texto: "No declarada",
      pais: "",
      session_token: uuid(),
      consentimiento_v: CONSENT_VERSION,
      fecha_registro: Date.now(),
    };
    const ok = await submitRegistro(reg, "api", label || href);
    setBusy(false);
    if (!ok) { setErr("No se pudo enviar el registro. Intente nuevamente."); return; }
    setRegistro(reg);
    setOpen(false);
    proceed();
  }

  return (
    <>
      <a href={href} onClick={handleClick} className={className} rel="noopener">
        {children}
      </a>
      {open && (
        <div className="fixed inset-0 bg-black/60 z-[100] flex items-center justify-center p-4" onClick={() => setOpen(false)}>
          <div className="bg-white rounded-xl max-w-md w-full overflow-hidden" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b bg-[var(--primary)] text-white">
              <div className="flex items-center gap-2">
                <Shield size={18}/>
                <div>
                  <h3 className="text-white text-base mb-0">Uso del geoportal</h3>
                  <div className="text-[11px] opacity-85">Aviso LOPDP · Versión {CONSENT_VERSION}</div>
                </div>
              </div>
              <button onClick={() => setOpen(false)} className="text-white/80 hover:text-white"><X size={18}/></button>
            </div>
            <div className="p-5 space-y-4 text-sm">
              <div className="bg-indigo-50 border-l-4 border-indigo-400 p-3 rounded-r text-xs">
                Para salir del geoportal o abrir un recurso externo (Zenodo, GitHub), le pedimos
                <strong> solo su correo electrónico</strong> con fines estadísticos y de mejora del servicio,
                conforme a la <strong>Ley Orgánica de Protección de Datos Personales</strong> del Ecuador.
                No recopilamos ubicación. Puede rechazar y continuar navegando el geoportal.
              </div>

              <label className="block">
                <span className="text-xs uppercase tracking-wider text-[var(--text-muted)] font-semibold flex items-center gap-1"><Mail size={12}/> Correo electrónico *</span>
                <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                  autoComplete="email" placeholder="ejemplo@institucion.ec"
                  className="mt-1 w-full px-3 py-2 border border-[var(--border)] rounded text-sm"/>
              </label>

              <details className="border border-[var(--border)] rounded text-xs">
                <summary className="px-3 py-2 cursor-pointer bg-[var(--bg)] font-semibold">Leer aviso legal completo (LOPDP)</summary>
                <div className="p-3 whitespace-pre-wrap text-[var(--text-muted)] max-h-40 overflow-y-auto">{AVISO_LEGAL_V1}</div>
              </details>

              <label className="flex items-start gap-2 text-xs cursor-pointer">
                <input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} className="mt-0.5"/>
                <span>
                  Acepto el tratamiento de mi correo para fines estadísticos del geoportal bajo la LOPDP,
                  versión {CONSENT_VERSION}.
                </span>
              </label>

              {err && <div className="text-xs text-red-600 flex items-center gap-1"><AlertCircle size={12}/> {err}</div>}

              <div className="flex justify-between gap-2">
                <button onClick={() => setOpen(false)} className="text-xs text-[var(--text-muted)] underline">No acepto, volver</button>
                <button onClick={submit} disabled={busy}
                  className="inline-flex items-center gap-1 bg-[var(--primary)] text-white px-4 py-2 rounded text-sm font-semibold hover:bg-[var(--primary-dark)] disabled:opacity-50">
                  {busy ? <Loader2 size={14} className="animate-spin"/> : <ExternalLink size={14}/>}
                  Aceptar y abrir
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
