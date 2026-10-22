@echo off
rem ==========================================================================================
rem  Instalator konfiguratora VAULT  /  VAULT configurator installer
rem  Wersja angielska: install.bat – ta sama logika, przy zmianach popraw oba pliki.
rem  1. sprawdza Pythona 3.9+ (w razie braku proponuje instalację przez winget),
rem  2. pobiera program z GitHuba (najnowsze wydanie, plik vault-konfigurator.zip),
rem  3. rozpakowuje do <folder>\konfigurator (ustawienia.json zostaje – można tak aktualizować),
rem  4. instaluje numpy, tworzy skrót na pulpicie i uruchamia program.
rem  Pliki STL/PDF VAULT nie są częścią programu (licencja USSA) – program poprosi o ich folder.
rem
rem  Do testów (bez pytań):  set VAULT_ZIP=plik.zip lub adres ^& set VAULT_DIR=folder ^& set VAULT_AUTO=1
rem                         set VAULT_NOSTART=1 – bez skrótu i bez uruchamiania
rem ==========================================================================================
chcp 65001 >nul
setlocal EnableExtensions
title Instalator konfiguratora VAULT
rem publiczne repozytorium tylko z wydaniami (kod źródłowy jest w prywatnym rawel2/Vault-Konfigurator)
set "REPO=rawel2/Vault-Konfigurator-wydania"
set "ZIP_URL=https://github.com/%REPO%/releases/latest/download/vault-konfigurator.zip"
if defined VAULT_ZIP set "ZIP_URL=%VAULT_ZIP%"

echo.
echo  ============================================================
echo    Konfigurator VAULT – instalacja  /  installation
echo  ============================================================
echo.

rem ---------- 1. Python ----------
echo [1/5] Sprawdzam Pythona...  /  Checking Python...
rem (bez bloków w nawiasach: zmienne z set /p byłyby w nich podstawione przed odpowiedzią)
call :znajdz_python
if defined PY goto :python_ok
echo   Nie znaleziono Pythona 3.9 lub nowszego.  /  Python 3.9+ not found.
where winget >nul 2>&1 || goto :python_recznie
if defined VAULT_AUTO goto :python_recznie
set "ODP="
set /p "ODP=  Zainstalować Pythona 3.12 przez winget? / Install Python 3.12 with winget? [T/n] "
if /i "%ODP%"=="n" goto :python_recznie
winget install -e --id Python.Python.3.12 --scope user --accept-source-agreements --accept-package-agreements
call :znajdz_python
if not defined PY goto :python_recznie
:python_ok
%PY% -c "import sys; print('  OK: Python ' + sys.version.split()[0])"

rem ---------- 2. Folder ----------
echo.
set "CEL=%USERPROFILE%\VAULT"
if defined VAULT_DIR set "CEL=%VAULT_DIR%"
if defined VAULT_AUTO goto :folder_ok
echo [2/5] Folder instalacji  /  Install folder
echo   Program trafi do ...\konfigurator, obok powstaną foldery vault (pliki STL) i do_druku.
echo   The program goes to ...\konfigurator, next to it: vault (STL files) and do_druku (output).
set /p "CEL=  Enter = %CEL%  > "
:folder_ok
for %%F in ("%CEL%") do set "CEL=%%~fF"
set "PROG=%CEL%\konfigurator"
echo   Folder: %CEL%

rem ---------- 3. Pobranie i rozpakowanie ----------
echo.
echo [3/5] Pobieram program...  /  Downloading the program...
set "TMPD=%TEMP%\vault_instalacja_%RANDOM%"
mkdir "%TMPD%" >nul 2>&1
set "ZIP=%TMPD%\vault-konfigurator.zip"
if exist "%ZIP_URL%" (
  copy /y "%ZIP_URL%" "%ZIP%" >nul
) else (
  curl.exe -L --fail --silent --show-error -o "%ZIP%" "%ZIP_URL%"
  if errorlevel 1 powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -UseBasicParsing -Uri '%ZIP_URL%' -OutFile '%ZIP%'" 2>nul
)
if not exist "%ZIP%" goto :blad_pobierania
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Force -LiteralPath '%ZIP%' -DestinationPath '%TMPD%\pliki'"
if not exist "%TMPD%\pliki\serwer.py" goto :blad_pobierania
rem robocopy: kopiuje nowe pliki, nie usuwa ustawień (ustawienia.json) ani pamięci geometrii z poprzedniej instalacji
robocopy "%TMPD%\pliki" "%PROG%" /E /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto :blad_kopiowania
if not exist "%CEL%\vault" mkdir "%CEL%\vault"
if not exist "%CEL%\do_druku" mkdir "%CEL%\do_druku"
rmdir /s /q "%TMPD%" >nul 2>&1
set "WERSJA="
if exist "%PROG%\wersja.txt" set /p WERSJA=<"%PROG%\wersja.txt"
echo   OK: %PROG%  %WERSJA%

rem ---------- 4. numpy ----------
echo.
echo [4/5] Instaluję numpy...  /  Installing numpy...
%PY% -c "import numpy" >nul 2>&1
if errorlevel 1 %PY% -m pip install --user --disable-pip-version-check numpy
%PY% -c "import numpy" >nul 2>&1
if errorlevel 1 (
  echo   Nie udało się zainstalować numpy – program spróbuje ponownie przy starcie.
  echo   Could not install numpy – the program will retry on start.
) else (
  echo   OK: numpy
)

rem ---------- 5. Skrót i start ----------
echo.
if defined VAULT_NOSTART goto :koniec
echo [5/5] Skrót na pulpicie i uruchomienie...  /  Desktop shortcut and start...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([IO.Path]::Combine([Environment]::GetFolderPath('Desktop'),'Konfigurator VAULT.lnk')); $s.TargetPath='%PROG%\uruchom.bat'; $s.WorkingDirectory='%PROG%'; $s.IconLocation='%SystemRoot%\System32\imageres.dll,165'; $s.Save()" >nul 2>&1
echo   Skrót: „Konfigurator VAULT” na pulpicie  /  shortcut: "Konfigurator VAULT" on the desktop
echo.
echo   Pliki STL VAULT rozpakuj do %CEL%\vault albo wskaż ich folder w programie.
echo   Unpack the VAULT STL files to %CEL%\vault or point the program to their folder.
echo.
start "Konfigurator VAULT" "%PROG%\uruchom.bat"
:koniec
echo  Gotowe.  /  Done.
if not defined VAULT_AUTO pause
exit /b 0

rem ---------- procedury ----------
:znajdz_python
set "PY="
py -3 -c "import sys; sys.exit(sys.version_info < (3, 9))" >nul 2>&1 && set "PY=py -3"
if defined PY exit /b 0
python -c "import sys; sys.exit(sys.version_info < (3, 9))" >nul 2>&1 && set "PY=python"
if defined PY exit /b 0
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%D\python.exe" set PY="%%D\python.exe"
exit /b 0

:python_recznie
echo.
echo   Zainstaluj Pythona 3.9+ ze strony python.org (zaznacz „Add python.exe to PATH”)
echo   i uruchom instalator ponownie.
echo   Install Python 3.9+ from python.org (tick "Add python.exe to PATH") and run the installer again.
if not defined VAULT_AUTO start "" "https://www.python.org/downloads/"
if not defined VAULT_AUTO pause
exit /b 1

:blad_pobierania
echo.
echo   Nie udało się pobrać lub rozpakować programu z:  /  Could not download or unpack:
echo   %ZIP_URL%
echo   Sprawdź połączenie z internetem albo pobierz wydanie ręcznie: https://github.com/%REPO%/releases
echo   Check your internet connection or download the release manually.
if not defined VAULT_AUTO pause
exit /b 2

:blad_kopiowania
echo.
echo   Nie udało się skopiować plików do %PROG%  /  Could not copy files to %PROG%
if not defined VAULT_AUTO pause
exit /b 3
