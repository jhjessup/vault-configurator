"""Ustawienia wspólne dla skryptów konfiguratora: katalog biblioteki VAULT (pliki STL/PDF) i katalog wyjściowy.

Zapisywane w ustawienia.json obok skryptów. Bez pliku ustawień przyjmowane są wartości domyślne:
biblioteka = ..\\vault (jeśli istnieje, inaczej katalog nadrzędny), wyjście = ..\\do_druku.
"zeskanowano" = katalog, z którego skanuj.py zrobił katalog.js (brak, póki nie było skanu na tym komputerze).
"""
import json
from pathlib import Path

from jezyk import tr

TU = Path(__file__).resolve().parent
PLIK = TU / "ustawienia.json"


def _domyslna_biblioteka():
    vault = TU.parent / "vault"
    return vault if vault.is_dir() else TU.parent


def wczytaj():
    """-> dict(biblioteka: Path, wyjscie: Path, zeskanowano: Path | None)"""
    d = {}
    if PLIK.exists():
        try:
            d = json.loads(PLIK.read_text(encoding="utf-8-sig"))  # -sig: plik po edycji w Notatniku może mieć BOM
        except (OSError, json.JSONDecodeError):
            d = {}
    return {
        "biblioteka": Path(d.get("biblioteka") or _domyslna_biblioteka()).resolve(),
        "wyjscie": Path(d.get("wyjscie") or TU.parent / "do_druku").resolve(),
        "zeskanowano": Path(d["zeskanowano"]).resolve() if d.get("zeskanowano") else None,
    }


def zapisz(biblioteka=None, wyjscie=None, zeskanowano=None):
    u = wczytaj()
    if biblioteka:
        u["biblioteka"] = Path(biblioteka).resolve()
    if wyjscie:
        u["wyjscie"] = Path(wyjscie).resolve()
    if zeskanowano:
        u["zeskanowano"] = Path(zeskanowano).resolve()
    PLIK.write_text(json.dumps({k: str(v) for k, v in u.items() if v}, ensure_ascii=False, indent=1), encoding="utf-8")
    return u


def sprawdz_biblioteke(sciezka):
    """-> (ok, komunikat). Sprawdza, czy katalog wygląda na bibliotekę VAULT."""
    p = Path(sciezka)
    if not p.is_dir():
        return False, tr("Katalog nie istnieje: {p}", p=p)
    if p.resolve() == TU or TU in p.resolve().parents:
        return False, tr("To jest katalog konfiguratora, a nie biblioteka plików.")
    brakuje = [k for k in ("01. DRAWERS", "02. SUSTAINERS", "03. MODIFICATIONS") if not (p / k).is_dir()]
    if len(brakuje) == 3:
        return False, tr("W katalogu {p} nie ma folderów 01. DRAWERS / 02. SUSTAINERS / 03. MODIFICATIONS.", p=p)
    if brakuje:
        return True, tr("Brakuje folderów: {list}", list=", ".join(brakuje))
    return True, ""
