"""Tłumaczenia komunikatów po stronie Pythona – ten sam słownik co w przeglądarce (tlumaczenia.js).

    import jezyk
    jezyk.ustaw("en")                                   # język bieżącego wątku (zadanie, zapytanie)
    jezyk.tr("płyta {nr}/{n}", nr=1, n=5)               # -> "plate 1/5"

Klucz to tekst polski; nazwa w nawiasach klamrowych to miejsce na wartość. Brak tłumaczenia -> tekst polski.
Wątek bez ustaw() (konsola, skrypty uruchamiane z wiersza poleceń) używa języka systemu: polski albo angielski.
"""
import json
import os
import sys
import threading
from pathlib import Path

PLIK = Path(__file__).resolve().parent / "tlumaczenia.js"
_watek = threading.local()
_cache = {"mtime": None, "dane": {}}


def _slowniki():
    mtime = PLIK.stat().st_mtime if PLIK.exists() else None
    if mtime != _cache["mtime"]:
        dane = {}
        if mtime is not None:
            t = PLIK.read_text(encoding="utf-8")
            dane = json.loads(t[t.index("{", t.index("VAULT_I18N")):t.rindex("}") + 1])
        _cache.update(mtime=mtime, dane=dane)
    return _cache["dane"]


def _jezyk_systemu():
    """"pl", gdy język systemu to polski, inaczej "en"."""
    for zmienna in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        if os.environ.get(zmienna):
            return "pl" if os.environ[zmienna].lower().startswith("pl") else "en"
    if sys.platform == "win32":
        import ctypes
        return "pl" if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == 0x15 else "en"  # LANG_POLISH
    return "en"


SYSTEM = _jezyk_systemu()


def ustaw(lang):
    _watek.lang = lang if lang in ("pl", "en") else "pl"


def biezacy():
    return getattr(_watek, "lang", SYSTEM)


def tr(tekst, **wartosci):
    jezyk = biezacy()
    if jezyk != "pl":
        tekst = _slowniki().get(jezyk, {}).get(tekst, tekst)
    for k, v in wartosci.items():
        tekst = tekst.replace("{" + k + "}", str(v))
    return tekst
