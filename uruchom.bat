@echo off
rem Konfigurator VAULT – start serwera i przeglądarki. Sam szuka Pythona i doinstalowuje numpy.
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"

rem Python 3.9+: launcher py, python z PATH (atrapa ze Sklepu Microsoft nie przejdzie testu),
rem a na koniec typowe miejsce instalacji (świeżo zainstalowany Python nie jest jeszcze w PATH tego okna).
set "PY="
py -3 -c "import sys; sys.exit(sys.version_info < (3, 9))" >nul 2>&1 && set "PY=py -3"
if not defined PY (
  python -c "import sys; sys.exit(sys.version_info < (3, 9))" >nul 2>&1 && set "PY=python"
)
if not defined PY (
  for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" set PY="%%D\python.exe"
  )
)
if not defined PY (
  echo.
  echo Nie znaleziono Pythona 3.9 lub nowszego.  /  Python 3.9+ not found.
  echo Uruchom instaluj.bat albo zainstaluj Pythona: https://www.python.org/downloads/
  echo.
  pause
  exit /b 1
)

%PY% -c "import numpy" >nul 2>&1
if errorlevel 1 (
  echo Instaluję bibliotekę numpy...  /  Installing numpy...
  %PY% -m pip install --user --disable-pip-version-check numpy
  if errorlevel 1 (
    echo Nie udało się zainstalować numpy.  /  Could not install numpy.
    pause
    exit /b 1
  )
)

rem argumenty (np. --bez-przegladarki) trafiaja do serwera
%PY% serwer.py %*
pause
