"use client";
import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import { X, MapPin, Loader2, CheckCircle2, AlertCircle, Shield } from "lucide-react";
import { AVISO_LEGAL_V1, CONSENT_VERSION, RegistroLocal, reverseGeocode, setRegistro, submitRegistro, uuid, isValidEmail, sanitizeInput } from "@/lib/registro";

interface Props {
  open: boolean;
  onClose: () => void;
  onCompleted: (r: RegistroLocal) => void;
  pending?: { tipo: "script" | "ficha"; name: string } | null;
}

export default function RegisterModal({ open, onClose, onCompleted, pending }: Props) {
  const [step, setStep] = useState<1 | 2>(1);
  const [nombre, setNombre] = useState("");
  const [email, setEmail] = useState("");
  const [institucion, setInstitucion] = useState("");
  const [rol, setRol] = useState("");
  const [lat, setLat] = useState<number | null>(null);
  const [lon, setLon] = useState<number | null>(null);
  const [placeText, setPlaceText] = useState("");
  const [country, setCountry] = useState("");
  const [consent, setConsent] = useState(false);
  const [geoStatus, setGeoStatus] = useState<"idle" | "locating" | "ok" | "manual" | "err">("idle");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  // Honeypot: campo oculto. Los bots suelen rellenarlo; los humanos no lo ven.
  const [hp_url, setHpUrl] = useState("");
  // Registro del tiempo de apertura para detectar envíos demasiado rápidos (bots)
  const openedAtRef = useRef<number>(Date.now());

  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);

  // Inicializar mapa (step 2)
  useEffect(() => {
    if (step !== 2 || !mapContainerRef.current || mapRef.current) return;
    // Retardo mínimo para que el contenedor tenga dimensiones correctas antes de iniciar
    const timer = setTimeout(() => {
      if (!mapContainerRef.current) return;
      const m = new maplibregl.Map({
        container: mapContainerRef.current,
        style: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        center: [lon ?? -78.2, lat ?? 0.35],
        zoom: lat ? 9 : 5,
        attributionControl: false,
      });
      m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");
      m.on("click", async (e) => {
        const { lng, lat: la } = e.lngLat;
        setLat(la); setLon(lng);
        setGeoStatus("manual");
        updateMarker(lng, la);
        try { const { place, country } = await reverseGeocode(la, lng); setPlaceText(place); setCountry(country); } catch {}
      });
      mapRef.current = m;
      // Forzar resize tras cargar para que los tiles pinten correctamente
      m.on("load", () => { setTimeout(() => m.resize(), 120); });
      if (lat && lon) {
        m.on("load", () => { updateMarker(lon!, lat!); });
      }
    }, 80);
    return () => {
      clearTimeout(timer);
      mapRef.current?.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step]);

  // Observar cambios de tamaño del contenedor del mapa (modal redimensionado)
  useEffect(() => {
    if (step !== 2 || !mapContainerRef.current) return;
    const obs = new ResizeObserver(() => { mapRef.current?.resize(); });
    obs.observe(mapContainerRef.current);
    return () => obs.disconnect();
  }, [step]);

  function updateMarker(lng: number, la: number) {
    const m = mapRef.current; if (!m) return;
    if (markerRef.current) markerRef.current.remove();
    markerRef.current = new maplibregl.Marker({ color: "#B2182B" }).setLngLat([lng, la]).addTo(m);
    m.flyTo({ center: [lng, la], zoom: 10, duration: 600 });
  }

  async function detectLocation() {
    if (!navigator.geolocation) { setGeoStatus("err"); return; }
    setGeoStatus("locating");
    navigator.geolocation.getCurrentPosition(async (pos) => {
      const la = pos.coords.latitude, lo = pos.coords.longitude;
      setLat(la); setLon(lo);
      updateMarker(lo, la);
      try {
        const { place, country } = await reverseGeocode(la, lo);
        setPlaceText(place); setCountry(country);
      } catch {}
      setGeoStatus("ok");
    }, () => setGeoStatus("err"), { enableHighAccuracy: false, timeout: 10000 });
  }

  function validate1(): string | null {
    const name = sanitizeInput(nombre, 120);
    if (!name || name.length < 3) return "Ingrese su nombre completo.";
    if (!isValidEmail(email.trim())) return "Correo electrónico no válido.";
    // Honeypot trap — si el bot rellenó el campo oculto, rechazamos silenciosamente
    if (hp_url.length > 0) return "Validación fallida. Si usted no es un bot, recargue la página.";
    // Tiempo mínimo de interacción: menos de 2 s = probable bot
    if (Date.now() - openedAtRef.current < 2000) return "Complete los campos y vuelva a intentarlo.";
    return null;
  }

  function next() {
    const e = validate1(); if (e) { setErr(e); return; }
    setErr(null); setStep(2);
  }

  async function submit() {
    setErr(null);
    if (lat == null || lon == null) { setErr("Seleccione su ubicación en el mapa o use 'Detectar mi ubicación'."); return; }
    if (!consent) { setErr("Debe aceptar el aviso de privacidad para continuar."); return; }
    setBusy(true);
    const reg: RegistroLocal = {
      nombre: nombre.trim(),
      email: email.trim().toLowerCase(),
      institucion: institucion.trim() || undefined,
      rol: rol.trim() || undefined,
      lat, lon,
      ubicacion_texto: placeText,
      pais: country,
      session_token: uuid(),
      consentimiento_v: CONSENT_VERSION,
      fecha_registro: Date.now(),
    };
    const ok = await submitRegistro(reg, pending?.tipo || "api", pending?.name);
    if (!ok) {
      setBusy(false);
      setErr("No se pudo enviar el registro. Verifique su conexión e intente nuevamente.");
      return;
    }
    setRegistro(reg);
    setBusy(false);
    onCompleted(reg);
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/60 z-[100] flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-xl max-w-3xl w-full max-h-[92vh] overflow-hidden flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between p-4 border-b bg-[var(--primary)] text-white">
          <div className="flex items-center gap-2">
            <Shield size={20}/>
            <div>
              <h3 className="text-white text-lg mb-0">Registro para descarga · {pending?.tipo === "ficha" ? "Ficha parroquial" : "Script Python"}</h3>
              <div className="text-[11px] opacity-80">Paso {step} de 2 · Aviso LOPDP (Ecuador) · Versión {CONSENT_VERSION}</div>
            </div>
          </div>
          <button onClick={onClose} className="text-white/80 hover:text-white"><X size={20}/></button>
        </div>

        <div className="p-5 overflow-y-auto flex-1">
          {step === 1 && (
            <div className="space-y-4">
              {/* Honeypot: campo oculto para detectar bots. No visible para usuarios humanos. */}
              <input
                type="text" name="website_url" tabIndex={-1} autoComplete="off"
                value={hp_url} onChange={(e) => setHpUrl(e.target.value)}
                aria-hidden="true"
                style={{ position: "absolute", left: "-9999px", width: "1px", height: "1px", opacity: 0 }}
              />
              <div className="bg-indigo-50 border-l-4 border-indigo-400 p-3 rounded-r text-sm">
                <strong>¿Por qué este registro?</strong> Para cumplir la <strong>Ley Orgánica de Protección de Datos Personales</strong> del
                Ecuador y generar estadísticas de uso académico del geoportal. Los datos se almacenan en ArcGIS Online
                (USGP-EC) y se usan exclusivamente para fines de investigación y mejora del servicio.
              </div>
              <div className="grid md:grid-cols-2 gap-4">
                <label className="block">
                  <span className="text-xs uppercase tracking-wider text-[var(--text-muted)] font-semibold">Nombre completo *</span>
                  <input value={nombre} onChange={e => setNombre(e.target.value)} required minLength={3}
                    className="mt-1 w-full px-3 py-2 border border-[var(--border)] rounded text-sm"
                    placeholder="Ej. María Pérez Torres"/>
                </label>
                <label className="block">
                  <span className="text-xs uppercase tracking-wider text-[var(--text-muted)] font-semibold">Correo electrónico *</span>
                  <input type="email" value={email} onChange={e => setEmail(e.target.value)} required
                    className="mt-1 w-full px-3 py-2 border border-[var(--border)] rounded text-sm"
                    placeholder="ejemplo@institucion.ec"/>
                </label>
                <label className="block">
                  <span className="text-xs uppercase tracking-wider text-[var(--text-muted)] font-semibold">Institución (opcional)</span>
                  <input value={institucion} onChange={e => setInstitucion(e.target.value)}
                    className="mt-1 w-full px-3 py-2 border border-[var(--border)] rounded text-sm"
                    placeholder="Ej. GAD Parroquial, Universidad..."/>
                </label>
                <label className="block">
                  <span className="text-xs uppercase tracking-wider text-[var(--text-muted)] font-semibold">Rol (opcional)</span>
                  <select value={rol} onChange={e => setRol(e.target.value)} className="mt-1 w-full px-3 py-2 border border-[var(--border)] rounded text-sm">
                    <option value="">Seleccione…</option>
                    <option>Estudiante</option>
                    <option>Investigador/a</option>
                    <option>Docente</option>
                    <option>Técnico/a GAD</option>
                    <option>Productor/a agrícola</option>
                    <option>Funcionario/a público</option>
                    <option>Consultor/a</option>
                    <option>Periodista</option>
                    <option>Otro</option>
                  </select>
                </label>
              </div>
              {err && <div className="text-sm text-red-600 flex items-center gap-1"><AlertCircle size={14}/> {err}</div>}
              <div className="flex justify-end gap-2">
                <button onClick={onClose} className="btn-secondary text-sm">Cancelar</button>
                <button onClick={next} className="btn-primary text-sm">Continuar · Ubicación y consentimiento →</button>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div>
                <div className="text-xs uppercase tracking-wider text-[var(--text-muted)] font-semibold mb-1">Ubicación aproximada *</div>
                <div className="flex gap-2 mb-2 flex-wrap">
                  <button onClick={detectLocation} disabled={geoStatus === "locating"}
                    className="btn-primary text-sm inline-flex items-center gap-2">
                    {geoStatus === "locating" ? <Loader2 size={14} className="animate-spin"/> : <MapPin size={14}/>}
                    Detectar mi ubicación
                  </button>
                  <div className="text-xs text-[var(--text-muted)] self-center">
                    o haga clic en el mapa
                    {geoStatus === "ok" && <> · <CheckCircle2 size={12} className="inline text-green-600"/> detectada</>}
                    {geoStatus === "manual" && <> · seleccionada manualmente</>}
                    {geoStatus === "err" && <> · <AlertCircle size={12} className="inline text-amber-600"/> permiso denegado, use el mapa</>}
                  </div>
                </div>
                <div ref={mapContainerRef} className="w-full h-64 rounded border border-[var(--border)] overflow-hidden"/>
                {(lat != null && lon != null) && (
                  <div className="text-xs text-[var(--text-muted)] mt-1">
                    <strong>{placeText || `${lat.toFixed(3)}, ${lon.toFixed(3)}`}</strong>
                    {country && ` · ${country}`}
                  </div>
                )}
              </div>

              <details className="border border-[var(--border)] rounded">
                <summary className="text-sm font-semibold px-3 py-2 cursor-pointer bg-[var(--bg)]">Leer el aviso de privacidad completo (LOPDP)</summary>
                <div className="p-3 text-xs whitespace-pre-wrap text-[var(--text-muted)] max-h-48 overflow-y-auto">
                  {AVISO_LEGAL_V1}
                </div>
              </details>

              <label className="flex items-start gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} className="mt-0.5"/>
                <span>
                  Acepto el tratamiento de mis datos personales para las finalidades descritas (estadística de uso, mejora
                  del geoportal, trazabilidad académica), bajo la LOPDP del Ecuador · versión {CONSENT_VERSION} del aviso.
                </span>
              </label>

              {err && <div className="text-sm text-red-600 flex items-center gap-1"><AlertCircle size={14}/> {err}</div>}

              <div className="flex justify-between gap-2">
                <button onClick={() => setStep(1)} className="btn-secondary text-sm">← Volver</button>
                <button onClick={submit} disabled={busy} className="btn-primary text-sm">
                  {busy ? <><Loader2 size={14} className="animate-spin inline"/> Enviando…</> : "Aceptar y descargar"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
