"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { MENU, SITE } from "@/data/config";
import { Menu, X, ChevronDown } from "lucide-react";
import { asset } from "@/lib/assets";

function isActive(currentPath: string, slug: string): boolean {
  if (slug === "/") return currentPath === "/" || currentPath === "";
  return currentPath === slug || currentPath.startsWith(slug + "/");
}

const LINK_INACTIVE: React.CSSProperties = { color: "#ffffff" };
const LINK_ACTIVE:   React.CSSProperties = { background: "#ffffff", color: "#0F4C81", fontWeight: 800, boxShadow: "0 2px 6px rgba(0,0,0,0.2)" };

export default function Header() {
  const [open, setOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const closeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const rawPath = usePathname() || "/";
  const base = process.env.NEXT_PUBLIC_BASE_PATH || "";
  const pathname = base && rawPath.startsWith(base) ? rawPath.slice(base.length) || "/" : rawPath;

  const primary = MENU.slice(0, 6);
  const secondary = MENU.slice(6);
  const moreActive = secondary.some(m => isActive(pathname, m.slug));

  // Cerrar con retardo para permitir mover el mouse del botón al panel
  function scheduleClose() {
    if (closeTimerRef.current) clearTimeout(closeTimerRef.current);
    closeTimerRef.current = setTimeout(() => setMoreOpen(false), 350);
  }
  function cancelClose() {
    if (closeTimerRef.current) { clearTimeout(closeTimerRef.current); closeTimerRef.current = null; }
  }
  function openMore() { cancelClose(); setMoreOpen(true); }

  // Cerrar el panel al cambiar de ruta
  useEffect(() => { setMoreOpen(false); setOpen(false); }, [pathname]);

  // Cerrar al hacer clic fuera o presionar Escape
  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      const t = e.target as HTMLElement;
      if (!t.closest("[data-menu-more]")) setMoreOpen(false);
    }
    function onKey(e: KeyboardEvent) { if (e.key === "Escape") setMoreOpen(false); }
    document.addEventListener("click", onDocClick);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("click", onDocClick); document.removeEventListener("keydown", onKey); };
  }, []);

  return (
    <header className="bg-[var(--primary)] text-white shadow-md sticky top-0 z-50">
      <div className="container-prose flex items-center justify-between py-3">
        <Link href="/" className="flex items-center gap-3 no-underline" style={{ color: "#fff" }}>
          <img
            src={asset("/logo.png")}
            alt="Geoportal Riesgo Agroclimático — Logo"
            className="w-12 h-12 rounded-lg bg-white object-contain p-1 flex-shrink-0"
          />
          <div className="leading-tight">
            <div className="text-lg font-bold">Geoportal Riesgo Agroclimático</div>
            <div className="text-xs opacity-80">{SITE.province} · USGP {SITE.year}</div>
          </div>
        </Link>
        <button className="md:hidden text-white" onClick={() => setOpen(!open)} aria-label="menu">
          {open ? <X size={24}/> : <Menu size={24}/>}
        </button>
        <nav className="hidden md:flex gap-1 text-sm items-center">
          {primary.map(m => {
            const active = isActive(pathname, m.slug);
            return (
              <Link key={m.slug} href={m.slug}
                aria-current={active ? "page" : undefined}
                style={active ? LINK_ACTIVE : LINK_INACTIVE}
                className={`px-3 py-2 rounded no-underline transition ${active ? "" : "hover:bg-white/15"}`}>
                {m.label}
              </Link>
            );
          })}
          <div className="relative" data-menu-more onMouseEnter={openMore} onMouseLeave={scheduleClose}>
            <button
              type="button"
              aria-haspopup="true"
              aria-expanded={moreOpen}
              onClick={() => setMoreOpen(v => !v)}
              onFocus={openMore}
              style={moreActive ? LINK_ACTIVE : LINK_INACTIVE}
              className={`px-3 py-2 rounded no-underline transition inline-flex items-center gap-1 ${moreActive ? "" : "hover:bg-white/15"}`}>
              Más <ChevronDown size={14} className={`transition-transform ${moreOpen ? "rotate-180" : ""}`}/>
            </button>
            {/* Puente invisible entre botón y panel para que el mouse no pierda el hover */}
            {moreOpen && <div className="absolute right-0 top-full h-2 w-60" aria-hidden="true"/>}
            <div
              onMouseEnter={openMore}
              onMouseLeave={scheduleClose}
              className={`absolute right-0 mt-2 w-60 bg-white rounded shadow-xl transition-opacity duration-150 ${
                moreOpen ? "opacity-100 visible pointer-events-auto" : "opacity-0 invisible pointer-events-none"
              }`}
              style={{ color: "#1A202C", top: "100%" }}
              role="menu">
              {secondary.map(m => {
                const active = isActive(pathname, m.slug);
                return (
                  <Link key={m.slug} href={m.slug}
                    aria-current={active ? "page" : undefined}
                    style={active ? { color: "#0F4C81", fontWeight: 700, background: "#F7FAFC", borderLeft: "4px solid #0F4C81" } : { color: "#1A202C", borderLeft: "4px solid transparent" }}
                    className={`block px-4 py-2.5 no-underline ${active ? "" : "hover:bg-gray-50"}`}
                    role="menuitem"
                    onClick={() => setMoreOpen(false)}>
                    {m.label}
                  </Link>
                );
              })}
            </div>
          </div>
        </nav>
      </div>
      {open && (
        <nav className="md:hidden flex flex-col gap-1 bg-[var(--primary-dark)] px-4 pb-4">
          {MENU.map(m => {
            const active = isActive(pathname, m.slug);
            return (
              <Link key={m.slug} href={m.slug} onClick={() => setOpen(false)}
                aria-current={active ? "page" : undefined}
                style={active ? LINK_ACTIVE : LINK_INACTIVE}
                className={`px-3 py-2 text-sm no-underline rounded ${active ? "" : "hover:bg-white/15"}`}>
                {m.label}
              </Link>
            );
          })}
        </nav>
      )}
    </header>
  );
}
