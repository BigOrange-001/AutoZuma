@echo off
setlocal

cd /d "%~dp0"
set "PYTHON=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo AutoZuma Next virtual environment was not found:
    echo   %PYTHON%
    echo.
    echo Create the local .venv and install dependencies first, then run this launcher again.
    echo.
    pause
    exit /b 1
)

"%PYTHON%" -m autozuma.gui.app %*
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo AutoZuma Next GUI exited with error code %EXIT_CODE%.
    echo.
    pause
)

exit /b %EXIT_CODE%
