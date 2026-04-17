"use client";
import { useState, useRef } from "react";
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

export default function RegisterGateLink({ href, fileName, tipo, className, ariaLabel, children }: Props) {
  const [open, setOpen] = useState(false);
  const linkRef = useRef<HTMLAnchorElement>(null);

  async function handleClick(e: React.MouseEvent) {
    e.preventDefault();
    const reg = getRegistro();
    if (reg) {
      // Registrar descarga (sin bloquear la descarga si el log falla)
      submitRegistro(reg, tipo, fileName).catch(() => {});
      triggerDownload();
      return;
    }
    setOpen(true);
  }

  function triggerDownload() {
    // Crea un enlace dinámico y fuerza la descarga
    const a = document.createElement("a");
    a.href = href;
    a.download = fileName;
    a.target = "_blank";
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  return (
    <>
      <a ref={linkRef} href={href} onClick={handleClick} className={className} aria-label={ariaLabel}>
        <Lock size={11} className="inline mr-0.5 opacity-70" aria-hidden="true"/>
        {children}
      </a>
      <RegisterModal
        open={open}
        onClose={() => setOpen(false)}
        onCompleted={() => { setOpen(false); triggerDownload(); }}
        pending={{ tipo, name: fileName }}
      />
    </>
  );
}
