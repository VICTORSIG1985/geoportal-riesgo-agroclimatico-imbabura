import { asset } from "@/lib/assets";

interface PageHeroProps {
  title: string;
  subtitle: string;
  image: string;
  credit?: string;
  overlayColor?: string;
  accent?: string;
  height?: "sm" | "md" | "lg";
  children?: React.ReactNode;
}

export default function PageHero({
  title, subtitle, image, credit,
  overlayColor = "rgba(15,76,129,0.35)", // por defecto muy tenue
  accent = "#FFB088",
  height = "md",
  children,
}: PageHeroProps) {
  const h = height === "sm" ? "py-14 md:py-16" : height === "lg" ? "py-20 md:py-28" : "py-16 md:py-20";
  // Sombra fuerte multi-capa para que el texto sea legible incluso sobre paisajes claros
  const textShadow = "0 2px 8px rgba(0,0,0,0.85), 0 0 24px rgba(0,0,0,0.45)";
  return (
    <section className="relative overflow-hidden">
      <img
        src={asset(`/img/${image}`)}
        alt=""
        aria-hidden="true"
        className="absolute inset-0 w-full h-full object-cover"
      />
      {/* Overlay color institucional muy tenue */}
      <div className="absolute inset-0" style={{ background: overlayColor }}></div>
      {/* Viñeta lateral/inferior para garantizar legibilidad del título a la izquierda */}
      <div className="absolute inset-0 bg-gradient-to-r from-black/50 via-black/10 to-transparent"></div>
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-black/55"></div>
      <div className={`relative container-prose ${h} text-white`}>
        <h1 className="text-white mb-3" style={{ textShadow }}>
          {title}{accent && <> <span style={{ color: accent }}>·</span></>}
        </h1>
        <p className="text-xl max-w-3xl" style={{ color: "#F7FAFC", textShadow }}>{subtitle}</p>
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
