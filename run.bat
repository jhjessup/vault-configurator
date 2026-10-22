@echo off
rem VAULT configurator – English name for uruchom.bat (starts the server and the browser).
rem All the logic is in uruchom.bat; arguments (e.g. --bez-przegladarki) are passed on.
call "%~dp0uruchom.bat" %*
