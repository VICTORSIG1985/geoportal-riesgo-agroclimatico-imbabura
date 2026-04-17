import { asset } from "@/lib/assets";

interface PageHeroProps {
  title: string;
  subtitle: string;
  image: string;          // nombre de archivo dentro de /img/
  credit?: string;
  overlayColor?: string;  // CSS color con alpha, e.g. "rgba(15,76,129,0.55)"
  accent?: string;
  height?: "sm" | "md" | "lg";
  children?: React.ReactNode;
}

export default function PageHero({ title, subtitle, image, credit, overlayColor = "rgba(15,76,129,0.55)", accent = "#FFB088", height = "md", children }: PageHeroProps) {
  const h = height === "sm" ? "py-14 md:py-16" : height === "lg" ? "py-20 md:py-28" : "py-16 md:py-20";
  return (
    <section className="relative overflow-hidden">
      <img
        src={asset(`/img/${image}`)}
        alt=""
        aria-hidden="true"
        className="absolute inset-0 w-full h-full object-cover"
      />
      {/* Overlay: color institucional tenue + degradado oscuro inferior para legibilidad del credit */}
      <div className="absolute inset-0" style={{ background: overlayColor }}></div>
      <div className="absolute inset-0 bg-gradient-to-b from-black/10 via-black/35 to-black/65"></div>
      <div className={`relative container-prose ${h} text-white`}>
        <h1 className="text-white mb-3 drop-shadow-[0_2px_8px_rgba(0,0,0,0.85)]" style={{ textShadow: "0 2px 12px rgba(0,0,0,0.75)" }}>
          {title}{accent && <> <span style={{ color: accent }}>·</span></>}
        </h1>
        <p className="text-xl max-w-3xl" style={{ color: "#F7FAFC", textShadow: "0 1px 6px rgba(0,0,0,0.85)" }}>{subtitle}</p>
        {children && <div className="mt-6">{children}</div>}
      </div>
      {credit && (
        <div className="absolute bottom-0 left-0 right-0 bg-black/70 text-white text-[10px] md:text-[11px] py-1 px-4 text-center">
          {credit}
        </div>
      )}
    </section>
  );
}
