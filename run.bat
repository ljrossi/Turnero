@echo off
title Shift Scheduler Launcher
echo ==============================
echo   SHIFT SCHEDULER - SETUP
echo ==============================
echo.

:: Detectar si existe 'py' (launcher de Windows) o 'python'
where py >nul 2>nul
if %errorlevel% equ 0 (
    set PYTHON_CMD=py -3
    echo [OK] Python Launcher (py) detected.
) else (
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        set PYTHON_CMD=python
        echo [OK] Python detected.
    ) else (
        echo [ERROR] Python 3 is not installed or not in PATH.
        echo.
        echo Please download and install Python 3 from: https://www.python.org/downloads/
        echo IMPORTANT: During installation, check the box "Add Python to PATH".
        pause
        exit /b 1
    )
)

:: Verificar version de Python
echo [CHECK] Python version:
%PYTHON_CMD% --version
if %errorlevel% neq 0 (
    echo [ERROR] Failed to run Python.
    pause
    exit /b 1
)

:: Instalar ReportLab (única dependencia externa)
echo.
echo [INSTALL] Installing ReportLab (PDF generator)...
%PYTHON_CMD% -m pip install --upgrade reportlab
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install ReportLab.
    echo Please try manually: %PYTHON_CMD% -m pip install reportlab
    pause
    exit /b 1
)

:: Ejecutar la aplicación
echo.
echo [RUN] Starting the application...
echo ==============================
%PYTHON_CMD% main.py

:: Reemplaza "main.py" por el nombre real de tu archivo principal (ej. turnero.py)

echo.
echo ==============================
echo Application closed.
pause