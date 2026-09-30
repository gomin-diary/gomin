:; exec bash "$(dirname "$0")/setup.sh" "$@" # POSIX entry; ignore the CR in CRLF
@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" %*
exit /b %errorlevel%
