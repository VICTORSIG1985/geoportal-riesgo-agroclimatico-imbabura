"use client";
import { CONSENT_VERSION } from "@/lib/registro";
import { Shield, X, CheckCircle2 } from "lucide-react";

interface Props {
  open: boolean;
  onCancel: () => void;
  onAccept: () => void;
  fileName: string;
  tipo: string;
  registroEmail?: string;
}

/**
 * Mini-modal de confirmación legal antes de cada descarga cuando el usuario
 * ya tiene un registro activo. Recuerda el tratamiento LOPDP por cada acción.
 */
export default function LegalConfirmModal({ open, onCancel, onAccept, fileName, tipo, registroEmail }: Props) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-black/60 z-[110] flex items-center justify-center p-4" onClick={onCancel}>
      <div className="bg-white rounded-xl max-w-md w-full overflow-hidden" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between p-3 border-b bg-[var(--primary)] text-white">
          <div className="flex items-center gap-2">
            <Shield size={16}/>
            <h3 className="text-white text-base mb-0">Confirmar descarga</h3>
          </div>
          <button onClick={onCancel} className="text-white/80 hover:text-white"><X size={18}/></button>
        </div>
        <div className="p-5 space-y-3 text-sm">
          <p>
            Va a descargar <strong className="break-words">{fileName}</strong> ({tipo}).
          </p>
          <div className="bg-indigo-50 border-l-4 border-indigo-400 p-3 rounded-r text-xs">
            Conforme a la <strong>Ley Orgánica de Protección de Datos Personales</strong> del Ecuador, esta acción queda
            <strong> registrada</strong> en la base de datos institucional del geoportal con fines estadísticos y de mejora del
            servicio. Se guardarán: su identidad registrada {registroEmail ? <>(<code className="text-[11px]">{registroEmail}</code>)</> : null},
            la ubicación indicada al registrarse, el archivo descargado y la fecha.
            <br/><br/>
            Aviso vigente: versión <strong>{CONSENT_VERSION}</strong>.
          </div>
          <p className="text-xs text-[var(--text-muted)]">
            Puede retirar su consentimiento en cualquier momento escribiendo al responsable del tratamiento
            (sección <em>Acerca</em>).
          </p>
          <div className="flex justify-between gap-2 pt-2">
            <button onClick={onCancel} className="text-sm text-[var(--text-muted)] underline">Cancelar</button>
            <button onClick={onAccept}
              className="inline-flex items-center gap-1 bg-[var(--primary)] text-white px-4 py-2 rounded text-sm font-semibold hover:bg-[var(--primary-dark)]">
              <CheckCircle2 size={14}/> Aceptar y descargar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
