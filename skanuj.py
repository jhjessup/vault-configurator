"""Skanuje bibliotekę VAULT i zapisuje do katalog.js listę plików STL (z geometrią potrzebną do szacunku druku)
oraz listę instrukcji (PDF, obrazki).

    python skanuj.py                         – skanuje katalog z ustawień (ustawienia.json)
    python skanuj.py "D:\\3d\\pojemniki\\vault" – ustawia nowy katalog biblioteki i go skanuje

Geometria jest zapamiętywana w geometria_cache.json (klucz: ścieżka względem biblioteki) – liczone są tylko
nowe/zmienione pliki, więc przeniesienie całej biblioteki w inne miejsce nie wymaga ponownego liczenia.
Po skanowaniu uruchamiany jest kalibruj.py (szacunek czasu druku i filamentu).
katalog.js nie zawiera ścieżki biblioteki (plik jest w repo, a biblioteka leży na każdym komputerze gdzie indziej) –
po udanym skanie katalog trafia do ustawienia.json jako "zeskanowano", a konfigurator porównuje go z "biblioteka".
"""
import json
import re
import runpy
import sys
import time
from pathlib import Path

import numpy as np

import ustawienia
from jezyk import tr

TU = Path(__file__).resolve().parent
CACHE = TU / "geometria_cache.json"
TRI = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("attr", "<u2")])
CHUNK = 2_000_000
DOKUMENTY = {".pdf", ".png", ".jpg", ".jpeg"}


def geometria_trojkatow(v):
    """v: tablica (N, 3, 3) w mm -> (objętość mm3, powierzchnia mm2, min xyz, max xyz)"""
    v = v.astype(np.float64)
    a, b, c = v[:, 0], v[:, 1], v[:, 2]
    vol = np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1).sum()
    flat = v.reshape(-1, 3)
    return vol, area, flat.min(axis=0), flat.max(axis=0)


def analizuj(sciezka):
    rozmiar = sciezka.stat().st_size
    with open(sciezka, "rb") as f:
        naglowek = f.read(84)
    n = int.from_bytes(naglowek[80:84], "little")
    vol = area = 0.0
    lo = np.full(3, np.inf)
    hi = np.full(3, -np.inf)
    if 84 + n * 50 == rozmiar:  # binarny STL
        mm = np.memmap(sciezka, dtype=TRI, mode="r", offset=84, shape=(n,))
        for i in range(0, n, CHUNK):
            dv, da, dlo, dhi = geometria_trojkatow(np.asarray(mm["v"][i:i + CHUNK]))
            vol += dv; area += da; lo = np.minimum(lo, dlo); hi = np.maximum(hi, dhi)
        del mm
    else:  # ASCII STL
        tekst = sciezka.read_text(errors="ignore")
        liczby = re.findall(r"vertex\s+(\S+)\s+(\S+)\s+(\S+)", tekst)
        v = np.array(liczby, dtype=np.float64).reshape(-1, 3, 3)
        vol, area, lo, hi = geometria_trojkatow(v)
    wym = hi - lo
    # cm3, cm2, wymiary w mm
    return [round(abs(vol) / 1000, 3), round(area / 100, 2), *[round(float(x), 1) for x in wym]]


def skanuj(postep=print):
    """Skanuje bibliotekę z ustawień, zapisuje katalog.js i przelicza szacunki druku. Zwraca liczbę plików STL."""
    u = ustawienia.wczytaj()
    bib, wyj = u["biblioteka"], u["wyjscie"]
    ok, komunikat = ustawienia.sprawdz_biblioteke(bib)
    if not ok:
        raise ValueError(komunikat)
    pomin = [TU, wyj]  # konfigurator i katalog wyjściowy mogą leżeć wewnątrz biblioteki
    wszystkie = [p for p in bib.rglob("*")
                 if p.is_file() and not any(x == p or x in p.parents for x in pomin)]
    pliki = sorted(p for p in wszystkie if p.suffix.lower() == ".stl")
    dokumenty = sorted(p.relative_to(bib).as_posix() for p in wszystkie if p.suffix.lower() in DOKUMENTY)

    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    geom, nowe, t0 = {}, 0, time.time()
    for i, p in enumerate(pliki, 1):
        rel = p.relative_to(bib).as_posix()
        st = p.stat()
        klucz = st.st_size  # rozmiar wystarcza – mtime zmienia się przy kopiowaniu między dyskami
        stary = cache.get(rel, {}).get("k")
        if stary == klucz or (isinstance(stary, str) and stary.split(":")[0] == str(klucz)):  # też stary format "rozmiar:mtime"
            geom[rel] = cache[rel]["g"]
            continue
        try:
            geom[rel] = analizuj(p)
        except Exception as e:  # uszkodzony plik nie blokuje reszty
            postep(f"! {rel}: {e}")
            continue
        cache[rel] = {"k": klucz, "g": geom[rel]}
        nowe += 1
        if nowe % 20 == 0:
            CACHE.write_text(json.dumps(cache), encoding="utf-8")
            postep(tr("geometria {i}/{n} ({s} s)", i=i, n=len(pliki), s=f"{time.time() - t0:.0f}"))
    CACHE.write_text(json.dumps(cache), encoding="utf-8")

    with open(TU / "katalog.js", "w", encoding="utf-8") as f:
        f.write("// Wygenerowane przez skanuj.py - nie edytuj ręcznie\n")
        f.write("// VAULT_GEOM: [objętość cm3, powierzchnia cm2, X mm, Y mm, Z mm]\n")
        f.write("window.VAULT_FILES = ")
        json.dump([p.relative_to(bib).as_posix() for p in pliki], f, ensure_ascii=False, indent=0)
        f.write(";\nwindow.VAULT_DOCS = ")
        json.dump(dokumenty, f, ensure_ascii=False, indent=0)
        f.write(";\nwindow.VAULT_GEOM = ")
        json.dump(geom, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    # ścieżka biblioteki nie trafia do katalog.js (jest w repo) – konfigurator porównuje "zeskanowano" z "biblioteka"
    ustawienia.zapisz(zeskanowano=bib)
    postep(tr("Zapisano {n} plików STL ({new} przeliczonych) i {docs} instrukcji z {dir}", n=len(pliki), new=nowe, docs=len(dokumenty), dir=bib))

    if ustawienia.plik_danych_ussa():
        postep(tr("szacunek czasu druku (kalibruj.py)…"))
        runpy.run_path(str(TU / "kalibruj.py"), run_name="__main__")
    return len(pliki)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) > 1:
        ok, komunikat = ustawienia.sprawdz_biblioteke(sys.argv[1])
        if not ok:
            print("BŁĄD: " + komunikat)
            sys.exit(1)
        ustawienia.zapisz(biblioteka=sys.argv[1])
        print(f"Katalog biblioteki ustawiony na: {Path(sys.argv[1]).resolve()}")
    skanuj(lambda s: print("  " + s, flush=True))
