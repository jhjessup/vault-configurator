// Wizualizacja 3D wieży VAULT – okno otwierane przyciskiem „Wizualizacja 3D” w podglądzie zestawu (openViz()).
// WebGL2 bez bibliotek (program działa bez internetu). Wymiary z geometrii plików STL: szerokości z WIDTH_MM,
// moduł = 48·F + 9 mm, głębokość = 42·d + 20 mm, front 10 mm, podstawa 52 mm. Dachy, uchwyty, kręgosłup,
// pegboard, koła i stopki są poglądowe (kształt uproszczony).
// Korzysta z globalnych z index.html: state, tr, el, save, FAMILIES, LAYOUT_WIDTH, WIDTH_MM, baseWidth.
"use strict";

// ussa = jak na rysunkach w instrukcji (jasnoszary PLA Bambu 10104, pomarańczowe znaczniki, czarne dodatki)
const VIZ_PALETTES = {
  ussa: { housing: "#cfd0cc", front: "#dedfdb", sust: "#dedfdb" },
  black: { housing: "#2b2d31", front: "#e8662b", sust: "#d8d6cf" },
  white: { housing: "#e9e8e3", front: "#fbfbf9", sust: "#b9cdbf" },
  graphite: { housing: "#43464b", front: "#9aa0a8", sust: "#6f8f7a" },
  forest: { housing: "#2e3a32", front: "#86ab8f", sust: "#cdb88c" },
};
// [obrót wokół pionu, pochylenie] w radianach
const VIZ_VIEWS = { front: [0, 0.08], side: [Math.PI / 2, 0.08], q: [0.62, 0.38], top: [0.25, 1.4], back: [Math.PI + 0.55, 0.32] };
const VIZ_FOV = 35 * Math.PI / 180;

// ---------- Wektory, macierze, kolory ----------
const vSub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const vAdd = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const vMul = (a, s) => [a[0] * s, a[1] * s, a[2] * s];
const vDot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const vCross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const vNorm = a => vMul(a, 1 / (Math.hypot(a[0], a[1], a[2]) || 1));
const M4 = {
  persp(f, a, n, fa) {
    const t = 1 / Math.tan(f / 2);
    return new Float32Array([t / a, 0, 0, 0, 0, t, 0, 0, 0, 0, (fa + n) / (n - fa), -1, 0, 0, 2 * fa * n / (n - fa), 0]);
  },
  look(e, c, u) {
    const z = vNorm(vSub(e, c)), x = vNorm(vCross(u, z)), y = vCross(z, x);
    return new Float32Array([x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, -vDot(x, e), -vDot(y, e), -vDot(z, e), 1]);
  },
  mul(a, b) {  // kolumnowo: (a·b)
    const o = new Float32Array(16);
    for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) {
      let s = 0;
      for (let k = 0; k < 4; k++) s += a[k * 4 + j] * b[i * 4 + k];
      o[i * 4 + j] = s;
    }
    return o;
  },
};
const vHex = h => {
  const m = /^#?([0-9a-f]{6})$/i.exec((h || "").trim());
  const n = m ? parseInt(m[1], 16) : 0x888888;
  return [(n >> 16 & 255) / 255, (n >> 8 & 255) / 255, (n & 255) / 255];
};
const vMix = (a, b, t) => a.map((x, i) => x + (b[i] - x) * t);
const V_WHITE = [1, 1, 1], V_BLACK = [0, 0, 0];

// ---------- Budowa siatki ----------
// xf: przesunięcie {t:[x,y,z]} (wysunięta szuflada) i/lub obrót wokół osi X {a, py, pz} (front skrzynki na zawiasach)
function vizMesh() {
  const tri = [], lin = [], lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
  const EDGE = [0, 0, 0, 0.32];
  const xp = (p, xf) => {
    if (!xf) return p;
    let [x, y, z] = p;
    if (xf.a) {
      const c = Math.cos(xf.a), s = Math.sin(xf.a), dy = y - xf.py, dz = z - xf.pz;
      y = xf.py + dy * c - dz * s; z = xf.pz + dy * s + dz * c;
    }
    if (xf.t) { x += xf.t[0]; y += xf.t[1]; z += xf.t[2]; }
    return [x, y, z];
  };
  const xn = (n, xf) => {
    if (!xf || !xf.a) return n;
    const c = Math.cos(xf.a), s = Math.sin(xf.a);
    return [n[0], n[1] * c - n[2] * s, n[1] * s + n[2] * c];
  };
  const grow = p => { for (let i = 0; i < 3; i++) { lo[i] = Math.min(lo[i], p[i]); hi[i] = Math.max(hi[i], p[i]); } };
  const poly = (pts, n, col, xf, order) => {
    const P = pts.map(p => xp(p, xf)), N = xn(n, xf);
    for (const i of order) tri.push(P[i][0], P[i][1], P[i][2], N[0], N[1], N[2], col[0], col[1], col[2]);
    P.forEach(grow);
  };
  const quad = (a, b, c, d, n, col, xf) => poly([a, b, c, d], n, col, xf, [0, 1, 2, 0, 2, 3]);
  const line = (a, b, rgba, xf) => {
    const A = xp(a, xf), B = xp(b, xf);
    lin.push(A[0], A[1], A[2], ...rgba, B[0], B[1], B[2], ...rgba);
  };
  function boxEdges(a, b, xf, rgba = EDGE) {
    const [x0, y0, z0] = a, [x1, y1, z1] = b;
    const c = [[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0], [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]];
    for (const [i, j] of [[0, 1], [1, 2], [2, 3], [3, 0], [4, 5], [5, 6], [6, 7], [7, 4], [0, 4], [1, 5], [2, 6], [3, 7]])
      line(c[i], c[j], rgba, xf);
  }
  function box(a, b, col, xf = null, edges = true) {
    const [x0, y0, z0] = a, [x1, y1, z1] = b;
    quad([x0, y0, z0], [x0, y0, z1], [x0, y1, z1], [x0, y1, z0], [-1, 0, 0], col, xf);
    quad([x1, y0, z1], [x1, y0, z0], [x1, y1, z0], [x1, y1, z1], [1, 0, 0], col, xf);
    quad([x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1], [0, -1, 0], col, xf);
    quad([x0, y1, z1], [x1, y1, z1], [x1, y1, z0], [x0, y1, z0], [0, 1, 0], col, xf);
    quad([x1, y0, z0], [x0, y0, z0], [x0, y1, z0], [x1, y1, z0], [0, 0, -1], col, xf);
    quad([x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1], [0, 0, 1], col, xf);
    if (edges) boxEdges(a, b, xf);
  }
  // walec: c = środek, axis 0/1/2 = oś X/Y/Z
  function cyl(c, axis, r, len, col, xf = null, segs = 24) {
    const u = (axis + 1) % 3, v = (axis + 2) % 3;
    const pt = (ang, s) => { const p = c.slice(); p[axis] += s * len / 2; p[u] += r * Math.cos(ang); p[v] += r * Math.sin(ang); return p; };
    for (let i = 0; i < segs; i++) {
      const a0 = i / segs * 2 * Math.PI, a1 = (i + 1) / segs * 2 * Math.PI, am = (a0 + a1) / 2;
      const n = [0, 0, 0]; n[u] = Math.cos(am); n[v] = Math.sin(am);
      quad(pt(a0, -1), pt(a1, -1), pt(a1, 1), pt(a0, 1), n, col, xf);
      for (const s of [-1, 1]) {
        const cc = c.slice(), nc = [0, 0, 0];
        cc[axis] += s * len / 2; nc[axis] = s;
        poly([cc, pt(a0, s), pt(a1, s)], nc, col, xf, [0, 1, 2]);
      }
    }
  }
  return { tri, lin, lo, hi, xp, box, boxEdges, cyl, line };
}

// Obudowa modułu: dno, sufit, boki i tył – przód otwarty (zakrywają go fronty)
function vizHousing(m, xa, xb, ya, yb, D, col, inner) {
  const t = 3;
  m.box([xa, ya, -D], [xb, ya + t, 0], col, null, false);
  m.box([xa, yb - t, -D], [xb, yb, 0], col, null, false);
  m.box([xa, ya + t, -D], [xa + t, yb - t, 0], col, null, false);
  m.box([xb - t, ya + t, -D], [xb, yb - t, 0], col, null, false);
  m.box([xa + t, ya + t, -D], [xb - t, yb - t, -D + t], inner, null, false);
  m.boxEdges([xa, ya, -D], [xb, yb, 0]);
}

// Siatka gridfinity (co 42 mm) na prostokącie [a,b] × [z0,z1] na wysokości y
function vizGrid(m, a, b, z0, z1, y, h, col, xf) {
  for (let x = a + 42; x < b - 6; x += 42) m.box([x - 0.9, y, z0], [x + 0.9, y + h, z1], col, xf, false);
  for (let z = z1 - 42; z > z0 + 6; z -= 42) m.box([a, y, z - 0.9], [b, y + h, z + 0.9], col, xf, false);
}

// Wieża według rysunków z instrukcji USSA (Modifications, Roof Types, Drawers Naming): jasnoszare moduły z pomarańczowym
// znacznikiem na bokach, front z okrągłym zamkiem na dole, skrzynka z dwoma zatrzaskami u góry, 2 koła Ø160 z tyłu na pręcie
// przez podstawę i stopka (belka) z przodu, kręgosłup jako czarne listwy na każdym module.
function vizStack(m, S, st, si, x0, P) {
  const fam = baseWidth(st), W = WIDTH_MM[fam], D = 42 * st.depth + 20, x1 = x0 + W, md = st.mods, xm = (x0 + x1) / 2;
  const dark = P.dark, inner = vMix(P.housing, V_BLACK, 0.3), baseCol = vMix(P.housing, V_BLACK, 0.06);
  const light = vMix(P.housing, V_WHITE, 0.35), metal = [0.72, 0.73, 0.75], rubber = [0.12, 0.12, 0.13], plate = [0.97, 0.97, 0.95];
  const hole = vMix(dark, V_BLACK, 0.55);
  // pomarańczowy znacznik na obu bokach modułu (przy przodzie)
  const mark = (ya, yb) => {
    const c = (ya + yb) / 2;
    m.box([x0 - 0.8, c - 9, -34], [x0, c + 9, -24], P.accent, null, false);
    m.box([x1, c - 9, -34], [x1 + 0.8, c + 9, -24], P.accent, null, false);
  };
  // okrągły zamek frontu (Key Lock) z wycięciem na kluczyk
  const knob = (x, y, xf) => {
    m.cyl([x, y, 13], 2, 13, 6, dark, xf);
    m.box([x - 2, y - 7, 16], [x + 2, y + 7, 16.6], light, xf, false);
  };

  // koła (z tyłu, na pręcie M16 przez podstawę) i stopka (z przodu); bez kół i stopek wieża stoi na podłodze
  let y = 0;
  const lift = md.wheels || md.feet ? 58 : 0, wz = -D + 72, wy = 80;
  const footW = Math.min({ S: 104.8, M: 194, L: 269.6, XL: 358.8 }[fam], W - 10);
  const foot = (z0, z1, ghost) => {
    if (ghost) { m.boxEdges([xm - footW / 2, 0, z0], [xm + footW / 2, lift, z1], null, [...P.accent, 0.9]); return; }
    m.box([xm - footW / 2 + 6, 0, z0 + 6], [xm + footW / 2 - 6, 10, z1 - 6], rubber);
    m.box([xm - footW / 2, 10, z0], [xm + footW / 2, lift, z1], dark);
  };
  if (md.wheels) {
    m.cyl([xm, wy, wz], 0, 8, W + 92, metal);
    for (const [wx, s] of [[x0 - 26, -1], [x1 + 26, 1]]) {
      m.cyl([wx, wy, wz], 0, 80, 40, rubber, null, 40);
      m.cyl([wx, wy, wz], 0, 70, 42, light, null, 40);
      m.cyl([wx + s * 6, wy, wz], 0, 52, 36, dark, null, 32);
      m.cyl([wx + s * 25, wy, wz], 0, 9, 2, metal, null, 16);
    }
    // stopka z przodu; bez niej (nie wybrana) – tylko obrys, żeby było widać, czego brakuje
    foot(-74, -14, !md.feet);
  } else if (md.feet) { foot(-74, -14); foot(-D + 14, -D + 74); }
  y = lift;
  if (md.base) {
    m.box([x0, y, -D], [x1, y + 52, 0], baseCol);
    m.box([x0 + 16, y + 18, 0], [x1 - 16, y + 34, 1.2], vMix(baseCol, V_BLACK, 0.18), null, false);
    mark(y, y + 52);
    y += 52;
  }

  const y0 = y, layerY = [];
  st.layers.forEach((l, li) => {
    const H = 48 * l.height + 9, ya = y, yb = y + H, fams = FAMILIES[l.layout];
    layerY.push([ya, yb]);
    const cols = [];
    let cx = x0;
    for (const f of fams) { cols.push([cx, cx + WIDTH_MM[f], f]); cx += WIDTH_MM[f]; }
    // osobne moduły (2× S, S + M) mają własne obudowy; L², XL² i pełne moduły – jedną wspólną
    const separate = l.layout === "SS" || l.layout === "SM";
    let reach = 0;  // jak daleko przed obudowę wystają otwarte szuflady/fronty tej warstwy (etykieta przesuwa się z nimi)
    for (const [ha, hb] of separate ? cols : [[x0, x1]]) vizHousing(m, ha, hb, ya, yb, D, P.housing, inner);
    if (!separate) for (const c of cols.slice(1)) m.box([c[0] - 1.5, ya + 3, -D + 3], [c[0] + 1.5, yb - 3, 0], P.housing, null, false);
    mark(ya, yb);

    cols.forEach(([ca, cb], ci) => {
      const c = l.cols[ci], cw = cb - ca, mid = (ca + cb) / 2;
      if (l.type === "D") {
        let top = yb - 5;
        c.pattern.forEach((h, k) => {
          const fh = 48 * h - 1, fy0 = top - fh, fy1 = top, id = `${si}-${li}-${ci}-${k}`;
          top -= fh + 1;
          const o = S.open.get(id) || 0, xf = o > 0.0005 ? { t: [0, 0, o * D * 0.72] } : null;
          reach = Math.max(reach, o * D * 0.72);
          const col = id === S.hover ? vMix(P.front, P.accent, 0.3) : P.front;
          m.box([ca + 1, fy0, 0], [cb - 1, fy1, 10], col, xf);
          knob(mid, fy0 + Math.min(23.5, fh / 2), xf);
          m.box([ca + 12, fy0 + 7, 10], [ca + 46, fy0 + 15, 11], plate, xf);  // etykieta (Label)
          if (xf) {  // pudełko szuflady (czarne, jak w instrukcji) widać tylko po wysunięciu
            const a = ca + 9, b = cb - 9, ty0 = fy0 + 3, ty1 = fy1 - 7, z0 = -(D - 16), t = 2.2;
            m.box([a, ty0, z0], [b, ty0 + t, 0], P.box, xf, false);
            m.box([a, ty0, z0], [a + t, ty1, 0], P.box, xf, false);
            m.box([b - t, ty0, z0], [b, ty1, 0], P.box, xf, false);
            m.box([a, ty0, z0], [b, ty1, z0 + t], P.box, xf, false);
            m.boxEdges([a, ty0, z0], [b, ty1, 0], xf);
            if (c.insert !== "none") {
              m.box([a + t, ty0 + t, z0 + t], [b - t, ty0 + t + 1.5, -0.5], light, xf, false);
              vizGrid(m, a + t, b - t, z0 + t, -0.5, ty0 + t + 1.5, 4, light, xf);
            }
          }
          S.picks.push({ id, a: [ca, fy0, 0], b: [cb, fy1, 16], xf });
        });
      } else {
        const id = `${si}-${li}-${ci}-s`, fy0 = ya + 5, fy1 = yb - 5;
        const o = S.open.get(id) || 0, xf = o > 0.0005 ? { a: o * 1.5, py: fy0, pz: 10 } : null;
        reach = Math.max(reach, Math.sin(o * 1.5) * (fy1 - fy0));
        const col = id === S.hover ? vMix(P.sust, P.accent, 0.3) : P.sust;
        m.box([ca + 1, fy0, 0], [cb - 1, fy1, 10], col, xf);
        // dwa zatrzaski u góry (zachodzą na górną krawędź) i zamek na dole
        for (const lx of [ca + cw * 0.2, cb - cw * 0.2]) m.box([lx - 12, fy1 - 30, 10], [lx + 12, fy1 + 3, 15], dark, xf);
        knob(mid, fy0 + 22, xf);
        m.box([ca + 12, fy0 + 7, 10], [ca + 46, fy0 + 15, 11], plate, xf);
        if (c.grid) vizGrid(m, ca + 3, cb - 3, -D + 3, -1, ya + 3, 4, light, null);
        S.picks.push({ id, a: [ca, fy0, 0], b: [cb, fy1, 16], xf });
      }
    });
    if (S.V.labels) {
      const tags = separate ? fams.map(f => f + st.depth)
        : [l.layout === "L2" ? `L${st.depth}²` : l.layout === "XL2" ? `XL${st.depth}²` : fams[0] + st.depth];
      // face: etykieta należy do przodu wieży – znika, gdy patrzymy od tyłu
      S.labels.push({ p: [x0 - 14, (ya + yb) / 2, 12 + reach], face: [0, 0, 1], text: `${tags.join(" + ")} · ${l.height}F`, cls: "layer" });
    }
    y = yb;
  });
  const y1 = y;

  // dach (tylko nad szufladami) – kształty jak na stronie „Roof Types”
  const top = st.layers[st.layers.length - 1];
  if (top && top.type === "D" && st.roof !== "none") {
    const rc = P.housing;
    if (st.roof === "table") {
      m.box([x0, y, -D], [x1, y + 14, 0], rc);
      m.box([x0 + 7, y + 14, -D + 7], [x1 - 7, y + 18, -7], light);
      y += 18;
    } else if (st.roof === "heavy") {
      m.box([x0, y, -D], [x1, y + 10, 0], rc);
      const b = Math.min(W * 0.3, D - 30), cz = -D / 2, bh = 72;
      for (const bx of [x0 + 8, x1 - 8 - b]) {  // dwa kosze
        m.box([bx, y + 10, cz - b / 2], [bx + b, y + 14, cz + b / 2], inner, null, false);
        for (const [a, c] of [[[bx, y + 10, cz - b / 2], [bx + 5, y + 10 + bh, cz + b / 2]], [[bx + b - 5, y + 10, cz - b / 2], [bx + b, y + 10 + bh, cz + b / 2]],
          [[bx + 5, y + 10, cz - b / 2], [bx + b - 5, y + 10 + bh, cz - b / 2 + 5]], [[bx + 5, y + 10, cz + b / 2 - 5], [bx + b - 5, y + 10 + bh, cz + b / 2]]]) m.box(a, c, rc);
      }
      m.cyl([xm, y + 10 + 34, cz], 0, 14, W - 16 - 2 * b, dark, null, 20);  // drążek między koszami
      y += 10 + bh;
    } else if (st.roof === "bowl") {
      m.box([x0, y, -D], [x1, y + 8, 0], rc);
      m.box([x0 + 10, y + 8, -D + 10], [x1 - 10, y + 9, -10], light, null, false);
      for (const [a, b] of [[[x0, y + 8, -D], [x0 + 10, y + 24, 0]], [[x1 - 10, y + 8, -D], [x1, y + 24, 0]],
        [[x0 + 10, y + 8, -D], [x1 - 10, y + 24, -D + 10]], [[x0 + 10, y + 8, -10], [x1 - 10, y + 24, 0]]]) m.box(a, b, rc);
      y += 24;
    } else if (st.roof === "under") {
      m.box([x0, y, -D], [x1, y + 16, 0], rc);
      const nx = Math.max(2, Math.round(W / 70)), nz = Math.max(2, Math.round(D / 70));
      for (let i = 0; i < nx; i++) for (let k = 0; k < nz; k++) {
        const hx = x0 + W * (i + 0.5) / nx, hz = -D + D * (k + 0.5) / nz;
        m.box([hx - 2.5, y + 16, hz - 2.5], [hx + 2.5, y + 16.5, hz + 2.5], hole, null, false);
      }
      y += 16;
    } else {  // grid: płyta z kratką gridfinity i obrzeżem
      m.box([x0, y, -D], [x1, y + 10, 0], rc);
      for (const [a, b] of [[[x0, y + 10, -D], [x0 + 4, y + 22, 0]], [[x1 - 4, y + 10, -D], [x1, y + 22, 0]],
        [[x0 + 4, y + 10, -D], [x1 - 4, y + 22, -D + 4]], [[x0 + 4, y + 10, -4], [x1 - 4, y + 22, 0]]]) m.box(a, b, rc, null, false);
      vizGrid(m, x0 + 4, x1 - 4, -D + 4, -4, y + 10, 12, light, null);
      y += 22;
    }
    // uchwyt górny: zaokrąglona belka 126 × 51 × 37 mm wzdłuż szerokości; stoi na dnie kratki/misy,
    // przy Heavyweight pominięty (ten dach ma własny drążek między koszami)
    if (st.topHandle && st.roof !== "heavy") {
      const cz = -D / 2, hy = st.roof === "grid" ? y - 12 : st.roof === "bowl" ? y - 15 : y;
      m.box([xm - 63, hy, cz - 25.5], [xm + 63, hy + 12, cz + 25.5], dark, null, false);
      m.cyl([xm, hy + 12, cz], 0, 25.5, 126, dark, null, 28);
      y = Math.max(y, hy + 37.5);
    }
  }

  // tył: kręgosłup (czarne listwy na każdym module), nakładki pegboardu, uchwyty, uchwyty ścienne
  let back = -D;
  if (md.backbone !== "none") {
    const z0 = -D - 33;
    for (const [ya, yb] of layerY) {
      const a = ya + 4, b = yb - 4, c = (a + b) / 2;
      if (md.backbone === "ded") {
        m.box([x0, a, z0], [x1, b, -D], dark);
        for (const hx of [x0 + 18, x0 + 36, x1 - 36, x1 - 18])
          for (const hy of b - a > 60 ? [a + 12, b - 12] : [c]) m.box([hx - 3.5, hy - 3.5, z0 - 0.5], [hx + 3.5, hy + 3.5, z0], hole, null, false);
        for (const q of [0.3, 0.7]) m.box([x0 + W * q - 26, c - 4, z0 - 0.5], [x0 + W * q + 26, c + 4, z0], hole, null, false);
      } else for (const [p, q] of [[x0, x0 + 46], [x1 - 46, x1]]) m.box([p, a, z0], [q, b, -D], dark);
    }
    back = z0;
  }
  if (md.pegboard !== "none") {
    const ikea = md.pegboard === "ikea", t = ikea ? 5 : 12, pw = W - 42;
    for (const [ya, yb] of layerY) {
      const a = ya + 4, b = yb - 4;
      m.box([xm - pw / 2, a, back - t], [xm + pw / 2, b, back], light);
      if (ikea) {
        for (let gx = xm - pw / 2 + 12, i = 0; gx < xm + pw / 2 - 6; gx += 20, i++)
          for (let gy = a + 14 + (i % 2) * 10; gy < b - 10; gy += 40) m.box([gx - 2.5, gy - 7.5, back - t - 0.5], [gx + 2.5, gy + 7.5, back - t], hole, null, false);
      } else {
        for (let gx = xm - pw / 2 + 14; gx < xm + pw / 2 - 8; gx += 25)
          for (let gy = a + 12; gy < b - 8; gy += 25) m.box([gx - 3, gy - 3, back - t - 0.5], [gx + 3, gy + 3, back - t], hole, null, false);
      }
    }
    back -= t;
  }
  if (md.wall) {  // uchwyty ścienne: płyty na tyle modułów z listwą-hakiem u góry
    for (const [ya, yb] of layerY) m.box([x0, ya + 2, back - 17], [x1, yb - 2, back], light);
    m.box([x0 + 20, y1 - 28, back - 31], [x1 - 20, y1 - 14, back - 17], dark);
    back -= 17;
  }
  if (md.handleStatic && layerY.length) {  // uchwyt stały: „D” odstające od tyłu najwyższego modułu
    const [ya, yb] = layerY[layerY.length - 1], c = (ya + yb) / 2, hw = W - 42;
    for (const hx of [xm - hw / 2, xm + hw / 2 - 18]) m.box([hx, c - 18, back - 50], [hx + 18, c + 18, back], light);
    m.box([xm - hw / 2, c - 18, back - 50], [xm + hw / 2, c + 18, back - 36], light);
  }
  if (md.handlePull) {  // uchwyt wysuwany: 2 pręty M16 wzdłuż tyłu i rączka nad wieżą (jak w walizce)
    const rz = back - 14, hw = W - 52, ry = y + 150;
    for (const rx of [xm - hw / 2 + 16, xm + hw / 2 - 16]) m.cyl([rx, (y0 + ry) / 2, rz], 1, 8, ry - y0, metal, null, 16);
    m.box([xm - hw / 2, ry, rz - 30], [xm + hw / 2, ry + 35, rz + 30], dark);
    m.box([xm - hw / 2 + 30, ry + 8, rz - 31], [xm + hw / 2 - 30, ry + 22, rz + 31], hole, null, false);
    m.box([x0, y1 - 35, rz - 16], [x1, y1, rz + 16], dark);  // blokada rączki (Pull-out Handle Lock)
  }

  // wymiary (linie + opisy)
  if (S.V.dims) {
    const A = [...S.accent, 1], tick = 12, front = 12, dz = front + 55, dx = x1 + (md.wheels ? 90 : 55);
    m.line([x0, 1, dz], [x1, 1, dz], A); m.line([x0, 1, dz - tick], [x0, 1, dz + tick], A); m.line([x1, 1, dz - tick], [x1, 1, dz + tick], A);
    m.line([dx, 0, front], [dx, y, front], A); m.line([dx - tick, 0, front], [dx + tick, 0, front], A); m.line([dx - tick, y, front], [dx + tick, y, front], A);
    m.line([dx, 1, back], [dx, 1, front], A); m.line([dx - tick, 1, back], [dx + tick, 1, back], A);
    S.labels.push({ p: [xm, 1, dz], text: `${Math.round(W)} mm`, cls: "dim" });
    S.labels.push({ p: [dx, y / 2, front], text: `${Math.round(y)} mm`, cls: "dim" });
    S.labels.push({ p: [dx, 1, (back + front) / 2], text: `${Math.round(front - back)} mm`, cls: "dim" });
  }
  if (S.V.all) S.labels.push({ p: [xm, y + 40, -D / 2], text: `${st.name} ×${st.qty}`, cls: "stack" });
  const kw = md.wheels ? 46 : 0;
  S.rects.push([x0 - kw, back, x1 + kw, 12]);  // obrys na podłodze dla cienia
}

function vizScene(V, open, hover, accent) {
  const m = vizMesh(), S = { V, open, hover, accent, picks: [], labels: [], rects: [] };
  // dark: zamki, zatrzaski, kręgosłup, stopka, uchwyty; box: pudełka szuflad; accent: znaczniki na bokach
  const P = { housing: vHex(V.housing), front: vHex(V.front), sust: vHex(V.sust),
    dark: vHex("#303135"), box: vHex("#232427"), accent: vHex("#e8662b") };
  const list = V.all ? state.stacks.map((st, i) => [st, i]) : [[state.stacks[state.current], state.current]];
  let x = 0;
  for (const [st, si] of list) {
    const W = WIDTH_MM[baseWidth(st)];
    vizStack(m, S, st, si, x - (list.length === 1 ? W / 2 : 0), P);
    x += W + 170;
  }
  // obrys do klikania: narożniki przekształcone tak samo jak front (wysunięcie, obrót)
  for (const p of S.picks) {
    const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
    for (let i = 0; i < 8; i++) {
      const q = m.xp([i & 1 ? p.b[0] : p.a[0], i & 2 ? p.b[1] : p.a[1], i & 4 ? p.b[2] : p.a[2]], p.xf);
      for (let k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], q[k]); hi[k] = Math.max(hi[k], q[k]); }
    }
    p.lo = lo; p.hi = hi;
  }
  return { m, ...S };
}

// ---------- Renderer WebGL2 ----------
function vizRenderer(gl) {
  const shader = (type, src) => {
    const s = gl.createShader(type);
    gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
    return s;
  };
  const program = (vs, fs) => {
    const p = gl.createProgram();
    gl.attachShader(p, shader(gl.VERTEX_SHADER, "#version 300 es\n" + vs));
    gl.attachShader(p, shader(gl.FRAGMENT_SHADER, "#version 300 es\nprecision highp float;\n" + fs));
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
    const u = {};
    for (let i = 0, n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS); i < n; i++) {
      const name = gl.getActiveUniform(p, i).name.replace(/\[0\]$/, "");
      u[name] = gl.getUniformLocation(p, name);
    }
    return { p, u };
  };
  const lit = program(
    `layout(location=0) in vec3 aP; layout(location=1) in vec3 aN; layout(location=2) in vec3 aC;
     uniform mat4 uVP; out vec3 vN; out vec3 vC; out vec3 vW;
     void main() { vN = aN; vC = aC; vW = aP; gl_Position = uVP * vec4(aP, 1.0); }`,
    `in vec3 vN; in vec3 vC; in vec3 vW; uniform vec3 uEye; out vec4 o;
     void main() {
       vec3 n = normalize(vN), l1 = normalize(vec3(0.45, 0.85, 0.6)), l2 = normalize(vec3(-0.6, 0.35, 0.45));
       vec3 l3 = normalize(vec3(-0.3, 0.5, -0.8));  // słabe światło od tyłu – żeby tył wieży nie był czarny
       float d = max(dot(n, l1), 0.0) * 0.6 + max(dot(n, l2), 0.0) * 0.22 + max(dot(n, l3), 0.0) * 0.28 + 0.3 + 0.1 * (n.y * 0.5 + 0.5);
       vec3 v = normalize(uEye - vW);
       float s = pow(max(dot(n, normalize(l1 + v)), 0.0), 40.0) * 0.16;
       float ao = mix(0.8, 1.0, smoothstep(0.0, 110.0, vW.y));
       o = vec4(vC * d * ao + s, 1.0);
     }`);
  const lines = program(
    `layout(location=0) in vec3 aP; layout(location=1) in vec4 aC; uniform mat4 uVP; out vec4 vC;
     void main() { vC = aC; gl_Position = uVP * vec4(aP, 1.0); }`,
    `in vec4 vC; out vec4 o; void main() { o = vec4(vC.rgb * vC.a, vC.a); }`);
  const floor = program(
    `layout(location=0) in vec3 aP; uniform mat4 uVP; out vec2 vP;
     void main() { vP = aP.xz; gl_Position = uVP * vec4(aP, 1.0); }`,
    `in vec2 vP; uniform vec4 uRects[16]; uniform int uN; uniform vec3 uColor; uniform vec2 uC; uniform float uR; out vec4 o;
     float sdBox(vec2 p, vec4 r) { vec2 c = (r.xy + r.zw) * 0.5, h = (r.zw - r.xy) * 0.5; vec2 d = abs(p - c) - h;
       return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0); }
     void main() {
       float d = 1e9;
       for (int i = 0; i < 16; i++) { if (i >= uN) break; d = min(d, sdBox(vP, uRects[i])); }
       float sh = (1.0 - smoothstep(-40.0, 220.0, d)) * 0.28 + (1.0 - smoothstep(-6.0, 22.0, d)) * 0.3;
       vec2 g = abs(fract(vP / 42.0 - 0.5) - 0.5) / fwidth(vP / 42.0);
       float grid = 1.0 - min(min(g.x, g.y), 1.0);
       float fade = 1.0 - smoothstep(uR * 0.3, uR, length(vP - uC));
       vec3 col = uColor * (1.0 - sh) * (1.0 - grid * 0.07);
       o = vec4(col * fade, fade);
     }`);

  const vao = (layout) => {
    const v = gl.createVertexArray(), b = gl.createBuffer();
    gl.bindVertexArray(v); gl.bindBuffer(gl.ARRAY_BUFFER, b);
    const stride = layout.reduce((n, k) => n + k, 0) * 4;
    let off = 0;
    layout.forEach((k, i) => { gl.enableVertexAttribArray(i); gl.vertexAttribPointer(i, k, gl.FLOAT, false, stride, off); off += k * 4; });
    gl.bindVertexArray(null);
    return { v, b, n: 0, per: stride / 4 };
  };
  const T = vao([3, 3, 3]), L = vao([3, 4]), F = vao([3]);
  const put = (o, data) => {
    gl.bindBuffer(gl.ARRAY_BUFFER, o.b);
    gl.bufferData(gl.ARRAY_BUFFER, data instanceof Float32Array ? data : new Float32Array(data), gl.DYNAMIC_DRAW);
    o.n = data.length / o.per;
  };
  let fl = null;
  return {
    upload(scene) {
      put(T, scene.m.tri); put(L, scene.m.lin);
      const lo = scene.m.lo, hi = scene.m.hi, cx = (lo[0] + hi[0]) / 2, cz = (lo[2] + hi[2]) / 2;
      const R = Math.max(hi[0] - lo[0], hi[2] - lo[2], hi[1] - lo[1]) * 1.6 + 600;
      put(F, [cx - R, -0.5, cz - R, cx + R, -0.5, cz - R, cx + R, -0.5, cz + R, cx - R, -0.5, cz - R, cx + R, -0.5, cz + R, cx - R, -0.5, cz + R]);
      const rects = new Float32Array(64);
      scene.rects.slice(0, 16).forEach((r, i) => rects.set(r, i * 4));
      fl = { rects, n: Math.min(16, scene.rects.length), c: [cx, cz], R };
    },
    draw(VP, eye, floorColor) {
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
      gl.disable(gl.DEPTH_TEST);
      gl.useProgram(floor.p);
      gl.uniformMatrix4fv(floor.u.uVP, false, VP);
      gl.uniform4fv(floor.u.uRects, fl.rects); gl.uniform1i(floor.u.uN, fl.n);
      gl.uniform3fv(floor.u.uColor, floorColor); gl.uniform2fv(floor.u.uC, fl.c); gl.uniform1f(floor.u.uR, fl.R);
      gl.bindVertexArray(F.v); gl.drawArrays(gl.TRIANGLES, 0, F.n);

      gl.enable(gl.DEPTH_TEST); gl.depthFunc(gl.LEQUAL); gl.depthMask(true);
      gl.enable(gl.POLYGON_OFFSET_FILL); gl.polygonOffset(1, 1);
      gl.useProgram(lit.p);
      gl.uniformMatrix4fv(lit.u.uVP, false, VP); gl.uniform3fv(lit.u.uEye, eye);
      gl.bindVertexArray(T.v); gl.drawArrays(gl.TRIANGLES, 0, T.n);
      gl.disable(gl.POLYGON_OFFSET_FILL);

      gl.depthMask(false);
      gl.useProgram(lines.p);
      gl.uniformMatrix4fv(lines.u.uVP, false, VP);
      gl.bindVertexArray(L.v); gl.drawArrays(gl.LINES, 0, L.n);
      gl.depthMask(true);
      gl.bindVertexArray(null);
    },
  };
}

function vizRayBox(o, d, lo, hi) {
  let t0 = 0, t1 = Infinity;
  for (let i = 0; i < 3; i++) {
    const inv = 1 / d[i];
    let a = (lo[i] - o[i]) * inv, b = (hi[i] - o[i]) * inv;
    if (a > b) [a, b] = [b, a];
    t0 = Math.max(t0, a); t1 = Math.min(t1, b);
    if (!(t0 <= t1)) return Infinity;
  }
  return t0;
}

// ---------- Okno wizualizacji ----------
let VIZ = null;

function openViz() {
  if (VIZ) return;
  state.viz = Object.assign({ palette: "ussa", ...VIZ_PALETTES.ussa, labels: true, dims: false, all: false, rotate: false }, state.viz || {});
  const V = state.viz;
  if (VIZ_PALETTES[V.palette]) Object.assign(V, VIZ_PALETTES[V.palette]);  // paleta mogła się zmienić w nowej wersji
  if (state.stacks.length < 2) V.all = false;
  const css = getComputedStyle(document.documentElement), cssHex = k => css.getPropertyValue(k);

  const canvas = el("canvas", { class: "viz-canvas" });
  const labelsBox = el("div", { class: "viz-labels" });
  const stage = el("div", { class: "viz-stage" }, canvas, labelsBox);
  const bar = el("div", { class: "viz-bar" });
  const ov = el("div", { class: "viz-overlay", role: "dialog" }, bar, stage,
    el("div", { class: "viz-foot hint" },
      tr("Przeciągnij – obrót, kółko – przybliżenie, kliknięcie frontu – otwarcie, dwuklik – widok domyślny.") + " " +
      tr("Wymiary z plików STL; dachy, uchwyty, kręgosłup i pegboard są poglądowe.")));
  document.body.append(ov);
  document.body.style.overflow = "hidden";

  const gl = canvas.getContext("webgl2", { antialias: true, alpha: true, premultipliedAlpha: true, preserveDrawingBuffer: true });
  let R = null;
  try { if (gl) R = vizRenderer(gl); } catch (e) { console.error(e); }
  if (!R) stage.replaceChildren(el("p", { class: "err", style: "padding:20px" }, tr("Ta przeglądarka nie obsługuje WebGL 2 – wizualizacja 3D jest niedostępna.")));

  const cam = { yaw: VIZ_VIEWS.q[0], pitch: VIZ_VIEWS.q[1], dist: 2000, t: [0, 150, 0] };
  const goal = { yaw: cam.yaw, pitch: cam.pitch, dist: cam.dist, t: cam.t.slice() };
  const open = new Map(), target = new Map();
  let hover = null, scene = null, labelsKey = "", geo = true, dirty = true, last = performance.now(), raf = 0;
  let drag = null, lastEye = [0, 0, 0];
  const accent = vHex(cssHex("--accent"));

  const rebuild = () => {
    scene = vizScene(V, open, hover, accent);
    R.upload(scene);
    const key = scene.labels.map(l => l.cls + "|" + l.text).join("\n");
    if (key !== labelsKey) {
      labelsKey = key;
      labelsBox.replaceChildren(...scene.labels.map(l => el("div", { class: "viz-label " + l.cls }, l.text)));
    }
    geo = false; dirty = true;
  };
  const fit = (instant) => {
    const lo = scene.m.lo, hi = scene.m.hi;
    goal.t = [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2];
    const r = Math.hypot(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]) / 2;
    const asp = canvas.clientWidth / Math.max(1, canvas.clientHeight);
    goal.dist = r / Math.sin(VIZ_FOV / 2) * (asp < 1 ? 1 / asp : 1) * 0.98;
    if (instant) { cam.t = goal.t.slice(); cam.dist = goal.dist; }
    dirty = true;
  };
  const view = k => { [goal.yaw, goal.pitch] = VIZ_VIEWS[k]; fit(false); };

  const draw = () => {
    const dpr = Math.min(2, window.devicePixelRatio || 1), w = canvas.clientWidth, h = canvas.clientHeight;
    if (!w || !h) return;
    if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
      canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
    }
    gl.viewport(0, 0, canvas.width, canvas.height);
    const cp = Math.cos(cam.pitch);
    const eye = vAdd(cam.t, vMul([Math.sin(cam.yaw) * cp, Math.sin(cam.pitch), Math.cos(cam.yaw) * cp], cam.dist));
    const VP = M4.mul(M4.persp(VIZ_FOV, w / h, cam.dist * 0.05, cam.dist * 20), M4.look(eye, cam.t, [0, 1, 0]));
    lastEye = eye;
    const bg = vHex(cssHex("--bg")), panel = vHex(cssHex("--panel"));
    R.draw(VP, eye, vMix(bg, panel, 0.55));
    // opisy: rzut punktu 3D na ekran
    const kids = labelsBox.children;
    scene.labels.forEach((l, i) => {
      const p = l.p, e = kids[i];
      const cx = VP[0] * p[0] + VP[4] * p[1] + VP[8] * p[2] + VP[12], cy = VP[1] * p[0] + VP[5] * p[1] + VP[9] * p[2] + VP[13];
      const cw = VP[3] * p[0] + VP[7] * p[1] + VP[11] * p[2] + VP[15];
      if (!e) return;
      if (cw <= 0 || (l.face && vDot(vSub(eye, p), l.face) < 0)) { e.style.display = "none"; return; }
      e.style.display = "";
      e.style.left = ((cx / cw) * 0.5 + 0.5) * w + "px";
      e.style.top = (0.5 - (cy / cw) * 0.5) * h + "px";
    });
    dirty = false;
  };

  const angDiff = (a, b) => { let d = (a - b) % (2 * Math.PI); if (d > Math.PI) d -= 2 * Math.PI; if (d < -Math.PI) d += 2 * Math.PI; return d; };
  const frame = now => {
    try { step(now); } catch (e) { console.error("wizualizacja:", e); }
    raf = requestAnimationFrame(frame);
  };
  const step = now => {
    const dt = Math.min(0.05, Math.max(0, now - last) / 1000);
    last = now;
    for (const [id, t] of target) {
      const o = open.get(id) || 0, n = o + (t - o) * Math.min(1, dt * 7);
      const v = Math.abs(t - n) < 0.002 ? t : n;
      if (v !== o) { open.set(id, v); geo = true; }
      if (v === t && t === 0) { target.delete(id); open.delete(id); }
    }
    if (V.rotate && !drag) { goal.yaw += dt * 0.3; cam.yaw += dt * 0.3; dirty = true; }
    const k = 1 - Math.exp(-dt * 9);
    const dy = angDiff(goal.yaw, cam.yaw), dp = goal.pitch - cam.pitch, dd = goal.dist - cam.dist, dtv = vSub(goal.t, cam.t);
    if (Math.abs(dy) + Math.abs(dp) > 1e-4 || Math.abs(dd) > 0.5 || Math.hypot(...dtv) > 0.5) {
      cam.yaw += dy * k; cam.pitch += dp * k; cam.dist += dd * k; cam.t = vAdd(cam.t, vMul(dtv, k)); dirty = true;
    }
    if (geo) rebuild();
    if (dirty) draw();
  };

  const pick = (px, py) => {
    const w = canvas.clientWidth, h = canvas.clientHeight, nx = px / w * 2 - 1, ny = 1 - py / h * 2, th = Math.tan(VIZ_FOV / 2);
    const f = vNorm(vSub(cam.t, lastEye)), r = vNorm(vCross(f, [0, 1, 0])), u = vCross(r, f);
    const d = vNorm(vAdd(f, vAdd(vMul(r, nx * th * w / h), vMul(u, ny * th))));
    let best = null, bt = Infinity;
    for (const p of scene.picks) { const t = vizRayBox(lastEye, d, p.lo, p.hi); if (t < bt) { bt = t; best = p.id; } }
    return best;
  };
  const toggle = id => { const now = target.has(id) ? target.get(id) : (open.get(id) || 0); target.set(id, now > 0.5 ? 0 : 1); };
  const setAll = v => { for (const p of scene.picks) target.set(p.id, v); };

  canvas.addEventListener("pointerdown", e => {
    drag = { x: e.clientX, y: e.clientY, moved: 0 };
    canvas.setPointerCapture(e.pointerId);
  });
  canvas.addEventListener("pointermove", e => {
    const rc = canvas.getBoundingClientRect();
    if (drag) {
      const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
      drag.moved += Math.abs(dx) + Math.abs(dy); drag.x = e.clientX; drag.y = e.clientY;
      goal.yaw -= dx * 0.008; cam.yaw -= dx * 0.008;
      goal.pitch = Math.max(0.02, Math.min(1.45, goal.pitch + dy * 0.006)); cam.pitch = goal.pitch;
      dirty = true;
      canvas.style.cursor = "grabbing";
      return;
    }
    const id = pick(e.clientX - rc.left, e.clientY - rc.top);
    if (id !== hover) { hover = id; geo = true; }
    canvas.style.cursor = id ? "pointer" : "grab";
  });
  canvas.addEventListener("pointerup", e => {
    const rc = canvas.getBoundingClientRect();
    if (drag && drag.moved < 5) { const id = pick(e.clientX - rc.left, e.clientY - rc.top); if (id) toggle(id); }
    drag = null;
    canvas.style.cursor = "grab";
  });
  canvas.addEventListener("pointerleave", () => { if (hover) { hover = null; geo = true; } });
  canvas.addEventListener("wheel", e => {
    e.preventDefault();
    goal.dist = Math.max(250, Math.min(20000, goal.dist * Math.exp(e.deltaY * 0.0012)));
    dirty = true;
  }, { passive: false });
  canvas.addEventListener("dblclick", () => view("q"));

  const close = () => {
    cancelAnimationFrame(raf);
    ro.disconnect();
    document.removeEventListener("keydown", onKey);
    const lose = gl && gl.getExtension("WEBGL_lose_context");
    if (lose) lose.loseContext();
    ov.remove();
    document.body.style.overflow = "";
    VIZ = null;
  };
  const onKey = e => { if (e.key === "Escape") close(); };
  document.addEventListener("keydown", onKey);
  const ro = new ResizeObserver(() => { dirty = true; });
  ro.observe(stage);

  const savePng = () => {
    if (dirty && scene) draw();
    const name = (V.all ? "VAULT" : state.stacks[state.current].name).replace(/[\\/:*?"<>|]+/g, "_").trim() || "VAULT";
    canvas.toBlob(b => {
      const a = el("a", { href: URL.createObjectURL(b), download: name + ".png" });
      document.body.append(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    });
  };

  function renderBar() {
    const tog = (k, text) => el("button", { class: "small" + (V[k] ? " on" : ""), onclick: () => {
      V[k] = !V[k]; save(); geo = true; renderBar();
      if (k === "all") { setTimeout(() => fit(false)); }
    } }, text);
    const color = (k, title) => el("input", { type: "color", value: V[k], title, oninput: e => { V[k] = e.target.value; V.palette = "custom"; save(); geo = true; renderBar(); } });
    const palettes = [["ussa", tr("jasnoszary (jak w instrukcji)")], ["black", tr("czarny + pomarańcz")], ["white", tr("biały")], ["graphite", tr("grafit")], ["forest", tr("leśny")], ["custom", tr("własne")]];
    bar.replaceChildren(
      el("b", {}, tr("Wizualizacja 3D")),
      el("span", { class: "viz-group" }, tr("Widok:") + " ",
        ...[["front", tr("przód")], ["side", tr("bok")], ["q", "3/4"], ["top", tr("góra")], ["back", tr("tył")]]
          .map(([k, t]) => el("button", { class: "small", onclick: () => view(k) }, t))),
      el("span", { class: "viz-group" },
        el("button", { class: "small", onclick: () => setAll(1) }, tr("Otwórz wszystkie")),
        el("button", { class: "small", onclick: () => setAll(0) }, tr("Zamknij wszystkie"))),
      el("span", { class: "viz-group" }, tog("rotate", tr("Obracaj")), tog("labels", tr("Etykiety")), tog("dims", tr("Wymiary")),
        state.stacks.length > 1 ? tog("all", tr("Wszystkie zestawy")) : null),
      el("span", { class: "viz-group" }, tr("Kolory:") + " ",
        sel(V.palette, palettes, v => { V.palette = v; if (VIZ_PALETTES[v]) Object.assign(V, VIZ_PALETTES[v]); save(); geo = true; renderBar(); }),
        color("housing", tr("obudowa")), color("front", tr("fronty szuflad")), color("sust", tr("fronty skrzynek"))),
      el("span", { class: "viz-group", style: "margin-left:auto" },
        el("button", { class: "small", onclick: savePng }, tr("Zapisz PNG")),
        el("button", { class: "small", title: tr("Zamknij (Esc)"), onclick: close }, "✕")));
  }
  renderBar();

  // step: ręczne klatki do testów (np. gdy karta w tle nie dostaje requestAnimationFrame)
  VIZ = { close, step: (ms = 16) => step(last + ms), view, setAll, toggleFirst: () => scene.picks[0] && toggle(scene.picks[0].id),
    state: () => ({ cam: { ...cam }, open: [...open], picks: scene && scene.picks.length }) };
  if (!R) return;
  rebuild();
  requestAnimationFrame(() => { fit(true); raf = requestAnimationFrame(frame); });
}
