"use client";
import { useState } from "react";
import RegisterModal from "./RegisterModal";
import { getRegistro, submitRegistro } from "@/lib/registro";
import { Lock } from "lucide-react";

interface Props {
  href: string;
  fileName: string;
  tipo: "script" | "ficha";
  className?: string;
  ariaLabel?: string;
  children: React.ReactNode;
}

/**
 * - Primera descarga: abre modal COMPLETO de registro (nombre, email, ubicación, consentimiento).
 * - Descargas subsiguientes: descarga directa + registro silencioso en el Feature Service
 *   (mantiene email, ubicación y metadatos del usuario registrado).
 */
export default function RegisterGateLink({ href, fileName, tipo, className, ariaLabel, children }: Props) {
  const [registerOpen, setRegisterOpen] = useState(false);

  function triggerDownload() {
    const a = document.createElement("a");
    a.href = href; a.download = fileName; a.target = "_blank"; a.rel = "noopener";
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
  }

  async function handleClick(e: React.MouseEvent) {
    e.preventDefault();
    const reg = getRegistro();
    if (reg) {
      // Registrar silenciosamente esta descarga + seguir (NO molestar al usuario)
      submitRegistro(reg, tipo, fileName).catch(() => {});
      triggerDownload();
      return;
    }
    setRegisterOpen(true);
  }

  return (
    <>
      <a href={href} onClick={handleClick} className={className} aria-label={ariaLabel}>
        <Lock size={11} className="inline mr-0.5 opacity-70" aria-hidden="true"/>
        {children}
      </a>
      <RegisterModal
        open={registerOpen}
        onClose={() => setRegisterOpen(false)}
        onCompleted={() => { setRegisterOpen(false); triggerDownload(); }}
        pending={{ tipo, name: fileName }}
      />
    </>
  );
}
