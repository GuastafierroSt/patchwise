# PatchWise Desktop — Python Software Updater (Portable)

Applicazione desktop Windows sviluppata in Python con architettura OOP a classi per:
1. **Scansione locale** dei programmi installati tramite Registro di Windows (`WindowsRegistryDetector`) e Windows Package Manager (`WingetDetector`).
2. **Confronto online** con le versioni più recenti disponibili (`WingetVersionChecker`, `GitHubReleasesChecker`).
3. **Aggiornamento esclusivamente manuale** (`AUTO_UPDATE_ALLOWED = False`): nessun interruttore o pianificazione di auto-update.
4. **Monitoraggio live del download e installazione** tramite barra di avanzamento intuitiva (fase, percentuale, MB, velocità, ETA, pausa/annulla).
5. **Cronologia stateless di sessione** (`StatelessSessionHistoryManager`): mantiene in RAM gli aggiornamenti della sessione attiva e salva su chiusura solo uno snapshot volatile in `%TEMP%\patchwise_last_session.json` relativo all'ultima sessione, scartando tutte le sessioni più vecchie.

## Gerarchia delle Classi
- `AppDetector (ABC)` → `WindowsRegistryDetector`, `WingetDetector`, `CompositeAppDetector`
- `VersionChecker (ABC)` → `WingetVersionChecker`, `GitHubReleasesChecker`, `CompositeVersionChecker`
- `AppUpdater (ABC)` → `WingetAppUpdater`, `DirectHttpInstaller`
- `StatelessSessionHistoryManager`
- `UpdateManagerController` (Facade)
- `PatchWiseMainWindow (QMainWindow)` + `ScanWorker` / `UpdateWorker` (`QThread`) + `ActiveDownloadBanner` / `AppUpdateCard`

## Avvio rapido in sviluppo
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Creazione dell'eseguibile Portable (`.exe`)
Su Windows è sufficiente eseguire un doppio clic su `build_portable.bat` oppure lanciare:
```bash
python build_portable.py --name PatchWise_Portable
```
Verrà generato `dist\PatchWise_Portable.exe`: un file autonomo, eseguibile su qualsiasi altro PC Windows 10/11 senza installazione e senza Python preinstallato.
