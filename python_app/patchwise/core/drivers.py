"""OOP engine for Windows hardware driver detection, update discovery, and manual updates.

Follows PatchWise's strict architectural rules:
- Zero auto-update scheduling (`AUTO_UPDATE_SUPPORTED = False`).
- Uses only native Windows Registry + Windows Update Agent (WUA) COM APIs (zero external deps).
- Fully testable via deterministic parsing methods.
"""

from __future__ import annotations

import ctypes
import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from patchwise.core.checkers import VersionChecker
from patchwise.core.detectors import AppDetector, CompositeAppDetector
from patchwise.core.installer import AppUpdater, ProgressCallback, UpdateControlToken
from patchwise.core.version_utils import is_update_available
from patchwise.models import (
    DownloadProgress,
    InstalledApp,
    OnlineVersionInfo,
    UpdateCandidate,
    UpdateCategory,
    UpdatePhase,
    UpdateRecord,
)

# Classes prioritized when categorizing hardware driver updates
_FEATURE_DRIVER_CLASSES = {
    "display",
    "media",
    "audioendpoint",
    "net",
    "bluetooth",
    "camera",
    "image",
    "biometric",
}
_SECURITY_DRIVER_CLASSES = {
    "firmware",
    "securitydevices",
    "system",
    "processor",
    "diskdrive",
    "scsiadapter",
}


class WindowsDriverRegistryDetector(AppDetector):
    """Fast, pure-winreg detector reading installed hardware drivers from Control\\Class."""

    CLASS_ROOT = r"SYSTEM\CurrentControlSet\Control\Class"

    @property
    def provider_name(self) -> str:
        return "driver-registry"

    def is_supported(self) -> bool:
        return sys.platform.startswith("win") or platform.system() == "Windows"

    def detect(self) -> List[InstalledApp]:
        if not self.is_supported():
            return []

        import winreg  # Windows-only standard library module

        discovered: Dict[str, InstalledApp] = {}
        try:
            root_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, self.CLASS_ROOT)
        except OSError:
            return []

        with root_key:
            cls_idx = 0
            while True:
                try:
                    class_guid = winreg.EnumKey(root_key, cls_idx)
                    cls_idx += 1
                except OSError:
                    break

                try:
                    class_key = winreg.OpenKey(root_key, class_guid)
                except OSError:
                    continue

                with class_key:
                    class_name = self._query_str(winreg, class_key, "Class") or "Hardware"
                    sub_idx = 0
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(class_key, sub_idx)
                            sub_idx += 1
                        except OSError:
                            break
                        if not subkey_name.isdigit():
                            continue

                        driver = self._read_driver_subkey(winreg, class_key, subkey_name, class_name)
                        if driver and driver.app_id not in discovered:
                            discovered[driver.app_id] = driver

        return sorted(discovered.values(), key=lambda item: item.name.lower())

    def _read_driver_subkey(
        self, winreg, class_key, subkey_name: str, class_name: str
    ) -> Optional[InstalledApp]:
        try:
            with winreg.OpenKey(class_key, subkey_name) as key:
                desc = self._query_str(winreg, key, "DriverDesc").strip()
                version = self._query_str(winreg, key, "DriverVersion").strip()
                if not desc or not version:
                    return None
                provider = self._query_str(winreg, key, "ProviderName").strip() or "Microsoft"
                hw_id = self._query_str(winreg, key, "MatchingDeviceId").strip()
                inf_path = self._query_str(winreg, key, "InfPath").strip()

                return InstalledApp(
                    app_id=f"drv-{self._slugify(desc)}",
                    name=desc,
                    publisher=provider,
                    installed_version=version,
                    source=self.provider_name,
                    install_location=inf_path,
                    item_type="driver",
                    device_class=class_name,
                    hardware_id=hw_id,
                )
        except OSError:
            return None

    @staticmethod
    def _query_str(winreg, key, value_name: str) -> str:
        try:
            value, _ = winreg.QueryValueEx(key, value_name)
            return str(value) if value is not None else ""
        except OSError:
            return ""


class WindowsCimDriverDetector(AppDetector):
    """Enriches installed drivers via Win32_PnPSignedDriver when WMI/CIM is available."""

    _PS_QUERY = (
        "$items = Get-CimInstance Win32_PnPSignedDriver -ErrorAction Stop | "
        "Where-Object { $_.DeviceName -and $_.DriverVersion } | "
        "Select-Object DeviceName, Manufacturer, DriverVersion, DeviceClass, HardWareID, InfName; "
        "@($items) | ConvertTo-Json -Compress -Depth 2"
    )

    @property
    def provider_name(self) -> str:
        return "driver-cim"

    def is_supported(self) -> bool:
        return sys.platform.startswith("win") or platform.system() == "Windows"

    def detect(self) -> List[InstalledApp]:
        if not self.is_supported():
            return []

        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    self._PS_QUERY,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=20,
                creationflags=creation_flags,
            )
        except (FileNotFoundError, subprocess.SubprocessError):
            return []

        if result.returncode != 0 or not result.stdout.strip():
            return []
        return self.parse_cim_json(result.stdout)

    def parse_cim_json(self, stdout: str) -> List[InstalledApp]:
        try:
            raw = json.loads(stdout.strip())
        except json.JSONDecodeError:
            return []

        rows = raw if isinstance(raw, list) else [raw] if isinstance(raw, dict) else []
        seen: Dict[str, InstalledApp] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = str(row.get("DeviceName") or "").strip()
            version = str(row.get("DriverVersion") or "").strip()
            if not name or not version:
                continue
            manufacturer = str(row.get("Manufacturer") or "").strip() or "Microsoft"
            device_class = str(row.get("DeviceClass") or "").strip() or "Hardware"
            hw_id = str(row.get("HardWareID") or "").strip()
            inf_name = str(row.get("InfName") or "").strip()

            app_id = f"drv-{self._slugify(name)}"
            if app_id not in seen:
                seen[app_id] = InstalledApp(
                    app_id=app_id,
                    name=name,
                    publisher=manufacturer,
                    installed_version=version,
                    source=self.provider_name,
                    install_location=inf_name,
                    item_type="driver",
                    device_class=device_class,
                    hardware_id=hw_id,
                )
        return sorted(seen.values(), key=lambda item: item.name.lower())


class WindowsUpdateDriverChecker(VersionChecker):
    """Queries official Microsoft Windows Update Agent (WUA) for pending WHQL driver updates."""

    _VERSION_RE = re.compile(r"\b(\d+\.\d+(?:\.\d+){1,3})\b")
    _PS_SEARCH = r"""
$ErrorActionPreference = 'Stop'
$session = New-Object -ComObject Microsoft.Update.Session
$searcher = $session.CreateUpdateSearcher()
$result = $searcher.Search("IsInstalled=0 and Type='Driver' and IsHidden=0")
$list = @()
foreach ($u in $result.Updates) {
    $dateStr = ""
    try {
        if ($u.DriverVerDate) { $dateStr = ([datetime]$u.DriverVerDate).ToString("yyyy.MM.dd") }
    } catch {}
    $list += [PSCustomObject]@{
        UpdateID = [string]$u.Identity.UpdateID
        Title = [string]$u.Title
        Description = [string]$u.Description
        DriverManufacturer = [string]$u.DriverManufacturer
        DriverModel = [string]$u.DriverModel
        DriverClass = [string]$u.DriverClass
        DriverHardwareID = [string]$u.DriverHardwareID
        DriverVerDate = $dateStr
        MaxDownloadSize = [double]$u.MaxDownloadSize
        MsrcSeverity = [string]$u.MsrcSeverity
    }
}
@($list) | ConvertTo-Json -Compress -Depth 3
"""

    @property
    def provider_name(self) -> str:
        return "windows-update-driver"

    def fetch_latest_versions(
        self, installed_apps: Sequence[InstalledApp]
    ) -> Dict[str, OnlineVersionInfo]:
        return {c.app_id: c.online for c in self.find_updates(installed_apps)}

    def find_updates(self, installed_apps: Sequence[InstalledApp]) -> List[UpdateCandidate]:
        if not sys.platform.startswith("win"):
            return []

        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    self._PS_SEARCH,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
                creationflags=creation_flags,
            )
        except (FileNotFoundError, subprocess.SubprocessError):
            return []

        if result.returncode != 0 or not result.stdout.strip():
            return []
        return self.parse_wua_driver_updates(result.stdout, installed_apps)

    def parse_wua_driver_updates(
        self, stdout: str, installed_drivers: Sequence[InstalledApp]
    ) -> List[UpdateCandidate]:
        """Parse Windows Update Agent JSON into driver UpdateCandidate objects."""
        text = stdout.strip()
        if not text:
            return []
        try:
            raw = json.loads(text)
        except json.JSONDecodeError:
            return []

        rows = raw if isinstance(raw, list) else [raw] if isinstance(raw, dict) else []
        by_hw = {
            drv.hardware_id.lower(): drv for drv in installed_drivers if drv.hardware_id
        }
        by_name = {drv.name.lower(): drv for drv in installed_drivers}

        candidates: List[UpdateCandidate] = []
        seen_ids: set[str] = set()

        for row in rows:
            if not isinstance(row, dict):
                continue
            update_id = str(row.get("UpdateID") or "").strip()
            title = str(row.get("Title") or "").strip()
            if not update_id or not title:
                continue

            model = str(row.get("DriverModel") or "").strip() or title
            manufacturer = str(row.get("DriverManufacturer") or "").strip() or "Hardware Vendor"
            dev_class = str(row.get("DriverClass") or "").strip() or "Driver"
            hw_id = str(row.get("DriverHardwareID") or "").strip()
            ver_date = str(row.get("DriverVerDate") or "").strip()
            desc = str(row.get("Description") or "").strip()
            severity = str(row.get("MsrcSeverity") or "").strip().lower()
            try:
                size_mb = round(float(row.get("MaxDownloadSize") or 0) / (1024 * 1024), 2)
            except (TypeError, ValueError):
                size_mb = 0.0

            ver_match = self._VERSION_RE.search(title)
            latest_version = ver_match.group(1) if ver_match else (ver_date or "Nuova release")

            matched = self._match_local_driver(hw_id, model, title, by_hw, by_name, installed_drivers)
            if matched is not None:
                # Skip only if both versions are numeric and installed >= latest
                if ver_match and not is_update_available(matched.installed_version, latest_version):
                    continue
                driver_app = InstalledApp(
                    app_id=matched.app_id,
                    name=matched.name,
                    publisher=matched.publisher or manufacturer,
                    installed_version=matched.installed_version,
                    source=matched.source,
                    install_location=matched.install_location,
                    item_type="driver",
                    device_class=matched.device_class or dev_class,
                    hardware_id=matched.hardware_id or hw_id,
                    driver_update_id=update_id,
                )
            else:
                slug = re.sub(r"[^a-z0-9]+", "-", model.lower()).strip("-") or update_id[:8]
                driver_app = InstalledApp(
                    app_id=f"drv-{slug}",
                    name=model,
                    publisher=manufacturer,
                    installed_version="Installata",
                    source=self.provider_name,
                    item_type="driver",
                    device_class=dev_class,
                    hardware_id=hw_id,
                    driver_update_id=update_id,
                )

            if driver_app.app_id in seen_ids:
                continue
            seen_ids.add(driver_app.app_id)

            lower_class = dev_class.lower()
            if severity in ("critical", "important") or lower_class in _SECURITY_DRIVER_CLASSES:
                category = UpdateCategory.SECURITY
            elif lower_class in _FEATURE_DRIVER_CLASSES:
                category = UpdateCategory.FEATURES
            else:
                category = UpdateCategory.PATCH

            notes = desc[:220] if desc else (
                f"Driver ufficiale firmato WHQL ({dev_class} · {manufacturer}) tramite Windows Update."
            )
            online = OnlineVersionInfo(
                app_id=driver_app.app_id,
                latest_version=latest_version,
                size_mb=size_mb,
                category=category,
                release_notes=notes,
                provider=self.provider_name,
                published_at=ver_date or None,
            )
            candidates.append(UpdateCandidate(app=driver_app, online=online))

        return candidates

    @staticmethod
    def _match_local_driver(
        hw_id: str,
        model: str,
        title: str,
        by_hw: Dict[str, InstalledApp],
        by_name: Dict[str, InstalledApp],
        installed: Sequence[InstalledApp],
    ) -> Optional[InstalledApp]:
        if hw_id and hw_id.lower() in by_hw:
            return by_hw[hw_id.lower()]
        if model and model.lower() in by_name:
            return by_name[model.lower()]
        lower_title = title.lower()
        for drv in installed:
            if drv.hardware_id and hw_id and (
                drv.hardware_id.lower() in hw_id.lower() or hw_id.lower() in drv.hardware_id.lower()
            ):
                return drv
            if len(drv.name) >= 6 and drv.name.lower() in lower_title:
                return drv
        return None


def is_process_elevated() -> bool:
    """Return True if the current process holds Windows Administrator privileges."""
    if not sys.platform.startswith("win"):
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return False


class WindowsUpdateDriverUpdater(AppUpdater):
    """Downloads and installs a selected WHQL driver manually via Windows Update Agent COM API.

    When PatchWise runs as a standard user, automatically requests on-demand Windows UAC
    elevation (`ShellExecuteExW` with `runas`) solely for the driver installation helper
    so `IUpdateDownloader.Download()` and `IUpdateInstaller.Install()` succeed without
    forcing the whole app to start elevated.
    """

    # WUA OperationResultCode labels
    _WUA_RESULT_LABELS: Dict[int, str] = {
        0: "orcNotStarted (non avviato)",
        1: "orcInProgress (in corso)",
        2: "orcSucceeded (completato)",
        3: "orcSucceededWithErrors (completato con avvisi)",
        4: "orcFailed (operazione fallita)",
        5: "orcAborted (operazione interrotta)",
    }

    # Known Windows Update Agent & PnP HRESULT catalog: hex -> (title, cause, advice)
    _WUA_HRESULT_CATALOG: Dict[str, Tuple[str, str, str]] = {
        "0X80070005": (
            "E_ACCESSDENIED — Permessi di amministratore insufficienti",
            "Windows Update Agent ha negato il download o l'installazione del driver perché il processo non dispone di privilegi elevati o i permessi su SoftwareDistribution sono bloccati.",
            "• Accetta la richiesta UAC (Amministratore) quando PatchWise aggiorna un driver.\n"
            "• In alternativa avvia PatchWise con tasto destro → 'Esegui come amministratore'.\n"
            "• Se il problema persiste, verifica che un antivirus non stia bloccando C:\\Windows\\SoftwareDistribution.",
        ),
        "0X80240022": (
            "WU_E_ALL_UPDATES_FAILED — Operazione Windows Update non riuscita",
            "Windows Update non è riuscito a completare il download/installazione del pacchetto driver (spesso per mancanza di privilegi elevati, cache Windows Update incoerente o blocco da antivirus/criteri).",
            "• Accetta la richiesta UAC o esegui PatchWise come Amministratore.\n"
            "• Apri Impostazioni → Windows Update → Opzioni avanzate → Aggiornamenti facoltativi per verificare se Windows segnala dettagli aggiuntivi.\n"
            "• Se il driver è di un produttore con software dedicato (es. Razer Synapse, NVIDIA, Intel), prova ad aggiornarlo dal relativo gestore ufficiale.",
        ),
        "0X80240044": (
            "WU_E_PER_MACHINE_UPDATE_ACCESS_DENIED — Accesso negato da criteri o privilegi",
            "L'aggiornamento del driver di sistema è bloccato dai privilegi dell'account corrente o dai criteri di Windows Update.",
            "• Esegui l'aggiornamento con privilegi di Amministratore (UAC).\n"
            "• Verifica in Impostazioni → Privacy e sicurezza / Windows Update che gli aggiornamenti driver non siano bloccati da policy locali.",
        ),
        "0X80246007": (
            "WU_E_DM_NOTDOWNLOADED — Download Windows Update/BITS non completato",
            "Il gestore download di Windows Update (BITS) non ha completato il trasferimento o la verifica del pacchetto driver.",
            "• Controlla la connessione Internet e riprova tra qualche istante.\n"
            "• Verifica che il servizio 'Servizio trasferimento intelligente in background (BITS)' sia avviato.\n"
            "• Se persiste, esegui lo strumento di risoluzione problemi di Windows Update.",
        ),
        "0X80070103": (
            "ERROR_NO_MORE_ITEMS — Driver già installato o meno adatto",
            "Sul PC è già installata una versione identica, più recente o più specifica per questa periferica rispetto al pacchetto offerto da Windows Update.",
            "• Nella maggior parte dei casi questo avviso è innocuo: il driver attuale è già corretto.\n"
            "• Puoi ignorare questo aggiornamento facoltativo oppure aggiornare direttamente dal software del produttore.",
        ),
        "0X800F020B": (
            "ERROR_NO_SUCH_DEVINST — Dispositivo hardware non connesso",
            "La periferica associata al driver non risulta attualmente collegata o attiva (molto comune per mouse, cuffie, webcam o monitor USB scollegati).",
            "• Collega e accendi la periferica hardware, poi clicca nuovamente su 'Aggiorna'.",
        ),
        "0X8024002E": (
            "WU_E_WU_DISABLED — Servizio Windows Update disabilitato da criteri",
            "L'accesso ai server Microsoft Update è disabilitato da una policy di gruppo o da un'impostazione di registro.",
            "• Controlla in services.msc che il servizio 'Windows Update (wuauserv)' sia attivo.\n"
            "• Verifica eventuali criteri locali di Windows Update.",
        ),
        "0X8024402C": (
            "WU_E_PT_WINHTTP_NAME_NOT_RESOLVED — Errore rete / DNS",
            "Windows Update Agent non è riuscito a risolvere l'indirizzo dei server Microsoft Update.",
            "• Controlla la connessione di rete, VPN o proxy e riprova.",
        ),
        "0X80248007": (
            "WU_E_DS_NODATA — Cache locale Windows Update incoerente",
            "Il database locale di Windows Update (SoftwareDistribution) non contiene i metadati attesi per questo driver.",
            "• Riavvia il PC o esegui una nuova scansione in Windows Update e poi riprova.",
        ),
        "0X80240016": (
            "WU_E_INSTALL_NOT_ALLOWED — Altra installazione Windows Update già attiva",
            "Windows Update sta già installando un altro aggiornamento di sistema in background.",
            "• Attendi il termine degli aggiornamenti in corso in Windows Update e riprova.",
        ),
        "0X80240020": (
            "WU_E_NO_USERTOKEN — Sessione utente non autorizzata per WUA",
            "Windows Update Agent richiede una sessione utente interattiva elevata.",
            "• Esegui PatchWise come Amministratore nella sessione desktop corrente.",
        ),
        "0X80070422": (
            "ERROR_SERVICE_DISABLED — Servizio Windows Update disabilitato",
            "Il servizio di sistema Windows Update (wuauserv) risulta disabilitato.",
            "• Apri 'Servizi' (services.msc), imposta 'Windows Update' su Manuale o Automatico e avvialo.",
        ),
    }

    _PS_INSTALL_TEMPLATE = r"""
param(
    [string]$UpdateId = '',
    [string]$LogFile = '',
    [string]$ExitFile = ''
)
$ErrorActionPreference = 'Stop'

function Emit([string]$Text) {
    if ($LogFile) {
        [System.IO.File]::AppendAllText($LogFile, ($Text + "`r`n"), [System.Text.Encoding]::UTF8)
    } else {
        Write-Output $Text
    }
}

function Format-Hr($hr) {
    try {
        return ('0x{0:X8}' -f ([int32]$hr))
    } catch {
        try {
            return ('0x{0:X8}' -f ([uint32]$hr))
        } catch {
            return [string]$hr
        }
    }
}

function Finish([int]$Code) {
    if ($ExitFile) {
        [System.IO.File]::WriteAllText($ExitFile, [string]$Code, [System.Text.Encoding]::ASCII)
    }
    exit $Code
}

$isAdmin = $false
try {
    $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    $isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
} catch {}
Emit ("META:elevated=" + $isAdmin)
Emit ("META:update_id=" + $UpdateId)

try {
    Emit "PROGRESS:10:downloading:Ricerca pacchetto driver Windows Update..."
    $session = New-Object -ComObject Microsoft.Update.Session
    $searcher = $session.CreateUpdateSearcher()
    $res = $searcher.Search("IsInstalled=0 and Type='Driver'")
    $coll = New-Object -ComObject Microsoft.Update.UpdateColl
    $target = $null
    foreach ($u in $res.Updates) {
        if ([string]$u.Identity.UpdateID -eq $UpdateId) {
            $target = $u
            Emit ("META:title=" + [string]$u.Title)
            Emit ("META:driver_class=" + [string]$u.DriverClass)
            Emit ("META:hardware_id=" + [string]$u.DriverHardwareID)
            Emit ("META:is_downloaded=" + [string]$u.IsDownloaded)
            if (-not $u.EulaAccepted) { $u.AcceptEula() }
            [void]$coll.Add($u)
            break
        }
    }
    if ($coll.Count -eq 0 -or $null -eq $target) {
        Emit "META:phase=search"
        Emit "ERROR:Pacchetto driver non trovato nel catalogo Windows Update (potrebbe essere già stato installato o rimosso)."
        Finish 2
    }

    if (-not $target.IsDownloaded) {
        Emit "PROGRESS:28:downloading:Download pacchetto driver firmato WHQL..."
        $downloader = $session.CreateUpdateDownloader()
        try { $downloader.Priority = 3 } catch {}
        $downloader.Updates = $coll
        $dlRes = $downloader.Download()
        $dlHr = Format-Hr $dlRes.HResult
        $uCode = ""
        $uHr = ""
        try {
            $uRes = $dlRes.GetUpdateResult(0)
            $uCode = [string]$uRes.ResultCode
            $uHr = Format-Hr $uRes.HResult
        } catch {}
        Emit ("META:phase=download")
        Emit ("META:result_code=" + [string]$dlRes.ResultCode)
        Emit ("META:hresult=" + $dlHr)
        if ($uCode) { Emit ("META:update_result_code=" + $uCode) }
        if ($uHr) { Emit ("META:update_hresult=" + $uHr) }
        if ($dlRes.ResultCode -ne 2 -and $dlRes.ResultCode -ne 3) {
            $bestHr = if ($uHr -and $uHr -ne '0x00000000') { $uHr } else { $dlHr }
            Emit ("ERROR:Download driver fallito (codice WUA " + $dlRes.ResultCode + ", HResult " + $bestHr + ").")
            Finish 3
        }
    } else {
        Emit "PROGRESS:76:downloading:Pacchetto già presente nella cache Windows Update..."
    }

    Emit "PROGRESS:82:verifying:Verifica firma digitale WHQL del driver..."
    Emit "PROGRESS:90:installing:Installazione driver di sistema in corso..."
    $installer = $session.CreateUpdateInstaller()
    $installer.Updates = $coll
    $instRes = $installer.Install()
    $instHr = Format-Hr $instRes.HResult
    $iuCode = ""
    $iuHr = ""
    try {
        $iuRes = $instRes.GetUpdateResult(0)
        $iuCode = [string]$iuRes.ResultCode
        $iuHr = Format-Hr $iuRes.HResult
    } catch {}
    Emit ("META:phase=install")
    Emit ("META:result_code=" + [string]$instRes.ResultCode)
    Emit ("META:hresult=" + $instHr)
    if ($iuCode) { Emit ("META:update_result_code=" + $iuCode) }
    if ($iuHr) { Emit ("META:update_hresult=" + $iuHr) }

    if ($instRes.ResultCode -eq 2 -or $instRes.ResultCode -eq 3) {
        if ($instRes.RebootRequired) {
            Emit "DONE_REBOOT"
        } else {
            Emit "DONE"
        }
        Finish 0
    }
    $bestInstHr = if ($iuHr -and $iuHr -ne '0x00000000') { $iuHr } else { $instHr }
    Emit ("ERROR:Installazione driver fallita (codice WUA " + $instRes.ResultCode + ", HResult " + $bestInstHr + ").")
    Finish 4
} catch {
    $exHr = Format-Hr $_.Exception.HResult
    Emit ("META:exception_hresult=" + $exHr)
    Emit ("ERROR:" + $_.Exception.Message)
    Finish 5
}
"""

    def __init__(self, use_uac_elevation: bool = True) -> None:
        self._use_uac_elevation = use_uac_elevation

    def can_handle(self, candidate: UpdateCandidate) -> bool:
        return bool(
            candidate.app.driver_update_id
            or candidate.app.item_type == "driver"
            and candidate.online.provider == "windows-update-driver"
        )

    @classmethod
    def decode_wua_failure(
        cls,
        candidate: UpdateCandidate,
        meta: Dict[str, str],
        error_lines: Sequence[str],
        returncode: int,
    ) -> Tuple[str, str]:
        """Return `(short_summary, rich_details)` explaining a Windows Update driver error."""
        phase_raw = meta.get("phase", "").lower()
        phase_it = (
            "Download driver"
            if phase_raw == "download"
            else "Installazione driver"
            if phase_raw == "install"
            else "Aggiornamento driver"
        )
        result_code_str = meta.get("update_result_code") or meta.get("result_code") or ""
        try:
            result_code_int = int(result_code_str)
            result_code_desc = cls._WUA_RESULT_LABELS.get(
                result_code_int, f"codice {result_code_int}"
            )
        except ValueError:
            result_code_desc = result_code_str or "n/d"

        # Pick the most specific non-zero HRESULT
        hr_candidates = [
            meta.get("update_hresult", ""),
            meta.get("hresult", ""),
            meta.get("exception_hresult", ""),
        ]
        raw_err = " ".join(error_lines).strip()
        if not any(hr_candidates):
            found_hr = re.search(r"0x[0-9a-fA-F]{8}", raw_err)
            if found_hr:
                hr_candidates.append(found_hr.group(0))

        best_hr = ""
        for hr in hr_candidates:
            cleaned = hr.strip()
            if not cleaned:
                continue
            if cleaned.lower().startswith("0x"):
                if cleaned.upper() != "0X00000000":
                    best_hr = "0x" + cleaned[2:].upper()
                    break
            else:
                try:
                    num = int(cleaned) & 0xFFFFFFFF
                    if num != 0:
                        best_hr = f"0x{num:08X}"
                        break
                except ValueError:
                    best_hr = cleaned
                    break

        # Detect Access Denied even from plain text when HResult wasn't parsed
        if not best_hr and any(
            tok in raw_err.lower() for tok in ("0x80070005", "access is denied", "accesso negato")
        ):
            best_hr = "0x80070005"

        elevated_str = meta.get("elevated", "")
        not_elevated = elevated_str.lower() == "false"

        catalog_entry = cls._WUA_HRESULT_CATALOG.get(best_hr.upper()) if best_hr else None
        if catalog_entry is not None:
            hr_title, cause, advice = catalog_entry
            if best_hr.upper() == "0X80070005":
                summary = (
                    f"{phase_it} fallito ({best_hr}): privilegi di amministratore richiesti."
                )
            else:
                code_part = f"WUA {result_code_str} · {best_hr}" if result_code_str else best_hr
                summary = f"{phase_it} fallito ({code_part}): {hr_title.split('—')[-1].strip()}."
        elif result_code_str == "4":
            if not_elevated:
                hr_title = "Privilegi di amministratore non presenti"
                cause = (
                    "Windows Update Agent ha restituito codice 4 (orcFailed) mentre PatchWise "
                    "non disponeva di privilegi di Amministratore. La ricerca dei driver funziona "
                    "come utente standard, ma il download e l'installazione richiedono l'elevazione UAC."
                )
                advice = (
                    "• Accetta la richiesta UAC (Amministratore) quando aggiorni un driver.\n"
                    "• In alternativa chiudi PatchWise e riavvialo con tasto destro → 'Esegui come amministratore'."
                )
                summary = (
                    f"{phase_it} fallito (WUA 4): privilegi di amministratore richiesti."
                )
            else:
                hr_title = f"WUA ResultCode 4 ({best_hr or 'HResult non specificato'})"
                cause = (
                    "Windows Update Agent ha segnalato errore generico (orcFailed) durante "
                    "il trasferimento o l'applicazione del pacchetto driver."
                )
                advice = (
                    "• Verifica in Impostazioni → Windows Update → Opzioni avanzate → Aggiornamenti facoltativi.\n"
                    "• Controlla che la periferica sia collegata e che il servizio Windows Update / BITS sia attivo.\n"
                    "• Per driver di periferiche con suite dedicata (es. Razer, Logitech, NVIDIA), aggiorna dal software ufficiale."
                )
                summary = (
                    f"{phase_it} fallito (codice WUA 4"
                    + (f", {best_hr}" if best_hr else "")
                    + ")."
                )
        elif raw_err:
            hr_title = best_hr or f"Codice uscita {returncode}"
            cause = raw_err
            advice = (
                "• Verifica i dettagli tecnici qui sotto e riprova con privilegi di Amministratore.\n"
                "• Controlla Windows Update nelle Impostazioni di sistema."
            )
            summary = raw_err[:200]
        else:
            hr_title = f"Codice uscita {returncode}"
            cause = f"Il processo di aggiornamento driver è terminato con codice {returncode}."
            advice = "• Riprova eseguendo PatchWise come Amministratore."
            summary = f"Windows Update terminato con codice {returncode}."

        detail_lines = [
            f"Driver: {candidate.name} ({candidate.app.publisher})",
            f"Versione: {candidate.app.installed_version} → {candidate.online.latest_version}",
            f"Classe dispositivo: {meta.get('driver_class') or candidate.app.device_class or 'n/d'}",
            f"Hardware ID: {meta.get('hardware_id') or candidate.app.hardware_id or 'n/d'}",
            f"Update ID (WUA): {meta.get('update_id') or candidate.app.driver_update_id or 'n/d'}",
            f"Privilegi Amministratore: {'Sì' if elevated_str.lower() == 'true' else 'No' if not_elevated else 'n/d'}",
            "",
            "CODICI TECNICI",
            f"Fase: {phase_it}",
            f"Esito WUA (ResultCode): {result_code_desc}",
            f"HRESULT specifico: {best_hr or 'n/d'}",
            f"HRESULT aggregato: {meta.get('hresult') or 'n/d'}",
            f"Codice processo: {returncode}",
            "",
            "CAUSA PROBABILE",
            f"{hr_title}: {cause}",
            "",
            "SOLUZIONI CONSIGLIATE",
            advice,
        ]
        if error_lines:
            detail_lines.extend(["", "LOG DIAGNOSTICO WINDOWS UPDATE", *error_lines[-10:]])

        return summary, "\n".join(detail_lines)

    def _build_ps_script(
        self, update_id: str, log_file: str = "", exit_file: str = ""
    ) -> str:
        safe_id = update_id.replace("'", "''")
        safe_log = log_file.replace("'", "''")
        safe_exit = exit_file.replace("'", "''")
        body = self._PS_INSTALL_TEMPLATE.split("$ErrorActionPreference = 'Stop'", 1)[-1]
        return (
            f"$UpdateId = '{safe_id}'\n"
            f"$LogFile = '{safe_log}'\n"
            f"$ExitFile = '{safe_exit}'\n"
            "$ErrorActionPreference = 'Stop'"
            f"{body}"
        )

    def _process_output_line(
        self,
        raw_line: str,
        candidate: UpdateCandidate,
        on_progress: ProgressCallback,
        state: Dict[str, object],
        meta: Dict[str, str],
        error_lines: List[str],
    ) -> None:
        line = raw_line.strip()
        if not line:
            return
        if line.startswith("META:"):
            kv = line[5:]
            if "=" in kv:
                k, v = kv.split("=", 1)
                meta[k.strip().lower()] = v.strip()
        elif line.startswith("PROGRESS:"):
            parts = line.split(":", 3)
            if len(parts) == 4:
                try:
                    pct = float(parts[1])
                except ValueError:
                    pct = float(state["last_percent"])
                phase_name = parts[2].lower()
                msg = parts[3]
                state["last_percent"] = max(float(state["last_percent"]), pct)
                phase = {
                    "downloading": UpdatePhase.DOWNLOADING,
                    "verifying": UpdatePhase.VERIFYING,
                    "installing": UpdatePhase.INSTALLING,
                }.get(phase_name, UpdatePhase.DOWNLOADING)
                on_progress(
                    DownloadProgress(
                        app_id=candidate.app_id,
                        app_name=candidate.name,
                        phase=phase,
                        percent=float(state["last_percent"]),
                        downloaded_mb=round(
                            candidate.online.size_mb * (float(state["last_percent"]) / 100.0), 2
                        ),
                        total_mb=candidate.online.size_mb,
                        message=msg,
                    )
                )
        elif line == "DONE_REBOOT":
            state["reboot_required"] = True
        elif line == "DONE":
            pass
        elif line.startswith("ERROR:"):
            error_lines.append(line[6:].strip())
        else:
            error_lines.append(line)

    def _execute_elevated_uac(
        self,
        candidate: UpdateCandidate,
        update_id: str,
        on_progress: ProgressCallback,
        control: UpdateControlToken,
        state: Dict[str, object],
        meta: Dict[str, str],
        error_lines: List[str],
    ) -> Tuple[Optional[int], bool, Optional[str]]:
        """Launch the driver update PowerShell helper elevated via Windows UAC (`runas`).

        Returns `(returncode, was_cancelled, uac_or_spawn_error)`.
        """
        from ctypes import wintypes

        class _SHELLEXECUTEINFOW(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("fMask", wintypes.ULONG),
                ("hwnd", wintypes.HWND),
                ("lpVerb", wintypes.LPCWSTR),
                ("lpFile", wintypes.LPCWSTR),
                ("lpParameters", wintypes.LPCWSTR),
                ("lpDirectory", wintypes.LPCWSTR),
                ("nShow", ctypes.c_int),
                ("hInstApp", wintypes.HINSTANCE),
                ("lpIDList", ctypes.c_void_p),
                ("lpClass", wintypes.LPCWSTR),
                ("hkeyClass", wintypes.HKEY),
                ("dwHotKey", wintypes.DWORD),
                ("hIconOrMonitor", wintypes.HANDLE),
                ("hProcess", wintypes.HANDLE),
            ]

        SEE_MASK_NOCLOSEPROCESS = 0x00000040
        SW_HIDE = 0
        WAIT_TIMEOUT = 0x00000102
        ERROR_CANCELLED = 1223

        # IMPORTANT: Do NOT use tempfile.mkdtemp() here on Windows Python 3.13+.
        # mkdtemp() applies a 0o700 DACL (CREATOR OWNER + Administrators only), so files
        # created by the UAC-elevated Admin process become unreadable (Errno 13) to the
        # non-elevated user process. mkdir() under %TEMP% preserves inherited user ACLs.
        tmp_dir = Path(tempfile.gettempdir()) / f"patchwise_drv_{uuid.uuid4().hex[:10]}"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        ps1_path = tmp_dir / "update_driver.ps1"
        log_path = tmp_dir / "progress.log"
        exit_path = tmp_dir / "exit.code"

        try:
            # Pre-create log & exit files owned by the current user before launching UAC
            log_path.write_text("", encoding="utf-8")
            exit_path.write_text("", encoding="ascii")

            script = self._build_ps_script(
                update_id=update_id,
                log_file=str(log_path),
                exit_file=str(exit_path),
            )
            ps1_path.write_text(script, encoding="utf-8-sig")

            on_progress(
                DownloadProgress(
                    app_id=candidate.app_id,
                    app_name=candidate.name,
                    phase=UpdatePhase.DOWNLOADING,
                    percent=6.0,
                    total_mb=candidate.online.size_mb,
                    message="Richiesta autorizzazione Amministratore (UAC) per il driver...",
                )
            )

            params = (
                f'-NoProfile -NonInteractive -ExecutionPolicy Bypass '
                f'-WindowStyle Hidden -File "{ps1_path}"'
            )
            sei = _SHELLEXECUTEINFOW()
            sei.cbSize = ctypes.sizeof(_SHELLEXECUTEINFOW)
            sei.fMask = SEE_MASK_NOCLOSEPROCESS
            sei.lpVerb = "runas"
            sei.lpFile = "powershell.exe"
            sei.lpParameters = params
            sei.nShow = SW_HIDE

            shell32 = ctypes.WinDLL("shell32", use_last_error=True)
            shell32.ShellExecuteExW.argtypes = [ctypes.POINTER(_SHELLEXECUTEINFOW)]
            shell32.ShellExecuteExW.restype = wintypes.BOOL

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            kernel32.WaitForSingleObject.restype = wintypes.DWORD
            kernel32.GetExitCodeProcess.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(wintypes.DWORD),
            ]
            kernel32.GetExitCodeProcess.restype = wintypes.BOOL
            kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
            kernel32.TerminateProcess.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL

            ok = shell32.ShellExecuteExW(ctypes.byref(sei))
            if not ok:
                err_code = ctypes.get_last_error()
                if err_code == ERROR_CANCELLED:
                    return None, True, "Autorizzazione Amministratore (UAC) annullata dall'utente."
                return None, False, f"Impossibile avviare processo elevato (codice Windows {err_code})."

            h_proc = sei.hProcess
            read_offset = 0
            try:
                while True:
                    if control.is_cancelled:
                        if h_proc:
                            kernel32.TerminateProcess(h_proc, 1)
                        return None, True, None

                    if log_path.exists():
                        try:
                            with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
                                fh.seek(read_offset)
                                chunk = fh.read()
                                read_offset = fh.tell()
                            for ln in chunk.splitlines():
                                self._process_output_line(
                                    ln, candidate, on_progress, state, meta, error_lines
                                )
                        except OSError:
                            pass

                    if not h_proc:
                        break
                    wait_res = kernel32.WaitForSingleObject(h_proc, 150)
                    if wait_res != WAIT_TIMEOUT:
                        break

                # Drain any final lines written just before process exit
                if log_path.exists():
                    for _ in range(3):
                        try:
                            with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
                                fh.seek(read_offset)
                                chunk = fh.read()
                                read_offset = fh.tell()
                            for ln in chunk.splitlines():
                                self._process_output_line(
                                    ln, candidate, on_progress, state, meta, error_lines
                                )
                            break
                        except OSError:
                            time.sleep(0.08)

                rc: Optional[int] = None
                if exit_path.exists():
                    for _ in range(4):
                        try:
                            raw_rc = exit_path.read_text(encoding="ascii").strip()
                            if raw_rc:
                                rc = int(raw_rc)
                            break
                        except (OSError, ValueError):
                            time.sleep(0.08)

                if rc is None and h_proc:
                    exit_code = wintypes.DWORD(1)
                    if kernel32.GetExitCodeProcess(h_proc, ctypes.byref(exit_code)):
                        rc = int(exit_code.value)

                return (rc if rc is not None else 1), False, None
            finally:
                if h_proc:
                    kernel32.CloseHandle(h_proc)
        except Exception as exc:  # noqa: BLE001
            return None, False, f"Errore durante l'esecuzione elevata del driver: {exc}"
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def execute_update(
        self,
        candidate: UpdateCandidate,
        on_progress: ProgressCallback,
        control: Optional[UpdateControlToken] = None,
    ) -> UpdateRecord:
        control = control or UpdateControlToken()
        started_at = time.monotonic()
        update_id = candidate.app.driver_update_id or ""

        if not update_id:
            err = "Identificativo pacchetto driver Windows Update mancante."
            on_progress(
                DownloadProgress(
                    app_id=candidate.app_id,
                    app_name=candidate.name,
                    phase=UpdatePhase.FAILED,
                    percent=0.0,
                    message=err,
                )
            )
            return self._build_record(candidate, "failed", started_at, err, err)

        on_progress(
            DownloadProgress(
                app_id=candidate.app_id,
                app_name=candidate.name,
                phase=UpdatePhase.DOWNLOADING,
                percent=4.0,
                total_mb=candidate.online.size_mb,
                message="Avvio aggiornamento driver tramite Windows Update...",
            )
        )

        state: Dict[str, object] = {"last_percent": 5.0, "reboot_required": False}
        meta: Dict[str, str] = {}
        error_lines: List[str] = []

        # Request on-demand Windows UAC elevation if running as standard user
        if self._use_uac_elevation and sys.platform.startswith("win") and not is_process_elevated():
            rc, was_cancelled, uac_err = self._execute_elevated_uac(
                candidate=candidate,
                update_id=update_id,
                on_progress=on_progress,
                control=control,
                state=state,
                meta=meta,
                error_lines=error_lines,
            )
            if was_cancelled:
                cancel_msg = uac_err or "Aggiornamento driver annullato dall'utente."
                on_progress(
                    DownloadProgress(
                        app_id=candidate.app_id,
                        app_name=candidate.name,
                        phase=UpdatePhase.CANCELLED,
                        percent=float(state["last_percent"]),
                        message=cancel_msg,
                    )
                )
                return self._build_record(
                    candidate, "cancelled", started_at, cancel_msg, cancel_msg
                )
            if uac_err is not None or rc is None:
                err = uac_err or "Errore avvio elevazione UAC."
                on_progress(
                    DownloadProgress(
                        app_id=candidate.app_id,
                        app_name=candidate.name,
                        phase=UpdatePhase.FAILED,
                        percent=float(state["last_percent"]),
                        message=err,
                    )
                )
                return self._build_record(candidate, "failed", started_at, err, err)
        else:
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            script_with_arg = self._build_ps_script(update_id=update_id)
            try:
                proc = subprocess.Popen(
                    [
                        "powershell",
                        "-NoProfile",
                        "-NonInteractive",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-Command",
                        script_with_arg,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=creation_flags,
                )
            except OSError as exc:
                err = f"Errore avvio Windows Update Agent: {exc}"
                on_progress(
                    DownloadProgress(
                        app_id=candidate.app_id,
                        app_name=candidate.name,
                        phase=UpdatePhase.FAILED,
                        percent=0.0,
                        message=err,
                    )
                )
                return self._build_record(candidate, "failed", started_at, err, err)

            assert proc.stdout is not None
            for raw_line in proc.stdout:
                if control.is_cancelled:
                    proc.terminate()
                    on_progress(
                        DownloadProgress(
                            app_id=candidate.app_id,
                            app_name=candidate.name,
                            phase=UpdatePhase.CANCELLED,
                            percent=float(state["last_percent"]),
                            message="Aggiornamento driver annullato dall'utente.",
                        )
                    )
                    return self._build_record(candidate, "cancelled", started_at, "Annullato")

                self._process_output_line(
                    raw_line, candidate, on_progress, state, meta, error_lines
                )

            rc = proc.wait()

        if rc == 0:
            done_msg = (
                f"{candidate.name} aggiornato alla v{candidate.online.latest_version} "
                "(riavvio consigliato)."
                if bool(state["reboot_required"])
                else f"{candidate.name} aggiornato alla v{candidate.online.latest_version}."
            )
            on_progress(
                DownloadProgress(
                    app_id=candidate.app_id,
                    app_name=candidate.name,
                    phase=UpdatePhase.COMPLETED,
                    percent=100.0,
                    downloaded_mb=candidate.online.size_mb,
                    total_mb=candidate.online.size_mb,
                    message=done_msg,
                )
            )
            return self._build_record(candidate, "success", started_at)

        summary, rich_details = self.decode_wua_failure(
            candidate=candidate,
            meta=meta,
            error_lines=error_lines,
            returncode=rc,
        )
        on_progress(
            DownloadProgress(
                app_id=candidate.app_id,
                app_name=candidate.name,
                phase=UpdatePhase.FAILED,
                percent=float(state["last_percent"]),
                message=summary,
            )
        )
        return self._build_record(candidate, "failed", started_at, summary, rich_details)


def create_default_driver_detector() -> AppDetector:
    """Create the default composite Windows driver detector (Registry + CIM fallback)."""
    return CompositeAppDetector([WindowsDriverRegistryDetector(), WindowsCimDriverDetector()])
