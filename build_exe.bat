@echo off
setlocal
cd /d "%~dp0"
title PhonePad - build exe

if not exist ".venv\Scripts\python.exe" (
  echo [!] The Python environment is missing.
  echo     Run setup.bat once, then run this again.
  echo.
  pause
  exit /b 1
)

if not exist "backend\static\index.html" (
  echo [!] The web app has not been built yet.
  echo     Run setup.bat once, then run this again.
  echo.
  pause
  exit /b 1
)

echo [1/2] Installing PyInstaller...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --quiet "pyinstaller>=6.10"
if errorlevel 1 goto :failed

echo [2/2] Building dist\PhonePad.exe...
echo       (this takes about a minute)
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean PhonePad.spec
if errorlevel 1 goto :failed

echo.
echo ============================================
echo   Done: dist\PhonePad.exe
echo.
echo   That single file includes Python, the
echo   server and the web app. Send it to anyone
echo   on Windows 10/11.
echo ============================================
echo.
pause
exit /b 0

:failed
echo.
echo [!] Build failed. Scroll up for the error above.
echo.
pause
exit /b 1
