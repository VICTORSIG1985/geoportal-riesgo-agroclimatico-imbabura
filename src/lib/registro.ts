// Utilidades del sistema de registro obligatorio con LOPDP Ecuador.

export const REGISTRO_FS_URL = "https://services.arcgis.com/LNQOp9d1bu5VZNME/arcgis/rest/services/USO_GEOPORTAL_IMBABURA/FeatureServer/0";
export const CONSENT_VERSION = "v1.0-2026-04";

const LS_KEY = "geoportal_registro_v1";
const RATE_LIMIT_KEY = "geoportal_last_submit_ts";
const RATE_LIMIT_MS = 20_000; // 20 s entre submits del mismo browser (anti-spam mínimo)

// Sanitiza cualquier string de usuario antes de enviarlo a AGO:
// - elimina caracteres de control
// - recorta whitespace
// - limita longitud máxima
// - elimina backticks y etiquetas HTML básicas (defensa en profundidad ante XSS cruzado)
export function sanitizeInput(s: string | undefined, maxLen = 200): string {
  if (!s) return "";
  let out = String(s);
  // Remover caracteres de control excepto tab/newline
  out = out.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, "");
  // Remover etiquetas HTML
  out = out.replace(/<[^>]{0,200}>/g, "");
  // Remover backticks (reducen riesgo si llegan a HTML injertado en otros contextos)
  out = out.replace(/[`]/g, "'");
  return out.trim().slice(0, maxLen);
}

// Validación estricta de email (RFC 5322 simplificada + sin direcciones descartables comunes)
export function isValidEmail(s: string): boolean {
  if (!s) return false;
  if (s.length < 5 || s.length > 120) return false;
  // RFC-like básico
  return /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/.test(s);
}

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

// Envía el registro al FS público (addFeatures anónimo). Con rate-limit, sanitización y validación.
export async function submitRegistro(r: RegistroLocal, tipo: "script" | "ficha" | "visor" | "api" | "geojson", nombreArchivo?: string): Promise<boolean> {
  // Rate-limit por sesión del navegador (anti-spam desde la misma pestaña)
  if (typeof window !== "undefined") {
    const last = parseInt(window.sessionStorage.getItem(RATE_LIMIT_KEY) || "0", 10);
    if (last && Date.now() - last < RATE_LIMIT_MS) {
      // Silencioso: no enviamos pero tampoco mostramos error al usuario
      return true;
    }
    window.sessionStorage.setItem(RATE_LIMIT_KEY, String(Date.now()));
  }

  // Validación de email y sanitización
  if (!isValidEmail(r.email)) return false;
  const lat = Number(r.lat), lon = Number(r.lon);
  if (!isFinite(lat) || !isFinite(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) return false;

  const feature = {
    geometry: { x: lon, y: lat, spatialReference: { wkid: 4326 } },
    attributes: {
      nombre: sanitizeInput(r.nombre, 120),
      email: sanitizeInput(r.email, 120).toLowerCase(),
      institucion: sanitizeInput(r.institucion, 160),
      rol: sanitizeInput(r.rol, 80),
      tipo_descarga: sanitizeInput(tipo, 20),
      nombre_archivo: sanitizeInput(nombreArchivo, 240),
      ubicacion_texto: sanitizeInput(r.ubicacion_texto, 200),
      pais: sanitizeInput(r.pais, 80),
      session_token: sanitizeInput(r.session_token, 64),
      consentimiento_v: sanitizeInput(r.consentimiento_v, 20),
      fecha_registro: Date.now(),
      user_agent: sanitizeInput(typeof navigator !== "undefined" ? navigator.userAgent : "", 500),
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
      // Con cache:"no-store" evitamos que el browser conserve respuestas con datos del usuario
      cache: "no-store",
      credentials: "omit",
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
