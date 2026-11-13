@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Earth System Trend Detective

echo ============================================================
echo   EARTH SYSTEM TREND DETECTIVE
echo ============================================================
echo.
echo Starting the Russian desktop application.
echo First setup requires internet to install Python packages.
echo Live analysis downloads real observations from NASA services.
echo.

set "PYTHON_CMD="
where py >nul 2>&1
if not errorlevel 1 (
    py -3.12 --version >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=py -3.12"
    if not defined PYTHON_CMD (
        py -3 --version >nul 2>&1
        if not errorlevel 1 set "PYTHON_CMD=py -3"
    )
)
if not defined PYTHON_CMD (
    where python >nul 2>&1
    if not errorlevel 1 (
        python --version >nul 2>&1
        if not errorlevel 1 set "PYTHON_CMD=python"
    )
)
if not defined PYTHON_CMD (
    echo Python 3.12 or newer was not found.
    echo Install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

%PYTHON_CMD% -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)"
if errorlevel 1 (
    echo Python 3.12 or newer is required.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating an isolated Python environment...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto :error
)

if not exist ".venv\requirements-installed.flag" (
    echo Installing project dependencies. This is needed only on first start.
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    if errorlevel 1 goto :error
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto :error
    echo installed>".venv\requirements-installed.flag"
)

echo Starting the application...
".venv\Scripts\python.exe" -m science_core.desktop
if errorlevel 1 (
    echo.
    echo The application stopped with an error. Read the message above.
    pause
    exit /b 1
)
exit /b 0

:error
echo.
echo Setup failed. Check internet connection and Python installation.
pause
exit /b 1
