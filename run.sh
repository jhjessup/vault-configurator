#!/bin/sh
# VAULT configurator - start on Linux/macOS (Linux counterpart of run.bat / uruchom.bat).
# Finds Python 3.9+, makes sure numpy is available, starts the server and opens the browser.
# Arguments (e.g. --bez-przegladarki = do not open the browser) are passed on to serwer.py.
# If the system Python has no numpy, numpy is installed into a local .venv folder next to this script.
set -e
cd "$(dirname "$0")"

if [ -x .venv/bin/python ]; then
    PY=.venv/bin/python
else
    PY=
    for p in python3 python; do
        if command -v "$p" >/dev/null 2>&1 && "$p" -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; then
            PY=$p
            break
        fi
    done
    if [ -z "$PY" ]; then
        echo "Python 3.9+ not found. Install it with your package manager (e.g. sudo apt install python3)."
        exit 1
    fi
    if ! "$PY" -c 'import numpy' 2>/dev/null; then
        echo "Installing numpy into .venv ..."
        if ! "$PY" -m venv .venv; then
            echo "Could not create .venv. Install numpy with your package manager"
            echo "(e.g. sudo apt install python3-numpy) or install python3-venv, then run this again."
            exit 1
        fi
        .venv/bin/python -m pip install --disable-pip-version-check --quiet numpy
        PY=.venv/bin/python
    fi
fi

if ! "$PY" -c 'import tkinter' 2>/dev/null; then
    echo "Note: tkinter is missing, so the folder picker is unavailable - type the folder path instead"
    echo "(or install it, e.g. sudo apt install python3-tk)."
fi

exec "$PY" serwer.py "$@"
