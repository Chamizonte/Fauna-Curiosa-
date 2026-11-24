import React from "react";
import { AbsoluteFill, interpolate, OffthreadVideo, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont } from "@remotion/google-fonts/Montserrat";
// @ts-ignore (sin tipos)
import { geoMercator, geoNaturalEarth1, geoPath } from "d3-geo";
// @ts-ignore (sin tipos)
import { feature } from "topojson-client";
// @ts-ignore (datos de Natural Earth, dominio público)
import mundo from "world-atlas/countries-110m.json";

const { fontFamily } = loadFont("normal", { weights: ["600", "800", "900"] });

// Animaciones propias de los vídeos largos (1920x1080). Cada escena "grafico" del guion
// trae su especificación y aquí se dibuja. Estilo común: fondo oscuro verdoso (o el plano
// anterior desenfocado), acento amarillo, Montserrat. Los 160 px de abajo quedan libres
// para los subtítulos.
export type Grafico =
  | { tipo: "cifra"; valor: number; prefijo?: string; unidad?: string; texto: string; decimales?: number;
      comparar?: { etiqueta: string; valor: number }[] }
  | { tipo: "comparativa"; titulo: string; unidad?: string; items: { nombre: string; valor: number; nota?: string }[] }
  | { tipo: "linea_tiempo"; titulo: string; eventos: { fecha: string; texto: string }[]; destacado?: number }
  | { tipo: "mapa"; titulo?: string; puntos: { nombre: string; lat: number; lon: number }[]; rutas?: number[][]; mundo?: boolean }
  | { tipo: "lista"; titulo: string; puntos: string[] }
  | { tipo: "proceso"; titulo: string; pasos: string[] }
  | { tipo: "cita"; texto: string; autor: string; obra?: string }
  | { tipo: "titular"; texto: string; subtitulo?: string };

const AMARILLO = "#FFD60A";
const VERDE = "#7CF29A";
const TEXTO_SUAVE = "#c9d3cd";
const ABAJO = 170; // hueco para los subtítulos

const useEntrada = (retraso = 0, damping = 16) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: f - retraso, fps, config: { damping, stiffness: 120 } });
};

// Momento (en fotogramas) en que aparece el elemento k de n: repartidos en el primer 65 %.
const aparicion = (k: number, n: number, frames: number) => Math.round(10 + (k * frames * 0.65) / Math.max(1, n));

const fmt = (v: number, dec = 0) =>
  v.toLocaleString("es-ES", { minimumFractionDigits: dec, maximumFractionDigits: dec });

const Fondo: React.FC<{ fondo?: string; frames: number }> = ({ fondo, frames }) => {
  const f = useCurrentFrame();
  const zoom = interpolate(f, [0, frames], [1.08, 1.0], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 35%, #1b2620 0%, #090c0a 75%)" }}>
      {fondo ? (
        <AbsoluteFill style={{ opacity: 0.35, filter: "blur(22px) saturate(0.7)", transform: `scale(${zoom})` }}>
          <OffthreadVideo src={staticFile(fondo)} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        </AbsoluteFill>
      ) : null}
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(9,12,10,0.35) 0%, rgba(9,12,10,0.75) 100%)" }} />
    </AbsoluteFill>
  );
};

const Titulo: React.FC<{ texto: string }> = ({ texto }) => {
  const e = useEntrada(0);
  return (
    <div style={{ position: "absolute", top: 70, left: 110, display: "flex", alignItems: "center", gap: 24,
                  opacity: e, transform: `translateX(${(1 - e) * -60}px)` }}>
      <div style={{ width: 14, height: 66, background: AMARILLO, borderRadius: 4 }} />
      <div style={{ fontFamily, fontWeight: 900, fontSize: 58, color: "white", textTransform: "uppercase", letterSpacing: 1 }}>
        {texto}
      </div>
    </div>
  );
};

// ---------- cifra: un número grande que cuenta ----------
const Cifra: React.FC<{ g: Extract<Grafico, { tipo: "cifra" }>; frames: number }> = ({ g, frames }) => {
  const f = useCurrentFrame();
  const cuenta = interpolate(f, [8, Math.min(frames * 0.45, 75)], [0, g.valor], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: (t) => 1 - Math.pow(1 - t, 3) });
  const e = useEntrada(0, 14);
  const t = useEntrada(18);
  const comparar = g.comparar || [];
  const maximo = Math.max(g.valor, ...comparar.map((c) => c.valor));
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", paddingBottom: ABAJO, fontFamily }}>
      <div style={{ transform: `scale(${0.7 + 0.3 * e})`, opacity: e, display: "flex", alignItems: "baseline", gap: 26 }}>
        {g.prefijo ? <span style={{ fontSize: 90, fontWeight: 800, color: TEXTO_SUAVE }}>{g.prefijo}</span> : null}
        <span style={{ fontSize: 260, fontWeight: 900, color: AMARILLO, lineHeight: 1, textShadow: "0 18px 60px rgba(0,0,0,0.6)" }}>
          {fmt(cuenta, g.decimales || 0)}
        </span>
        {g.unidad ? <span style={{ fontSize: 96, fontWeight: 900, color: "white", textTransform: "uppercase" }}>{g.unidad}</span> : null}
      </div>
      <div style={{ marginTop: 18, fontSize: 52, fontWeight: 800, color: "white", maxWidth: 1400, textAlign: "center",
                    opacity: t, transform: `translateY(${(1 - t) * 30}px)` }}>
        {g.texto}
      </div>
      {comparar.length ? (
        <div style={{ marginTop: 50, width: 1200, display: "flex", flexDirection: "column", gap: 18 }}>
          {[{ etiqueta: g.unidad ? `${fmt(g.valor, g.decimales || 0)} ${g.unidad}` : fmt(g.valor), valor: g.valor, propia: true },
            ...comparar.map((c) => ({ ...c, propia: false }))].map((c, k) => {
            const ini = 30 + k * 12;
            const w = interpolate(f, [ini, ini + 30], [0, c.valor / maximo], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
            return (
              <div key={k} style={{ display: "flex", alignItems: "center", gap: 20 }}>
                <div style={{ height: 34, width: `${w * 80}%`, borderRadius: 8, background: c.propia ? AMARILLO : "#4b5a52" }} />
                <div style={{ fontSize: 34, fontWeight: 800, color: c.propia ? AMARILLO : TEXTO_SUAVE, whiteSpace: "nowrap" }}>
                  {c.etiqueta}
                </div>
              </div>
            );
          })}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

// ---------- comparativa: barras proporcionales ----------
const Comparativa: React.FC<{ g: Extract<Grafico, { tipo: "comparativa" }>; frames: number }> = ({ g, frames }) => {
  const f = useCurrentFrame();
  const maximo = Math.max(...g.items.map((i) => i.valor), 1);
  const n = g.items.length;
  return (
    <AbsoluteFill style={{ fontFamily }}>
      <Titulo texto={g.titulo} />
      <div style={{ position: "absolute", top: 210, left: 110, right: 110, bottom: ABAJO + 20, display: "flex",
                    flexDirection: "column", justifyContent: "center", gap: Math.max(18, 70 - n * 8) }}>
        {g.items.map((it, k) => {
          const ini = aparicion(k, n, frames);
          const p = interpolate(f, [ini, ini + 28], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp",
                                                               easing: (t) => 1 - Math.pow(1 - t, 3) });
          const ganador = it.valor === maximo;
          return (
            <div key={k} style={{ opacity: interpolate(f, [ini - 4, ini + 6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 40, fontWeight: 800, color: "white", marginBottom: 8 }}>
                <span>{it.nombre}{it.nota ? <span style={{ color: TEXTO_SUAVE, fontWeight: 600, fontSize: 30 }}>  {it.nota}</span> : null}</span>
                <span style={{ color: ganador ? AMARILLO : "white" }}>{fmt(it.valor * p, it.valor % 1 ? 1 : 0)} {g.unidad || ""}</span>
              </div>
              <div style={{ height: 40, background: "rgba(255,255,255,0.08)", borderRadius: 10, overflow: "hidden" }}>
                <div style={{ height: "100%", width: `${(it.valor / maximo) * 100 * p}%`, borderRadius: 10,
                              background: ganador ? AMARILLO : VERDE }} />
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ---------- línea de tiempo ----------
const LineaTiempo: React.FC<{ g: Extract<Grafico, { tipo: "linea_tiempo" }>; frames: number }> = ({ g, frames }) => {
  const f = useCurrentFrame();
  const n = g.eventos.length;
  const x0 = 300, x1 = 1620, y = 520;
  const progreso = interpolate(f, [5, frames * 0.7], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ fontFamily }}>
      <Titulo texto={g.titulo} />
      <svg width={1920} height={1080} style={{ position: "absolute" }}>
        <line x1={x0} y1={y} x2={x0 + (x1 - x0) * progreso} y2={y} stroke="rgba(255,255,255,0.55)" strokeWidth={6} strokeLinecap="round" />
      </svg>
      {g.eventos.map((ev, k) => {
        const x = n === 1 ? (x0 + x1) / 2 : x0 + ((x1 - x0) * k) / (n - 1);
        const ini = aparicion(k, n, frames);
        const e = spring({ frame: f - ini, fps: 30, config: { damping: 14 } });
        const dest = g.destacado === k;
        const arriba = k % 2 === 0;
        return (
          <div key={k}>
            <div style={{ position: "absolute", left: x - 18, top: y - 18, width: 36, height: 36, borderRadius: 18,
                          background: dest ? AMARILLO : VERDE, transform: `scale(${e})`, boxShadow: "0 0 30px rgba(255,214,10,0.4)" }} />
            <div style={{ position: "absolute", left: x - 190, width: 380, textAlign: "center", opacity: e,
                          top: arriba ? y - 230 : y + 50, transform: `translateY(${(1 - e) * (arriba ? 20 : -20)}px)` }}>
              <div style={{ fontSize: 50, fontWeight: 900, color: dest ? AMARILLO : "white" }}>{ev.fecha}</div>
              <div style={{ fontSize: 30, fontWeight: 600, color: TEXTO_SUAVE, lineHeight: 1.25, marginTop: 6 }}>{ev.texto}</div>
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// ---------- mapa con puntos y rutas ----------
const PAISES = (feature as any)(mundo as any, (mundo as any).objects.countries).features;

const Mapa: React.FC<{ g: Extract<Grafico, { tipo: "mapa" }>; frames: number }> = ({ g, frames }) => {
  const f = useCurrentFrame();
  const W = 1920, H = 1080 - ABAJO;
  // encuadre: los puntos con margen (mínimo ~30º de ancho); o el mundo entero
  let proj: any;
  if (g.mundo || g.puntos.length === 0) {
    proj = geoNaturalEarth1().fitExtent([[80, 140], [W - 80, H - 20]], { type: "Sphere" });
  } else {
    const lons = g.puntos.map((p) => p.lon), lats = g.puntos.map((p) => p.lat);
    const cx = (Math.min(...lons) + Math.max(...lons)) / 2, cy = (Math.min(...lats) + Math.max(...lats)) / 2;
    const dx = Math.max(30, (Math.max(...lons) - Math.min(...lons)) * 1.6) / 2;
    const dy = Math.max(18, (Math.max(...lats) - Math.min(...lats)) * 1.6) / 2;
    // las esquinas como puntos (un polígono depende del sentido de giro en d3 y puede salir "todo menos la caja")
    const caja = { type: "MultiPoint", coordinates: [[cx - dx, cy - dy], [cx + dx, cy + dy], [cx - dx, cy + dy], [cx + dx, cy - dy]] };
    proj = geoMercator().fitExtent([[120, 160], [W - 120, H - 40]], caja);
  }
  const camino = geoPath(proj);
  const zoom = interpolate(f, [0, frames], [1.0, 1.06], { extrapolateRight: "clamp" });
  const pts = g.puntos.map((p) => proj([p.lon, p.lat]) as [number, number]);
  const n = pts.length;
  return (
    <AbsoluteFill style={{ fontFamily }}>
      <svg width={W} height={1080} style={{ position: "absolute", transform: `scale(${zoom})`, transformOrigin: "50% 45%" }}>
        <defs>
          <marker id="punta" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="5" markerHeight="5" orient="auto">
            <path d="M0,0 L10,5 L0,10 z" fill={AMARILLO} />
          </marker>
        </defs>
        {PAISES.map((p: any, i: number) => (
          <path key={i} d={camino(p) || ""} fill="#22312a" stroke="#3d5a4b" strokeWidth={1.2} />
        ))}
        {(g.rutas || []).map(([a, b], k) => {
          if (!pts[a] || !pts[b]) return null;
          const [x1, y1] = pts[a], [x2, y2] = pts[b];
          const mx = (x1 + x2) / 2, my = (y1 + y2) / 2 - Math.hypot(x2 - x1, y2 - y1) * 0.25;
          const d = `M${x1},${y1} Q${mx},${my} ${x2},${y2}`;
          const largo = Math.hypot(x2 - x1, y2 - y1) * 1.25;
          const ini = aparicion(Math.max(a, b), n, frames) + 10;
          const p = interpolate(f, [ini, ini + 40], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <path key={`r${k}`} d={d} fill="none" stroke={AMARILLO} strokeWidth={7} strokeLinecap="round"
                  strokeDasharray={largo} strokeDashoffset={largo * (1 - p)} markerEnd={p > 0.95 ? "url(#punta)" : undefined} />
          );
        })}
        {pts.map(([x, y], k) => {
          const ini = aparicion(k, n, frames);
          const e = spring({ frame: f - ini, fps: 30, config: { damping: 12 } });
          const pulso = 1 + 0.5 * ((f - ini) % 40) / 40;
          return (
            <g key={`p${k}`} opacity={e}>
              <circle cx={x} cy={y} r={16 * pulso} fill="none" stroke={AMARILLO} strokeWidth={3} opacity={1 - ((f - ini) % 40) / 40} />
              <circle cx={x} cy={y} r={12 * e} fill={AMARILLO} />
            </g>
          );
        })}
      </svg>
      {pts.map(([x, y], k) => {
        const e = spring({ frame: f - aparicion(k, n, frames) - 6, fps: 30, config: { damping: 14 } });
        return (
          <div key={`l${k}`} style={{ position: "absolute", left: x * zoom + (960 - 960 * zoom) + 22, top: y * zoom + (486 - 486 * zoom) - 30,
                                      fontSize: 36, fontWeight: 900, color: "white", opacity: e, whiteSpace: "nowrap",
                                      textShadow: "0 3px 12px rgba(0,0,0,0.9)" }}>
            {g.puntos[k].nombre}
          </div>
        );
      })}
      {g.titulo ? <Titulo texto={g.titulo} /> : null}
    </AbsoluteFill>
  );
};

// ---------- lista y proceso ----------
const Lista: React.FC<{ g: Extract<Grafico, { tipo: "lista" }>; frames: number }> = ({ g, frames }) => {
  const f = useCurrentFrame();
  const n = g.puntos.length;
  return (
    <AbsoluteFill style={{ fontFamily }}>
      <Titulo texto={g.titulo} />
      <div style={{ position: "absolute", top: 220, left: 160, right: 160, bottom: ABAJO + 20, display: "flex",
                    flexDirection: "column", justifyContent: "center", gap: 34 }}>
        {g.puntos.map((t, k) => {
          const e = spring({ frame: f - aparicion(k, n, frames), fps: 30, config: { damping: 15 } });
          return (
            <div key={k} style={{ display: "flex", alignItems: "center", gap: 34, opacity: e, transform: `translateX(${(1 - e) * 80}px)` }}>
              <div style={{ minWidth: 86, height: 86, borderRadius: 43, background: AMARILLO, color: "#0b0f0d", fontSize: 48,
                            fontWeight: 900, display: "flex", alignItems: "center", justifyContent: "center" }}>{k + 1}</div>
              <div style={{ fontSize: 50, fontWeight: 800, color: "white", lineHeight: 1.2 }}>{t}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const Proceso: React.FC<{ g: Extract<Grafico, { tipo: "proceso" }>; frames: number }> = ({ g, frames }) => {
  const f = useCurrentFrame();
  const n = g.pasos.length;
  const ancho = Math.min(420, 1600 / n - 40);
  return (
    <AbsoluteFill style={{ fontFamily }}>
      <Titulo texto={g.titulo} />
      <div style={{ position: "absolute", top: 200, left: 0, right: 0, bottom: ABAJO, display: "flex", alignItems: "center",
                    justifyContent: "center", gap: 20 }}>
        {g.pasos.map((t, k) => {
          const e = spring({ frame: f - aparicion(k, n, frames), fps: 30, config: { damping: 15 } });
          return (
            <React.Fragment key={k}>
              {k > 0 ? <div style={{ fontSize: 70, color: AMARILLO, fontWeight: 900, opacity: e }}>→</div> : null}
              <div style={{ width: ancho, minHeight: 300, padding: "34px 28px", borderRadius: 26, background: "rgba(255,255,255,0.07)",
                            border: `3px solid ${k === n - 1 ? AMARILLO : "rgba(255,255,255,0.18)"}`, opacity: e,
                            transform: `translateY(${(1 - e) * 60}px)`, display: "flex", flexDirection: "column", gap: 18 }}>
                <div style={{ fontSize: 34, fontWeight: 900, color: AMARILLO }}>PASO {k + 1}</div>
                <div style={{ fontSize: 40, fontWeight: 800, color: "white", lineHeight: 1.2 }}>{t}</div>
              </div>
            </React.Fragment>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ---------- cita y titular ----------
const Cita: React.FC<{ g: Extract<Grafico, { tipo: "cita" }> }> = ({ g }) => {
  const e = useEntrada(0, 20);
  const a = useEntrada(25);
  return (
    <AbsoluteFill style={{ fontFamily, alignItems: "center", justifyContent: "center", paddingBottom: ABAJO }}>
      <div style={{ maxWidth: 1450, opacity: e, transform: `translateY(${(1 - e) * 30}px)` }}>
        <div style={{ fontSize: 220, lineHeight: 0.6, color: AMARILLO, fontWeight: 900 }}>“</div>
        <div style={{ fontSize: 62, fontWeight: 600, fontStyle: "italic", color: "white", lineHeight: 1.3 }}>{g.texto}</div>
        <div style={{ marginTop: 40, fontSize: 40, fontWeight: 800, color: AMARILLO, opacity: a }}>
          — {g.autor}{g.obra ? <span style={{ color: TEXTO_SUAVE, fontWeight: 600 }}>, {g.obra}</span> : null}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Titular: React.FC<{ g: Extract<Grafico, { tipo: "titular" }> }> = ({ g }) => {
  const f = useCurrentFrame();
  const palabras = g.texto.split(" ");
  const s = useEntrada(8 + palabras.length * 4);
  return (
    <AbsoluteFill style={{ fontFamily, alignItems: "center", justifyContent: "center", paddingBottom: ABAJO }}>
      <div style={{ maxWidth: 1600, textAlign: "center", fontSize: 108, fontWeight: 900, lineHeight: 1.05, textTransform: "uppercase" }}>
        {palabras.map((w, k) => {
          const e = spring({ frame: f - k * 4, fps: 30, config: { damping: 13 } });
          return (
            <span key={k} style={{ display: "inline-block", marginRight: 26, opacity: e, transform: `translateY(${(1 - e) * 40}px)`,
                                   color: k === palabras.length - 1 ? AMARILLO : "white", textShadow: "0 12px 40px rgba(0,0,0,0.7)" }}>
              {w}
            </span>
          );
        })}
      </div>
      {g.subtitulo ? (
        <div style={{ marginTop: 30, fontSize: 44, fontWeight: 700, color: TEXTO_SUAVE, opacity: s, maxWidth: 1400, textAlign: "center" }}>
          {g.subtitulo}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

export const PlanoGrafico: React.FC<{ g: Grafico; frames: number; fondo?: string }> = ({ g, frames, fondo }) => {
  const f = useCurrentFrame();
  const salida = interpolate(f, [frames - 8, frames], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  let cuerpo: React.ReactNode = null;
  switch (g.tipo) {
    case "cifra": cuerpo = <Cifra g={g} frames={frames} />; break;
    case "comparativa": cuerpo = <Comparativa g={g} frames={frames} />; break;
    case "linea_tiempo": cuerpo = <LineaTiempo g={g} frames={frames} />; break;
    case "mapa": cuerpo = <Mapa g={g} frames={frames} />; break;
    case "lista": cuerpo = <Lista g={g} frames={frames} />; break;
    case "proceso": cuerpo = <Proceso g={g} frames={frames} />; break;
    case "cita": cuerpo = <Cita g={g} />; break;
    default: cuerpo = <Titular g={g as Extract<Grafico, { tipo: "titular" }>} />;
  }
  return (
    <AbsoluteFill>
      <Fondo fondo={fondo} frames={frames} />
      <AbsoluteFill style={{ opacity: salida }}>{cuerpo}</AbsoluteFill>
    </AbsoluteFill>
  );
};
