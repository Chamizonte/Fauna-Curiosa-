import React from "react";
import {
  AbsoluteFill,
  Composition,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

// Prueba de rendimiento: 20 s a 1080x1920 con subtítulos palabra a palabra,
// para medir cuánto tarda el runner de GitHub en renderizar un short.
const PALABRAS =
  "¿Por qué este pulpo cambia de color en menos de un segundo? Bajo su piel tiene miles de células llamadas cromatóforos".split(
    " "
  );

const Subtitulo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const porPalabra = Math.round(fps * 0.4);
  const idx = Math.min(PALABRAS.length - 1, Math.floor(frame / porPalabra));
  const inicio = idx * porPalabra;
  const escala = spring({ frame: frame - inicio, fps, config: { damping: 12 } });
  const grupo = PALABRAS.slice(Math.max(0, idx - 2), idx + 1);
  return (
    <div
      style={{
        position: "absolute",
        bottom: 520,
        width: "100%",
        textAlign: "center",
        fontFamily: "Arial Black, sans-serif",
        fontSize: 86,
        color: "white",
        textShadow: "0 6px 18px rgba(0,0,0,.8)",
      }}
    >
      {grupo.map((p, i) => (
        <span
          key={i}
          style={{
            display: "inline-block",
            margin: "0 14px",
            color: i === grupo.length - 1 ? "#facc15" : "white",
            transform: i === grupo.length - 1 ? `scale(${0.8 + 0.2 * escala})` : undefined,
          }}
        >
          {p}
        </span>
      ))}
    </div>
  );
};

const PruebaShort: React.FC = () => {
  const frame = useCurrentFrame();
  const fondo = interpolate(frame, [0, 600], [0, 360]);
  return (
    <AbsoluteFill style={{ background: `hsl(${fondo}, 45%, 25%)` }}>
      <Subtitulo />
    </AbsoluteFill>
  );
};

export const Root: React.FC = () => (
  <Composition
    id="PruebaShort"
    component={PruebaShort}
    durationInFrames={600}
    fps={30}
    width={1080}
    height={1920}
  />
);
