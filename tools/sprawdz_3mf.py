"""Sprawdza płyty 3MF tak, jak zobaczy je Bambu Studio.

Bambu Studio przy imporcie 3MF spoza Bambu przesuwa całą grupę obiektów tak, by środek jej bryły otaczającej
wypadł na środku stołu (Plater.cpp: center_instances_around_point(bed_center)). Ten skrypt robi to samo
przesunięcie, a potem sprawdza: obszar układania z drukarki, strefy exclude/wrap, wysokość, nachodzenie części.

    python tools/sprawdz_3mf.py "D:\\3d\\pojemniki\\do_druku\\projekt\\3mf" h2d

Klucz drukarki jak w drukarki.js. Wynik: OK albo lista problemów dla każdej płyty.
"""
import glob
import json
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import numpy as np

NS = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"
TU = Path(__file__).resolve().parent.parent


def wczytaj_plyte(plik):
    """-> lista (min xyz, max xyz) każdej sztuki po zastosowaniu transformacji z pliku"""
    z = zipfile.ZipFile(plik)
    obiekty, sztuki, cur, wierz = {}, [], None, []
    for ev, el in ET.iterparse(z.open("3D/3dmodel.model"), events=("start", "end")):
        tag = el.tag.replace(NS, "")
        if ev == "start" and tag == "object":
            cur, wierz = el.get("id"), []
        elif ev == "end" and tag == "vertex":
            wierz.append((float(el.get("x")), float(el.get("y")), float(el.get("z"))))
            el.clear()
        elif ev == "end" and tag == "object":
            v = np.array(wierz)
            obiekty[cur] = (v.min(0), v.max(0))
            el.clear()
        elif ev == "end" and tag == "item":
            sztuki.append((el.get("objectid"), np.array(el.get("transform").split(), float).reshape(4, 3)))
    pudelka = []
    for oid, m in sztuki:
        a, b = obiekty[oid]
        rogi = np.array([[x, y, q, 1] for x in (a[0], b[0]) for y in (a[1], b[1]) for q in (a[2], b[2])]) @ m
        pudelka.append((rogi.min(0), rogi.max(0)))
    return pudelka


def sprawdz(plik, dr):
    pudelka = wczytaj_plyte(plik)
    g0 = np.min([p[0] for p in pudelka], 0)
    g1 = np.max([p[1] for p in pudelka], 0)
    sh = np.array([dr["bed"][0] / 2 - (g0[0] + g1[0]) / 2, dr["bed"][1] / 2 - (g0[1] + g1[1]) / 2, 0])
    # pojedyncza duża część może zająć większy obszar area_max (druk.py: Plyta(pelny_stol=True))
    x0, y0, x1, y1 = dr["area_max"] if len(pudelka) == 1 and dr.get("area_max") else dr["area"]
    bledy, uwagi = set(), set()
    prost = []
    for a, b in pudelka:
        a, b = a + sh, b + sh
        prost.append((a, b))
        if a[0] < x0 - .01 or b[0] > x1 + .01 or a[1] < y0 - .01 or b[1] > y1 + .01:
            bledy.add(f"poza obszarem X {x0}–{x1} / Y {y0}–{y1}")
        if any(a[0] < e[2] and b[0] > e[0] and a[1] < e[3] and b[1] > e[1] for e in dr["exclude"]):
            bledy.add("w strefie zakazanej (exclude)")
        # strefa wykrywania owijania jest „miękka” – problem tylko przy włączonym wykrywaniu; druk.py wtedy ostrzega
        if any(a[0] < e[2] and b[0] > e[0] and a[1] < e[3] and b[1] > e[1] for e in dr["wrap"]):
            uwagi.add("zachodzi na strefę wykrywania owijania (wrap)")
        if b[2] > dr["h"] + .01:
            bledy.add("za wysokie")
    for i in range(len(prost)):
        for j in range(i + 1, len(prost)):
            (a1, b1), (a2, b2) = prost[i], prost[j]
            if a1[0] < b2[0] - .01 and a2[0] < b1[0] - .01 and a1[1] < b2[1] - .01 and a2[1] < b1[1] - .01:
                bledy.add("części nachodzą na siebie")
    return len(pudelka), sh, sorted(bledy), sorted(uwagi)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    tekst = (TU / "drukarki.js").read_text(encoding="utf-8")
    dr = json.loads(tekst[tekst.index("{"):tekst.rindex("}") + 1])[sys.argv[2]]
    wszystko_ok = True
    for plik in sorted(glob.glob(str(Path(sys.argv[1]) / "*.3mf"))):
        n, sh, bledy, uwagi = sprawdz(plik, dr)
        wszystko_ok &= not bledy
        print(f"{Path(plik).name}: {n} szt., przesunięcie przy imporcie {sh[0]:+.2f}/{sh[1]:+.2f} mm → "
              + ("OK" if not bledy else "BŁĄD: " + "; ".join(bledy))
              + ("" if not uwagi else " (uwaga: " + "; ".join(uwagi) + ")"))
    sys.exit(0 if wszystko_ok else 2)


if __name__ == "__main__":
    main()
