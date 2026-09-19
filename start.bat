@echo off
REM MARC Micromouse Simulator - one-click starter (Windows).
REM Double-click this file: it checks Python, installs dependencies,
REM then launches the simulator.
title MARC Micromouse Simulator
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found.
    echo Install Python 3.10 or newer from https://www.python.org/downloads/
    echo IMPORTANT: tick "Add python.exe to PATH" during installation.
    pause
    exit /b 1
)

echo [1/3] Python found:
python --version

echo [2/3] Installing dependencies (pygame)...
python -m pip install --upgrade pip >nul 2>nul
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [WARN] Standard install failed, retrying pygame-ce directly...
    python -m pip install "pygame-ce>=2.5.0"
)
if errorlevel 1 (
    echo [ERROR] Could not install dependencies. Check your internet connection.
    echo You can also try manually:  python -m pip install pygame-ce
    pause
    exit /b 1
)

echo [3/3] Launching simulator...
python main.py --2d
if errorlevel 1 (
    echo.
    echo [ERROR] The simulator exited with an error (see above).
    pause
    exit /b 1
)
