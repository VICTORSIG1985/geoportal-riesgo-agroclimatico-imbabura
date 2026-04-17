import Link from "next/link";
import { SITE } from "@/data/config";
import { Map, Image as ImgIcon, FileText, Database, Bot, BookOpen, Microscope, BarChart3, Info, ArrowRight } from "lucide-react";

const services = [
  { href: "/visor", icon: Map, color: "#B2182B", title: "Visor Cartográfico", desc: "Mapa interactivo con 3 capas, filtros por cultivo × SSP × horizonte, popups con descarga de fichas." },
  { href: "/galeria", icon: ImgIcon, color: "#0F4C81", title: "Galería Científica", desc: "60 figuras organizadas por grupo temático: síntesis, paneles, cambio temporal, infografías." },
  { href: "/fichas", icon: FileText, color: "#228B6E", title: "Fichas Parroquiales", desc: "42 PDFs públicos con IR por escenario, cultivo más vulnerable y recomendación operativa." },
  { href: "/metodologia", icon: Microscope, color: "#6B4E9B", title: "Metodología", desc: "Pipeline de 22 scripts Python en 5 fases, Random Forest + Red Bayesiana, métricas de desempeño." },
  { href: "/resultados", icon: BarChart3, color: "#EF8A62", title: "Resultados Interactivos", desc: "Ranking parroquial dinámico, IR por cultivo/SSP/horizonte, tablas y gráficos del manuscrito." },
  { href: "/datos", icon: Database, color: "#333333", title: "Datos Abiertos", desc: "3 Feature Services REST públicos, metadatos ISO 19115, código Python y DOI Zenodo." },
  { href: "/asistente", icon: Bot, color: "#4F46E5", title: "Asistente IA", desc: "Consulta en lenguaje natural sobre metodología y resultados. Retrieval sobre manuscrito (RAG)." },
  { href: "/acerca", icon: Info, color: "#4A5568", title: "Acerca del Geoportal", desc: "Autor, institución, cita sugerida, manuscrito de referencia, licencia y contacto." },
];

const stats = [
  { value: "42", label: "Parroquias" },
  { value: "4", label: "Cultivos andinos" },
  { value: "1.512", label: "Inferencias IR" },
  { value: "60", label: "Productos cartográficos" },
  { value: "9", label: "Escenarios SSP×Horizonte" },
  { value: "0,804–0,871", label: "AUC RF" },
];

export default function Home() {
  return (
    <>
      <section className="bg-gradient-to-br from-[var(--primary)] via-[var(--primary-dark)] to-[#051E33] text-white py-20">
        <div className="container-prose">
          <div className="max-w-4xl">
            <div className="inline-block bg-white/10 backdrop-blur px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider mb-6">
              USGP · Universidad San Gregorio de Portoviejo · {SITE.year}
            </div>
            <h1 className="text-white mb-6 leading-tight">
              Geoportal de Riesgo Agroclimático<br/>
              <span className="text-[var(--accent-3)]">Imbabura, Ecuador</span>
            </h1>
            <p className="text-xl opacity-90 max-w-3xl leading-relaxed mb-8">
              Evaluación integrada del <strong>riesgo agroclimático</strong> para cultivos andinos (papa, maíz,
              fréjol, quinua) en las <strong>42 parroquias</strong> de Imbabura bajo 9 escenarios climáticos <strong>CMIP6</strong>,
              combinando <strong>Random Forest</strong> (SDM) con una <strong>Red Bayesiana</strong> de 7 nodos
              (peligro-exposición-susceptibilidad).
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href="/visor" className="btn-primary bg-[var(--accent)] hover:bg-red-900 border-0 text-white">
                <Map size={20}/> Abrir Visor Cartográfico <ArrowRight size={18}/>
              </Link>
              <Link href="/resultados" className="btn-secondary bg-transparent border-white text-white hover:bg-white hover:text-[var(--primary)]">
                <BarChart3 size={20}/> Ver Resultados
              </Link>
              <Link href="/asistente" className="btn-secondary bg-transparent border-white text-white hover:bg-white hover:text-[var(--primary)]">
                <Bot size={20}/> Consultar con IA
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="bg-white border-b border-[var(--border)]">
        <div className="container-prose py-10 grid grid-cols-2 md:grid-cols-6 gap-4">
          {stats.map(s => (
            <div key={s.label} className="text-center">
              <div className="text-3xl md:text-4xl font-bold text-[var(--primary)]">{s.value}</div>
              <div className="text-xs uppercase tracking-wider text-[var(--text-muted)] mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="container-prose py-16">
        <div className="text-center mb-12">
          <h2 className="mb-3">Servicios del Geoportal</h2>
          <p className="text-lg text-[var(--text-muted)] max-w-2xl mx-auto">
            Ocho servicios integrados para acceder, analizar y descargar la información científica del proyecto.
          </p>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          {services.map(s => {
            const Icon = s.icon;
            return (
              <Link key={s.href} href={s.href} className="service-card group no-underline text-[var(--text)]">
                <div className="w-12 h-12 rounded-lg flex items-center justify-center mb-4 text-white" style={{ background: s.color }}>
                  <Icon size={24}/>
                </div>
                <h3 className="text-lg font-bold mb-2 group-hover:text-[var(--primary)] transition">{s.title}</h3>
                <p className="text-sm text-[var(--text-muted)] leading-relaxed">{s.desc}</p>
                <div className="mt-4 text-[var(--primary)] font-semibold text-sm flex items-center gap-1">
                  Acceder <ArrowRight size={14} className="group-hover:translate-x-1 transition"/>
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      <section className="bg-gradient-to-br from-[var(--bg)] to-white py-16 border-y border-[var(--border)]">
        <div className="container-prose grid md:grid-cols-2 gap-10 items-center">
          <div>
            <div className="text-sm uppercase tracking-wider text-[var(--accent)] font-bold mb-2">Hallazgo principal</div>
            <h2 className="mb-4">Un factor <span className="text-[var(--accent)]">1,97×</span> entre parroquias</h2>
            <p className="text-lg text-[var(--text-muted)] leading-relaxed mb-4">
              Bajo <strong>SSP5-8.5 al 2061–2080</strong>, el IR medio parroquial va de <strong>0,350 en Imbaya</strong>
              a <strong>0,689 en García Moreno</strong> — una diferenciación territorial que solo es visible a escala parroquial.
            </p>
            <ul className="space-y-2 text-sm">
              <li>🔴 <strong>Muy Alta</strong> (IR ≥ 0,65): 2 parroquias</li>
              <li>🟠 <strong>Alta</strong> (IR 0,55 – 0,65): 5 parroquias</li>
              <li>🟡 <strong>Alerta</strong> (IR 0,45 – 0,55): 22 parroquias</li>
              <li>🔵 <strong>Monitoreo</strong> (IR 0,40 – 0,45): 3 parroquias</li>
              <li>🟢 <strong>Favorable</strong> (IR &lt; 0,40): 10 parroquias</li>
            </ul>
          </div>
          <div className="bg-white rounded-xl shadow-lg overflow-hidden border border-[var(--border)]">
            <img
              src="https://www.arcgis.com/sharing/rest/content/items/97b6b4fdb0934e878b591f85a574137f/data"
              alt="Mapa de priorización parroquial bajo SSP5-8.5"
              className="w-full h-auto"
            />
            <div className="p-4 text-xs text-[var(--text-muted)]">
              Figura 5 del manuscrito · <Link href="/galeria">ver galería completa</Link>
            </div>
          </div>
        </div>
      </section>

      <section className="container-prose py-16">
        <div className="grid md:grid-cols-3 gap-6">
          <div className="card">
            <BookOpen className="text-[var(--primary)] mb-3" size={28}/>
            <h3 className="text-xl mb-2">Manuscrito</h3>
            <p className="text-sm text-[var(--text-muted)] mb-3">
              Pinto Páez, V.H. (2026). <em>Riesgo agroclimático bajo escenarios CMIP6 mediante Random Forest y Redes Bayesianas
              a escala parroquial en la provincia de Imbabura, Ecuador</em>. Sometido a <strong>Natural Hazards</strong> (Springer Nature).
            </p>
            <Link href="/acerca" className="text-sm font-semibold">Más detalles →</Link>
          </div>
          <div className="card">
            <Database className="text-[var(--accent-2)] mb-3" size={28}/>
            <h3 className="text-xl mb-2">Datos y código</h3>
            <p className="text-sm text-[var(--text-muted)] mb-3">
              22 scripts Python archivados en <a href={`https://github.com/${SITE.githubUser}/${SITE.githubRepo}`} target="_blank">GitHub</a> y
              Zenodo con DOI <a href={`https://doi.org/${SITE.doi}`} target="_blank">{SITE.doi}</a>.
            </p>
            <Link href="/datos" className="text-sm font-semibold">Datos abiertos →</Link>
          </div>
          <div className="card">
            <Bot className="text-indigo-600 mb-3" size={28}/>
            <h3 className="text-xl mb-2">Asistente IA</h3>
            <p className="text-sm text-[var(--text-muted)] mb-3">
              Consulta en lenguaje natural sobre metodología, cultivos, escenarios o resultados específicos.
              Retrieval-Augmented Generation sobre el manuscrito.
            </p>
            <Link href="/asistente" className="text-sm font-semibold">Abrir asistente →</Link>
          </div>
        </div>
      </section>
    </>
  );
}
