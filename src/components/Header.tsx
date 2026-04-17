"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { MENU, SITE } from "@/data/config";
import { Menu, X, ChevronDown } from "lucide-react";
import { asset } from "@/lib/assets";

function isActive(currentPath: string, slug: string): boolean {
  if (slug === "/") return currentPath === "/" || currentPath === "";
  return currentPath === slug || currentPath.startsWith(slug + "/");
}

// Estilos literales (evita resolver problemas de custom properties sobre clases dinámicas)
const LINK_INACTIVE: React.CSSProperties = { color: "#ffffff" };
const LINK_ACTIVE:   React.CSSProperties = { background: "#ffffff", color: "#0F4C81", fontWeight: 800, boxShadow: "0 2px 6px rgba(0,0,0,0.2)" };

export default function Header() {
  const [open, setOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const rawPath = usePathname() || "/";
  const base = process.env.NEXT_PUBLIC_BASE_PATH || "";
  const pathname = base && rawPath.startsWith(base) ? rawPath.slice(base.length) || "/" : rawPath;

  const primary = MENU.slice(0, 6);
  const secondary = MENU.slice(6);
  const moreActive = secondary.some(m => isActive(pathname, m.slug));

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
          <div className="relative" onMouseEnter={() => setMoreOpen(true)} onMouseLeave={() => setMoreOpen(false)}>
            <button
              style={moreActive ? LINK_ACTIVE : LINK_INACTIVE}
              className={`px-3 py-2 rounded no-underline transition inline-flex items-center gap-1 ${moreActive ? "" : "hover:bg-white/15"}`}>
              Más <ChevronDown size={14}/>
            </button>
            <div className={`absolute right-0 top-full mt-1 w-60 bg-white rounded shadow-xl transition ${moreOpen ? "opacity-100 visible" : "opacity-0 invisible"}`}
              style={{ color: "#1A202C" }}>
              {secondary.map(m => {
                const active = isActive(pathname, m.slug);
                return (
                  <Link key={m.slug} href={m.slug}
                    aria-current={active ? "page" : undefined}
                    style={active ? { color: "#0F4C81", fontWeight: 700, background: "#F7FAFC", borderLeft: "4px solid #0F4C81" } : { color: "#1A202C", borderLeft: "4px solid transparent" }}
                    className={`block px-4 py-2 no-underline ${active ? "" : "hover:bg-gray-50"}`}>
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
