"""Lokalny serwer konfiguratora VAULT.

Udostępnia konfigurator w przeglądarce i wykonuje zadania na plikach
(kopiowanie STL, tworzenie płyt 3MF, skanowanie biblioteki). Działa tylko na tym komputerze (127.0.0.1).

    python serwer.py          (albo dwuklik na uruchom.bat; Linux: ./run.sh)

Adresy:  /konfigurator/...  – pliki konfiguratora
         /biblioteka/...    – pliki z katalogu biblioteki VAULT (ustawienia.json)
"""
import importlib
import importlib.util
import json
import os
import posixpath
import subprocess
import sys
import threading
import traceback
import urllib.parse
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import druk
import jezyk
from jezyk import tr
import skanuj
import ustawienia

PORT = 8766
TU = Path(__file__).resolve().parent
STAN = {"running": False, "kind": None, "step": "", "log": [], "result": None, "error": None}
BLOKADA = threading.Lock()


def uruchom_zadanie(rodzaj, funkcja):
    """Uruchamia zadanie w tle; postęp i wynik trafiają do STAN (odpytywane przez przeglądarkę).
    Zadanie dostaje język wątku, który je uruchamia (nagłówek X-Lang zapytania)."""
    lang = jezyk.biezacy()
    def postep(s):
        STAN["step"] = s
        STAN["log"] = (STAN["log"] + [s])[-200:]

    def praca():
        jezyk.ustaw(lang)
        try:
            STAN["result"] = funkcja(postep)
        except Exception as e:  # błąd trafia do przeglądarki
            traceback.print_exc()
            STAN["error"] = str(e)
        finally:
            STAN["running"] = False

    with BLOKADA:
        if STAN["running"]:
            return False
        STAN.update(running=True, kind=rodzaj, step="start", log=[], result=None, error=None)
    threading.Thread(target=praca, daemon=True).start()
    return True


def przygotuj_druk(zlecenie):
    def f(postep):
        # jezyk.py celowo bez reload – wyzerowałby język wątku (słownik i tak odświeża się po zmianie pliku)
        importlib.reload(ustawienia)
        importlib.reload(druk)  # świeży kod i definicje drukarek – poprawki działają bez restartu serwera
        return druk.przygotuj(zlecenie, postep)
    return f


def skanuj_biblioteke(postep):
    importlib.reload(ustawienia)
    importlib.reload(skanuj)
    return {"files": skanuj.skanuj(postep), "biblioteka": str(ustawienia.wczytaj()["biblioteka"])}


# wersja wydania (wersja.txt dokłada tools/wydanie.py do paczki; w repozytorium go nie ma)
WERSJA = (TU / "wersja.txt").read_text(encoding="utf-8").strip() if (TU / "wersja.txt").exists() else "dev"
WYBOR_KATALOGU = importlib.util.find_spec("tkinter") is not None
WYBOR_BLOKADA = threading.Lock()
USSA_URL = "https://www.ussadesign.com/pages/vault"


def otworz_folder(sciezka):
    """Otwiera folder w systemowym menedżerze plików."""
    if sys.platform == "win32":
        os.startfile(sciezka)
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", sciezka],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wybierz_katalog():
    """Systemowe okno wyboru folderu (tkinter) – serwer działa na tym samym komputerze co przeglądarka.
    -> (odpowiedź, kod HTTP); pusta ścieżka = anulowano."""
    if not WYBOR_KATALOGU:
        return {"error": tr("Okno wyboru folderu jest niedostępne (Python bez tkinter) – wpisz ścieżkę ręcznie.")}, 501
    if not WYBOR_BLOKADA.acquire(blocking=False):
        return {"error": tr("Okno wyboru folderu jest już otwarte.")}, 409
    try:
        import tkinter
        from tkinter import filedialog
        root = tkinter.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        try:
            p = filedialog.askdirectory(parent=root, mustexist=True, title=tr("Wskaż folder z plikami VAULT (STL)"),
                                        initialdir=str(ustawienia.wczytaj()["biblioteka"]))
        finally:
            root.destroy()
        return {"path": str(Path(p)) if p else ""}, 200
    except Exception as e:  # np. brak środowiska graficznego
        return {"error": str(e)}, 500
    finally:
        WYBOR_BLOKADA.release()


def opis_ustawien():
    u = ustawienia.wczytaj()
    ok, komunikat = ustawienia.sprawdz_biblioteke(u["biblioteka"])
    return {"biblioteka": str(u["biblioteka"]), "wyjscie": str(u["wyjscie"]), "ok": ok, "message": komunikat,
            "zeskanowano": str(u["zeskanowano"]) if u["zeskanowano"] else None}


class Obsluga(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # bez zaśmiecania konsoli

    def end_headers(self):
        # katalog.js zmienia się po skanowaniu – przeglądarka ma zawsze pytać o aktualną wersję
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def translate_path(self, path):
        """/konfigurator/... -> katalog konfiguratora, /biblioteka/... -> katalog biblioteki; reszta nie istnieje."""
        sciezka = urllib.parse.unquote(urllib.parse.urlsplit(path).path)
        for prefiks, katalog in (("/konfigurator/", TU), ("/biblioteka/", ustawienia.wczytaj()["biblioteka"])):
            if sciezka.startswith(prefiks):
                rel = posixpath.normpath(sciezka[len(prefiks):]).lstrip("/")
                pelna = (Path(katalog) / rel).resolve()
                if pelna == Path(katalog).resolve() or Path(katalog).resolve() in pelna.parents:
                    return str(pelna)
        return str(TU / "__brak__")

    def _json(self, obj, kod=200):
        dane = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(kod)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(dane)))
        self.end_headers()
        self.wfile.write(dane)

    def _lokalne(self):
        # chroni przed wywołaniem API przez obce strony (CSRF / DNS rebinding)
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin")
        ok_host = host in (f"127.0.0.1:{PORT}", f"localhost:{PORT}")
        ok_origin = origin is None or origin in (f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}")
        return ok_host and ok_origin

    def _jezyk(self):
        jezyk.ustaw(self.headers.get("X-Lang", "pl"))

    def do_GET(self):
        self._jezyk()
        if self.path == "/":
            self.send_response(302)
            self.send_header("Location", "/konfigurator/index.html")
            self.end_headers()
            return
        if self.path.startswith("/api/"):
            if not self._lokalne():
                return self._json({"error": "forbidden"}, 403)
            if self.path == "/api/ping":
                if not STAN["running"]:
                    importlib.reload(ustawienia)
                    importlib.reload(druk)
                return self._json({"ok": True, "version": 3, "printers": druk.DRUKARKI, "settings": opis_ustawien(),
                                   "wersja": WERSJA, "wybor": WYBOR_KATALOGU})
            if self.path == "/api/druk":
                return self._json(STAN)
            return self._json({"error": tr("nie ma takiego adresu")}, 404)
        return super().do_GET()

    def do_POST(self):
        self._jezyk()
        if not self._lokalne():
            return self._json({"error": "forbidden"}, 403)
        dl = int(self.headers.get("Content-Length", 0))
        try:
            dane = json.loads(self.rfile.read(dl) or b"{}")
        except json.JSONDecodeError:
            return self._json({"error": tr("zły JSON")}, 400)
        if self.path == "/api/druk":
            if not uruchom_zadanie("druk", przygotuj_druk(dane)):
                return self._json({"error": tr("Poprzednie zadanie jeszcze trwa.")}, 409)
            return self._json({"ok": True})
        if self.path == "/api/ustawienia":
            bib = (dane.get("biblioteka") or "").strip().strip('"')
            if bib:
                ok, komunikat = ustawienia.sprawdz_biblioteke(bib)
                if not ok:
                    return self._json({"error": komunikat}, 400)
            wyj = (dane.get("wyjscie") or "").strip().strip('"') or None
            if STAN["running"]:
                return self._json({"error": tr("Poprzednie zadanie jeszcze trwa.")}, 409)
            ustawienia.zapisz(biblioteka=bib or None, wyjscie=wyj)
            uruchom_zadanie("skan", skanuj_biblioteke)
            return self._json({"ok": True, "settings": opis_ustawien()})
        if self.path == "/api/wybierz_katalog":
            return self._json(*wybierz_katalog())
        if self.path == "/api/otworz":
            # otwiera tylko folder wyniku z ostatniego zadania albo katalog biblioteki
            cel = (STAN.get("result") or {}).get("folder") if dane.get("co") != "biblioteka" \
                else str(ustawienia.wczytaj()["biblioteka"])
            if cel and Path(cel).is_dir():
                try:
                    otworz_folder(cel)
                except OSError:  # np. Linux bez xdg-open
                    return self._json({"error": tr("Nie można otworzyć folderu: {dir}", dir=cel)}, 500)
                return self._json({"ok": True})
            return self._json({"error": tr("brak folderu")}, 404)
        return self._json({"error": tr("nie ma takiego adresu")}, 404)


class Serwer(ThreadingHTTPServer):
    # Na Windows SO_REUSEADDR pozwala dwóm serwerom zająć ten sam port (odpowiada wtedy stary) –
    # wyłączone, żeby drugie uruchomienie dostało błąd zamiast cicho działać obok pierwszego.
    # Na Linuksie/macOS tak nie działa, a bez niego ponowne uruchomienie tuż po zamknięciu trafia na zajęty port.
    allow_reuse_address = sys.platform != "win32"
    daemon_threads = True


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    url = f"http://127.0.0.1:{PORT}/konfigurator/index.html"
    try:
        srv = Serwer(("127.0.0.1", PORT), Obsluga)
    except OSError:
        print(tr("Serwer konfiguratora już działa (port {port} zajęty) – otwieram go w przeglądarce.", port=PORT))
        print(tr("Jeśli to stara wersja, zamknij jej okno konsoli i uruchom konfigurator ponownie."))
        if "--bez-przegladarki" not in sys.argv:
            webbrowser.open(url)
        return
    s = opis_ustawien()
    print(tr("Konfigurator VAULT {ver} – rawel2, Claude (Anthropic). VAULT © USSA Design ({url})", ver=WERSJA, url=USSA_URL))
    print(tr("Konfigurator VAULT: {url}", url=url))
    print(tr("Biblioteka plików: {dir}", dir=s["biblioteka"]) + ("" if s["ok"] else f"  (!) {s['message']}"))
    if not s["ok"]:
        print(tr("Wskaż folder z plikami STL w oknie konfiguratora. Pliki VAULT sprzedaje USSA Design: {url}", url=USSA_URL))
    print(tr("Zamknij to okno, aby zatrzymać serwer."))
    if "--bez-przegladarki" not in sys.argv:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
