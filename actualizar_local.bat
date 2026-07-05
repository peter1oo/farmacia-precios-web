@echo off
setlocal

cd /d "%~dp0"

echo Extrayendo catalogo...
py scraper\extraer_catalogo.py
if errorlevel 1 goto :error

echo Calculando ranking de ventas...
py scraper\calcular_ranking_ventas.py
if errorlevel 1 goto :error

git add data\catalogo.json data\ranking_ventas.json
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Actualizacion diaria de catalogo local"
    git push
) else (
    echo Sin cambios en el catalogo hoy, no se sube nada.
)

echo Listo.
exit /b 0

:error
echo Fallo la actualizacion local. Revisa el mensaje de error arriba.
exit /b 1
