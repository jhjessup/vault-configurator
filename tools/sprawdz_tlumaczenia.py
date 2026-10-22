"""Statyczny test słownika: wyciąga z kodu wszystkie teksty do tłumaczenia i porównuje z tlumaczenia.js.

    python tools/sprawdz_tlumaczenia.py          – raport dla angielskiego
    python tools/sprawdz_tlumaczenia.py en brak.json  – dodatkowo zapisuje brakujące klucze do pliku (do uzupełnienia)

Źródła kluczy: index.html i wizualizacja.js (tr(...), etykiety b.add/hwAdd, uwagi, stałe z etykietami, data-tr w HTML),
drukarki.js (nazwy z dopiskiem i podpowiedzi) oraz pliki .py (wywołania tr(...), przez ast).
Uzupełnienie testu w przeglądarce: tools/test_tlumaczen.js (sprawdza też, co faktycznie widać na stronie).
Kod wyjścia 0 = komplet, 2 = brakuje tłumaczeń.
"""
import ast
import json
import re
import sys
from pathlib import Path

KAT = Path(__file__).resolve().parent.parent
STR = r'"((?:[^"\\]|\\.)*)"'


def u(x):
    return json.loads('"' + x + '"')


def klucze_html():
    s = (KAT / "index.html").read_text(encoding="utf-8")
    js = s[s.index('"use strict";'):] + (KAT / "wizualizacja.js").read_text(encoding="utf-8")
    k = []
    dodaj = lambda x: x and x not in k and k.append(x)
    for m in re.finditer(r"\btr\(\s*" + STR, js):
        dodaj(u(m.group(1)))
    for m in re.finditer(r"\btr\(\s*'((?:[^'\\]|\\.)*)'", js):
        dodaj(m.group(1).replace("\\\\", "\\"))
    for m in re.finditer(r"\btr\(([^()]*?\?\s*" + STR + r"\s*:\s*" + STR + ")", js, re.S):
        dodaj(u(m.group(2)))
        dodaj(u(m.group(3)))
    for m in re.finditer(r"\bb\.add\([A-Z]\w*,\s*" + STR, js):
        dodaj(u(m.group(1)))
    for m in re.finditer(r'\bb\.add\("[^"]+",\s*' + STR, js):
        dodaj(u(m.group(1)))
    for m in re.finditer(r"note:\s*" + STR, js):
        dodaj(u(m.group(1)))
    for m in re.finditer(r"hwAdd\(([^;]*)\);", js):
        for x in re.findall(STR, m.group(1)):
            dodaj(u(x))
    m = re.search(r'\[\["koło – tarcza".*?\]\]', js)
    for x in re.findall(STR, m.group(0))[::2]:
        dodaj(u(x))
    for nazwa in ("HW", "LAYOUT_LABEL", "ROOFS", "SRC_LABEL"):
        m = re.search(r"const " + nazwa + r" = \{(.*?)\};", js, re.S)
        for x in re.findall(r":\s*" + STR, m.group(1)):
            dodaj(u(x))
    for x in re.findall(STR, re.search(r"const GROUP_ORDER = \[(.*?)\]", js).group(1)):
        dodaj(u(x))
    m = re.search(r"const rows = \[\[(.*?)\]\.map", js)
    for x in re.findall(STR, m.group(1)):
        dodaj(u(x))
    for nazwa in ("PODPORY", "DWIE", "WERYF"):
        dodaj(u(re.search(nazwa + r" = " + STR, js).group(1)))
    dodaj("{n} warstwa")
    dodaj("{n} warstw")
    html = s[:s.index('"use strict";')]
    for m in re.finditer(r"<[^>]*\bdata-tr\b[^>]*>([^<]+)<", html):
        dodaj(m.group(1).strip())
    for m in re.finditer(r'data-tr-(?:title|placeholder)="([^"]+)"', html):
        dodaj(m.group(1))
    # etykiety układów, które są samymi oznaczeniami (S, M, L, XL), nie są tłumaczone
    return [x for x in k if x not in ("tekst polski", "S", "M", "L", "XL", "gridfinity baseplate")]


def klucze_drukarki():
    t = (KAT / "drukarki.js").read_text(encoding="utf-8")
    d = json.loads(t[t.index("{", t.index("VAULT_PRINTERS")):t.rindex("}") + 1])
    k = [p["name"] for p in d.values() if " – " in p["name"]]
    return k + [p["note"] for p in d.values() if p.get("note")]


def klucze_py():
    k = []
    for plik in sorted(KAT.glob("*.py")):
        for n in ast.walk(ast.parse(plik.read_text(encoding="utf-8"))):
            if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "tr" and n.args \
                    and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
                if n.args[0].value not in k:
                    k.append(n.args[0].value)
    return k


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    jezyk = sys.argv[1] if len(sys.argv) > 1 else "en"
    t = (KAT / "tlumaczenia.js").read_text(encoding="utf-8")
    slownik = json.loads(t[t.index("{", t.index("VAULT_I18N")):t.rindex("}") + 1]).get(jezyk, {})
    wszystkie = []
    for zrodlo in (klucze_html(), klucze_drukarki(), klucze_py()):
        wszystkie += [x for x in zrodlo if x not in wszystkie]
    brak = [x for x in wszystkie if x not in slownik]
    nadmiar = [x for x in slownik if x not in wszystkie]
    # {zmienne} muszą być takie same w tekście i tłumaczeniu
    zmienne = [x for x in wszystkie if x in slownik
               and sorted(re.findall(r"\{\w+\}", x)) != sorted(re.findall(r"\{\w+\}", slownik[x]))]
    print(f"{jezyk}: {len(wszystkie)} kluczy w kodzie, brakuje {len(brak)}, nieużywanych {len(nadmiar)}, "
          f"niezgodnych zmiennych {len(zmienne)}")
    for nazwa, lista in (("BRAK", brak), ("NIEUŻYWANE", nadmiar), ("ZMIENNE", zmienne)):
        for x in lista:
            print(f"  {nazwa}: {x}")
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps({x: "" for x in brak}, ensure_ascii=False, indent=0), encoding="utf-8")
    sys.exit(2 if brak or zmienne else 0)


if __name__ == "__main__":
    main()
