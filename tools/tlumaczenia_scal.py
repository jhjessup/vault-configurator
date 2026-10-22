"""Dopisuje tłumaczenia z pliku JSON do tlumaczenia.js (jeden wpis na linię, nagłówek bez zmian).

    python tools/tlumaczenia_scal.py nowe.json [en]

nowe.json: {"tekst polski": "translation", ...}. Istniejące klucze są nadpisywane, kolejność zachowana.
"""
import json
import sys
from pathlib import Path

PLIK = Path(__file__).resolve().parent.parent / "tlumaczenia.js"


def wczytaj():
    t = PLIK.read_text(encoding="utf-8")
    start = t.index("{", t.index("VAULT_I18N"))
    return t[:t.index("window.VAULT_I18N")], json.loads(t[start:t.rindex("}") + 1])


def zapisz(naglowek, dane):
    czesci = []
    for jezyk, slownik in dane.items():
        wpisy = ",\n".join(f"{json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}" for k, v in slownik.items())
        czesci.append(f"{json.dumps(jezyk)}: {{\n{wpisy}\n}}")
    PLIK.write_text(naglowek + "window.VAULT_I18N = {\n" + ",\n".join(czesci) + "\n};\n", encoding="utf-8")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    nowe = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    jezyk = sys.argv[2] if len(sys.argv) > 2 else "en"
    naglowek, dane = wczytaj()
    przed = len(dane.setdefault(jezyk, {}))
    dane[jezyk].update(nowe)
    zapisz(naglowek, dane)
    print(f"{jezyk}: {przed} -> {len(dane[jezyk])} wpisów")


if __name__ == "__main__":
    main()
