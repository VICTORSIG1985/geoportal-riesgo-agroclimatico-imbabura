"use client";
import { useState } from "react";
import RegisterModal from "./RegisterModal";
import LegalConfirmModal from "./LegalConfirmModal";
import { getRegistro, submitRegistro, RegistroLocal } from "@/lib/registro";
import { Lock } from "lucide-react";

interface Props {
  href: string;
  fileName: string;
  tipo: "script" | "ficha";
  className?: string;
  ariaLabel?: string;
  children: React.ReactNode;
}

export default function RegisterGateLink({ href, fileName, tipo, className, ariaLabel, children }: Props) {
  const [registerOpen, setRegisterOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [currentReg, setCurrentReg] = useState<RegistroLocal | null>(null);

  async function handleClick(e: React.MouseEvent) {
    e.preventDefault();
    const reg = getRegistro();
    if (reg) {
      // Ya registrado: mini-modal legal antes de cada descarga
      setCurrentReg(reg);
      setConfirmOpen(true);
      return;
    }
    // Primera vez: modal completo de registro
    setRegisterOpen(true);
  }

  function acceptAndDownload(reg: RegistroLocal) {
    submitRegistro(reg, tipo, fileName).catch(() => {});
    setConfirmOpen(false);
    triggerDownload();
  }

  function triggerDownload() {
    const a = document.createElement("a");
    a.href = href; a.download = fileName; a.target = "_blank"; a.rel = "noopener";
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
  }

  return (
    <>
      <a href={href} onClick={handleClick} className={className} aria-label={ariaLabel}>
        <Lock size={11} className="inline mr-0.5 opacity-70" aria-hidden="true"/>
        {children}
      </a>
      {/* Modal COMPLETO: primera vez */}
      <RegisterModal
        open={registerOpen}
        onClose={() => setRegisterOpen(false)}
        onCompleted={() => { setRegisterOpen(false); triggerDownload(); }}
        pending={{ tipo, name: fileName }}
      />
      {/* Mini-modal LEGAL: cada descarga posterior */}
      {currentReg && (
        <LegalConfirmModal
          open={confirmOpen}
          onCancel={() => setConfirmOpen(false)}
          onAccept={() => acceptAndDownload(currentReg)}
          fileName={fileName}
          tipo={tipo === "ficha" ? "Ficha parroquial PDF" : "Script Python"}
          registroEmail={currentReg.email}
        />
      )}
    </>
  );
}
