@echo off
setlocal
cd /d "%~dp0"
echo PhonePad is now a desktop application. This helper only builds the executable.
echo.
call build_exe.bat
exit /b %ERRORLEVEL%
