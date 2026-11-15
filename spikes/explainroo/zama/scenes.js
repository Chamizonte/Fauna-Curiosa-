// Zama, 202 a. C., visto desde arriba: Cartago arriba, Roma abajo.
// Las unidades y los elefantes se dibujan a mano en el canvas y se mueven con
// s.p(), fotograma a fotograma. Los rótulos van ARRIBA porque en el vídeo largo
// nuestros subtítulos ocupan la parte de abajo.
const C = { roma: '#c8463a', romaBorde: '#7e221a', elef: '#a8a399', elefBorde: '#4b4740',
            velite: '#5b9bd5', pasillo: '#f4c430', texto: '#f1ece2', suave: '#b4aea2' };
const quiet = { sfx: false };

const COLS = [420, 800, 1180, 1560];        // centro de cada columna de manípulos
const FILAS = [480, 640, 800];              // hastati, príncipes, triarios
const PASILLOS = [610, 990, 1370];          // centro de cada pasillo
const MW = 220, MH = 80, ESC = 1.3;         // tamaño del manípulo y escala del elefante
const Y_TITULO = 112, Y_ELEF = 270, Y_DETRAS = 905;

function manipulo(ctx) {
  ctx.fillStyle = C.roma; ctx.strokeStyle = C.romaBorde; ctx.lineWidth = 5;
  ctx.beginPath(); ctx.roundRect(-MW / 2, -MH / 2, MW, MH, 10); ctx.fill(); ctx.stroke();
  ctx.fillStyle = 'rgba(255,255,255,0.28)';           // escudos en fila
  for (let i = 0; i < 7; i++) { ctx.beginPath(); ctx.ellipse(-84 + i * 28, 0, 9, 24, 0, 0, Math.PI * 2); ctx.fill(); }
}

// Elefante visto desde arriba, mirando hacia abajo (hacia Roma).
function elefante(ctx) {
  ctx.scale(ESC, ESC);
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
  ctx.beginPath(); ctx.arc(0, 0, 16, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
}

// Cabecera y nombres de las filas, iguales en las tres escenas.
function marco(s) {
  const o = { at: -1, ...quiet };
  s.text('ZAMA · 202 a. C.', { x: 110, y: Y_TITULO, align: 'left', size: 38, color: C.suave, ...o });
  s.text('Hastati', { x: 110, y: FILAS[0], align: 'left', size: 34, color: C.suave, ...o });
  s.text('Príncipes', { x: 110, y: FILAS[1], align: 'left', size: 34, color: C.suave, ...o });
  s.text('Triarios', { x: 110, y: FILAS[2], align: 'left', size: 34, color: C.suave, ...o });
}

// Rótulo central de arriba. `hasta` hace que se vaya sin fundido cuando entra el siguiente.
function rotulo(s, texto, at, hasta, o = {}) {
  s.text(texto, { x: 960, y: Y_TITULO, size: 56, font: 'display', mark: C.pasillo, color: C.texto,
                  at, out: hasta, exit: hasta ? 'none' : 'fade', ...quiet, ...o });
}

// offset: cuánto se desplaza la fila central (190 = tablero de ajedrez, 0 = en fila).
function legiones(s, offset = 0) {
  FILAS.forEach((y, f) => COLS.forEach((x) => {
    const dx = f === 1 ? offset : 0;
    s.draw({ x: x + dx, y, at: -1, box: { x: 0, y: 0, w: MW, h: MH }, ...quiet }, manipulo);
  }));
}

function bandasPasillo(s, at, alpha = 0.16) {
  s.draw({ at, enter: at === -1 ? 'none' : 'fade', dur: 0.8, ...quiet }, (ctx) => {
    ctx.fillStyle = C.pasillo; ctx.globalAlpha *= alpha;
    PASILLOS.forEach((x) => ctx.fillRect(x - 80, FILAS[0] - 70, 160, FILAS[2] - FILAS[0] + 140));
  });
}

function elefanteEn(s, x, y, at, o = {}) {
  s.draw({ x, y, at, enter: 'fade', box: { x: 0, y: 0, w: 120 * ESC, h: 190 * ESC }, overlap: true, ...quiet, ...o }, elefante);
}

export default {
  tablero(s) {
    s.camera([{ at: 0, x: 990, y: 600, zoom: 1.08 }, { at: '#pasillos', x: 990, y: 640, zoom: 1.18, dur: 2.5 }]);
    marco(s);
    // Lo habitual: la fila central tapa los huecos de la primera.
    legiones(s, 190 * (1 - s.p('#fila', 1.6, 'inOut')));
    rotulo(s, 'Lo habitual: en tablero de ajedrez', '#habitual', '#fila');
    rotulo(s, 'Escipión: una detrás de otra', '#fila', '#pasillos');
    bandasPasillo(s, '#pasillos');
    rotulo(s, '*Pasillos* abiertos', '#pasillos');
  },

  carga(s) {
    s.camera([{ at: 0, x: 990, y: 600, zoom: 1.0 }]);
    marco(s);
    legiones(s);
    bandasPasillo(s, -1);
    // Tres elefantes bajan por los pasillos y salen por detrás sin tocar a nadie.
    const t0 = s.time('#carga');
    PASILLOS.forEach((x, i) => {
      const q = s.clamp((s.t - t0 - i * 0.4) / 5.5, 0, 1);
      elefanteEn(s, x, Y_ELEF + 1000 * s.ease.inOut(q), '#carga');
    });
    rotulo(s, '¿Un muro?', 'muro', '#largo');
    rotulo(s, 'No: un *pasillo*', '#largo');
  },

  velites(s) {
    s.camera([{ at: 0, x: 990, y: 600, zoom: 1.0 },
              { at: '#expuestos', x: 990, y: 600, zoom: 1.35, dur: 2.2 }]);
    marco(s);
    legiones(s);
    bandasPasillo(s, -1, 0.1);
    rotulo(s, '*Vélites*: infantería ligera con jabalinas', '#velites', '#expuestos');

    // Vélites: una línea delante y dos en cada pasillo. Al cargar, se repliegan detrás.
    const r = s.p('#repliegue', 2.0, 'inOut');
    const delante = [230, 420, 610, 800, 990, 1180, 1370, 1560, 1750];
    delante.forEach((x, i) => {
      s.draw({ x: x + (i % 2 ? 10 : -10) * r, y: s.lerp(385, Y_DETRAS, r), at: '#velites', enter: 'pop', ...quiet }, velite);
    });
    PASILLOS.forEach((x) => [560, 720].forEach((y0, k) => {
      const lado = k ? 1 : -1;  // uno se aparta a cada lado del pasillo
      const xa = s.lerp(x, x + lado * 58, s.p('#repliegue', 0.8));
      s.draw({ x: xa, y: s.lerp(y0, Y_DETRAS + 30, r), at: 'huecos', enter: 'pop', ...quiet }, velite);
    }));

    // Un elefante carga por el pasillo central y queda entre dos fuegos.
    const tc = s.time('#cargan');
    const avance = (t) => Y_ELEF + 360 * s.ease.out(s.clamp((t - tc) / 6.5, 0, 1));
    elefanteEn(s, PASILLOS[1], avance(s.t), '#cargan');

    // Jabalinas desde ambos lados mientras avanza.
    const te = s.time('#expuestos');
    for (let k = 0; k < 10; k++) {
      const lado = k % 2 ? 1 : -1;
      const ts = te + 0.3 + k * 0.38;
      s.draw({ at: ts, out: ts + 0.7, exit: 'fade', outDur: 0.15, ...quiet }, (ctx, life) => {
        const u = s.ease.out(s.clamp(life.local / 0.45, 0, 1));
        const y = avance(ts) - 70 + (k % 5) * 38;
        const x = s.lerp(PASILLOS[1] + lado * 330, PASILLOS[1] + lado * 62, u);
        ctx.strokeStyle = '#efe4c8'; ctx.lineWidth = 6; ctx.lineCap = 'round';
        ctx.beginPath(); ctx.moveTo(x + lado * 80, y + 10); ctx.lineTo(x, y); ctx.stroke();
        ctx.fillStyle = '#cfd6dd';
        ctx.beginPath(); ctx.moveTo(x - lado * 14, y - 2); ctx.lineTo(x + lado * 4, y - 7); ctx.lineTo(x + lado * 4, y + 5); ctx.fill();
      });
    }
    rotulo(s, 'Atacado desde *ambos lados*', '#expuestos');
  },
};
