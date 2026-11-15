// Zama, 202 a. C., visto desde arriba: Cartago arriba, Roma abajo.
// Las unidades y los elefantes se dibujan a mano en el canvas (sin el trazo
// tembloroso de los looks dibujados) y se mueven con s.p(), fotograma a fotograma.
const C = { roma: '#c8463a', romaBorde: '#7e221a', elef: '#9b968c', elefBorde: '#4b4740',
            velite: '#5b9bd5', pasillo: '#f4c430', texto: '#f1ece2', suave: '#a9a397' };
const quiet = { sfx: false };

const COLS = [480, 780, 1080, 1380];        // centro de cada columna de manípulos
const FILAS = [560, 700, 840];              // hastati, príncipes, triarios
const PASILLOS = [630, 930, 1230];          // centro de cada pasillo
const MW = 170, MH = 60;

function manipulo(ctx) {
  ctx.fillStyle = C.roma; ctx.strokeStyle = C.romaBorde; ctx.lineWidth = 4;
  ctx.beginPath(); ctx.roundRect(-MW / 2, -MH / 2, MW, MH, 8); ctx.fill(); ctx.stroke();
  ctx.fillStyle = 'rgba(255,255,255,0.28)';           // escudos en fila
  for (let i = 0; i < 6; i++) { ctx.beginPath(); ctx.ellipse(-62 + i * 25, 0, 8, 18, 0, 0, Math.PI * 2); ctx.fill(); }
}

// Elefante visto desde arriba, mirando hacia abajo (hacia Roma).
function elefante(ctx) {
  ctx.fillStyle = C.elef; ctx.strokeStyle = C.elefBorde; ctx.lineWidth = 3;
  ctx.beginPath(); ctx.ellipse(0, -30, 38, 55, 0, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  ctx.beginPath(); ctx.ellipse(-34, 20, 26, 20, -0.5, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  ctx.beginPath(); ctx.ellipse(34, 20, 26, 20, 0.5, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  ctx.beginPath(); ctx.arc(0, 28, 24, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  ctx.lineCap = 'round';
  ctx.strokeStyle = '#f3ecd8'; ctx.lineWidth = 5;
  ctx.beginPath(); ctx.moveTo(-10, 46); ctx.lineTo(-17, 68); ctx.moveTo(10, 46); ctx.lineTo(17, 68); ctx.stroke();
  ctx.strokeStyle = C.elefBorde; ctx.lineWidth = 10;
  ctx.beginPath(); ctx.moveTo(0, 48); ctx.quadraticCurveTo(7, 70, 0, 92); ctx.stroke();
  ctx.strokeStyle = C.elef; ctx.lineWidth = 6; ctx.stroke();
}

function velite(ctx) {
  ctx.fillStyle = C.velite; ctx.strokeStyle = '#1f4e7a'; ctx.lineWidth = 3;
  ctx.beginPath(); ctx.arc(0, 0, 13, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
}

// Cabecera y bandos, iguales en las tres escenas.
function marco(s, first) {
  const at = first ? 0 : -1, enter = first ? 'fade' : 'none';
  s.text('ZAMA · 202 a. C.', { x: 140, y: 90, align: 'left', size: 40, color: C.suave, at, enter, ...quiet });
  s.text('Elefantes de Aníbal', { x: 1780, y: 90, align: 'right', size: 40, color: C.elef, at, enter, ...quiet });
  s.text('Hastati', { x: 140, y: FILAS[0], align: 'left', size: 38, color: C.suave, at, enter, ...quiet });
  s.text('Príncipes', { x: 140, y: FILAS[1], align: 'left', size: 38, color: C.suave, at, enter, ...quiet });
  s.text('Triarios', { x: 140, y: FILAS[2], align: 'left', size: 38, color: C.suave, at, enter, ...quiet });
  s.text('Legiones de Escipión', { x: 1780, y: 990, align: 'right', size: 40, color: C.roma, at, enter, ...quiet });
}

// offset: cuánto se desplaza la fila central (150 = tablero de ajedrez, 0 = en fila).
function legiones(s, offset, at, enter = 'none') {
  FILAS.forEach((y, f) => COLS.forEach((x, c) => {
    const dx = f === 1 ? offset : 0;
    s.draw({ x: x + dx, y, at, enter, box: { x: 0, y: 0, w: MW, h: MH }, ...quiet }, manipulo);
  }));
}

function bandasPasillo(s, at, alpha = 0.18) {
  s.draw({ at, enter: 'fade', dur: 0.8, ...quiet }, (ctx) => {
    ctx.fillStyle = C.pasillo; ctx.globalAlpha *= alpha;
    PASILLOS.forEach((x) => ctx.fillRect(x - 60, 500, 120, 400));
  });
}

function elefanteEn(s, x, y, at) {
  s.draw({ x, y, at, enter: 'fade', box: { x: 0, y: 0, w: 120, h: 190 }, ...quiet }, elefante);
}

export default {
  tablero(s) {
    s.camera([]);
    marco(s, true);
    // Lo habitual: la fila central tapa los huecos de la primera.
    const p = s.p('#fila', 1.6, 'inOut');
    legiones(s, 150 * (1 - p), 0, 'fade');
    s.text('Lo habitual: tablero de ajedrez', { x: 960, y: 330, size: 52, color: C.texto, at: '#habitual', out: '#fila', ...quiet });
    s.text('Escipión: en fila', { x: 960, y: 330, size: 52, color: C.texto, at: '#fila', out: '#pasillos', ...quiet });
    bandasPasillo(s, '#pasillos');
    s.text('*Pasillos* abiertos', { x: 960, y: 330, size: 60, font: 'display', mark: C.pasillo, color: C.texto, at: '#pasillos', ...quiet });
    PASILLOS.forEach((x) => s.arrow([x, 395], [x, 485], { at: '#pasillos', color: C.pasillo, width: 5, headSize: 18, ...quiet }));
  },

  carga(s) {
    s.camera([]);
    marco(s, false);
    legiones(s, 0, -1);
    bandasPasillo(s, -1);
    // Tres elefantes bajan por los pasillos y salen por detrás sin tocar a nadie.
    const t0 = s.time('#carga');
    PASILLOS.forEach((x, i) => {
      const q = s.clamp((s.t - t0 - i * 0.35) / 5.2, 0, 1);
      elefanteEn(s, x, 210 + 980 * s.ease.inOut(q), '#carga');
    });
    s.text('¿Un muro?', { x: 960, y: 330, size: 52, color: C.texto, at: 'muro', out: '#largo', ...quiet });
    s.text('No: un *pasillo*', { x: 960, y: 330, size: 60, font: 'display', mark: C.pasillo, color: C.texto, at: '#largo', ...quiet });
  },

  velites(s) {
    s.camera([]);
    marco(s, false);
    legiones(s, 0, -1);
    bandasPasillo(s, -1, 0.12);
    s.text('Vélites con jabalinas', { x: 960, y: 330, size: 52, color: C.velite, at: '#velites', out: '#expuestos', ...quiet });

    // Vélites: una línea delante y dos en cada pasillo. Al cargar, se repliegan detrás.
    const r = s.p('#repliegue', 1.8, 'inOut');
    const delante = [330, 480, 630, 780, 930, 1080, 1230, 1380, 1530];
    delante.forEach((x, i) => {
      const y = s.lerp(460, 940, r);
      s.draw({ x: x + (i % 2 ? 8 : -8) * r, y, at: '#velites', enter: 'pop', ...quiet }, velite);
    });
    PASILLOS.forEach((x) => [610, 770].forEach((y0, k) => {
      const lado = k ? 1 : -1;  // uno se aparta a cada lado del pasillo
      const xa = s.lerp(x, x + lado * 44, s.p('#repliegue', 0.8));
      s.draw({ x: xa, y: s.lerp(y0, 940, r), at: 'huecos', enter: 'pop', ...quiet }, velite);
    }));

    // Un elefante carga por el pasillo central y queda entre dos fuegos.
    const tc = s.time('#cargan');
    const q = s.clamp((s.t - tc) / 6, 0, 1);
    elefanteEn(s, PASILLOS[1], 200 + 500 * s.ease.out(q), '#cargan');

    // Jabalinas desde ambos lados mientras avanza.
    const te = s.time('#expuestos');
    const ey = 200 + 500 * s.ease.out(s.clamp((te + 1 - tc) / 6, 0, 1));
    for (let k = 0; k < 8; k++) {
      const lado = k % 2 ? 1 : -1;
      const ts = te + 0.25 + k * 0.42;
      s.draw({ at: ts, out: ts + 0.75, exit: 'fade', outDur: 0.2, ...quiet }, (ctx, life) => {
        const u = s.clamp(life.local / 0.5, 0, 1);
        const y = ey - 60 + (k % 4) * 40;
        const x0 = PASILLOS[1] + lado * 260, x1 = PASILLOS[1] + lado * 40;
        const x = s.lerp(x0, x1, u);
        ctx.strokeStyle = '#e8dcc0'; ctx.lineWidth = 4; ctx.lineCap = 'round';
        ctx.beginPath(); ctx.moveTo(x + lado * 46, y + 6); ctx.lineTo(x, y); ctx.stroke();
      });
    }
    s.text('Fuego desde *ambos lados*', { x: 960, y: 330, size: 60, font: 'display', mark: C.pasillo, color: C.texto, at: '#expuestos', ...quiet });
  },
};
