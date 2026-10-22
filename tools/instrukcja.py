"""Instrukcje użytkownika do PDF: docs/instrukcja_pl.html i docs/instrukcja_en.html → dist/*.pdf (druk przez Edge).

    python tools/instrukcja.py 1.0.1      – wstawia numer wersji i tworzy dist/VAULT_instrukcja_PL.pdf i VAULT_manual_EN.pdf

Zrzuty ekranu są w docs/img (robione z tools/test_wizualizacja.html#okno=0&lang=pl… – opis w CLAUDE.md).
Wywoływany też przez tools/wydanie.py.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

KAT = Path(__file__).resolve().parent.parent
DOCS, DIST = KAT / "docs", KAT / "dist"
PLIKI = {"pl": "VAULT_instrukcja_PL.pdf", "en": "VAULT_manual_EN.pdf"}


def edge():
    for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe"):
        if Path(p).exists():
            return p
    sys.exit("Nie znaleziono Edge ani Chrome – są potrzebne do druku PDF.")


def zbuduj(wersja):
    DIST.mkdir(exist_ok=True)
    profil = DIST / "_profil_przegladarki"
    wynik = []
    for jezyk, nazwa in PLIKI.items():
        zrodlo = DOCS / f"instrukcja_{jezyk}.html"
        tymczasowy = DOCS / f"_druk_{jezyk}.html"  # obok zrodla, zeby dzialaly sciezki img/ i instrukcja.css
        tymczasowy.write_text(zrodlo.read_text(encoding="utf-8").replace("{{WERSJA}}", wersja), encoding="utf-8")
        pdf = DIST / nazwa
        if pdf.exists():
            pdf.unlink()
        try:
            # Edge potrafi zakończyć proces przed zapisem PDF (np. przy pierwszym użyciu profilu) – czekamy i ponawiamy
            for _ in range(3):
                subprocess.run([edge(), "--headless=new", "--disable-gpu", f"--user-data-dir={profil}", "--no-pdf-header-footer",
                                f"--print-to-pdf={pdf}", tymczasowy.as_uri()], check=True, capture_output=True, timeout=120)
                for _ in range(20):
                    if pdf.exists():
                        break
                    time.sleep(0.5)
                if pdf.exists():
                    break
        finally:
            tymczasowy.unlink(missing_ok=True)
        if not pdf.exists():
            sys.exit(f"Nie powstał {pdf}")
        print(f"Zbudowano {pdf} ({pdf.stat().st_size // 1024} KB)")
        wynik.append(pdf)
    return wynik


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    zbuduj(sys.argv[1])
