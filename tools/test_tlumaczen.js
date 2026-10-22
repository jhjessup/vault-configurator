// Test kompletności tłumaczeń (domyślnie angielskiego).
// Użycie: otwórz konfigurator (uruchom.bat), F12 -> Konsola, wklej całość i Enter.
// Przełącza język, generuje listę części dla wszystkich kombinacji i renderuje wszystkie widoki,
// po czym wypisuje: brakujące tłumaczenia (missing) i polskie znaki widoczne na stronie poza nazwami plików (polishText).
// Oczekiwane: missing: [] i polishText: []. Stan i język są przywracane po teście.
(async (jezyk = "en") => {
  const saved = JSON.stringify(state);
  MISSING_TR.clear();
  state.lang = jezyk; update();
  const pol = /[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]/;
  const polishText = new Set();
  // widoczny tekst poza nazwami plików, ścieżkami, polami edycji i kodem
  const scan = () => {
    const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let n; (n = w.nextNode());) {
      const p = n.parentElement;
      if (!p || p.closest("a, .path, code, script, style, option[value=pl], .pv-tag, .stack-list") || !pol.test(n.nodeValue)) continue;
      const zLang = p.closest("[lang]");  // np. ostrzeżenia z zadania wykonanego wcześniej w innym języku
      if (zLang && zLang !== document.documentElement && zLang.lang !== jezyk) continue;
      polishText.add(n.nodeValue.trim().slice(0, 120));
    }
    for (const e of document.querySelectorAll("[title], [placeholder]"))
      for (const a of ["title", "placeholder"]) if (pol.test(e.getAttribute(a) || "") && !e.closest(".pv-mod, a")) polishText.add(a + ": " + e.getAttribute(a).slice(0, 120));
  };
  let combos = 0;
  for (const key of ["normal", "hidden"]) {
    state.key = key; state.rails = "always";
    for (const type of ["D", "S"]) for (const bl of allowedLayouts(type, null)) for (const layout of allowedLayouts(type, LAYOUT_WIDTH[bl]))
      for (const h of allowedHeights(layout)) for (const d of [3, 6]) for (const pat of allowedPatterns(type, h)) for (const roof of ["none", "grid", "under", "heavy"]) {
        if (roof === "heavy" && !["L", "XL"].includes(LAYOUT_WIDTH[bl])) continue;
        const st = newStack(1); st.depth = d; st.roof = roof; st.topHandle = true;
        const lay = newLayer(type, layout, h);
        st.layers = [newLayer(type, bl, allowedHeights(bl)[0]), lay];
        st.layers.forEach(l => l.cols.forEach(c => {
          if (l === lay) c.pattern = pat.slice();
          c.insert = ["grid", "grid2", "grid1"][combos % 3]; c.sInt = ["flat", "dividers", "sealed"][combos % 3];
          c.splitLid = combos % 2 === 0; c.grid = true; c.div = { n: 1, w: 1, d: 1, s: 1, sc: 1, ss: 1 };
        }));
        st.mods = { base: true, baseSplit: d >= 6 && combos % 2 === 0, wheels: true, feet: true,
          backbone: ["ded", "uni"][combos % 2], pegboard: ["ikea", "ussa"][combos % 2], wall: true, handleStatic: true, handlePull: combos % 3 === 0 };
        state.stacks = [st]; combos++;
        buildBom(); csvText();
        if (combos % 97 === 0) { for (const t of ["print", "hw", "job"]) { state.tab = t; render(); scan(); } }
      }
  }
  // widoki szczególne: pusta wieża skrzynek na górze, uchwyt bez kręgosłupa, wynik zadania i skanowania
  state.stacks = [newStack(1)]; state.stacks[0].mods.handlePull = true; state.tab = "job";
  const s0 = SERVER.status;
  SERVER.status = { kind: "druk", running: false, result: { folder: "X", copied: 1, seconds: 1, warnings: ["w"], plates: [{ file: "plyta_01.3mf", material: "PLA/PETG", sec: 60, g: 5, items: { "a.stl": 1 }, too_big: false }] } };
  render(); scan();
  SERVER.status = { kind: "skan", running: true, step: "x" }; render(); scan();
  SERVER.status = s0;
  // okno wizualizacji 3D (wizualizacja.js): pasek, opisy, stopka
  if (typeof openViz === "function") {
    state.stacks = [newStack(1), newStack(2)]; state.current = 0;
    state.viz = Object.assign(state.viz || {}, { labels: true, dims: true, all: true });
    openViz(); scan(); VIZ.close();
  }
  state = JSON.parse(saved); update();
  const wynik = { jezyk, combos, missing: [...MISSING_TR], polishText: [...polishText] };
  console.log(wynik);
  return wynik;
})();
