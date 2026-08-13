@echo off
setlocal enabledelayedexpansion

echo ========================================
echo  SUBIR PROYECTO A GITHUB
echo ========================================
echo.

set /p repoURL="Introduce la URL del repositorio (ej: https://github.com/usuario/repo.git): "

if "%repoURL%"=="" (
    echo ERROR: No introdujiste ninguna URL.
    pause
    exit /b 1
)

echo.
echo [1/6] Inicializando repositorio Git...
git init

echo.
echo [2/6] Añadiendo todos los archivos...
git add .

echo.
echo [3/6] Creando commit...
git commit -m "Subida inicial automatica"

echo.
echo [4/6] Renombrando rama a 'main' (para estandarizar)...
git branch -M main

echo.
echo [5/6] Configurando repositorio remoto 'origin'...
git remote add origin %repoURL% 2>nul
if errorlevel 1 (
    echo El remoto 'origin' ya existe. Actualizando URL...
    git remote set-url origin %repoURL%
)

echo.
echo [6/6] Subiendo codigo a GitHub (rama main)...
git push -u origin main

echo.
echo ========================================
echo  ¡PROCESO FINALIZADO!
echo ========================================
pause