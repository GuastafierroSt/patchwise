@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ============================================================
echo   PatchWise Desktop - Build Eseguibile Portable (.EXE)
echo ============================================================
echo.

REM Individua un interprete Python Windows nativo (CPython MSC >= 3.10),
REM evitando Python MSYS2/MinGW (che crea .venv\bin anziche' .venv\Scripts)
REM e gli alias di Microsoft Store (WindowsApps).
set "PYTHON_EXE="
for /f "usebackq delims=" %%P in (`where python 2^>nul`) do (
    if not defined PYTHON_EXE (
        echo "%%~P" | findstr /I /C:"\WindowsApps" /C:"\msys64" /C:"\mingw" /C:"\cygwin" >nul
        if errorlevel 1 (
            "%%~P" -c "import sys; raise SystemExit(0 if ('MSC' in sys.version and sys.version_info >= (3, 10)) else 1)" >nul 2>nul
            if not errorlevel 1 set "PYTHON_EXE=%%~P"
        )
    )
)

REM Fallback: cerca installazioni CPython standard se non trovate nel PATH
if not defined PYTHON_EXE (
    if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
        "%LOCALAPPDATA%\Python\bin\python.exe" -c "import sys; raise SystemExit(0 if ('MSC' in sys.version and sys.version_info >= (3, 10)) else 1)" >nul 2>nul
        if not errorlevel 1 set "PYTHON_EXE=%LOCALAPPDATA%\Python\bin\python.exe"
    )
)
if not defined PYTHON_EXE (
    for /d %%D in ("%LOCALAPPDATA%\Python\pythoncore-*" "%LOCALAPPDATA%\Programs\Python\Python3*" "C:\Python3*") do (
        if not defined PYTHON_EXE if exist "%%~D\python.exe" (
            "%%~D\python.exe" -c "import sys; raise SystemExit(0 if ('MSC' in sys.version and sys.version_info >= (3, 10)) else 1)" >nul 2>nul
            if not errorlevel 1 set "PYTHON_EXE=%%~D\python.exe"
        )
    )
)

if not defined PYTHON_EXE (
    echo [ERRORE] Python 3.10+ nativo per Windows non trovato.
    echo Scarica Python da https://www.python.org/downloads/ e riprova.
    goto :fail
)

echo Interprete Python rilevato: "%PYTHON_EXE%"
echo.

REM Ricrea .venv se mancante o creata con un interprete non compatibile (es. MSYS2)
if not exist ".venv\Scripts\python.exe" (
    if exist ".venv" (
        echo [1/4] Rimozione ambiente virtuale .venv non compatibile...
        rmdir /s /q ".venv"
    )
    echo [1/4] Creazione ambiente virtuale isolato .venv...
    "%PYTHON_EXE%" -m venv .venv
    if errorlevel 1 (
        echo [ERRORE] Impossibile creare l'ambiente virtuale .venv.
        goto :fail
    )
)

set "VENV_PY=%CD%\.venv\Scripts\python.exe"

echo [2/4] Attivazione ambiente virtuale e installazione dipendenze...
call ".venv\Scripts\activate.bat"
"%VENV_PY%" -m pip install --upgrade pip >nul 2>nul
"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERRORE] Installazione delle dipendenze fallita.
    goto :fail
)

echo [3/4] Esecuzione test unitari del motore OOP...
"%VENV_PY%" -m unittest discover -s tests -v
if errorlevel 1 (
    echo [ERRORE] I test unitari non sono stati superati. Build interrotta.
    goto :fail
)

echo [4/4] Compilazione eseguibile portable single-file...
taskkill /IM PatchWise_Portable.exe /F /T >nul 2>nul
if not errorlevel 1 (
    echo Chiusa istanza precedente di PatchWise_Portable.exe...
    timeout /t 1 /nobreak >nul
)
"%VENV_PY%" build_portable.py --name PatchWise_Portable
if errorlevel 1 (
    echo [ERRORE] Compilazione eseguibile fallita.
    goto :fail
)

echo.
echo Eseguibile pronto in: dist\PatchWise_Portable.exe
echo Copialo su qualsiasi PC Windows ed eseguilo direttamente senza installazione.
if /I not "%~1"=="--no-pause" pause
exit /b 0

:fail
if /I not "%~1"=="--no-pause" pause
exit /b 1
