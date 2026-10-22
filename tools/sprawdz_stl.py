"""Sprawdza siatki plików STL z biblioteki VAULT: otwarte krawędzie, krawędzie nierozmaitościowe
(więcej niż 2 ściany na krawędzi), niespójnie odwrócone ściany i trójkąty zdegenerowane.

    python tools/sprawdz_stl.py                 – cała biblioteka z ustawień
    python tools/sprawdz_stl.py "plik.stl" ...  – wybrane pliki (wynik tylko na ekranie)
    python tools/sprawdz_stl.py --en            – dodatkowo raport po angielsku dla producenta (VAULT_STL_mesh_errors.csv)
    python tools/sprawdz_stl.py --procesy 3    – liczba równoległych procesów (domyślnie 2, duże pliki zajmują ~2 GB)

Wierzchołki są łączone przy dokładnie równych współrzędnych (jak pierwszy krok admesh w slicerach).
Wynik: <wyjście>\\bledy_stl.csv (tylko pliki z błędami: waga, nazwa, pełna ścieżka folderu, liczby błędów)
i bledy_stl.json (pamięć podręczna: ścieżka + rozmiar,
więc ponowne uruchomienie liczy tylko nowe pliki).
"""
import csv
import json
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ustawienia  # noqa: E402

TRI = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("attr", "<u2")])


def wczytaj_trojkaty(p):
    rozmiar = p.stat().st_size
    with open(p, "rb") as f:
        naglowek = f.read(84)
    n = int.from_bytes(naglowek[80:84], "little")
    if 84 + n * 50 == rozmiar:
        mm = np.memmap(p, dtype=TRI, mode="r", offset=84, shape=(n,))
        v = np.array(mm["v"], dtype=np.float32)
        del mm
        return v
    tekst = p.read_text(errors="ignore")
    liczby = re.findall(r"vertex\s+(\S+)\s+(\S+)\s+(\S+)", tekst)
    return np.array(liczby, dtype=np.float32).reshape(-1, 3, 3)


def sprawdz(p):
    t0 = time.time()
    v = wczytaj_trojkaty(p)
    n = len(v)
    pkt = np.ascontiguousarray(v.reshape(-1, 3) + np.float32(0))  # +0 zamienia -0.0 na 0.0
    del v
    klucze = pkt.view(np.dtype((np.void, 12))).ravel()
    _, idx = np.unique(klucze, return_inverse=True)
    del pkt, klucze
    nw = int(idx.max()) + 1 if len(idx) else 0
    f = idx.reshape(-1, 3).astype(np.int64)
    del idx
    zdeg = (f[:, 0] == f[:, 1]) | (f[:, 1] == f[:, 2]) | (f[:, 0] == f[:, 2])
    n_zdeg = int(zdeg.sum())
    f = f[~zdeg]
    a = np.concatenate([f[:, 0], f[:, 1], f[:, 2]])
    b = np.concatenate([f[:, 1], f[:, 2], f[:, 0]])
    del f
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    nkl, ile = np.unique(lo * nw + hi, return_counts=True)
    del lo, hi, nkl
    otwarte = int((ile == 1).sum())
    nierozm = int((ile > 2).sum())
    krawedzi = len(ile)
    del ile
    _, ile_sk = np.unique(a * nw + b, return_counts=True)  # ta sama krawędź skierowana 2× = sąsiad odwrócony
    odwrocone = int((ile_sk > 1).sum())
    del a, b, ile_sk
    # Euler: V - E + F = 2·powłoki dla zamkniętych brył; tu tylko informacyjnie
    return {"trojkaty": n, "wierzcholki": nw, "krawedzie": krawedzi, "otwarte": otwarte, "nierozmaitosciowe": nierozm,
            "odwrocone": odwrocone, "zdegenerowane": n_zdeg, "s": round(time.time() - t0, 1)}


def ma_bledy(r):
    return bool(r.get("blad") or r["otwarte"] or r["nierozmaitosciowe"] or r["odwrocone"])


def waga(r):
    """Ocena dla raportu wg liczby złych krawędzi (otwarte + nierozmaitościowe)."""
    if r.get("blad"):
        return "nieczytelny"
    n = r["otwarte"] + r["nierozmaitosciowe"]
    return "1 poważne" if n >= 1000 else "2 duże" if n >= 100 else "3 średnie" if n >= 10 else "4 drobne"


def praca(sciezka):
    try:
        return sprawdz(Path(sciezka))
    except Exception as e:  # uszkodzony plik nie zatrzymuje reszty
        return {"blad": str(e)}


def main(arg):
    sys.stdout.reconfigure(encoding="utf-8")  # nazwy plików ze znakiem ² w konsoli Windows
    procesy = 2
    angielski = "--en" in arg
    arg = [a for a in arg if a != "--en"]
    if "--procesy" in arg:
        i = arg.index("--procesy")
        procesy = int(arg[i + 1])
        arg = arg[:i] + arg[i + 2:]
    if arg:
        for a in arg:
            print(a, praca(a))
        return

    u = ustawienia.wczytaj()
    bib, wyj = u["biblioteka"], u["wyjscie"]
    wyj.mkdir(parents=True, exist_ok=True)
    plik_json, plik_csv = wyj / "bledy_stl.json", wyj / "bledy_stl.csv"
    cache = json.loads(plik_json.read_text(encoding="utf-8")) if plik_json.exists() else {}
    pliki = sorted(p for p in bib.rglob("*") if p.is_file() and p.suffix.lower() == ".stl"
                   and wyj not in p.parents and wyj != p)
    do_zrobienia = [p for p in pliki if cache.get(p.relative_to(bib).as_posix(), {}).get("rozmiar") != p.stat().st_size]
    # od największych: najdłuższe zadania startują pierwsze
    do_zrobienia.sort(key=lambda p: -p.stat().st_size)
    print(f"Plików STL: {len(pliki)}, do sprawdzenia: {len(do_zrobienia)} (procesy: {procesy})", flush=True)
    t0 = time.time()
    with ProcessPoolExecutor(procesy) as ex:
        zad = {ex.submit(praca, str(p)): p for p in do_zrobienia}
        for i, fut in enumerate(as_completed(zad), 1):
            p = zad[fut]
            rel = p.relative_to(bib).as_posix()
            r = fut.result()
            r["rozmiar"] = p.stat().st_size
            cache[rel] = r
            if i % 10 == 0 or ma_bledy(r):
                plik_json.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")
            znak = "!" if ma_bledy(r) else " "
            print(f"{znak} {i}/{len(do_zrobienia)} {time.time() - t0:5.0f}s {rel}", flush=True)
    plik_json.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")

    obecne = {p.relative_to(bib).as_posix() for p in pliki}
    zle = sorted(((k, r) for k, r in cache.items() if k in obecne and ma_bledy(r)),
                 key=lambda kr: (-(kr[1].get("nierozmaitosciowe", 0) + kr[1].get("otwarte", 0)), kr[0]))
    pola = ["trojkaty", "otwarte", "nierozmaitosciowe", "odwrocone", "zdegenerowane"]
    with open(plik_csv, "w", newline="", encoding="utf-8-sig") as f:  # średnik + BOM: polski Excel otwiera wprost
        w = csv.writer(f, delimiter=";")
        w.writerow(["waga", "nazwa pliku", "folder", "zle krawedzie", *pola, "blad"])
        for k, r in zle:
            p = bib / k
            w.writerow([waga(r), p.name, str(p.parent), r.get("otwarte", 0) + r.get("nierozmaitosciowe", 0),
                        *[r.get(x, "") for x in pola], r.get("blad", "")])
    print(f"\nPliki z błędami: {len(zle)} z {len(obecne)}. Raport: {plik_csv}")
    if angielski:
        plik_en = wyj / "VAULT_STL_mesh_errors.csv"
        stopnie = {"1 poważne": "1 severe", "2 duże": "2 major", "3 średnie": "3 moderate", "4 drobne": "4 minor",
                   "nieczytelny": "unreadable"}
        # dla producenta: folder względem głównego katalogu paczki VAULT (bez ścieżek tego komputera), CSV z przecinkiem
        with open(plik_en, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["severity", "file name", "folder (in the VAULT package)", "bad edges (open + non-manifold)",
                        "triangles", "open edges", "non-manifold edges", "inconsistently oriented edges",
                        "degenerate triangles", "read error"])
            for k, r in zle:
                folder, _, nazwa = k.rpartition("/")
                w.writerow([stopnie[waga(r)], nazwa, folder, r.get("otwarte", 0) + r.get("nierozmaitosciowe", 0),
                            *[r.get(x, "") for x in pola], r.get("blad", "")])
        print(f"Raport angielski: {plik_en}")


if __name__ == "__main__":
    main(sys.argv[1:])
