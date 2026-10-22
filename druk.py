"""Przygotowanie wydruku: kopiowanie wybranych plików STL i układanie ich na płytach w plikach 3MF.

Użycie z wiersza poleceń (zlecenie pobrane z konfiguratora):
    python druk.py vault-zlecenie.json

Zwykle wywoływane przez serwer.py po kliknięciu „Przygotuj do druku” w konfiguratorze.
"""
import json
import re
import shutil
import sys
import time
import zipfile
from pathlib import Path

import numpy as np

import ustawienia
from jezyk import biezacy as biezacy_jezyk
from jezyk import tr

TU = Path(__file__).resolve().parent
_u = ustawienia.wczytaj()
KORZEN = _u["biblioteka"]  # biblioteka VAULT – ścieżki plików w zleceniu są względem niej
WYJSCIE = _u["wyjscie"]
TRI = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("attr", "<u2")])

# Definicje drukarek (obszar dyszy, wysokość, strefy wykluczone) – wspólne z konfiguratorem.
_tekst = (TU / "drukarki.js").read_text(encoding="utf-8")
DRUKARKI = json.loads(_tekst[_tekst.index("{"):_tekst.rindex("}") + 1])


def drukarka(opts):
    """Definicja drukarki ze zlecenia: znany klucz albo własny stół [w, d, h]."""
    if opts.get("printer") in DRUKARKI:
        return DRUKARKI[opts["printer"]]
    w, d, h = (float(x) for x in opts.get("bed", (256, 256, 256)))
    return {"name": f"własna {w:.0f}×{d:.0f}×{h:.0f} mm", "bed": [w, d], "area": [0, 0, w, d], "h": h, "exclude": [], "wrap": []}


def obszar_symetryczny(dr):
    """Część obszaru dyszy symetryczna względem środka stołu.
    Slicer centruje importowaną grupę na środku stołu, więc tylko taki obszar jest pewny."""
    cx, cy = dr["bed"][0] / 2, dr["bed"][1] / 2
    x0, y0, x1, y1 = dr["area"]
    hw, hh = min(cx - x0, x1 - cx), min(cy - y0, y1 - cy)
    return [cx - hw, cy - hh, cx + hw, cy + hh]


# ---------------------------------------------------------------- pomocnicze

def bezpieczna_nazwa(s, dl=80):
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", s).strip(" .")
    return (s or "projekt")[:dl]


def plik_w_korzeniu(rel):
    """Ścieżka względna z konfiguratora -> pełna ścieżka; odrzuca wyjście poza folder projektu."""
    p = (KORZEN / rel).resolve()
    if KORZEN not in p.parents or p.suffix.lower() != ".stl" or not p.is_file():
        raise ValueError(tr("Nieprawidłowy plik: {rel}", rel=rel))
    return p


def wczytaj_stl(p):
    """Zwraca tablicę trójkątów (N, 3, 3) float32."""
    rozmiar = p.stat().st_size
    with open(p, "rb") as f:
        naglowek = f.read(84)
    n = int.from_bytes(naglowek[80:84], "little")
    if 84 + n * 50 == rozmiar:
        return np.fromfile(p, dtype=TRI, offset=84, count=n)["v"]
    tekst = p.read_text(errors="ignore")
    liczby = re.findall(r"vertex\s+(\S+)\s+(\S+)\s+(\S+)", tekst)
    return np.array(liczby, dtype=np.float32).reshape(-1, 3, 3)


def siatka(trojkaty):
    """Scala wspólne wierzchołki i usuwa zdegenerowane trójkąty -> (wierzchołki, indeksy)."""
    v = np.ascontiguousarray(trojkaty.reshape(-1, 3), dtype=np.float32)
    klucz = v.view(np.dtype((np.void, 12))).ravel()
    uniq, inv = np.unique(klucz, return_inverse=True)
    wierz = uniq.view(np.float32).reshape(-1, 3)
    idx = inv.reshape(-1, 3).astype(np.int64)
    ok = (idx[:, 0] != idx[:, 1]) & (idx[:, 1] != idx[:, 2]) & (idx[:, 0] != idx[:, 2])
    return wierz, idx[ok]


# ---------------------------------------------------------------- układanie na płytach

class MaxRects:
    """Prosty MaxRects (best short side fit) z obrotem o 90°."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.wolne = [(0.0, 0.0, w, h)]

    def wstaw(self, w, h):
        najlepsze = None
        for (x, y, fw, fh) in self.wolne:
            for (rw, rh, obr) in ((w, h, False), (h, w, True)):
                if rw <= fw + 1e-6 and rh <= fh + 1e-6:
                    ocena = (min(fw - rw, fh - rh), max(fw - rw, fh - rh))
                    if najlepsze is None or ocena < najlepsze[0]:
                        najlepsze = (ocena, x, y, rw, rh, obr)
        if not najlepsze:
            return None
        _, x, y, rw, rh, obr = najlepsze
        self._podziel(x, y, rw, rh)
        return x, y, obr

    def _podziel(self, x, y, w, h):
        nowe = []
        for (fx, fy, fw, fh) in self.wolne:
            if x >= fx + fw or x + w <= fx or y >= fy + fh or y + h <= fy:
                nowe.append((fx, fy, fw, fh))
                continue
            if x > fx: nowe.append((fx, fy, x - fx, fh))
            if x + w < fx + fw: nowe.append((x + w, fy, fx + fw - x - w, fh))
            if y > fy: nowe.append((fx, fy, fw, y - fy))
            if y + h < fy + fh: nowe.append((fx, y + h, fw, fy + fh - y - h))
        # usuń prostokąty zawarte w innych
        self.wolne = [a for i, a in enumerate(nowe) if not any(
            i != j and a[0] >= b[0] and a[1] >= b[1] and a[0] + a[2] <= b[0] + b[2] and a[1] + a[3] <= b[1] + b[3]
            and (a != b or i > j) for j, b in enumerate(nowe))]


def _koliduje(prost, strefy):
    x0, y0, x1, y1 = prost
    return any(x0 < z[2] and x1 > z[0] and y0 < z[3] and y1 > z[1] for z in strefy)


class Plyta:
    """Płyta w trakcie układania.

    Pozycje są pakowane lokalnie w obszarze R (część obszaru dyszy symetryczna względem środka stołu).
    wynik() zwraca pozycje po wyśrodkowaniu całej grupy na środku stołu – dokładnie tak, jak zrobi to
    Bambu Studio przy imporcie – więc sprawdzamy dokładnie to, co zobaczy slicer."""

    def __init__(self, dr, odstep, pelny_stol=False):
        self.dr, self.odstep, self.pelny = dr, odstep, pelny_stol
        # pelny_stol: płyta dla jednej dużej części – obszar area_max (np. pełna głębokość stołu H2D) zamiast area
        rx0, ry0, rx1, ry1 = self.R = obszar_symetryczny({**dr, "area": dr["area_max"]} if pelny_stol else dr)
        # część zajmuje [x, x+w] w polu R+odstęp, bo pakowany jest prostokąt część+odstęp
        self.pk = MaxRects(rx1 - rx0 + odstep, ry1 - ry0 + odstep)
        for z in dr["exclude"] + dr["wrap"]:  # strefy zajęte wstępnie; ostatecznie decyduje sprawdzenie po wyśrodkowaniu
            a, b = max(z[0], rx0) - rx0, max(z[1], ry0) - ry0
            c, d = min(z[2], rx1) - rx0 + odstep, min(z[3], ry1) - ry0 + odstep
            if c > a and d > b:
                self.pk._podziel(a, b, c - a, d - b)
        self.czesci, self.za_duze, self.uwaga = [], False, None

    def wynik(self):
        """-> (lista (sztuka, X, Y, obrót) we współrzędnych stołu, lista zajętych prostokątów); grupa wyśrodkowana na stole"""
        prost = [(x, y, x + (s["dy"] if o else s["dx"]), y + (s["dx"] if o else s["dy"])) for s, x, y, o in self.czesci]
        bx0, by0 = min(p[0] for p in prost), min(p[1] for p in prost)
        bx1, by1 = max(p[2] for p in prost), max(p[3] for p in prost)
        sx = self.dr["bed"][0] / 2 - (bx0 + bx1) / 2
        sy = self.dr["bed"][1] / 2 - (by0 + by1) / 2
        return ([(s, x + sx, y + sy, o) for s, x, y, o in self.czesci],
                [(p[0] + sx, p[1] + sy, p[2] + sx, p[3] + sy) for p in prost])

    def kolizje(self):
        _, prost = self.wynik()
        return (any(_koliduje(p, self.dr["exclude"]) for p in prost),
                any(_koliduje(p, self.dr["wrap"]) for p in prost))

    def dodaj(self, s, wymus=False):
        kopia = list(self.pk.wolne)
        poz = self.pk.wstaw(s["dx"] + self.odstep, s["dy"] + self.odstep)
        if not poz:
            return False
        self.czesci.append((s, *poz))
        twarda, miekka = self.kolizje()
        if (twarda or miekka) and not wymus:
            self.czesci.pop()
            self.pk.wolne = kopia
            return False
        if twarda or miekka:
            self.uwaga = "twarda" if twarda else "miekka"
        return True


def rozmiesc(sztuki, dr, odstep):
    """sztuki: lista dict(file, dx, dy, ...) -> lista obiektów Plyta."""
    plyty = []
    for s in sorted(sztuki, key=lambda s: -(s["dx"] * s["dy"])):
        if any(not p.za_duze and not p.pelny and p.dodaj(s) for p in plyty):
            continue
        p = Plyta(dr, odstep)
        if not p.dodaj(s) and not p.dodaj(s, wymus=True):
            # nie mieści się w zwykłym obszarze – spróbuj większego (area_max) na osobnej płycie, tylko ta jedna część
            duzy = Plyta(dr, odstep, pelny_stol=True) if dr.get("area_max") else None
            if duzy and (duzy.dodaj(s) or duzy.dodaj(s, wymus=True)):
                p = duzy
            else:  # nie mieści się nigdzie – osobna płyta z ostrzeżeniem, część na środku stołu
                p.czesci, p.za_duze = [(s, 0.0, 0.0, False)], True
        plyty.append(p)
    return plyty


# ---------------------------------------------------------------- zapis 3MF

CONTENT_TYPES = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                 '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                 '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                 '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
                 '</Types>')
RELS = ('<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
        'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')


def xml_attr(s):
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def zapisz_3mf(cel, plyta, postep):
    """Zapisuje jedną płytę (pozycje we współrzędnych stołu, już wyśrodkowane).
    Każdy plik STL jest zapisany raz jako obiekt, kopie to kolejne elementy build."""
    pliki = list(dict.fromkeys(s["file"] for s, *_ in plyta))
    ids = {f: i + 1 for i, f in enumerate(pliki)}
    mins = {}
    with zipfile.ZipFile(cel, "w", zipfile.ZIP_DEFLATED, compresslevel=5) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES)
        zf.writestr("_rels/.rels", RELS)
        with zf.open("3D/3dmodel.model", "w", force_zip64=True) as m:
            m.write(b'<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="pl-PL" '
                    b'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">\n'
                    b'<metadata name="Application">VAULT konfigurator</metadata>\n<resources>\n')
            for f in pliki:
                postep(tr("siatka: {name}", name=Path(f).name))
                wierz, idx = siatka(wczytaj_stl(KORZEN / f))
                mins[f] = wierz.min(axis=0), wierz.max(axis=0)
                m.write(f'<object id="{ids[f]}" type="model" name="{xml_attr(Path(f).stem)}"><mesh><vertices>\n'.encode())
                np.savetxt(m, wierz, fmt='<vertex x="%.4f" y="%.4f" z="%.4f"/>', newline="\n")
                m.write(b"</vertices><triangles>\n")
                np.savetxt(m, idx, fmt='<triangle v1="%d" v2="%d" v3="%d"/>', newline="\n")
                m.write(b"</triangles></mesh></object>\n")
                del wierz, idx
            m.write(b"</resources>\n<build>\n")
            for s, x, y, obr in plyta:
                lo, hi = mins[s["file"]]
                tz = -lo[2]
                if obr:  # obrót o 90° wokół Z: x' = -y, y' = x
                    t = f"0 1 0 -1 0 0 0 0 1 {x + hi[1]:.4f} {y - lo[0]:.4f} {tz:.4f}"
                else:
                    t = f"1 0 0 0 1 0 0 0 1 {x - lo[0]:.4f} {y - lo[1]:.4f} {tz:.4f}"
                m.write(f'<item objectid="{ids[s["file"]]}" transform="{t}"/>\n'.encode())
            m.write(b"</build>\n</model>\n")


# ---------------------------------------------------------------- zadanie

def fmt_czas(sec):
    m = round(sec / 60)
    return f"{m // 60} h {m % 60:02d} min" if m >= 60 else f"{m} min"


def przygotuj(zlecenie, postep=print):
    """zlecenie: {name, items:[{file, qty, label, sec, g}], csv, opts:{copy, make3mf, printer, bed:[w,d,h], gap}}"""
    t0 = time.time()
    opts = zlecenie.get("opts", {})
    nazwa = bezpieczna_nazwa(zlecenie.get("name") or "projekt")
    folder = WYJSCIE / nazwa
    n = 2
    while folder.exists():
        folder = WYJSCIE / f"{nazwa} ({n})"
        n += 1
    folder.mkdir(parents=True)
    ostrzezenia, wynik = [], {"folder": str(folder), "plates": [], "copied": 0, "lang": biezacy_jezyk()}

    pozycje = []
    for it in zlecenie["items"]:
        p = plik_w_korzeniu(it["file"])
        q = int(it["qty"])
        if q > 0:
            pozycje.append({**it, "qty": q, "path": p})

    if zlecenie.get("csv"):
        (folder / tr("lista.csv")).write_text(zlecenie["csv"], encoding="utf-8-sig")

    # --- kopiowanie STL
    if opts.get("copy", True):
        (folder / "stl").mkdir()
        nazwy = {}
        for it in pozycje:
            nazwy.setdefault(it["path"].name.lower(), []).append(it)
        for i, it in enumerate(pozycje, 1):
            baza = it["path"].name
            if len(nazwy[baza.lower()]) > 1:  # ta sama nazwa w różnych folderach – dopisz 2 poziomy folderów
                baza = f"{it['path'].parent.parent.name} {it['path'].parent.name} - {baza}"
            cel = folder / "stl" / bezpieczna_nazwa(f"{it['qty']}x {baza}", 150)
            k = 2
            while cel.exists():
                cel = cel.with_name(f"{cel.stem} ({k}){cel.suffix}")
                k += 1
            postep(tr("kopiowanie {i}/{n}: {name}", i=i, n=len(pozycje), name=it["path"].name))
            shutil.copy2(it["path"], cel)
            wynik["copied"] += 1

    # --- płyty 3MF
    if opts.get("make3mf", True):
        dr = drukarka(opts)
        x0, y0, x1, y1 = obszar_symetryczny(dr)
        bed_h = dr["h"]
        odstep = float(opts.get("gap", 5))
        geom = {}
        cache = TU / "geometria_cache.json"
        if cache.exists():
            geom = {k: v["g"] for k, v in json.loads(cache.read_text(encoding="utf-8")).items()}
        materialy = {}
        for it in pozycje:
            g = geom.get(it["file"])
            if not g:
                t = wczytaj_stl(it["path"]).reshape(-1, 3)
                g = [0, 0, *(t.max(axis=0) - t.min(axis=0)).tolist()]
            if g[4] > bed_h:
                ostrzezenia.append(tr("{name}: wysokość {h} mm > {max} mm dostępne w tej drukarce", name=it["path"].name, h=f"{g[4]:.0f}", max=f"{bed_h:.0f}"))
            mat = "TPU" if "tpu" in it["path"].name.lower() else "PLA/PETG"
            for _ in range(it["qty"]):
                materialy.setdefault(mat, []).append({"file": it["file"], "dx": g[2], "dy": g[3], "dz": g[4],
                                                      "sec": it.get("sec") or 0, "g": it.get("g") or 0})
        (folder / "3mf").mkdir()
        nr, opis = 0, []
        wszystkie = [(mat, p) for mat, sztuki in materialy.items() for p in rozmiesc(sztuki, dr, odstep)]
        for mat, p in wszystkie:
            nr += 1
            plyta, _ = p.wynik()
            za_duze = p.za_duze
            plik = folder / "3mf" / f"{tr('plyta')}_{nr:02d}{'_TPU' if mat == 'TPU' else ''}{tr('_ZA_DUZE') if za_duze else ''}.3mf"
            etap = tr("płyta {nr}/{n}", nr=nr, n=len(wszystkie))
            postep(etap)
            zapisz_3mf(plik, plyta, lambda s: postep(f"{etap} – {s}"))
            if p.uwaga == "twarda" and not za_duze:
                ostrzezenia.append(tr("{name}: część zachodzi na strefę zakazaną stołu – przesuń ją ręcznie w slicerze", name=plik.name))
            if p.uwaga == "miekka":
                ostrzezenia.append(tr("{name}: część zachodzi na strefę wykrywania owijania (tylna krawędź) – "
                                      "wyłącz wykrywanie owijania (wrapping detection) albo przesuń część w slicerze", name=plik.name))
            sec = sum(s["sec"] for s, *_ in plyta)
            gr = sum(s["g"] for s, *_ in plyta)
            zawartosc = {}
            for s, *_ in plyta:
                zawartosc[Path(s["file"]).name] = zawartosc.get(Path(s["file"]).name, 0) + 1
            if za_duze:
                ostrzezenia.append(tr("{name}: część nie mieści się w obszarze druku {w}×{d} mm "
                                      "(z uwzględnieniem stref wykluczonych) – użyj wersji dzielonej albo innej drukarki/dyszy",
                                      name=plik.name, w=f"{x1 - x0:.0f}", d=f"{y1 - y0:.0f}"))
            if p.pelny:
                mx0, my0, mx1, my1 = p.R
                ostrzezenia.append(tr("{name}: duża część – nie mieści się w obszarze {w}×{d} mm, więc zajmuje większy obszar "
                                      "{w2}×{d2} mm (pełna głębokość stołu); sprawdź jej położenie w slicerze",
                                      name=plik.name, w=f"{x1 - x0:.0f}", d=f"{y1 - y0:.0f}",
                                      w2=f"{mx1 - mx0:.0f}", d2=f"{my1 - my0:.0f}"))
            wynik["plates"].append({"file": plik.name, "material": mat, "sec": sec, "g": gr, "items": zawartosc,
                                    "too_big": za_duze, "full_bed": p.pelny})
            opis.append(f"{plik.name}  [{mat}]  ≈ {fmt_czas(sec)}, ≈ {gr:.0f} g\n" +
                        "".join(f"    {q}× {n}\n" for n, q in sorted(zawartosc.items())))
        nazwa_dr = tr(dr["name"]) if " – " in dr["name"] else dr["name"]
        (folder / "3mf" / tr("plyty.txt")).write_text(
            tr("Drukarka: {printer} – części w obszarze X {x0}–{x1}, Y {y0}–{y1}, wysokość {h} mm, odstęp {gap} mm",
               printer=nazwa_dr, x0=f"{x0:g}", x1=f"{x1:g}", y0=f"{y0:g}", y1=f"{y1:g}", h=bed_h, gap=f"{odstep:.0f}") + "\n"
            + tr("Układ każdej płyty jest wyśrodkowany na stole – tak samo ustawia go Bambu Studio przy imporcie.") + "\n"
            + (tr("UWAGA: przypisz w slicerze filament do lewej dyszy.") + "\n" if dr.get("nozzle") == "left" else "")
            + (tr("UWAGA: przypisz w slicerze filament do prawej dyszy.") + "\n" if dr.get("nozzle") == "right" else "")
            + (tr("Uwaga: {note}", note=tr(dr["note"])) + "\n" if dr.get("note") else "")
            + tr("Pliki 3MF zawierają rozmieszczone części (w orientacji z plików STL). Otwórz w Bambu Studio / OrcaSlicer / PrusaSlicer, "
                 "wybierz profil i filament, włącz podpory tam, gdzie lista każe („Turn On Supports”).") + "\n\n" + "\n".join(opis),
            encoding="utf-8")

    wynik["warnings"] = ostrzezenia
    wynik["seconds"] = round(time.time() - t0, 1)
    postep(tr("gotowe"))
    return wynik


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    z = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    w = przygotuj(z, lambda s: print("  " + s, flush=True))
    print("\n" + tr("Gotowe w {s} s: {dir}", s=w["seconds"], dir=w["folder"]))
    print(tr("Skopiowano {n} plików, płyt 3MF: {plates}", n=w["copied"], plates=len(w["plates"])))
    for o in w["warnings"]:
        print(tr("UWAGA: {msg}", msg=o))
