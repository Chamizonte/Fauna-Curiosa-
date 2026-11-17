import React from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  OffthreadVideo,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Montserrat";

const { fontFamily } = loadFont("normal", { weights: ["800", "900"] });

export type Plano = {
  src: string; // archivo en public/ ya recortado a 1080x1920
  duracion: number; // segundos en pantalla
};
export type Palabra = { t: string; ini: number; fin: number };
export type PropsShort = {
  duracion: number;
  planos: Plano[];
  palabras: Palabra[];
  gancho: string;
  ganchoFin?: number; // segundo en que termina la primera frase (el gancho la sustituye)
  voz?: string;
  musica?: string;
  volMusica: number;
};

const AMARILLO = "#FFD60A";
const FUNDIDO = 5; // fotogramas de fundido cruzado entre planos

// ---------- Vídeo: planos encadenados con zoom lento ----------
const PlanoVideo: React.FC<{ plano: Plano; frames: number; indice: number }> = ({ plano, frames, indice }) => {
  const f = useCurrentFrame();
  const opacidad = indice === 0 ? 1 : interpolate(f, [0, FUNDIDO], [0, 1], { extrapolateRight: "clamp" });
  // alterna acercar / alejar para que no todos los planos se muevan igual
  const [z0, z1] = indice % 2 === 0 ? [1.0, 1.08] : [1.08, 1.0];
  const zoom = interpolate(f, [0, frames], [z0, z1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ opacity: opacidad }}>
      <OffthreadVideo
        src={staticFile(plano.src)}
        muted
        style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${zoom})` }}
      />
    </AbsoluteFill>
  );
};

// ---------- Gancho: texto grande los primeros segundos ----------
const Gancho: React.FC<{ texto: string; fin: number }> = ({ texto, fin }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const entrada = spring({ frame: f, fps, config: { damping: 14, stiffness: 160 } });
  const salida = interpolate(f, [fps * (fin - 0.3), fps * fin], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: "center", paddingTop: 300 }}>
      <div
        style={{
          fontFamily,
          fontWeight: 900,
          fontSize: 88,
          lineHeight: 1.05,
          color: "white",
          textAlign: "center",
          padding: "28px 44px",
          maxWidth: 960,
          background: "rgba(0,0,0,0.55)",
          borderRadius: 28,
          borderBottom: `10px solid ${AMARILLO}`,
          textTransform: "uppercase",
          opacity: salida,
          transform: `translateY(${(1 - entrada) * -80}px) scale(${0.9 + 0.1 * entrada})`,
        }}
      >
        {texto}
      </div>
    </AbsoluteFill>
  );
};

// ---------- Subtítulos palabra a palabra ----------
function agrupar(palabras: Palabra[], maxPorGrupo = 3): Palabra[][] {
  const grupos: Palabra[][] = [];
  let actual: Palabra[] = [];
  for (const p of palabras) {
    actual.push(p);
    const finFrase = /[.,;:?!¿¡…]$/.test(p.t);
    if (actual.length >= maxPorGrupo || finFrase) {
      grupos.push(actual);
      actual = [];
    }
  }
  if (actual.length) grupos.push(actual);
  return grupos;
}

const Subtitulos: React.FC<{ palabras: Palabra[]; desde: number }> = ({ palabras, desde }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = f / fps;
  // mientras el gancho está en pantalla no se repite su frase en subtítulos
  const grupos = agrupar(palabras.filter((p) => p.ini >= desde - 0.01));
  const grupo = grupos.find((g) => t >= g[0].ini - 0.05 && t < g[g.length - 1].fin + 0.25);
  if (!grupo) return null;
  return (
    <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: "center", paddingTop: 1130 }}>
      <div style={{ textAlign: "center", maxWidth: 940 }}>
        {grupo.map((p, i) => {
          const activa = t >= p.ini && t < p.fin + 0.05;
          const pop = spring({ frame: f - Math.round(p.ini * fps), fps, config: { damping: 10, stiffness: 220 } });
          return (
            <span
              key={i}
              style={{
                display: "inline-block",
                margin: "0 22px",
                transformOrigin: "center bottom",
                fontFamily,
                fontWeight: 900,
                fontSize: 96,
                color: activa ? AMARILLO : "white",
                // El trazo va DETRÁS del relleno: si no, Montserrat (contornos solapados)
                // enseña rayas negras dentro de las letras.
                WebkitTextStroke: "12px black",
                paintOrder: "stroke fill",
                textShadow: "0 8px 24px rgba(0,0,0,0.85)",
                transform: activa ? `scale(${1 + 0.07 * pop})` : "scale(1)",
                textTransform: "uppercase",
              }}
            >
              {p.t}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

export const Short: React.FC<PropsShort> = (props) => {
  const { fps, durationInFrames } = useVideoConfig();
  let desde = 0;
  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {props.planos.map((p, i) => {
        const frames = Math.round(p.duracion * fps);
        const inicio = Math.max(0, desde - (i === 0 ? 0 : FUNDIDO));
        desde += frames;
        return (
          <Sequence key={i} from={inicio} durationInFrames={frames + (i === 0 ? 0 : FUNDIDO)}>
            <PlanoVideo plano={p} frames={frames} indice={i} />
          </Sequence>
        );
      })}
      {/* degradados para que el texto se lea sobre cualquier fondo */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(0,0,0,0.35) 0%, rgba(0,0,0,0) 30%, rgba(0,0,0,0) 50%, rgba(0,0,0,0.45) 75%, rgba(0,0,0,0.2) 100%)",
        }}
      />
      <Sequence durationInFrames={Math.round(fps * (props.ganchoFin ?? 3))}>
        <Gancho texto={props.gancho} fin={props.ganchoFin ?? 3} />
      </Sequence>
      <Subtitulos palabras={props.palabras} desde={props.ganchoFin ?? 0} />
      {props.voz ? <Audio src={staticFile(props.voz)} /> : null}
      {props.musica ? (
        <Audio
          src={staticFile(props.musica)}
          loop
          volume={(f) =>
            interpolate(f, [0, 15, durationInFrames - 30, durationInFrames], [0, props.volMusica, props.volMusica, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            })
          }
        />
      ) : null}
    </AbsoluteFill>
  );
};
