@echo off
setlocal
cd /d "%~dp0"
title PhonePad

if not exist ".venv\Scripts\python.exe" goto :setup
if not exist "backend\static\index.html" goto :setup

rem Let the user pick a pad type for this run:  start.bat ps
if /i "%~1"=="ps" set "PHONEPAD_PAD=ps"
if /i "%~1"=="xbox" set "PHONEPAD_PAD=xbox"

echo Starting PhonePad - close this window to stop the server.
echo.
".venv\Scripts\python.exe" -m backend.main
set "CODE=%ERRORLEVEL%"

echo.
if not "%CODE%"=="0" (
  echo PhonePad exited with code %CODE%.
) else (
  echo PhonePad stopped.
)
pause
exit /b %CODE%

:setup
echo PhonePad is not set up yet. Running setup first...
echo.
call "%~dp0setup.bat"
if errorlevel 1 exit /b 1
echo.
echo Starting PhonePad...
echo.
".venv\Scripts\python.exe" -m backend.main
echo.
pause
exit /b 0
