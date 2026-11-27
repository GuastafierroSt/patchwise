<div align="center">

<img src="python_app/assets/patchwise.png" alt="PatchWise Logo" width="104" height="104" />

# PatchWise

**Software & Driver Updater Portable per Windows 10/11**  
*Interfaccia Apple Liquid Glass (tema chiaro & scuro) · 100% controllo manuale · Zero installazione*

[![Latest Release](https://img.shields.io/github/v/release/GuastafierroSt/patchWise?label=Release&color=685bd9&style=for-the-badge)](https://github.com/GuastafierroSt/patchWise/releases/latest)
[![Platform](https://img.shields.io/badge/Windows-10%20%2F%2011-0ea5e9?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/GuastafierroSt/patchWise/releases/latest)
[![Python](https://img.shields.io/badge/Python-3.10%2B%20%7C%20PySide6-a451d6?style=for-the-badge&logo=python&logoColor=white)](python_app/)
[![Portable](https://img.shields.io/badge/Portable-.EXE%20Single--File-10b981?style=for-the-badge)](https://github.com/GuastafierroSt/patchWise/releases/latest/download/PatchWise.exe)

<br />

<a href="https://github.com/GuastafierroSt/patchWise/releases/latest/download/PatchWise.exe">
  <img src="https://img.shields.io/badge/%E2%AC%87%EF%B8%8F%20Scarica%20PatchWise.exe-Windows%2064--bit-685bd9?style=for-the-badge" alt="Scarica PatchWise.exe" height="40" />
</a>

</div>

---

## Panoramica

**PatchWise** è un'applicazione desktop **portable** per Windows 10 e Windows 11 pensata per individuare e aggiornare in modo rapido, trasparente e **strettamente manuale** sia le **applicazioni installate** sia i **driver hardware ufficiali WHQL**, senza installare servizi in background, senza modificare il Registro di sistema e senza eseguire mai aggiornamenti automatici non richiesti.

---

## Avvio rapido (Utenti)

1. Scarica **`PatchWise.exe`** dalla pagina delle [**Release ufficiali**](https://github.com/GuastafierroSt/patchWise/releases/latest) (oppure dal pulsante in alto).
2. Eseguilo direttamente con un doppio clic — **non richiede installazione né Python**.
3. Clicca su **Nuova Scansione** nella sezione **Aggiorna App** o **Aggiorna Driver** e scegli cosa aggiornare.

> **Nota su Windows SmartScreen:** essendo un eseguibile portable open-source non ancora firmato con certificato commerciale EV, al primo avvio Windows Defender SmartScreen potrebbe mostrare un avviso di *"PC protetto da Windows"*. Clicca su **Ulteriori informazioni → Esegui comunque** (oppure compila tu stesso l'eseguibile dai sorgenti seguendo la sezione qui sotto).

### Requisiti
- **Windows 10 (1809+) o Windows 11 (64-bit)**
- **App Installer / `winget`** (già incluso in Windows 11 e Windows 10 aggiornato) per gli aggiornamenti applicazioni
- Connessione Internet per la verifica online e il download dei pacchetti ufficiali

---

## Architettura del progetto

```text
patchWise/
├── python_app/
│   ├── main.py                     # Entry-point portable (dev + PyInstaller --onefile)
│   ├── build_portable.bat          # Script Windows 1-click: venv -> test -> .exe
│   ├── build_portable.py           # Generatore PyInstaller --onefile --windowed
│   ├── requirements.txt            # PySide6 & PyInstaller
│   ├── assets/                     # Logo PNG e icona multi-risoluzione ICO
│   ├── patchwise/
│   │   ├── models.py               # Dataclass di dominio (InstalledApp, UpdateCandidate, UpdateRecord)
│   │   ├── core/
│   │   │   ├── detectors.py        # AppDetector: Registry + Winget + Composite
│   │   │   ├── checkers.py         # VersionChecker: Winget multi-tabella + GitHub Releases
│   │   │   ├── installer.py        # AppUpdater: Winget (silent -> interactive) + Direct HTTPS
│   │   │   ├── drivers.py          # Motore Driver: Registry + CIM + WUA + UAC on-demand
│   │   │   ├── session_history.py  # Gestione cronologia stateless in RAM + temp snapshot
│   │   │   └── controller.py       # Facade UpdateManagerController (App & Driver)
│   │   └── ui/
│   │       ├── main_window.py      # Shell principale PySide6, navigazione, tema, notifiche
│   │       ├── section_view.py     # Vista riusabile App/Driver con overlay 60fps
│   │       ├── widgets.py          # Componenti Liquid Glass, toast, popover, dialog diagnostico
│   │       ├── theme.py            # Token e QSS Apple Liquid Glass (Light & Dark)
│   │       ├── icons.py            # Icone vettoriali HiDPI QPainter
│   │       └── workers.py          # QThread asincroni per scansioni e aggiornamenti
│   └── tests/
│       └── test_patchwise_core.py  # Suite completa di test unitari & UI offscreen
└── .github/workflows/
    └── release-windows.yml         # Build & pubblicazione automatica su GitHub Releases
```

---

## Sviluppo e compilazione

### Esecuzione da sorgente (Windows, Python 3.10+)
```powershell
cd python_app
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

### Esecuzione della suite di test
```powershell
cd python_app
$env:QT_QPA_PLATFORM = "offscreen"
python -m unittest discover -s tests -v
```

### Compilazione eseguibile Portable (`.exe`)
Fai doppio clic su **`python_app\build_portable.bat`** oppure esegui da terminale:
```powershell
cd python_app
.\build_portable.bat
```
Lo script rileva automaticamente CPython nativo Windows, prepara `.venv`, esegue tutti i test unitari e genera l'eseguibile autonomo in `python_app\dist\PatchWise.exe`.

---

## Sicurezza & Privacy

- **Zero telemetria** e nessuna raccolta dati.
- **Fonti ufficiali verificate**: pacchetti Winget con controllo integrità SHA-256, release ufficiali GitHub e driver firmati WHQL da Microsoft Windows Update.
- **Nessun servizio persistente**: alla chiusura della finestra tutti i worker vengono arrestati pulitamente.
