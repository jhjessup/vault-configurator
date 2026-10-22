// Test wszystkich kombinacji konfiguracji: czy każda część trafia w istniejący plik STL.
// Użycie: otwórz konfigurator (uruchom.bat), F12 -> Konsola, wklej całość i Enter.
// Wynik: liczba kombinacji, błędy, pozycje bez pliku (powinno być [] i []) oraz nieużyte pliki biblioteki.
// Stan projektu zostaje przywrócony po teście.
(() => {
  const saved = JSON.stringify(state);
  const missing = new Map(), used = new Set(), errors = [];
  let combos = 0;
  for (const key of ["normal", "hidden"]) {
    state.key = key; state.rails = "always";
    for (const type of ["D", "S"]) for (const bl of allowedLayouts(type, null)) for (const layout of allowedLayouts(type, LAYOUT_WIDTH[bl]))
      for (const h of allowedHeights(layout)) for (const d of [3, 4, 5, 6, 7]) for (const pat of allowedPatterns(type, h))
        for (const roof of ["none", "grid", "table", "bowl", "under", "heavy"]) {
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
            backbone: ["ded", "uni"][combos % 2], pegboard: ["ikea", "ussa"][combos % 2], wall: true, handleStatic: true, handlePull: true };
          state.stacks = [st]; combos++;
          try {
            for (const e of buildBom().parts.values()) e.missing ? missing.set(e.file, (missing.get(e.file) || 0) + 1) : used.add(e.file);
          } catch (err) { errors.push(String(err)); }
        }
  }
  state = JSON.parse(saved); update();
  const unused = FILES.filter(f => !used.has(f) && !/grid dividers|manual supports/i.test(f));
  console.log({ combos, errors: errors.slice(0, 10), missing: [...missing], unused });
})();
