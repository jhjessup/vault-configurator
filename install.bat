@echo off
rem ==========================================================================================
rem  VAULT configurator installer (English).  Polish version: instaluj.bat – keep both in sync.
rem  1. checks for Python 3.9+ (offers to install it with winget if missing),
rem  2. downloads the program from GitHub (latest release, vault-konfigurator.zip),
rem  3. unpacks it to <folder>\konfigurator (ustawienia.json is kept – also works as an update),
rem  4. installs numpy, creates a desktop shortcut and starts the program.
rem  The VAULT STL/PDF files are not part of the program (USSA licence) – the program asks for their folder.
rem
rem  For tests (no questions):  set VAULT_ZIP=file.zip or URL ^& set VAULT_DIR=folder ^& set VAULT_AUTO=1
rem                            set VAULT_NOSTART=1 – no shortcut and no start
rem ==========================================================================================
chcp 65001 >nul
setlocal EnableExtensions
title VAULT configurator installer
rem public repository with releases only (the source code is in the private rawel2/Vault-Konfigurator)
set "REPO=rawel2/Vault-Konfigurator-wydania"
set "ZIP_URL=https://github.com/%REPO%/releases/latest/download/vault-konfigurator.zip"
if defined VAULT_ZIP set "ZIP_URL=%VAULT_ZIP%"

echo.
echo  ============================================================
echo    VAULT configurator - installation
echo  ============================================================
echo.

rem ---------- 1. Python ----------
echo [1/5] Checking Python...
rem (no blocks in brackets: variables from set /p would be expanded there before the answer)
call :find_python
if defined PY goto :python_ok
echo   Python 3.9 or newer was not found.
where winget >nul 2>&1 || goto :python_manual
if defined VAULT_AUTO goto :python_manual
set "ANS="
set /p "ANS=  Install Python 3.12 with winget? [Y/n] "
if /i "%ANS%"=="n" goto :python_manual
winget install -e --id Python.Python.3.12 --scope user --accept-source-agreements --accept-package-agreements
call :find_python
if not defined PY goto :python_manual
:python_ok
%PY% -c "import sys; print('  OK: Python ' + sys.version.split()[0])"

rem ---------- 2. Folder ----------
echo.
set "DEST=%USERPROFILE%\VAULT"
if defined VAULT_DIR set "DEST=%VAULT_DIR%"
if defined VAULT_AUTO goto :folder_ok
echo [2/5] Install folder
echo   The program goes to ...\konfigurator; next to it the installer creates
echo   vault (for the VAULT STL files) and do_druku (prepared prints).
set /p "DEST=  Enter = %DEST%  > "
:folder_ok
for %%F in ("%DEST%") do set "DEST=%%~fF"
set "PROG=%DEST%\konfigurator"
echo   Folder: %DEST%

rem ---------- 3. Download and unpack ----------
echo.
echo [3/5] Downloading the program...
set "TMPD=%TEMP%\vault_install_%RANDOM%"
mkdir "%TMPD%" >nul 2>&1
set "ZIP=%TMPD%\vault-konfigurator.zip"
if exist "%ZIP_URL%" (
  copy /y "%ZIP_URL%" "%ZIP%" >nul
) else (
  curl.exe -L --fail --silent --show-error -o "%ZIP%" "%ZIP_URL%"
  if errorlevel 1 powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -UseBasicParsing -Uri '%ZIP_URL%' -OutFile '%ZIP%'" 2>nul
)
if not exist "%ZIP%" goto :download_error
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Force -LiteralPath '%ZIP%' -DestinationPath '%TMPD%\files'"
if not exist "%TMPD%\files\serwer.py" goto :download_error
rem robocopy: copies the new files, keeps the settings (ustawienia.json) and geometry cache of a previous installation
robocopy "%TMPD%\files" "%PROG%" /E /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto :copy_error
if not exist "%DEST%\vault" mkdir "%DEST%\vault"
if not exist "%DEST%\do_druku" mkdir "%DEST%\do_druku"
rmdir /s /q "%TMPD%" >nul 2>&1
set "VERSION="
if exist "%PROG%\wersja.txt" set /p VERSION=<"%PROG%\wersja.txt"
echo   OK: %PROG%  %VERSION%

rem ---------- 4. numpy ----------
echo.
echo [4/5] Installing numpy...
%PY% -c "import numpy" >nul 2>&1
if errorlevel 1 %PY% -m pip install --user --disable-pip-version-check numpy
%PY% -c "import numpy" >nul 2>&1
if errorlevel 1 (
  echo   Could not install numpy - the program will retry on start.
) else (
  echo   OK: numpy
)

rem ---------- 5. Shortcut and start ----------
echo.
if defined VAULT_NOSTART goto :done
echo [5/5] Desktop shortcut and start...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([IO.Path]::Combine([Environment]::GetFolderPath('Desktop'),'VAULT Configurator.lnk')); $s.TargetPath='%PROG%\run.bat'; $s.WorkingDirectory='%PROG%'; $s.IconLocation='%SystemRoot%\System32\imageres.dll,165'; $s.Save()" >nul 2>&1
echo   Shortcut: "VAULT Configurator" on the desktop
echo.
echo   Unpack the VAULT STL files to %DEST%\vault or point the program to their folder.
echo   Switch the program language with "Language" at the top of the page (automatic, Polski, English).
echo.
start "VAULT configurator" "%PROG%\run.bat"
:done
echo  Done.
if not defined VAULT_AUTO pause
exit /b 0

rem ---------- procedures ----------
:find_python
set "PY="
py -3 -c "import sys; sys.exit(sys.version_info < (3, 9))" >nul 2>&1 && set "PY=py -3"
if defined PY exit /b 0
python -c "import sys; sys.exit(sys.version_info < (3, 9))" >nul 2>&1 && set "PY=python"
if defined PY exit /b 0
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%D\python.exe" set PY="%%D\python.exe"
exit /b 0

:python_manual
echo.
echo   Install Python 3.9+ from python.org (tick "Add python.exe to PATH")
echo   and run this installer again.
if not defined VAULT_AUTO start "" "https://www.python.org/downloads/"
if not defined VAULT_AUTO pause
exit /b 1

:download_error
echo.
echo   Could not download or unpack the program from:
echo   %ZIP_URL%
echo   Check your internet connection or download the release manually: https://github.com/%REPO%/releases
if not defined VAULT_AUTO pause
exit /b 2

:copy_error
echo.
echo   Could not copy files to %PROG%
if not defined VAULT_AUTO pause
exit /b 3
