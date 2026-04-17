// Utilidades del sistema de registro obligatorio con LOPDP Ecuador.

export const REGISTRO_FS_URL = "https://services.arcgis.com/LNQOp9d1bu5VZNME/arcgis/rest/services/USO_GEOPORTAL_IMBABURA/FeatureServer/0";
export const CONSENT_VERSION = "v1.0-2026-04";

const LS_KEY = "geoportal_registro_v1";

export interface RegistroLocal {
  nombre: string;
  email: string;
  institucion?: string;
  rol?: string;
  lat: number;
  lon: number;
  ubicacion_texto?: string;
  pais?: string;
  session_token: string;
  consentimiento_v: string;
  fecha_registro: number;
}

export function getRegistro(): RegistroLocal | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(LS_KEY);
    if (!raw) return null;
    const r = JSON.parse(raw);
    if (!r?.email || !r?.nombre) return null;
    if (r.consentimiento_v !== CONSENT_VERSION) return null; // forzar re-aceptación si cambia el aviso
    return r;
  } catch { return null; }
}

export function setRegistro(r: RegistroLocal) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(LS_KEY, JSON.stringify(r));
}

export function clearRegistro() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(LS_KEY);
}

export function uuid(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = Math.random() * 16 | 0, v = c === "x" ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

// Reverse geocoding con Nominatim (OSM) — libre, sin key
export async function reverseGeocode(lat: number, lon: number): Promise<{ place: string; country: string }> {
  const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&zoom=10&accept-language=es`, {
    headers: { "User-Agent": "GeoportalImbabura/1.0 (https://victorsig1985.github.io)" }
  });
  if (!res.ok) return { place: `${lat.toFixed(3)}, ${lon.toFixed(3)}`, country: "" };
  const data = await res.json();
  const a = data.address || {};
  const place = [a.city || a.town || a.village || a.county, a.state, a.country].filter(Boolean).join(", ");
  return { place: place || data.display_name || `${lat.toFixed(3)}, ${lon.toFixed(3)}`, country: a.country || "" };
}

// Envía el registro al FS público (addFeatures anónimo)
export async function submitRegistro(r: RegistroLocal, tipo: "script" | "ficha" | "visor" | "api", nombreArchivo?: string): Promise<boolean> {
  const feature = {
    geometry: { x: r.lon, y: r.lat, spatialReference: { wkid: 4326 } },
    attributes: {
      nombre: r.nombre.slice(0, 120),
      email: r.email.slice(0, 120),
      institucion: (r.institucion || "").slice(0, 160),
      rol: (r.rol || "").slice(0, 80),
      tipo_descarga: tipo,
      nombre_archivo: (nombreArchivo || "").slice(0, 240),
      ubicacion_texto: (r.ubicacion_texto || "").slice(0, 200),
      pais: (r.pais || "").slice(0, 80),
      session_token: r.session_token,
      consentimiento_v: r.consentimiento_v,
      fecha_registro: Date.now(),
      user_agent: (typeof navigator !== "undefined" ? navigator.userAgent : "").slice(0, 500),
    }
  };
  const body = new URLSearchParams();
  body.set("features", JSON.stringify([feature]));
  body.set("f", "json");
  try {
    const res = await fetch(`${REGISTRO_FS_URL}/addFeatures`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString(),
    });
    if (!res.ok) return false;
    const data = await res.json();
    return !!data?.addResults?.[0]?.success;
  } catch {
    return false;
  }
}

// Texto del aviso legal (LOPDP Ecuador) — se versiona para trazabilidad
export const AVISO_LEGAL_V1 = `
AVISO DE PRIVACIDAD · Ley Orgánica de Protección de Datos Personales (LOPDP) · Registro Oficial Suplemento No. 459, 26 de mayo de 2021.

Responsable del tratamiento: Víctor Hugo Pinto Páez · Maestrando · Universidad San Gregorio de Portoviejo (USGP) · vpintopaez@hotmail.com

Finalidad del tratamiento: (a) estadísticas anónimas y agregadas de uso del Geoportal; (b) mejora continua del servicio; (c) registro de descargas con fines de trazabilidad científica.

Base legal: consentimiento libre, específico, informado e inequívoco del titular (Art. 4 num. 7 y Art. 7 LOPDP). Usted puede retirarlo en cualquier momento escribiendo al responsable.

Datos recopilados: nombre, correo electrónico, institución (opcional), rol profesional (opcional), ubicación aproximada (geolocalización consentida), archivo descargado, fecha, navegador (user agent).

Tiempo de conservación: máximo 5 años desde el registro; pasado este plazo los datos serán eliminados o anonimizados.

Medidas de protección: datos almacenados en ArcGIS Online USGP-EC (Managed Services) con políticas de seguridad corporativas. No se venden ni transfieren a terceros con fines comerciales. Pueden usarse en publicaciones académicas de forma agregada y anónima.

Derechos ARCO+: acceso, rectificación, cancelación, oposición y portabilidad. Ejerza sus derechos enviando solicitud al correo del responsable; respuesta en 15 días hábiles conforme a la Ley.

Autoridad de control: Superintendencia de Protección de Datos Personales del Ecuador.

Al registrarse acepta expresamente este tratamiento bajo la versión ${CONSENT_VERSION} del presente aviso.
`;
