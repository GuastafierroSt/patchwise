# PatchWise v1.0.0 — Software & Driver Updater (Portable)

Applicazione desktop Windows (stile Apple Liquid Glass, tema chiaro/scuro) sviluppata in Python con architettura OOP a classi per:
1. **Aggiornamenti Applicazioni**: scansione locale tramite Registro di Windows (`WindowsRegistryDetector`) e Winget (`WingetDetector`), confronto online (`WingetVersionChecker`, `GitHubReleasesChecker`) e aggiornamento manuale (`WingetAppUpdater`, `DirectHttpInstaller`).
2. **Aggiornamenti Driver**: scansione hardware locale tramite Registro di Windows (`WindowsDriverRegistryDetector`) e WMI/CIM (`WindowsCimDriverDetector`), ricerca driver ufficiali firmati WHQL tramite Windows Update Agent (`WindowsUpdateDriverChecker`) e installazione manuale controllata (`WindowsUpdateDriverUpdater`).
3. **Aggiornamento esclusivamente manuale** (`AUTO_UPDATE_ALLOWED = False`): nessun interruttore o pianificazione di auto-update.
4. **Monitoraggio live e Centro Notifiche**: barra di avanzamento dedicata visibile solo durante il download, notifiche con badge campanella e toast discreto in basso a destra.
5. **Cronologia stateless di sessione** (`StatelessSessionHistoryManager`): mantiene in RAM gli aggiornamenti di app e driver della sessione attiva e salva su chiusura solo uno snapshot volatile in `%TEMP%\patchwise_last_session.json`.

## Gerarchia delle Classi
- `AppDetector (ABC)` → `WindowsRegistryDetector`, `WingetDetector`, `WindowsDriverRegistryDetector`, `WindowsCimDriverDetector`, `CompositeAppDetector`
- `VersionChecker (ABC)` → `WingetVersionChecker`, `GitHubReleasesChecker`, `WindowsUpdateDriverChecker`, `CompositeVersionChecker`
- `AppUpdater (ABC)` → `WingetAppUpdater`, `DirectHttpInstaller`, `WindowsUpdateDriverUpdater`
- `StatelessSessionHistoryManager`
- `UpdateManagerController` (Facade per App e Driver)
- `PatchWiseMainWindow (QMainWindow)` + `UpdateSectionView` + `ScanWorker` / `UpdateWorker` (`QThread`) + `LiquidGlassBackdrop` / `GlassSheetTransitionOverlay` / `NotificationsPopover`

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
