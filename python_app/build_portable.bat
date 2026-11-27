@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo   PatchWise Desktop - Build Eseguibile Portable (.EXE)
echo ============================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERRORE] Python 3.10+ non trovato nel PATH di sistema.
    echo Scarica Python da https://www.python.org/downloads/ e riprova.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo [1/4] Creazione ambiente virtuale isolato .venv...
    python -m venv .venv
)

echo [2/4] Attivazione ambiente virtuale e installazione dipendenze...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
pip install -r requirements.txt

echo [3/4] Esecuzione test unitari del motore OOP...
python -m unittest discover -s tests -v
if %errorlevel% neq 0 (
    echo [ERRORE] I test unitari non sono stati superati. Build interrotta.
    pause
    exit /b 1
)

echo [4/4] Compilazione eseguibile portable single-file...
python build_portable.py --name PatchWise_Portable

echo.
echo Eseguibile pronto in: dist\PatchWise_Portable.exe
echo Copialo su qualsiasi PC Windows ed eseguilo direttamente senza installazione.
pause
