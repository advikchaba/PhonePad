@echo off
setlocal
cd /d "%~dp0"
title PhonePad setup

echo ============================================
echo   PhonePad - first time setup
echo ============================================
echo.

rem ---------------------------------------------------------------- Python
set "PY="
py -3 --version >nul 2>nul
if not errorlevel 1 for /f "delims=" %%P in ('py -3 -c "import sys;print(sys.executable)"') do set "PY=%%P"
if not defined PY (
  python --version >nul 2>nul
  if not errorlevel 1 for /f "delims=" %%P in ('python -c "import sys;print(sys.executable)"') do set "PY=%%P"
)
if not defined PY (
  for %%D in (
    "%LocalAppData%\Programs\Python\Python313\python.exe"
    "%LocalAppData%\Programs\Python\Python312\python.exe"
    "%LocalAppData%\Programs\Python\Python311\python.exe"
    "%LocalAppData%\Programs\Python\Python310\python.exe"
    "%ProgramFiles%\Python312\python.exe"
    "%ProgramFiles%\Python311\python.exe"
  ) do if not defined PY if exist "%%~fD" set "PY=%%~fD"
)
if not defined PY (
  echo [!] Python 3 was not found.
  echo     Install it from https://www.python.org/downloads/ and tick
  echo     "Add python.exe to PATH" during the install, then run setup again.
  echo.
  pause
  exit /b 1
)

rem ------------------------------------------------------------------ venv
if exist ".venv\Scripts\python.exe" (
  echo [1/4] Python environment already exists.
) else (
  echo [1/4] Creating Python environment...
  "%PY%" -m venv .venv
  if errorlevel 1 goto :failed
)

echo [2/4] Installing Python packages...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --quiet --upgrade pip
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r backend\requirements.txt
if errorlevel 1 goto :failed

rem ------------------------------------------------------------------ node
set "NPM="
for /f "delims=" %%P in ('where npm.cmd 2^>nul') do if not defined NPM set "NPM=%%P"
if not defined NPM if exist "%ProgramFiles%\nodejs\npm.cmd" set "NPM=%ProgramFiles%\nodejs\npm.cmd"
if not defined NPM (
  echo [!] Node.js was not found.
  echo     Install the LTS build from https://nodejs.org/ then run setup again.
  echo.
  pause
  exit /b 1
)

echo [3/4] Installing web app packages...
pushd frontend
call "%NPM%" install --no-fund --no-audit
if errorlevel 1 (
  popd
  goto :failed
)

echo [4/4] Building the web app...
call "%NPM%" run build
if errorlevel 1 (
  popd
  goto :failed
)
popd

echo.
echo ============================================
echo   Setup finished.
echo.
echo   Start PhonePad with:  start.bat
echo ============================================
echo.
pause
exit /b 0

:failed
echo.
echo [!] Setup failed. Scroll up to see the error above.
echo.
pause
exit /b 1
