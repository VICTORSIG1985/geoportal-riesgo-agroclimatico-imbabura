import Link from "next/link";
import { SITE, MENU } from "@/data/config";

export default function Footer() {
  return (
    <footer className="bg-[var(--primary-dark)] text-white mt-16">
      <div className="container-prose py-10 grid md:grid-cols-4 gap-8 text-sm">
        <div className="md:col-span-2">
          <h3 className="text-lg font-bold mb-3">{SITE.title}</h3>
          <p className="opacity-90 leading-relaxed">
            Portal de acceso al resultado de la investigación de Maestría en Prevención y Gestión
            de Riesgos (USGP 2026) sobre el riesgo agroclimático de cultivos andinos en las 42 parroquias de
            Imbabura bajo escenarios CMIP6.
          </p>
          <p className="mt-3 opacity-80 text-xs">
            DOI: <a href={`https://doi.org/${SITE.doi}`} target="_blank" className="underline text-white">{SITE.doi}</a>
          </p>
        </div>
        <div>
          <h4 className="font-bold mb-3 uppercase tracking-wider text-xs opacity-80">Navegación</h4>
          <ul className="space-y-1">
            {MENU.map(m => (
              <li key={m.slug}>
                <Link href={m.slug} className="text-white/90 hover:text-white no-underline">{m.label}</Link>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h4 className="font-bold mb-3 uppercase tracking-wider text-xs opacity-80">Contacto</h4>
          <ul className="space-y-2 opacity-90">
            <li><strong>{SITE.author}</strong></li>
            <li>{SITE.institution}</li>
            <li className="text-xs">{SITE.program}</li>
            <li>📧 <a href={`mailto:${SITE.email}`} className="text-white underline">{SITE.email}</a></li>
            <li>🆔 ORCID <a href={`https://orcid.org/${SITE.orcid}`} target="_blank" className="text-white underline">{SITE.orcid}</a></li>
            <li>💻 GitHub <a href={`https://github.com/${SITE.githubUser}`} target="_blank" className="text-white underline">{SITE.githubUser}</a></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-white/10 py-4 text-center text-xs opacity-70">
        © {SITE.year} {SITE.author} · {SITE.institution} · Licencia CC BY 4.0 · Datos en ArcGIS Online ({SITE.arcgisOrg})
      </div>
    </footer>
  );
}
