"use client";
import Link from "next/link";
import { useState } from "react";
import { MENU, SITE } from "@/data/config";
import { Menu, X } from "lucide-react";

export default function Header() {
  const [open, setOpen] = useState(false);
  return (
    <header className="bg-[var(--primary)] text-white shadow-md sticky top-0 z-50">
      <div className="container-prose flex items-center justify-between py-3">
        <Link href="/" className="flex items-center gap-3 no-underline text-white">
          <img
            src={process.env.NEXT_PUBLIC_BASE_PATH ? `${process.env.NEXT_PUBLIC_BASE_PATH}/logo.png` : "/logo.png"}
            alt="Geoportal Riesgo Agroclimático — Logo"
            className="w-12 h-12 rounded-lg bg-white object-contain p-1"
          />
          <div className="leading-tight">
            <div className="text-lg font-bold">Geoportal Riesgo Agroclimático</div>
            <div className="text-xs opacity-80">{SITE.province} · USGP {SITE.year}</div>
          </div>
        </Link>
        <button className="md:hidden" onClick={() => setOpen(!open)} aria-label="menu">
          {open ? <X size={24}/> : <Menu size={24}/>}
        </button>
        <nav className="hidden md:flex gap-1 text-sm">
          {MENU.slice(0, 6).map(m => (
            <Link key={m.slug} href={m.slug} className="px-3 py-2 rounded hover:bg-white/10 text-white no-underline">{m.label}</Link>
          ))}
          <div className="relative group">
            <button className="px-3 py-2 rounded hover:bg-white/10">Más ▾</button>
            <div className="absolute right-0 top-full mt-1 w-56 bg-white text-[var(--text)] rounded shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition">
              {MENU.slice(6).map(m => (
                <Link key={m.slug} href={m.slug} className="block px-4 py-2 hover:bg-gray-50 no-underline text-[var(--text)]">{m.label}</Link>
              ))}
            </div>
          </div>
        </nav>
      </div>
      {open && (
        <nav className="md:hidden flex flex-col gap-1 bg-[var(--primary-dark)] px-4 pb-4">
          {MENU.map(m => (
            <Link key={m.slug} href={m.slug} onClick={() => setOpen(false)}
              className="px-3 py-2 text-sm text-white no-underline hover:bg-white/10 rounded">{m.label}</Link>
          ))}
        </nav>
      )}
    </header>
  );
}
