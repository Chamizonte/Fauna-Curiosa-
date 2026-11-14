import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  OffthreadVideo,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Montserrat";

const { fontFamily } = loadFont("normal", { weights: ["600", "800", "900"] });

// Vídeo largo horizontal 1920x1080: planos encadenados, subtítulos por frases,
// rótulos inferiores, cartelas de capítulo y cartelas de texto (cifras, fechas).
export type PlanoLargo = { src: string; duracion: number };
export type Tramo = { texto: string; ini: number; fin: number };
export type PropsLargo = {
  duracion: number;
  planos: PlanoLargo[];
  subtitulos: Tramo[];
  rotulos: Tramo[];
  capitulos: { titulo: string; ini: number; numero: number }[];
  cartelas: Tramo[];
  voz?: string;
  musica?: string;
  volMusica: number;
};

const AMARILLO = "#FFD60A";
const FUNDIDO = 12;

const Plano: React.FC<{ src: string; frames: number; indice: number }> = ({ src, frames, indice }) => {
  const f = useCurrentFrame();
  const opacidad = indice === 0 ? 1 : interpolate(f, [0, FUNDIDO], [0, 1], { extrapolateRight: "clamp" });
  const [z0, z1] = indice % 2 === 0 ? [1.0, 1.05] : [1.05, 1.0];
  const zoom = interpolate(f, [0, frames], [z0, z1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ opacity: opacidad }}>
      <OffthreadVideo
        src={staticFile(src)}
        muted
        style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${zoom})` }}
      />
    </AbsoluteFill>
  );
};

const Subtitulo: React.FC<{ texto: string }> = ({ texto }) => (
  <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 70 }}>
    <div
      style={{
        fontFamily,
        fontWeight: 800,
        fontSize: 46,
        color: "white",
        textAlign: "center",
        maxWidth: 1500,
        padding: "8px 22px",
        background: "rgba(0,0,0,0.55)",
        borderRadius: 12,
        lineHeight: 1.25,
      }}
    >
      {texto}
    </div>
  </AbsoluteFill>
);

const Rotulo: React.FC<{ texto: string; frames: number }> = ({ texto, frames }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const entrada = spring({ frame: f, fps, config: { damping: 16 } });
  const salida = interpolate(f, [frames - 10, frames], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: "flex-start", padding: "70px 80px" }}>
      <div
        style={{
          fontFamily,
          fontWeight: 900,
          fontSize: 64,
          color: "white",
          textTransform: "uppercase",
          borderLeft: `12px solid ${AMARILLO}`,
          padding: "10px 26px",
          background: "rgba(0,0,0,0.6)",
          opacity: salida,
          transform: `translateX(${(1 - entrada) * -120}px)`,
        }}
      >
        {texto}
      </div>
    </AbsoluteFill>
  );
};

const Capitulo: React.FC<{ titulo: string; numero: number; frames: number }> = ({ titulo, numero, frames }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const entrada = spring({ frame: f, fps, config: { damping: 18 } });
  const salida = interpolate(f, [frames - 15, frames], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        background: `rgba(0,0,0,${0.45 * salida})`,
        opacity: salida,
      }}
    >
      <div style={{ fontFamily, textAlign: "center", transform: `scale(${0.85 + 0.15 * entrada})` }}>
        <div style={{ color: AMARILLO, fontWeight: 800, fontSize: 40, letterSpacing: 8 }}>CAPÍTULO {numero}</div>
        <div style={{ color: "white", fontWeight: 900, fontSize: 96, textTransform: "uppercase", maxWidth: 1600 }}>
          {titulo}
        </div>
        <div style={{ margin: "18px auto 0", height: 8, width: 260 * entrada, background: AMARILLO, borderRadius: 4 }} />
      </div>
    </AbsoluteFill>
  );
};

const Cartela: React.FC<{ texto: string }> = ({ texto }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const entrada = spring({ frame: f, fps, config: { damping: 14, stiffness: 140 } });
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", background: "rgba(5,10,8,0.72)" }}>
      <div
        style={{
          fontFamily,
          fontWeight: 900,
          fontSize: 110,
          color: AMARILLO,
          textAlign: "center",
          maxWidth: 1600,
          textTransform: "uppercase",
          lineHeight: 1.05,
          transform: `scale(${0.8 + 0.2 * entrada})`,
          opacity: entrada,
          textShadow: "0 10px 40px rgba(0,0,0,0.8)",
        }}
      >
        {texto}
      </div>
    </AbsoluteFill>
  );
};

export const Largo: React.FC<PropsLargo> = (props) => {
  const { fps, durationInFrames } = useVideoConfig();
  const fr = (s: number) => Math.round(s * fps);
  let desde = 0;
  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {props.planos.map((p, i) => {
        const frames = fr(p.duracion);
        const inicio = Math.max(0, desde - (i === 0 ? 0 : FUNDIDO));
        desde += frames;
        return (
          <Sequence key={`p${i}`} from={inicio} durationInFrames={frames + (i === 0 ? 0 : FUNDIDO)}>
            <Plano src={p.src} frames={frames} indice={i} />
          </Sequence>
        );
      })}
      {props.cartelas.map((c, i) => (
        <Sequence key={`c${i}`} from={fr(c.ini)} durationInFrames={Math.max(1, fr(c.fin - c.ini))}>
          <Cartela texto={c.texto} />
        </Sequence>
      ))}
      {props.rotulos.map((r, i) => (
        <Sequence key={`r${i}`} from={fr(r.ini)} durationInFrames={Math.max(1, fr(r.fin - r.ini))}>
          <Rotulo texto={r.texto} frames={fr(r.fin - r.ini)} />
        </Sequence>
      ))}
      {props.subtitulos.map((s, i) => (
        <Sequence key={`s${i}`} from={fr(s.ini)} durationInFrames={Math.max(1, fr(s.fin - s.ini))}>
          <Subtitulo texto={s.texto} />
        </Sequence>
      ))}
      {props.capitulos.map((c, i) =>
        c.numero > 0 ? (
          <Sequence key={`k${i}`} from={fr(c.ini)} durationInFrames={fr(3)}>
            <Capitulo titulo={c.titulo} numero={c.numero} frames={fr(3)} />
          </Sequence>
        ) : null,
      )}
      {props.voz ? <Audio src={staticFile(props.voz)} /> : null}
      {props.musica ? (
        <Audio
          src={staticFile(props.musica)}
          loop
          volume={(f) =>
            interpolate(f, [0, 30, durationInFrames - 90, durationInFrames], [0, props.volMusica, props.volMusica, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            })
          }
        />
      ) : null}
    </AbsoluteFill>
  );
};

// ---------- Miniatura 1280x720 ----------
export type PropsMiniatura = { imagen: string; texto: string; posicionX: number };

export const Miniatura: React.FC<PropsMiniatura> = ({ imagen, texto, posicionX }) => {
  // animal a un lado, texto grande al otro (regla de la miniatura: 1 sujeto + 2-4 palabras)
  const animalIzq = posicionX < 0.5;
  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <Img
        src={staticFile(imagen)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          objectPosition: `${Math.round(posicionX * 100)}% 50%`,
          filter: "saturate(1.25) contrast(1.12) brightness(1.05)",
        }}
      />
      <AbsoluteFill
        style={{
          background: animalIzq
            ? "linear-gradient(90deg, rgba(0,0,0,0) 35%, rgba(0,0,0,0.75) 70%)"
            : "linear-gradient(270deg, rgba(0,0,0,0) 35%, rgba(0,0,0,0.75) 70%)",
        }}
      />
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: animalIzq ? "flex-end" : "flex-start",
          padding: "0 60px",
        }}
      >
        <div
          style={{
            fontFamily,
            fontWeight: 900,
            fontSize: 118,
            lineHeight: 0.98,
            color: "white",
            textTransform: "uppercase",
            textAlign: animalIzq ? "right" : "left",
            maxWidth: 640,
            // el contorno se pinta por detrás del relleno (sin artefactos dentro de las letras)
            WebkitTextStroke: "14px black",
            paintOrder: "stroke fill",
            textShadow: "0 10px 0 rgba(0,0,0,0.9)",
          }}
        >
          {texto.split(" ").map((w, i, a) => (
            <span key={i} style={{ color: i === a.length - 1 ? AMARILLO : "white" }}>
              {w}{" "}
            </span>
          ))}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
