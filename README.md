# VAULT configurator

*Wersja polska: [README.pl.md](README.pl.md)*

> **About this repository:** an independent copy of the VAULT configurator by rawel2, started from version 1.1.2 of
> [rawel2/Vault-Konfigurator-wydania](https://github.com/rawel2/Vault-Konfigurator-wydania). Changes from upstream:
> the source code is kept in git, it runs on **Linux and macOS** (`run.sh`), console messages are translated,
> and the USSA print data is no longer bundled (see [Print data](#print-data-ussa_print_datajson)).
> It is not maintained by rawel2 or USSA Design.

A local tool for the **VAULT** 3D-printed storage system by USSA (https://www.ussadesign.com/pages/vault).
You configure towers of drawers and sustainers (top-opening cases), and the program gives you:

- the list of STL files to print, with quantities,
- the hardware list (bolts, M16 rods, bearings, heat inserts),
- a print time, filament and cost estimate,
- optionally: copies of the STL files and ready 3MF plates for your printer.

The program works fully offline. The VAULT STL/PDF files are **not** included – you need your own copy
(Kickstarter or ussadesign.com); the USSA licence does not allow sharing them.

## Installation

Requirements: Python 3.9+ and `numpy` (the start scripts install `numpy` if needed), and a current web browser.

### Linux and macOS

```sh
git clone https://github.com/jhjessup/vault-configurator
cd vault-configurator
./run.sh
```

`run.sh` finds Python, uses the system `numpy` if it is installed, otherwise installs it into a local `.venv` folder
(on Debian/Ubuntu this needs `python3-venv`; alternatively `sudo apt install python3-numpy`). The folder picker needs
tkinter (`sudo apt install python3-tk`); without it, type the folder path instead. To update: `git pull`.

### Windows

Download this repository (`git clone`, or *Code → Download ZIP* on GitHub) and double-click **`run.bat`**.

**Note:** `install.bat` and `instaluj.bat` are upstream's installers: they download and install **rawel2's release**,
not this repository. Use them if you want the original Windows version.

### Folders

By default the program uses two folders **next to** the program folder (not inside it): `vault` for the STL library
and `to_print` for output (`do_druku` on Polish systems, or if that folder already exists). Both can be changed in
the **File library** panel. Settings are saved in `ustawienia.json` in the program folder.

The full manual with screenshots (`VAULT_manual_EN.pdf`) is in upstream's
[release](https://github.com/rawel2/Vault-Konfigurator-wydania/releases/latest); it describes version 1.1.2 on Windows.

## Authors and rights

- Program authors: **rawel2** and **Claude** (Anthropic); changes in this repository: **jhjessup** and **Claude**.
  Program licence: **MIT** (`LICENSE` file);
  it does not cover USSA Design materials – see `NOTICE.md`.
- The VAULT system, its design, STL files and PDF manuals belong to **USSA Design**. Buy the files from the maker:
  https://www.ussadesign.com/pages/vault. The program does not include them.
- The configurator is an unofficial tool and is not affiliated with USSA Design.
- rawel2's version is shared with the permission of USSA Design (October 2026). Still unofficial – USSA Design is not
  responsible for the program and does not support it. That permission was given to rawel2; this repository does not
  claim any permission of its own and does not include USSA materials.

## Starting

Run **`./run.sh`** (Linux/macOS) or **`run.bat`** (Windows; `uruchom.bat` is the same). It starts a small local
server (127.0.0.1 only) and opens the configurator in the browser. Keep the console window open while you work;
press Ctrl+C or close it to stop the server. Starting it again while the server is running just opens the running one.

Opening `index.html` directly also works, but without copying files and creating 3MF plates
(the manual links then work only when the library is in `..\vault`).

**Language:** the selector in the header – *automatic* (the first of your browser's languages that the program
supports, otherwise English), *Polski*, *English*. Console messages follow the system language.

## File library (STL/PDF)

The VAULT files (folders `01. DRAWERS`, `02. SUSTAINERS`, `03. MODIFICATIONS` and the PDF manuals) can live in
any folder. Set it in the **File library** panel (left column): type the path and click *Change and scan*.
The page reloads when the scan is finished. From a console: `python3 skanuj.py "/path/to/vault"`.

The first scan of the full library (~23 GB) computes the geometry of every STL file and takes 2–3 minutes;
later scans only process new or changed files. The PDF manuals and images are linked in the *Instructions* panel.

## Using the configurator

- **Sets**: each set is one tower with a common depth (3–7, × 42 mm). The quantity multiplies the whole set.
- **Layers**: layer 1 is the bottom and sets the tower width. L, L² and 2× S give width L; XL, XL² and S + M give
  width XL. Drawer modules can hold several facades (e.g. 4F as 2F / 1F / 1F).
- **Top**: a drawer roof (Grid, Table, Bowl, Under Table Mount, Heavyweight) and an optional top handle.
  A sustainer on top closes the tower with its own lid.
- **Modifications**: base with wheels and feet, backbone, pegboard, stationary or pull-out handle, wall mounts.
- **Result**: *To print* (STL files with quantities, click to open a file) and *Hardware*. *Export CSV* creates
  a spreadsheet (comma-separated in English, semicolon-separated in Polish).
- **Extra files**: add any STL by hand, e.g. grid dividers for drawers or manual supports.
- The project is saved in the browser automatically; *Save/Load project* makes a JSON copy.

Items marked “quantity to be verified” are quantities the manual does not state explicitly
(L² accessories, lid and base connectors, wall mount second part, universal backbone).

## 3D view

The **3D view** button in the stack preview opens the tower in perspective, with dimensions taken from the STL files.
Drag to rotate and use the wheel to zoom. Clicking a front slides the drawer out or opens the sustainer.
Double-click restores the default view, and Esc closes the window.

- Preset views: front, side, 3/4, top and back. Automatic rotation is also available.
- Layer labels and tower dimensions in mm.
- All stacks side by side when the project has several.
- Filament colors for the housing, drawer fronts and sustainer fronts, with preset palettes or custom colors.
- Saving the image as PNG.

The look and placement of the add-ons follow the drawings in the USSA manual. The wheels are at the back, the foot
at the front, and the pull-out handle has its rods at the back. Roofs, handles, backbone, pegboard, wheels and feet are simplified. A browser with WebGL 2 is required,
which means any current browser.

## Print data (`ussa_print_data.json`)

The print time and filament estimate uses print data published by USSA Design. It is **not included** in this
repository. Without it the program works normally, but shows no print estimate. To use it, take
`dane/ussa_print_data.json` from upstream's `vault-konfigurator.zip`
([latest release](https://github.com/rawel2/Vault-Konfigurator-wydania/releases/latest)) and either:

- put `ussa_print_data.json` in your STL library folder (next to `01. DRAWERS`), or
- set its full path as `"dane_ussa"` in `ustawienia.json`, or
- put it in `dane/` inside the program folder (upstream's layout).

Then run *Scan* in the **File library** panel so the estimate is calculated.

## Print estimate

- Values from the USSA sheet (Bambu Lab H2S, basic settings) cover modules, boxes, facades, lids, runners, springs
  and keys; they are marked ●.
- Other files are estimated by a model fitted to the sheet (STL volume + surface area); marked ○.
- *Time multiplier* scales the times for another printer or profile; *Filament price/kg* gives the material cost.
- Supports, plate changes and waste are not included.

## Prepare print (tab “Prepare print”)

Creates `to_print/<project name>/` (see [Folders](#folders)) with:
- `stl/` – copies of the needed files with the quantity in the name, e.g. `2x S3 Box 1F.stl`,
- `3mf/plate_NN.3mf` – parts arranged on the bed of the selected printer, one file per plate. TPU parts (tyres)
  get their own plates; a part larger than the bed gets a `_TOO_BIG` plate,
- `3mf/plates.txt` – contents of each plate with estimated time and filament,
- `parts.csv` – the same list as the CSV export.

Open the 3MF files in Bambu Studio, OrcaSlicer or PrusaSlicer and choose the profile, filament and supports there.
Parts keep the orientation from the STL files. An existing folder is never overwritten (`project (2)` etc.).

Without the server: *Download job (JSON)*, then `python3 druk.py vault-job.json`.

### Printers (`drukarki.js`)

Print areas come from the Bambu Studio printer profiles. **Important:** when Bambu Studio opens a 3MF that
was not created by Bambu Studio, it moves the whole group of parts to the centre of the bed. The program therefore
writes each plate already centred and only uses the part of the nozzle area that is symmetric around the bed centre:
- H2D and H2C: a 325×300 mm area in the centre of the bed (single-nozzle reach; 300 mm depth avoids the zone at the
  back edge). A wide plate may overlap a single-nozzle strip after import – then shift the group by 10–20 mm or assign
  the filament to the matching nozzle.
- X2D: both nozzles X 20.5–235.5 (215×256), left nozzle only X 0–256 (256×256).

Excluded zones (wrapping detection at the back edge of H2S/H2D/H2C, the X1/P1 corner) are avoided.
Add a printer by adding an entry to `drukarki.js`.

## Updating data

New STL files in the library: *Scan* in the panel or `python3 skanuj.py`. If the print data is available, the scan
also runs `kalibruj.py`, which combines the geometry with it into `dane_druku.js`. The files the scan creates
(`katalog.js`, `geometria_cache.json`, `dane_druku.js`) are not kept in git.

## Translations

All texts go through `tr()` with the Polish text as the key; translations are in `tlumaczenia.js`, shared by the
browser and the Python scripts. Check completeness with `python3 tools/sprawdz_tlumaczenia.py` and, in the browser
console, `tools/test_tlumaczen.js`. `tools/instrukcja.py` and `tools/wydanie.py` (manual and release builds) need
upstream's `docs/` folder, which is not public, so they do not work in this repository.
