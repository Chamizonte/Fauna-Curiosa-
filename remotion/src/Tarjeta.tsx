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

const { fontFamily } = loadFont("normal", { weights: ["600", "800", "900"] });

// Formato "¿Sabías que…?" en tarjeta: texto arriba, vídeo/foto horizontal en el centro,
// sin voz (solo música). Funciona con material horizontal sin recortarlo a vertical.
export type PlanoTarjeta = { src: string; duracion: number }; // ya recortado a ANCHO x ALTO
export type PropsTarjeta = {
  duracion: number;
  titular: string; // p. ej. "¿SABÍAS QUE…?"
  numero?: number;
  texto: string; // admite **resaltado**
  planos: PlanoTarjeta[];
  musica?: string;
  volMusica: number;
};

export const ANCHO_MEDIA = 1000;
export const ALTO_MEDIA = 760;
const AMARILLO = "#FFD60A";
const COLORES = [AMARILLO, "#7CF29A", "#FF9F43", "#6EC6FF"];
const FUNDIDO = 6;

// "**palabra**" -> resaltada; cada resaltado con un color distinto, en rotación
function trozos(texto: string) {
  return texto.split(/(\*\*[^*]+\*\*)/g).filter(Boolean).map((t, i) =>
    t.startsWith("**") ? { t: t.slice(2, -2), resaltado: true, i } : { t, resaltado: false, i },
  );
}

const Media: React.FC<{ planos: PlanoTarjeta[] }> = ({ planos }) => {
  const { fps } = useVideoConfig();
  let desde = 0;
  return (
    <div
      style={{
        position: "relative",
        width: ANCHO_MEDIA,
        height: ALTO_MEDIA,
        borderRadius: 26,
        overflow: "hidden",
        boxShadow: "0 20px 60px rgba(0,0,0,0.7)",
        border: "3px solid rgba(255,255,255,0.12)",
        background: "#111",
      }}
    >
      {planos.map((p, i) => {
        const frames = Math.round(p.duracion * fps);
        const inicio = Math.max(0, desde - (i === 0 ? 0 : FUNDIDO));
        desde += frames;
        return (
          <Sequence key={i} from={inicio} durationInFrames={frames + (i === 0 ? 0 : FUNDIDO)}>
            <PlanoMedia src={p.src} frames={frames} indice={i} />
          </Sequence>
        );
      })}
    </div>
  );
};

const PlanoMedia: React.FC<{ src: string; frames: number; indice: number }> = ({ src, frames, indice }) => {
  const f = useCurrentFrame();
  const opacidad = indice === 0 ? 1 : interpolate(f, [0, FUNDIDO], [0, 1], { extrapolateRight: "clamp" });
  const [z0, z1] = indice % 2 === 0 ? [1.0, 1.06] : [1.06, 1.0];
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

export const Tarjeta: React.FC<PropsTarjeta> = (props) => {
  const f = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const entrada = spring({ frame: f, fps, config: { damping: 16, stiffness: 120 } });
  const entradaTexto = spring({ frame: f - 6, fps, config: { damping: 18, stiffness: 110 } });
  const progreso = f / durationInFrames;
  let color = 0;
  return (
    <AbsoluteFill
      style={{
        background: "radial-gradient(ellipse at 50% 30%, #1f2a24 0%, #0b0f0d 70%)",
        alignItems: "center",
        fontFamily,
      }}
    >
      {/* Cabecera */}
      <div
        style={{
          marginTop: 170,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          opacity: entrada,
          transform: `translateY(${(1 - entrada) * -40}px)`,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
          <div
            style={{
              width: 64,
              height: 64,
              borderRadius: 32,
              background: AMARILLO,
              color: "#0b0f0d",
              fontWeight: 900,
              fontSize: 30,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            CF
          </div>
          <div style={{ color: "white", fontWeight: 800, fontSize: 44 }}>
            Curiosa <span style={{ color: AMARILLO }}>Fauna</span>
            {props.numero ? <span style={{ color: "#9aa59f", fontWeight: 600 }}> #{props.numero}</span> : null}
          </div>
        </div>
        <div
          style={{
            marginTop: 14,
            color: AMARILLO,
            fontWeight: 900,
            fontSize: 58,
            textTransform: "uppercase",
            textAlign: "center",
            maxWidth: 980,
            lineHeight: 1.05,
          }}
        >
          {props.titular}
        </div>
      </div>

      {/* Texto del dato */}
      <div
        style={{
          marginTop: 34,
          maxWidth: 960,
          color: "white",
          fontWeight: 800,
          fontSize: 47,
          lineHeight: 1.28,
          textAlign: "center",
          opacity: entradaTexto,
          transform: `translateY(${(1 - entradaTexto) * 30}px)`,
        }}
      >
        {trozos(props.texto).map((t) =>
          t.resaltado ? (
            <span key={t.i} style={{ color: COLORES[color++ % COLORES.length] }}>
              {t.t}
            </span>
          ) : (
            <span key={t.i}>{t.t}</span>
          ),
        )}
      </div>

      {/* Vídeo o foto */}
      <div style={{ marginTop: 40, opacity: entrada }}>
        <Media planos={props.planos} />
      </div>

      {/* Barra de progreso: indica cuánto queda de lectura */}
      <div style={{ position: "absolute", bottom: 300, width: ANCHO_MEDIA, height: 8, borderRadius: 4, background: "rgba(255,255,255,0.12)" }}>
        <div style={{ width: `${progreso * 100}%`, height: "100%", borderRadius: 4, background: AMARILLO }} />
      </div>

      {props.musica ? (
        <Audio
          src={staticFile(props.musica)}
          loop
          volume={(fr) =>
            interpolate(fr, [0, 15, durationInFrames - 30, durationInFrames], [0, props.volMusica, props.volMusica, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            })
          }
        />
      ) : null}
    </AbsoluteFill>
  );
};
