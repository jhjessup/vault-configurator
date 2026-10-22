> **About this repository:** this is an independent copy of the VAULT configurator by rawel2, started from
> version 1.1.2 of [rawel2/Vault-Konfigurator-wydania](https://github.com/rawel2/Vault-Konfigurator-wydania),
> with the source code kept in git and Linux support added. It is not maintained by rawel2 or USSA Design.
> USSA Design materials (STL files, PDF manuals, print data) are not included – see [NOTICE.md](NOTICE.md).

# Konfigurator VAULT

*English version: [README.en.md](README.en.md)*

## Instalacja

Pobierz **`instaluj.bat`** z najnowszego wydania
(https://github.com/rawel2/Vault-Konfigurator-wydania/releases/latest) i uruchom go (`install.bat` to ta sama
instalacja z komunikatami po angielsku). Instalator wykona trzy kroki:

1. Sprawdzi Pythona 3.9+. Jeśli go brakuje, zaproponuje instalację przez winget albo otworzy python.org.
2. Zapyta o folder (domyślnie `%USERPROFILE%\VAULT`) i pobierze program do `...\konfigurator`.
   Obok utworzy foldery `vault` na pliki STL i `do_druku` na wyniki.
3. Zainstaluje `numpy`, utworzy skrót **Konfigurator VAULT** na pulpicie i uruchomi program.

Przy pierwszym starcie program poprosi o folder z plikami STL VAULT. Gdy folder jest zły, poda odnośnik
do strony producenta. Aktualizacja polega na ponownym uruchomieniu `instaluj.bat`. Ustawienia zostają.
Pełna instrukcja ze zrzutami ekranu to `VAULT_instrukcja_PL.pdf` w wydaniu (źródło: `docs/instrukcja_pl.html`).

## Autorzy i prawa

- Autorzy programu: **rawel2** i **Claude** (Anthropic). Licencja programu: **MIT** (plik `LICENSE`);
  nie obejmuje materiałów USSA Design – szczegóły w `NOTICE.md`.
- System VAULT, jego projekt, pliki STL i instrukcje PDF należą do **USSA Design**. Pliki trzeba kupić u producenta:
  https://www.ussadesign.com/pages/vault. Program ich nie zawiera.
- Konfigurator jest nieoficjalnym narzędziem i nie jest powiązany z USSA Design.
- Udostępniane za zgodą USSA Design (październik 2026). Nadal nieoficjalne – USSA Design nie odpowiada za program ani go nie wspiera.

## Uruchamianie

Wymagania: Windows i Python 3.9+ z `numpy`. `uruchom.bat` sam znajduje Pythona i w razie potrzeby instaluje `numpy`.

Uruchom **`uruchom.bat`** (dwuklik). Startuje mały lokalny serwer i otwiera konfigurator
w przeglądarce. Okno konsoli musi zostać otwarte, póki pracujesz.
Samo `index.html` (dwuklik) też działa, ale bez kopiowania plików i tworzenia 3MF
(linki do instrukcji działają wtedy tylko, gdy biblioteka leży w `..\vault`).

Projekt zapisuje się w przeglądarce osobno dla każdego sposobu otwarcia (adresu).
Projekt z jednej wersji do drugiej przeniesiesz przyciskami *Zapisz/Wczytaj projekt*.

Drugie uruchomienie `uruchom.bat`, gdy serwer już działa, nie startuje kolejnego serwera, tylko otwiera działający.

## Języki

Przełącznik **Język** w nagłówku: *automatycznie* (według języka przeglądarki), *Polski*, *English*.
Po angielsku są też komunikaty serwera i pliki wynikowe (`plates.txt`, `parts.csv`, `plate_NN.3mf`),
a CSV używa przecinka jako separatora i kropki dziesiętnej. Po polsku CSV ma średniki i przecinek dziesiętny.

Tłumaczenia są w `tlumaczenia.js` (klucz to tekst polski). Kompletność sprawdzają
`python tools/sprawdz_tlumaczenia.py` oraz `tools/test_tlumaczen.js` (w konsoli przeglądarki).

## Biblioteka plików (STL/PDF)

Pliki VAULT (foldery `01. DRAWERS`, `02. SUSTAINERS`, `03. MODIFICATIONS` i instrukcje PDF) mogą leżeć
w dowolnym katalogu. Jego ścieżka jest zapisana w `ustawienia.json`. Domyślnie jest to `..\vault`.

- W konfiguratorze (uruchom.bat): panel **Biblioteka plików** w lewej kolumnie. Wpisz ścieżkę i kliknij
  *Zmień i przeskanuj*. Po skanowaniu strona sama się odświeży.
- W konsoli: `python skanuj.py "D:\3d\pojemniki\vault"`.

Geometria jest pamiętana według ścieżek względem biblioteki, więc po przeniesieniu całego katalogu
w inne miejsce skanowanie trwa sekundy. Instrukcje PDF i obrazki z biblioteki są podlinkowane w panelu *Instrukcje*.
Katalog wyjściowy (`do_druku`) też jest w `ustawienia.json` (klucz `wyjscie`).

## Wizualizacja 3D

Przycisk **Wizualizacja 3D** w podglądzie zestawu otwiera wieżę w perspektywie, z wymiarami z plików STL.
Przeciągnij myszą, żeby obrócić widok, a kółkiem przybliżysz. Kliknięcie frontu wysuwa szufladę albo otwiera skrzynkę.
Dwuklik przywraca widok domyślny, a Esc zamyka okno.

- Gotowe widoki: przód, bok, 3/4, góra i tył. Jest też automatyczny obrót.
- Etykiety warstw i wymiary wieży w mm.
- Wszystkie zestawy obok siebie, jeśli projekt ma ich kilka.
- Kolory filamentu: obudowa, fronty szuflad i fronty skrzynek. Są gotowe palety albo własne kolory.
- Zapis obrazu do PNG.

Wygląd i układ dodatków odwzorowują rysunki z instrukcji USSA. Koła stoją z tyłu, stopka z przodu, a uchwyt
wysuwany ma pręty z tyłu. Dachy, uchwyty, kręgosłup, pegboard, koła i stopki są narysowane w uproszczeniu. Potrzebna jest przeglądarka z WebGL 2,
czyli każda współczesna.

## Przygotowanie wydruku (zakładka „Przygotuj wydruk”)

Tworzy folder `do_druku/<nazwa projektu>/`, a w nim:
- `stl/`: kopie potrzebnych plików z ilością w nazwie, np. `2x S3 Box 1F.stl`,
- `3mf/plyta_NN.3mf`: części rozmieszczone na stole wybranej drukarki, jeden plik na płytę.
  Części z TPU (opony) trafiają na osobne płyty. Część większa niż stół dostaje płytę `_ZA_DUZE`.
- `3mf/plyty.txt`: zawartość każdej płyty z szacowanym czasem i filamentem,
- `lista.csv`: ta sama lista co eksport CSV.

Pliki 3MF otwierasz w Bambu Studio, OrcaSlicer albo PrusaSlicer, a profil, filament i podpory
ustawiasz w slicerze. Części zostają w orientacji z plików STL.
Istniejący folder nie jest nadpisywany: kolejne przygotowanie tworzy np. `projekt (2)`.

Bez serwera: przycisk *Pobierz zlecenie (JSON)*, potem `python druk.py vault-zlecenie.json`.

### Drukarki (`drukarki.js`)

Obszary druku pochodzą z profili Bambu Studio. W drukarkach dwudyszowych (H2D, H2C, X2D)
każda dysza ma inny zasięg w osi X.

**Ważne:** Bambu Studio przy otwieraniu pliku 3MF spoza Bambu przesuwa całą grupę części
na środek stołu. Dlatego program układa każdą płytę od razu wyśrodkowaną i używa tylko części
obszaru symetrycznej względem środka stołu:
- H2D i H2C: przyjęty obszar 325×300 mm (zasięg jednej dyszy) na środku stołu. 300 mm głębokości
  omija strefę przy tylnej krawędzi. Szeroka płyta może po imporcie zachodzić na pas jednej dyszy;
  wtedy przesuń grupę w bok o kilkanaście mm albo przypisz filament do odpowiedniej dyszy.
- X2D: obie dysze X 20,5–235,5 (215×256), tylko lewa X 0–256 (256×256).

Przy wariancie „tylko lewa dysza” trzeba w slicerze przypisać filament do lewej dyszy.
Strefy wykluczone (np. wykrywanie owijania przy tylnej krawędzi H2S/H2D/H2C, róg X1/P1) są omijane.
Nową drukarkę dodasz, dopisując wpis do `drukarki.js`.

- **Zestawy**: każdy zestaw to jedna wieża o wspólnej głębokości. Ilość mnoży cały zestaw.
- **Warstwy**: warstwa 1 to spód i wyznacza szerokość. Szuflady mogą mieć kilka frontów w jednym module (np. 4F jako 2F / 1F / 1F).
- **Wynik**: zakładki *Do druku* (pliki STL z ilościami, kliknięcie otwiera plik) i *Niedrukowane* (śruby, pręty, łożyska). Eksport CSV otwiera się w Excelu (po polsku rozdzielany średnikami).
- **Dodatkowe pliki**: ręczne dopisanie dowolnego STL, np. przegródek siatkowych (Grid Dividers) albo podpór ręcznych.
- Projekt zapisuje się automatycznie w przeglądarce. Przyciski *Zapisz/Wczytaj projekt* robią kopię do pliku JSON.

## Szacunek czasu druku i filamentu

- Wartości z arkusza USSA (Bambu Lab H2S, basic settings) dotyczą modułów, pudełek, frontów, wiek, prowadnic, sprężyn i kluczyków. Oznaczone są ●.
- Pozostałe pliki są szacowane modelem dopasowanym do arkusza: objętość + powierzchnia z pliku STL. Oznaczone są ○.
- *Mnożnik czasu* przelicza czasy na inną drukarkę lub profil. *Filament zł/kg* liczy koszt materiału.
- Podpory, wymiany płyty i odpady nie są wliczone.

## Odświeżanie danych

Gdy w bibliotece pojawią się nowe pliki STL: *Przeskanuj* w panelu albo `python skanuj.py`.

`skanuj.py` liczy geometrię tylko nowych plików (pamięć podręczna: `geometria_cache.json`)
i na koniec uruchamia `kalibruj.py`, który łączy ją z arkuszem `dane/ussa_print_data.json` i zapisuje `dane_druku.js`.

## Kopia zapasowa

- GitHub (prywatne): https://github.com/rawel2/Vault-Konfigurator – po zmianach `git commit` i `git push`.
- Dropbox: `python kopia.py` tworzy `D:\Dropbox\pojemniki\RRRR-MM-DD\` (historia git .bundle, pliki .zip, CZYTAJ.txt);
  `python kopia.py --nadpisz` zastępuje dzisiejszą kopię nową zamiast tworzyć `_2`, `_3`…
- Biblioteka VAULT (STL/PDF) nie trafia ani do repo, ani do kopii programu, bo licencja USSA zabrania
  udostępniania plików. Jej kopia to `D:\Dropbox\pojemniki\261020_VAULT_USSA.rar`.

Pozycje oznaczone w wyniku jako „do weryfikacji” to ilości, których instrukcja nie podaje wprost
(akcesoria L², łączniki wiek/podstaw, uchwyty ścienne, kręgosłup uniwersalny).
