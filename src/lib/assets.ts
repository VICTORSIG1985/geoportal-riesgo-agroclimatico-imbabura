// Helper para resolver paths de assets respetando el basePath de Next.js
// en producción (GitHub Pages).
//
// Uso:
//   <img src={asset("/logo.png")}/>
//   <a href={asset("/scripts/mi_script.py")} download>...</a>

const BASE = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

export function asset(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${BASE}${p}`;
}

export function assetEncoded(path: string): string {
  // Encoda cada segmento (útil para scripts con espacios/acentos)
  const encoded = path.split("/").map(seg => seg === "" ? "" : encodeURIComponent(seg)).join("/");
  return asset(encoded);
}
