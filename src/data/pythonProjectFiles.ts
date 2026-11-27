import mainPy from '../../python_app/main.py?raw';
import requirementsTxt from '../../python_app/requirements.txt?raw';
import buildPortablePy from '../../python_app/build_portable.py?raw';
import buildPortableBat from '../../python_app/build_portable.bat?raw';
import readmeMd from '../../python_app/README.md?raw';
import pkgInitPy from '../../python_app/patchwise/__init__.py?raw';
import modelsPy from '../../python_app/patchwise/models.py?raw';
import coreInitPy from '../../python_app/patchwise/core/__init__.py?raw';
import versionUtilsPy from '../../python_app/patchwise/core/version_utils.py?raw';
import detectorsPy from '../../python_app/patchwise/core/detectors.py?raw';
import checkersPy from '../../python_app/patchwise/core/checkers.py?raw';
import installerPy from '../../python_app/patchwise/core/installer.py?raw';
import sessionHistoryPy from '../../python_app/patchwise/core/session_history.py?raw';
import controllerPy from '../../python_app/patchwise/core/controller.py?raw';
import uiInitPy from '../../python_app/patchwise/ui/__init__.py?raw';
import themePy from '../../python_app/patchwise/ui/theme.py?raw';
import workersPy from '../../python_app/patchwise/ui/workers.py?raw';
import widgetsPy from '../../python_app/patchwise/ui/widgets.py?raw';
import mainWindowPy from '../../python_app/patchwise/ui/main_window.py?raw';
import testsPy from '../../python_app/tests/test_patchwise_core.py?raw';

export interface PythonSourceFile {
  path: string;
  label: string;
  layer: 'build' | 'core' | 'ui' | 'tests';
  summary: string;
  content: string;
}

export interface ClassHierarchyNode {
  className: string;
  baseClass: string;
  role: string;
  filePath: string;
  layer: 'Rilevamento' | 'Confronto Online' | 'Installazione Manuale' | 'Stato & Facade' | 'Interfaccia Desktop';
  highlights: string[];
}

export const PYTHON_PROJECT_FILES: PythonSourceFile[] = [
  {
    path: 'build_portable.py',
    label: 'build_portable.py',
    layer: 'build',
    summary: 'Script PyInstaller --onefile --windowed per compilare PatchWise_Portable.exe senza installazione.',
    content: buildPortablePy,
  },
  {
    path: 'build_portable.bat',
    label: 'build_portable.bat',
    layer: 'build',
    summary: 'Batch Windows one-click: crea .venv, esegue unittest e compila dist\\PatchWise_Portable.exe.',
    content: buildPortableBat,
  },
  {
    path: 'main.py',
    label: 'main.py',
    layer: 'build',
    summary: 'Entry point portable (supporta sys._MEIPASS di PyInstaller) che avvia PatchWiseMainWindow.',
    content: mainPy,
  },
  {
    path: 'requirements.txt',
    label: 'requirements.txt',
    layer: 'build',
    summary: 'Dipendenze Python essenziali: PySide6 e PyInstaller.',
    content: requirementsTxt,
  },
  {
    path: 'README.md',
    label: 'README.md',
    layer: 'build',
    summary: 'Guida completa in italiano per sviluppo locale e generazione dell’eseguibile portable.',
    content: readmeMd,
  },
  {
    path: 'patchwise/__init__.py',
    label: 'patchwise/__init__.py',
    layer: 'core',
    summary: 'Metadati di pacchetto e vincolo architetturale __auto_update_allowed__ = False.',
    content: pkgInitPy,
  },
  {
    path: 'patchwise/models.py',
    label: 'patchwise/models.py',
    layer: 'core',
    summary: 'Dataclass immutabili: InstalledApp, OnlineVersionInfo, UpdateCandidate, DownloadProgress, UpdateRecord.',
    content: modelsPy,
  },
  {
    path: 'patchwise/core/__init__.py',
    label: 'patchwise/core/__init__.py',
    layer: 'core',
    summary: 'Package core del motore OOP.',
    content: coreInitPy,
  },
  {
    path: 'patchwise/core/version_utils.py',
    label: 'patchwise/core/version_utils.py',
    layer: 'core',
    summary: 'Comparatore multi-segmento per versioni software (es. 123.0.6312.86 vs 124.0.6367.60).',
    content: versionUtilsPy,
  },
  {
    path: 'patchwise/core/detectors.py',
    label: 'patchwise/core/detectors.py',
    layer: 'core',
    summary: 'Gerarchia AppDetector(ABC): WindowsRegistryDetector, WingetDetector, CompositeAppDetector.',
    content: detectorsPy,
  },
  {
    path: 'patchwise/core/checkers.py',
    label: 'patchwise/core/checkers.py',
    layer: 'core',
    summary: 'Gerarchia VersionChecker(ABC): WingetVersionChecker, GitHubReleasesChecker, CompositeVersionChecker.',
    content: checkersPy,
  },
  {
    path: 'patchwise/core/installer.py',
    label: 'patchwise/core/installer.py',
    layer: 'core',
    summary: 'Gerarchia AppUpdater(ABC): WingetAppUpdater e DirectHttpInstaller con progress bar live, SHA-256, pausa/annulla.',
    content: installerPy,
  },
  {
    path: 'patchwise/core/session_history.py',
    label: 'patchwise/core/session_history.py',
    layer: 'core',
    summary: 'StatelessSessionHistoryManager: RAM per la sessione attiva + singolo snapshot volatile in %TEMP% per l’ultima sessione.',
    content: sessionHistoryPy,
  },
  {
    path: 'patchwise/core/controller.py',
    label: 'patchwise/core/controller.py',
    layer: 'core',
    summary: 'UpdateManagerController (Facade) che orchestra scansione, confronto, aggiornamenti manuali e cronologia.',
    content: controllerPy,
  },
  {
    path: 'patchwise/ui/__init__.py',
    label: 'patchwise/ui/__init__.py',
    layer: 'ui',
    summary: 'Package interfaccia grafica PySide6.',
    content: uiInitPy,
  },
  {
    path: 'patchwise/ui/theme.py',
    label: 'patchwise/ui/theme.py',
    layer: 'ui',
    summary: 'Foglio di stile QSS Alexandria (Noto Serif, Public Sans, superfici tonali senza bordi).',
    content: themePy,
  },
  {
    path: 'patchwise/ui/workers.py',
    label: 'patchwise/ui/workers.py',
    layer: 'ui',
    summary: 'Worker asincroni QThread (ScanWorker, UpdateWorker) con segnali Qt per non bloccare la UI.',
    content: workersPy,
  },
  {
    path: 'patchwise/ui/widgets.py',
    label: 'patchwise/ui/widgets.py',
    layer: 'ui',
    summary: 'ActiveDownloadBanner, AppUpdateCard (senza toggle Auto-Update) e HistoryRowWidget.',
    content: widgetsPy,
  },
  {
    path: 'patchwise/ui/main_window.py',
    label: 'patchwise/ui/main_window.py',
    layer: 'ui',
    summary: 'PatchWiseMainWindow(QMainWindow): finestra desktop principale con chiusura stateless.',
    content: mainWindowPy,
  },
  {
    path: 'tests/test_patchwise_core.py',
    label: 'tests/test_patchwise_core.py',
    layer: 'tests',
    summary: 'Suite unittest verificata: 7 test su rilevamento, parser Winget, cronologia stateless e build portable.',
    content: testsPy,
  },
];

export const OOP_CLASS_HIERARCHY: ClassHierarchyNode[] = [
  {
    className: 'AppDetector → WindowsRegistryDetector · WingetDetector · CompositeAppDetector',
    baseClass: 'ABC (Strategy + Composite)',
    role: 'Rileva i software installati leggendo i rami Uninstall del Registro Windows (HKLM, HKCU, WOW6432) e winget list, deduplicando automaticamente per app_id.',
    filePath: 'patchwise/core/detectors.py',
    layer: 'Rilevamento',
    highlights: ['detect() -> List[InstalledApp]', 'parse_winget_list_output()', 'Deduplicazione metadati'],
  },
  {
    className: 'VersionChecker → WingetVersionChecker · GitHubReleasesChecker · CompositeVersionChecker',
    baseClass: 'ABC (Strategy + Composite)',
    role: 'Interroga i cataloghi online (winget upgrade e GitHub Releases REST API) e confronta le versioni locali tramite compare_versions().',
    filePath: 'patchwise/core/checkers.py',
    layer: 'Confronto Online',
    highlights: ['fetch_latest_versions()', 'find_updates() -> List[UpdateCandidate]', 'Classificazione CVE / Sicurezza'],
  },
  {
    className: 'AppUpdater → WingetAppUpdater · DirectHttpInstaller',
    baseClass: 'ABC + UpdateControlToken',
    role: 'Scarica e installa manualmente i pacchetti con auto-update disabilitato per architettura, streaming a chunk, controllo SHA-256 e callback live per la barra di avanzamento.',
    filePath: 'patchwise/core/installer.py',
    layer: 'Installazione Manuale',
    highlights: ['execute_update(candidate, on_progress, control)', 'Pausa / Riprendi / Annulla thread-safe', 'Pulizia file temporanei'],
  },
  {
    className: 'StatelessSessionHistoryManager & UpdateManagerController',
    baseClass: 'Facade + Stateless Session Store',
    role: 'Mantiene in RAM gli aggiornamenti della sessione corrente; alla chiusura sovrascrive un singolo snapshot volatile nella cartella temporanea di sistema per l’ultima sessione, scartando quelle precedenti.',
    filePath: 'patchwise/core/session_history.py',
    layer: 'Stato & Facade',
    highlights: ['AUTO_UPDATE_ALLOWED = False', 'finalize_session() su closeEvent', 'Nessun database permanente'],
  },
  {
    className: 'PatchWiseMainWindow · ScanWorker · UpdateWorker · ActiveDownloadBanner · AppUpdateCard',
    baseClass: 'QMainWindow · QThread · QFrame (PySide6)',
    role: 'Interfaccia desktop nativa in stile Alexandria senza interruttori Auto-Update, con thread separati per scansione e download live pronto per il packaging PyInstaller --onefile.',
    filePath: 'patchwise/ui/main_window.py',
    layer: 'Interfaccia Desktop',
    highlights: ['QThread con segnali progress_changed', 'Barra di caricamento multi-fase', 'Packaging PyInstaller --onefile'],
  },
];
