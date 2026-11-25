@echo off
setlocal
cd /d "%~dp0"
title Build PhonePad desktop application

if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 goto :failed
)

echo Installing desktop application dependencies...
set "VGAMEPAD_SKIP_VIGEMBUS_INSTALL=true"
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --upgrade -r requirements.txt
if errorlevel 1 goto :failed

echo Building the windowed PhonePad application...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean PhonePad.spec
if errorlevel 1 goto :failed

echo.
echo Built: dist\PhonePad.exe
echo Launch PhonePad.exe directly. It opens as a desktop window with no command prompt.
echo.
pause
exit /b 0

:failed
echo.
echo Build failed. Check the messages above and try again.
echo.
pause
exit /b 1
