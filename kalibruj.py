"""Łączy arkusz czasów druku USSA (dane/ussa_print_data.json, Bambu Lab H2S, basic settings)
z geometrią plików STL i zapisuje dane_druku.js dla konfiguratora.

- Pliki, które da się przypisać do pozycji z arkusza, dostają wartości z arkusza.
- Dla pozostałych liczony jest model: gramy/czas = a·objętość + b·powierzchnia,
  dopasowany metodą najmniejszych kwadratów na plikach z arkusza.

Uruchom po skanuj.py:  python kalibruj.py
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

TU = Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8")

cache = json.loads((TU / "geometria_cache.json").read_text(encoding="utf-8"))
GEOM = {k: v["g"] for k, v in cache.items()}
# Pamięć geometrii trzyma też pliki usunięte z biblioteki (np. stare „x3 Runner Guides”) – licz tylko bieżące
# pliki z katalog.js, inaczej wartości z arkusza trafiłyby do plików, których już nie ma.
_kat = TU / "katalog.js"
if _kat.exists():
    _t = _kat.read_text(encoding="utf-8")
    _a = _t.index("window.VAULT_FILES = ") + len("window.VAULT_FILES = ")
    _pliki = json.loads(_t[_a:_t.index(";", _t.index("]", _a))])
    GEOM = {k: v for k, v in GEOM.items() if k in set(_pliki)}
DANE = json.loads((TU / "dane" / "ussa_print_data.json").read_text(encoding="utf-8"))


def norm(p):
    p = p.lower().replace("'", "")
    p = re.sub(r"\s+", " ", p).replace(" /", "/")
    return re.sub(r" \.stl$", ".stl", p)


NORM = {norm(p): p for p in GEOM}


def znajdz(rx):
    r = re.compile(rx)
    return [p for n, p in NORM.items() if r.search(n)]


def pliki_dla(e):
    """Zwraca listę (plik, liczba sztuk z pozycji arkusza w tym pliku) dla pozycji arkusza."""
    fam, ln, h = e["family"], e["length"], e["height"]
    f = (fam or "").lower()
    part = e["part"]
    if part == "Drawer facade":
        rx = r"^01\. drawers/05\. xl families/xl facade 1f\.stl$" if fam == "XL" else rf"^01\. drawers/[^/]+/facades/{f}{h}f \(turn on supports\)\.stl$"
        return [(p, 1) for p in znajdz(rx)]
    if part == "Sustainer facade":
        rx = r"^02\. sustainers/04\. xl families/xl1f facade\.stl$" if fam == "XL" else rf"^02\. sustainers/[^/]+/facades/{f}{h}f facade\.stl$"
        return [(p, 1) for p in znajdz(rx)]
    if part == "Drawer box":
        if fam == "XL":
            return [(p, None) for p in znajdz(rf"^01\. drawers/[^/]+/xl{ln}/boxes/[^/]+\.stl$")]
        return [(p, 1) for p in znajdz(rf"^01\. drawers/[^/]+/{f}{ln}/boxes/{f}{ln} box {h}f\.stl$")]
    if part == "Drawer body":
        return [(p, 1) for p in znajdz(rf"^01\. drawers/[^/]+/{f}{ln}/modules/{f}{ln} module {h}f\.stl$")]
    if part == "Sustainer body":
        if fam in ("S", "M"):
            return [(p, 1) for p in znajdz(rf"^02\. sustainers/[^/]+/{f}{ln}/modules/{f}{ln} {h}f module\.stl$")]
        return [(p, 1) for p in znajdz(rf"^02\. sustainers/[^/]+/{f}{ln}/modules/{f}{ln} {h}f flat module\.stl$")]
    if part == "Sustainer lid":
        return [(p, 1) for p in znajdz(rf"^02\. sustainers/[^/]+/{f}{ln}/roofs?/{f}{ln} roof( whole)?\.stl$")]
    if part in ("Rail 1", "Rail 2"):
        kind = RAIL[part]  # "guide" / "slide"; arkusz podaje wartości dla 1 sztuki
        nowe = znajdz(rf"/runners/x{ln} runner {kind}\.stl$")  # nowa biblioteka: 1 sztuka w pliku
        if nowe:
            return [(p, 1) for p in nowe]
        return [(p, 2) for p in znajdz(rf"/runners/x{ln} runner {kind}s\.stl$")]  # stara: 2 sztuki w pliku
    if part == "Drawer lock":
        return [(p, 1) for p in znajdz(r"^01\. drawers/07\. universal/key \(turn on supports\)\.stl$")]
    if part == "Lock cap":
        return [(p, 1) for p in znajdz(r"^01\. drawers/07\. universal/key cap\.stl$")]
    if part == "Spring":
        return [(p, 2) for p in znajdz(r"^01\. drawers/07\. universal/springs\.stl$")]
    return []


# Rail 1 jest lżejszy od Rail 2 – przypisz go do lżejszego z plików prowadnic/ślizgów
def _objetosc_x5(kind):  # „x5 Runner Guide(s).stl” – nazwa zależy od wersji biblioteki
    lista = znajdz(rf"/runners/x5 runner {kind}s?\.stl$")
    return GEOM[lista[0]][0] if lista else 0


RAIL = {"Rail 1": "slide", "Rail 2": "guide"} if _objetosc_x5("slide") < _objetosc_x5("guide") else {"Rail 1": "guide", "Rail 2": "slide"}

# ---- wartości z arkusza przypisane do plików ----
zrodlo = {}  # plik -> [sekundy, gramy, szacowane_w_arkuszu]
for e in DANE["parts"]:
    if e["seconds"] is None or e["grams"] is None:
        continue
    lista = pliki_dla(e)
    if not lista:
        continue
    if any(n is None for _, n in lista):  # wartość dla zestawu kilku plików – dziel wg objętości
        suma = sum(GEOM[p][0] for p, _ in lista)
        for p, _ in lista:
            u = GEOM[p][0] / suma
            zrodlo[p] = [e["seconds"] * u, e["grams"] * u, e["status"] != "Source"]
    else:
        for p, n in lista:
            zrodlo[p] = [e["seconds"] * n, e["grams"] * n, e["status"] != "Source"]

# ---- dopasowanie modelu na pozycjach "Source" ----
uczace = [(GEOM[p], v) for p, v in zrodlo.items() if not v[2]]
X = np.array([[g[0], g[1]] for g, _ in uczace])
yg = np.array([v[1] for _, v in uczace])
yt = np.array([v[0] for _, v in uczace])


def dopasuj(X, y):
    # najmniejsze kwadraty względne (ważone 1/y), żeby małe części nie ginęły
    w = 1 / np.maximum(y, 1)
    coef, *_ = np.linalg.lstsq(X * w[:, None], y * w, rcond=None)
    return np.maximum(coef, 0)


kg, kt = dopasuj(X, yg), dopasuj(X, yt)
bl_g = np.abs(X @ kg - yg) / yg
bl_t = np.abs(X @ kt - yt) / yt
print(f"Pozycji z arkusza przypisanych do plików: {len(zrodlo)} (uczących: {len(uczace)})")
print(f"Model gramy = {kg[0]:.3f}·cm3 + {kg[1]:.4f}·cm2   błąd mediana {np.median(bl_g):.0%}, 90% {np.percentile(bl_g, 90):.0%}")
print(f"Model czas  = {kt[0]:.1f}·cm3 + {kt[1]:.2f}·cm2 [s]  błąd mediana {np.median(bl_t):.0%}, 90% {np.percentile(bl_t, 90):.0%}")

# warianty skrzynek L/XL (Dividers/Sealed) i dzielone wieka – skaluj wartość z arkusza przez model
def model(p):
    g = GEOM[p]
    return np.array([kt @ g[:2], kg @ g[:2]])


for p in list(GEOM):
    n = norm(p)
    m = re.match(r"^(02\. sustainers/[^/]+/(l|xl)\d/modules/(?:l|xl)\d \df) (dividers|sealed) module\.stl$", n)
    if m:
        flat = NORM.get(m.group(1) + " flat module.stl")
        if flat in zrodlo:
            s = np.array(zrodlo[flat][:2]) * model(p) / model(flat)
            zrodlo[p] = [*s, True]

# "Sustainer accessories" z arkusza = komplet na 1 skrzynkę: 2 zamki, zawiasy, piny, pręty.
# Model zawyża masę drobnych części, więc skalujemy wszystkie pliki z Locks/Hinges/Rods tak,
# by komplet dla S 1F dawał sumę z arkusza.
akc = next(e for e in DANE["parts"] if e["part"] == "Sustainer accessories" and e["family"] == "S")
U = "02. SUSTAINERS/05. Universal/"
komplet = [("Locks/LOCK HOLDER.stl", 2), ("Locks/LOCK INNER PART.stl", 2), ("Locks/LOCK OUTER PART 1F.stl", 2),
           ("Locks/1 SET OF PINS FOR 1 LOCK.stl", 2), ("Hinges/S-M 1F Hinge.stl", 1), ("Hinges/S Hinge Top.stl", 2),
           ("Rods/S-M Rods.stl", 1)]
suma = sum(model(U + p) * n for p, n in komplet)
skala = np.array([akc["seconds"], akc["grams"]]) / suma
print(f"Akcesoria skrzynki: model {suma[0]:.0f} s / {suma[1]:.1f} g, arkusz {akc['seconds']} s / {akc['grams']} g -> skala czas {skala[0]:.2f}, masa {skala[1]:.2f}")
for p in GEOM:
    if re.match(r"^02\. sustainers/05\. universal/(locks|hinges|rods)/", norm(p)):
        zrodlo[p] = [*(model(p) * skala), True]

dane = {
    "printer": DANE.get("printer"), "settings": DANE.get("settings"),
    "model": {"g": [round(float(x), 5) for x in kg], "t": [round(float(x), 3) for x in kt]},
    "source": {p: [round(v[0]), round(v[1], 2), int(v[2])] for p, v in sorted(zrodlo.items())},
}
with open(TU / "dane_druku.js", "w", encoding="utf-8") as f:
    f.write("// Wygenerowane przez kalibruj.py - czasy/gramy z arkusza USSA (Bambu Lab H2S, basic) + model geometryczny\n")
    f.write("window.VAULT_PRINT = ")
    json.dump(dane, f, ensure_ascii=False, separators=(",", ":"))
    f.write(";\n")
print(f"Zapisano {TU / 'dane_druku.js'}")
