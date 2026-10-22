"""Buduje wydanie programu: dist/vault-konfigurator.zip (pliki programu) + dist/instaluj.bat i dist/install.bat
(instalator polski i angielski).

    python tools/wydanie.py 1.0.0             – tylko zbudowanie paczki do dist/
    python tools/wydanie.py 1.0.0 --publikuj  – dodatkowo wydanie v1.0.0 w publicznym repozytorium WYDANIA
                                                (gh release create; kod źródłowy zostaje w prywatnym repozytorium)

Do paczki trafiają instrukcje PDF (tools/instrukcja.py) i pliki śledzone przez git (stan z HEAD – niezacommitowane zmiany są pomijane, skrypt o tym ostrzega),
bez plików potrzebnych tylko u autora (kopia.py, CLAUDE.md, .gitignore, .gitattributes). Dochodzi wersja.txt.
Pliki STL/PDF USSA nigdy nie są częścią paczki (nie ma ich w repozytorium).
Instalator pobiera https://github.com/<repo>/releases/latest/download/vault-konfigurator.zip – działa bez logowania
tylko dla publicznego repozytorium (REPO w instaluj.bat).
"""
import io
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import instrukcja  # noqa: E402  (PDF-y z docs/instrukcja_*.html)

KAT = Path(__file__).resolve().parent.parent
DIST = KAT / "dist"
POMIN = {"kopia.py", "CLAUDE.md", ".gitignore", ".gitattributes"}
POMIN_KATALOGI = ("docs/",)  # źródła instrukcji – w paczce są gotowe PDF-y
WYDANIA = "rawel2/Vault-Konfigurator-wydania"  # publiczne repozytorium tylko z wydaniami (to samo co REPO w instaluj.bat i install.bat)
INSTALATORY = ("instaluj.bat", "install.bat")  # polski i angielski instalator – ta sama logika, trzymaj je zgodne


def git(*arg, tekst=True):
    r = subprocess.run(["git", *arg], cwd=KAT, capture_output=True, check=True)
    return r.stdout.decode("utf-8") if tekst else r.stdout


def zbuduj(wersja):
    if git("status", "--porcelain").strip():
        print("UWAGA: są niezacommitowane zmiany – do paczki trafia stan z ostatniego commitu (HEAD).")
    commit = git("rev-parse", "--short", "HEAD").strip()
    pliki = [p for p in git("ls-files").splitlines() if p and p not in POMIN and not p.startswith(POMIN_KATALOGI)]
    pdfy = instrukcja.zbuduj(wersja)
    DIST.mkdir(exist_ok=True)
    zip_ = DIST / "vault-konfigurator.zip"
    with zipfile.ZipFile(zip_, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in pliki:
            dane = git("show", f"HEAD:{p}", tekst=False)
            if p.endswith(".bat"):  # cmd.exe wymaga CRLF (z LF potrafi zgubić etykiety goto)
                dane = dane.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            z.writestr(p, dane)
        z.writestr("wersja.txt", f"{wersja} ({commit})\n")
        for pdf in pdfy:
            z.write(pdf, pdf.name)
    for bat in INSTALATORY:  # instaluj.bat (PL) i install.bat (EN) – osobne pliki wydania, CRLF
        dane = git("show", f"HEAD:{bat}", tekst=False).replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        (DIST / bat).write_bytes(dane)
    print(f"Zbudowano {zip_} ({zip_.stat().st_size // 1024} KB, {len(pliki) + 1 + len(pdfy)} plików) i {', '.join(INSTALATORY)}")
    return zip_, commit, pdfy


NOTATKI = """Konfigurator wież z pojemników VAULT (USSA Design) – lista plików STL, szacunek druku, płyty 3MF, wizualizacja 3D.

**Instalacja (Windows):** pobierz `instaluj.bat` i uruchom go. Instalator sprawdzi Pythona (w razie braku zaproponuje
instalację przez winget), pobierze program, zainstaluje numpy, utworzy skrót na pulpicie i uruchomi konfigurator.
Pliki STL VAULT kupisz u producenta: https://www.ussadesign.com/pages/vault – program poprosi o ich folder.

**Installation (Windows):** download `install.bat` (English installer) and run it. It checks Python (offers to install
it with winget), downloads the program, installs numpy, creates a desktop shortcut and starts the configurator.
The VAULT STL files are sold by USSA Design: https://www.ussadesign.com/pages/vault – the program asks for their folder.
The program language can be switched at the top of the page (automatic / Polski / English).

Aktualizacja: uruchom `instaluj.bat` ponownie (ustawienia zostają). / Update: run `install.bat` again (settings are kept).

**Instrukcja / Manual:** `VAULT_instrukcja_PL.pdf`, `VAULT_manual_EN.pdf`.

Autorzy programu / Program authors: rawel2, Claude (Anthropic). VAULT, projekt i pliki STL / design and STL files © USSA Design.
Program nieoficjalny, niepowiązany z USSA Design. / Unofficial tool, not affiliated with USSA Design.
Udostępniane za zgodą USSA Design (10.2026). / Shared with the permission of USSA Design (10/2026).
Licencja programu / Program licence: MIT (bez materiałów USSA Design / excluding USSA Design materials – NOTICE.md).
"""


def publikuj(wersja, zip_, commit, pdfy):
    """Wydanie trafia do publicznego repozytorium z samymi wydaniami (tag na jego gałęzi głównej);
    kod źródłowy zostaje w prywatnym repozytorium, a w notatkach jest commit, z którego zbudowano paczkę."""
    tag = f"v{wersja}"
    subprocess.run(["gh", "release", "create", tag, str(zip_), *(str(DIST / b) for b in INSTALATORY), *map(str, pdfy), "-R", WYDANIA,
                    "--title", f"Konfigurator VAULT {wersja}", "--notes", NOTATKI + f"\nKod / source: {commit}\n"],
                   cwd=KAT, check=True)
    print(f"Opublikowano wydanie {tag} ({commit}) w {WYDANIA}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2 or sys.argv[1].startswith("-"):
        sys.exit(__doc__)
    z, c, pdfy = zbuduj(sys.argv[1])
    if "--publikuj" in sys.argv:
        publikuj(sys.argv[1], z, c, pdfy)
