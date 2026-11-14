import React from "react";
import { CalculateMetadataFunction, Composition, Still } from "remotion";
import { PropsShort, Short } from "./Short";
import { PropsTarjeta, Tarjeta } from "./Tarjeta";
import { Largo, Miniatura, PropsLargo, PropsMiniatura } from "./Largo";

const FPS = 30;

const metadatos: CalculateMetadataFunction<PropsShort> = ({ props }) => ({
  durationInFrames: Math.max(1, Math.ceil(props.duracion * FPS)),
});

// Props de ejemplo: solo para abrir la plantilla en Remotion Studio.
const ejemplo: PropsShort = {
  duracion: 6,
  planos: [],
  palabras: [
    { t: "¿Por", ini: 0.2, fin: 0.4 },
    { t: "qué", ini: 0.4, fin: 0.6 },
    { t: "pasa", ini: 0.6, fin: 0.9 },
    { t: "esto?", ini: 0.9, fin: 1.3 },
  ],
  gancho: "¿POR QUÉ PASA ESTO?",
  volMusica: 0.12,
};

const metadatosTarjeta: CalculateMetadataFunction<PropsTarjeta> = ({ props }) => ({
  durationInFrames: Math.max(1, Math.ceil(props.duracion * FPS)),
});

const ejemploTarjeta: PropsTarjeta = {
  duracion: 8,
  titular: "¿Sabías que…?",
  numero: 1,
  texto: "Esto **no es una avispa**. Es un sírfido, una mosca disfrazada para que **no se la coman**.",
  planos: [],
  volMusica: 0.35,
};

const metadatosLargo: CalculateMetadataFunction<PropsLargo> = ({ props }) => ({
  durationInFrames: Math.max(1, Math.ceil(props.duracion * FPS)),
});

const ejemploLargo: PropsLargo = {
  duracion: 5, planos: [], subtitulos: [], rotulos: [], cartelas: [{ texto: "3 toneladas", ini: 0, fin: 5 }],
  capitulos: [], volMusica: 0.12,
};
const ejemploMiniatura: PropsMiniatura = { imagen: "render/miniatura.jpg", texto: "EL PRIMER TANQUE", posicionX: 0.3 };

export const Root: React.FC = () => (
  <>
    <Composition
      id="Largo"
      component={Largo}
      fps={FPS}
      width={1920}
      height={1080}
      durationInFrames={FPS * 5}
      defaultProps={ejemploLargo}
      calculateMetadata={metadatosLargo}
    />
    <Still id="Miniatura" component={Miniatura} width={1280} height={720} defaultProps={ejemploMiniatura} />
    <Composition
      id="Short"
      component={Short}
      fps={FPS}
      width={1080}
      height={1920}
      durationInFrames={FPS * 6}
      defaultProps={ejemplo}
      calculateMetadata={metadatos}
    />
    <Composition
      id="Tarjeta"
      component={Tarjeta}
      fps={FPS}
      width={1080}
      height={1920}
      durationInFrames={FPS * 8}
      defaultProps={ejemploTarjeta}
      calculateMetadata={metadatosTarjeta}
    />
  </>
);
