"""OOP class hierarchy for manual update download & installation with live progress."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import tempfile
import threading
import time
import urllib.request
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Optional

from patchwise.models import (
    DownloadProgress,
    UpdateCandidate,
    UpdatePhase,
    UpdateRecord,
)

ProgressCallback = Callable[[DownloadProgress], None]


class UpdateControlToken:
    """Thread-safe pause/resume/cancel handle for an active update."""

    def __init__(self) -> None:
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused initially
        self._cancel_event = threading.Event()

    def pause(self) -> None:
        self._pause_event.clear()

    def resume(self) -> None:
        self._pause_event.set()

    def cancel(self) -> None:
        self._cancel_event.set()
        self._pause_event.set()

    @property
    def is_paused(self) -> bool:
        return not self._pause_event.is_set()

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def wait_if_paused(self) -> None:
        self._pause_event.wait()


class AppUpdater(ABC):
    """Abstract base class for downloading and installing a single manual update.

    Auto-update scheduling is explicitly prohibited across all subclasses.
    """

    AUTO_UPDATE_SUPPORTED: bool = False

    @abstractmethod
    def can_handle(self, candidate: UpdateCandidate) -> bool:
        """Return True if this updater strategy can update the given candidate."""

    @abstractmethod
    def execute_update(
        self,
        candidate: UpdateCandidate,
        on_progress: ProgressCallback,
        control: Optional[UpdateControlToken] = None,
    ) -> UpdateRecord:
        """Download, verify, and install the candidate update while emitting progress."""

    @staticmethod
    def _build_record(
        candidate: UpdateCandidate,
        status: str,
        started_at: float,
        error_message: str = "",
        error_details: str = "",
    ) -> UpdateRecord:
        return UpdateRecord(
            record_id=str(uuid.uuid4())[:8],
            app_id=candidate.app_id,
            app_name=candidate.name,
            publisher=candidate.app.publisher,
            from_version=candidate.app.installed_version,
            to_version=candidate.online.latest_version,
            size_mb=candidate.online.size_mb,
            category=candidate.online.category,
            status=status,
            duration_seconds=round(max(0.1, time.monotonic() - started_at), 2),
            error_message=error_message,
            item_type=candidate.app.item_type,
            error_details=error_details,
        )


class WingetAppUpdater(AppUpdater):
    """Installs updates using `winget upgrade --id <id> --exact` with smart interactive fallback.

    Runs silently (`--silent`) by default so standard apps update smoothly without
    popups. If the silent uninstall/install fails with a recoverable error (such as
    `0x8A150030` / `2316632112` when a package must uninstall its previous version
    interactively or needs user confirmation), automatically retries once with
    `--interactive` so the user can approve the vendor wizard or UAC prompt.
    """

    _PERCENT_RE = re.compile(r"(\d{1,3})\s*%")

    # Exit codes representing a completed update (reboot may be recommended)
    _SUCCESS_CODES = frozenset({0, 3010})

    # Exit codes where the user explicitly cancelled UAC or the installer wizard
    _USER_CANCELLED_CODES = frozenset({1223, 1602})

    # Exit codes where retrying interactively will not help and we should explain directly
    _NON_RETRYABLE_CODES = frozenset(
        {
            1223,        # ERROR_CANCELLED (UAC declined)
            1602,        # ERROR_INSTALL_USEREXIT
            1618,        # ERROR_INSTALL_ALREADY_RUNNING
            0x8A150011,  # APPINSTALLER_CLI_ERROR_INSTALLER_HASH_MISMATCH
            0x8A15002B,  # APPINSTALLER_CLI_ERROR_UPDATE_NOT_APPLICABLE
            0x8A150056,  # APPINSTALLER_CLI_ERROR_INSTALLER_PROHIBITS_ELEVATION
            0x8A150102,  # APPINSTALLER_CLI_ERROR_INSTALL_INSTALL_IN_PROGRESS
            0x8A150109,  # APPINSTALLER_CLI_ERROR_INSTALL_REBOOT_REQUIRED_TO_FINISH
        }
    )

    _ERROR_MESSAGES: dict[int, str] = {
        0x8A150030: (
            "Disinstallazione della versione precedente non riuscita (0x8A150030). "
            "Chiudi l'app o eventuali processi/launcher in background e riprova, "
            "oppure disinstalla prima la vecchia versione da Impostazioni di Windows."
        ),
        0x8A150011: (
            "Verifica hash dell'installer fallita nel catalogo Winget (0x8A150011). "
            "Il produttore potrebbe aver appena aggiornato il file: riprova più tardi."
        ),
        0x8A15002B: "Nessun aggiornamento applicabile rilevato da Winget (0x8A15002B).",
        0x8A150056: (
            "L'installer non può essere eseguito come Amministratore (0x8A150056). "
            "Avvia PatchWise come utente standard."
        ),
        0x8A150101: (
            "L'applicazione è attualmente in esecuzione (0x8A150101). "
            "Chiudila completamente (anche nella barra di sistema) e riprova."
        ),
        0x8A150102: (
            "Un'altra installazione è già in corso sul PC (0x8A150102). "
            "Attendi il completamento e riprova."
        ),
        0x8A150103: (
            "Uno o più file dell'app sono bloccati da un processo attivo (0x8A150103). "
            "Chiudi l'app e riprova."
        ),
        0x8A150109: (
            "È richiesto il riavvio del PC per completare un'installazione precedente "
            "(0x8A150109)."
        ),
        0x8A15010D: (
            "Un'altra versione dell'applicazione è già installata e impedisce la "
            "sovrascrittura diretta (0x8A15010D)."
        ),
        1603: (
            "Errore dell'installer Windows durante l'aggiornamento (codice 1603). "
            "Chiudi l'applicazione e riprova, oppure avvia PatchWise come Amministratore."
        ),
        1618: (
            "Un'altra installazione Windows è già in corso (codice 1618). "
            "Attendi che termini e riprova."
        ),
    }

    def __init__(self, interactive_fallback: bool = True) -> None:
        self._interactive_fallback = interactive_fallback

    def can_handle(self, candidate: UpdateCandidate) -> bool:
        return bool(candidate.app.winget_id)

    @staticmethod
    def normalize_exit_code(returncode: int) -> int:
        """Normalize signed/unsigned 32-bit Windows/HRESULT exit codes."""
        return returncode & 0xFFFFFFFF

    @classmethod
    def format_winget_error(
        cls, returncode: int, output_lines: list[str] | None = None
    ) -> str:
        """Translate cryptic Winget/MSI decimal codes into clear Italian diagnostics."""
        code = cls.normalize_exit_code(returncode)
        if code in cls._ERROR_MESSAGES:
            return cls._ERROR_MESSAGES[code]

        detail = ""
        if output_lines:
            for line in reversed(output_lines):
                clean = line.strip()
                if not clean or set(clean) <= {"-", "\\", "|", "/", ".", " "}:
                    continue
                if cls._PERCENT_RE.search(clean):
                    continue
                if len(clean) >= 8:
                    detail = clean[:160]
                    break

        hex_suffix = f" (0x{code:08X})" if code >= 0x80000000 else ""
        base = f"Winget terminato con codice {returncode}{hex_suffix}"
        return f"{base}: {detail}" if detail else base

    @staticmethod
    def _build_command(winget_id: str, interactive: bool) -> list[str]:
        mode_flag = "--interactive" if interactive else "--silent"
        return [
            "winget",
            "upgrade",
            "--id",
            winget_id,
            "--exact",
            mode_flag,
            "--accept-package-agreements",
            "--accept-source-agreements",
        ]

    def _run_attempt(
        self,
        candidate: UpdateCandidate,
        winget_id: str,
        interactive: bool,
        on_progress: ProgressCallback,
        control: UpdateControlToken,
        initial_percent: float = 5.0,
    ) -> tuple[Optional[int], float, bool, list[str], Optional[str]]:
        """Execute one `winget upgrade` attempt.

        Returns `(returncode, last_percent, was_cancelled, output_lines, spawn_error)`.
        """
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        cmd = self._build_command(winget_id, interactive=interactive)

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creation_flags,
            )
        except OSError as exc:
            return None, 0.0, False, [], str(exc)

        assert proc.stdout is not None
        last_percent = initial_percent
        captured_lines: list[str] = []

        for raw_line in proc.stdout:
            if control.is_cancelled:
                proc.terminate()
                return None, last_percent, True, captured_lines, None

            line = raw_line.strip()
            if line:
                captured_lines.append(line)
                if len(captured_lines) > 40:
                    captured_lines.pop(0)

            lower = line.lower()
            match = self._PERCENT_RE.search(line)
            if match:
                pct = min(90.0, float(match.group(1)) * 0.85)
                last_percent = max(last_percent, pct)
                on_progress(
                    DownloadProgress(
                        app_id=candidate.app_id,
                        app_name=candidate.name,
                        phase=UpdatePhase.DOWNLOADING,
                        percent=round(last_percent, 1),
                        downloaded_mb=round(
                            candidate.online.size_mb * (last_percent / 100.0), 1
                        ),
                        total_mb=candidate.online.size_mb,
                        message=f"Download pacchetto in corso ({int(last_percent)}%)...",
                    )
                )
            elif "verif" in lower or "hash" in lower:
                last_percent = max(last_percent, 88.0)
                on_progress(
                    DownloadProgress(
                        app_id=candidate.app_id,
                        app_name=candidate.name,
                        phase=UpdatePhase.VERIFYING,
                        percent=88.0,
                        downloaded_mb=candidate.online.size_mb,
                        total_mb=candidate.online.size_mb,
                        message="Verifica integrità hash SHA-256...",
                    )
                )
            elif "disinstall" in lower or "uninstall" in lower:
                last_percent = max(last_percent, 91.0)
                mode_hint = (
                    " (conferma nella finestra se richiesto)"
                    if interactive
                    else ""
                )
                on_progress(
                    DownloadProgress(
                        app_id=candidate.app_id,
                        app_name=candidate.name,
                        phase=UpdatePhase.INSTALLING,
                        percent=91.0,
                        downloaded_mb=candidate.online.size_mb,
                        total_mb=candidate.online.size_mb,
                        message=f"Disinstallazione versione precedente in corso{mode_hint}...",
                    )
                )
            elif "install" in lower:
                last_percent = max(last_percent, 93.0)
                msg = (
                    "Installazione interattiva in corso (conferma nella finestra)..."
                    if interactive
                    else "Installazione silenziosa in corso..."
                )
                on_progress(
                    DownloadProgress(
                        app_id=candidate.app_id,
                        app_name=candidate.name,
                        phase=UpdatePhase.INSTALLING,
                        percent=93.0,
                        downloaded_mb=candidate.online.size_mb,
                        total_mb=candidate.online.size_mb,
                        message=msg,
                    )
                )

        rc = proc.wait()
        return rc, last_percent, False, captured_lines, None

    def execute_update(
        self,
        candidate: UpdateCandidate,
        on_progress: ProgressCallback,
        control: Optional[UpdateControlToken] = None,
    ) -> UpdateRecord:
        control = control or UpdateControlToken()
        started_at = time.monotonic()
        winget_id = candidate.app.winget_id or ""

        on_progress(
            DownloadProgress(
                app_id=candidate.app_id,
                app_name=candidate.name,
                phase=UpdatePhase.DOWNLOADING,
                percent=2.0,
                total_mb=candidate.online.size_mb,
                message=f"Avvio download pacchetto Winget ({winget_id})...",
            )
        )

        rc, last_percent, cancelled, captured, spawn_err = self._run_attempt(
            candidate=candidate,
            winget_id=winget_id,
            interactive=False,
            on_progress=on_progress,
            control=control,
            initial_percent=5.0,
        )

        if spawn_err is not None:
            on_progress(
                DownloadProgress(
                    app_id=candidate.app_id,
                    app_name=candidate.name,
                    phase=UpdatePhase.FAILED,
                    percent=0.0,
                    message=f"Errore avvio Winget: {spawn_err}",
                )
            )
            return self._build_record(candidate, "failed", started_at, spawn_err)

        if cancelled:
            on_progress(
                DownloadProgress(
                    app_id=candidate.app_id,
                    app_name=candidate.name,
                    phase=UpdatePhase.CANCELLED,
                    percent=last_percent,
                    message="Aggiornamento annullato dall'utente.",
                )
            )
            return self._build_record(candidate, "cancelled", started_at, "Annullato")

        assert rc is not None
        norm_code = self.normalize_exit_code(rc)

        # Smart automatic fallback: if silent mode failed on an uninstall/installer step,
        # retry once in interactive mode so the user can confirm dialogs or UAC prompts.
        tried_interactive = False
        if (
            self._interactive_fallback
            and norm_code not in self._SUCCESS_CODES
            and norm_code not in self._NON_RETRYABLE_CODES
        ):
            tried_interactive = True
            on_progress(
                DownloadProgress(
                    app_id=candidate.app_id,
                    app_name=candidate.name,
                    phase=UpdatePhase.INSTALLING,
                    percent=max(last_percent, 90.0),
                    downloaded_mb=candidate.online.size_mb,
                    total_mb=candidate.online.size_mb,
                    message=(
                        "Modalità silenziosa non riuscita: avvio modalità interattiva "
                        "(conferma nella finestra di installazione)..."
                    ),
                )
            )
            rc2, last_percent2, cancelled2, captured2, spawn_err2 = self._run_attempt(
                candidate=candidate,
                winget_id=winget_id,
                interactive=True,
                on_progress=on_progress,
                control=control,
                initial_percent=max(last_percent, 90.0),
            )
            if spawn_err2 is None and not cancelled2 and rc2 is not None:
                rc = rc2
                norm_code = self.normalize_exit_code(rc2)
                last_percent = last_percent2
                captured = captured2 or captured
            elif cancelled2:
                on_progress(
                    DownloadProgress(
                        app_id=candidate.app_id,
                        app_name=candidate.name,
                        phase=UpdatePhase.CANCELLED,
                        percent=last_percent2,
                        message="Aggiornamento annullato dall'utente.",
                    )
                )
                return self._build_record(candidate, "cancelled", started_at, "Annullato")

        if norm_code in self._SUCCESS_CODES:
            reboot_note = " (riavvio consigliato)" if norm_code == 3010 else ""
            on_progress(
                DownloadProgress(
                    app_id=candidate.app_id,
                    app_name=candidate.name,
                    phase=UpdatePhase.COMPLETED,
                    percent=100.0,
                    downloaded_mb=candidate.online.size_mb,
                    total_mb=candidate.online.size_mb,
                    message=(
                        f"{candidate.name} aggiornato alla "
                        f"v{candidate.online.latest_version}{reboot_note}."
                    ),
                )
            )
            return self._build_record(candidate, "success", started_at)

        if norm_code in self._USER_CANCELLED_CODES:
            msg = "Aggiornamento annullato dall'utente nella finestra di installazione."
            on_progress(
                DownloadProgress(
                    app_id=candidate.app_id,
                    app_name=candidate.name,
                    phase=UpdatePhase.CANCELLED,
                    percent=last_percent,
                    message=msg,
                )
            )
            return self._build_record(candidate, "cancelled", started_at, msg)

        err = self.format_winget_error(rc, captured)
        details = self._build_diagnostic_details(
            candidate=candidate,
            winget_id=winget_id,
            returncode=rc,
            tried_interactive=tried_interactive,
            captured=captured,
            summary=err,
        )
        on_progress(
            DownloadProgress(
                app_id=candidate.app_id,
                app_name=candidate.name,
                phase=UpdatePhase.FAILED,
                percent=last_percent,
                message=err,
            )
        )
        return self._build_record(candidate, "failed", started_at, err, details)

    @classmethod
    def _build_diagnostic_details(
        cls,
        candidate: UpdateCandidate,
        winget_id: str,
        returncode: int,
        tried_interactive: bool,
        captured: list[str],
        summary: str,
    ) -> str:
        norm = cls.normalize_exit_code(returncode)
        mode_str = (
            "Silenziosa (--silent) → Fallback interattivo (--interactive)"
            if tried_interactive
            else "Silenziosa (--silent)"
        )
        lines = [
            f"Applicazione: {candidate.name} ({candidate.app.publisher})",
            f"Versione: {candidate.app.installed_version} → {candidate.online.latest_version}",
            f"Pacchetto Winget: {winget_id}",
            f"Modalità eseguita: {mode_str}",
            f"Codice di uscita: {returncode} (0x{norm:08X})",
            "",
            "DIAGNOSI",
            summary,
        ]
        meaningful_log = [
            ln.strip()
            for ln in captured
            if ln.strip() and not (set(ln.strip()) <= {"-", "\\", "|", "/", ".", " "})
        ][-12:]
        if meaningful_log:
            lines.extend(["", "OUTPUT WINGET (ULTIME RIGHE)", *meaningful_log])
        return "\n".join(lines)


class DirectHttpInstaller(AppUpdater):
    """Downloads an installer over HTTPS with streaming progress, optional SHA-256 check,
    and silent execution in an isolated temporary directory (portable-friendly)."""

    CHUNK_SIZE = 64 * 1024  # 64 KiB

    def can_handle(self, candidate: UpdateCandidate) -> bool:
        return candidate.online.download_url.startswith(("https://", "http://"))

    def execute_update(
        self,
        candidate: UpdateCandidate,
        on_progress: ProgressCallback,
        control: Optional[UpdateControlToken] = None,
    ) -> UpdateRecord:
        control = control or UpdateControlToken()
        started_at = time.monotonic()
        url = candidate.online.download_url

        if not url:
            return self._build_record(candidate, "failed", started_at, "URL di download assente")

        tmp_dir = Path(tempfile.mkdtemp(prefix="patchwise_dl_"))
        filename = Path(url.split("?")[0]).name or f"{candidate.app_id}_setup.exe"
        dest_file = tmp_dir / filename

        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "PatchWise/1.0"}
            )
            with urllib.request.urlopen(req, timeout=30) as response, open(dest_file, "wb") as out:
                total_bytes = int(response.headers.get("Content-Length", "0") or 0)
                total_mb = (
                    round(total_bytes / (1024 * 1024), 2)
                    if total_bytes > 0
                    else candidate.online.size_mb
                )
                downloaded_bytes = 0
                dl_start = time.monotonic()

                while True:
                    if control.is_cancelled:
                        on_progress(
                            DownloadProgress(
                                app_id=candidate.app_id,
                                app_name=candidate.name,
                                phase=UpdatePhase.CANCELLED,
                                percent=0.0,
                                message="Download annullato.",
                            )
                        )
                        return self._build_record(candidate, "cancelled", started_at, "Annullato")

                    if control.is_paused:
                        on_progress(
                            DownloadProgress(
                                app_id=candidate.app_id,
                                app_name=candidate.name,
                                phase=UpdatePhase.PAUSED,
                                percent=round(
                                    (downloaded_bytes / total_bytes) * 80.0
                                    if total_bytes
                                    else 0.0,
                                    1,
                                ),
                                downloaded_mb=round(downloaded_bytes / (1024 * 1024), 2),
                                total_mb=total_mb,
                                message="Download in pausa.",
                            )
                        )
                        control.wait_if_paused()
                        continue

                    chunk = response.read(self.CHUNK_SIZE)
                    if not chunk:
                        break
                    out.write(chunk)
                    downloaded_bytes += len(chunk)

                    elapsed = max(0.05, time.monotonic() - dl_start)
                    speed_mbps = (downloaded_bytes / (1024 * 1024)) / elapsed
                    pct = (downloaded_bytes / total_bytes) * 80.0 if total_bytes > 0 else 40.0
                    eta = (
                        int((total_bytes - downloaded_bytes) / max(1.0, downloaded_bytes / elapsed))
                        if total_bytes > 0
                        else None
                    )
                    on_progress(
                        DownloadProgress(
                            app_id=candidate.app_id,
                            app_name=candidate.name,
                            phase=UpdatePhase.DOWNLOADING,
                            percent=round(min(80.0, pct), 1),
                            downloaded_mb=round(downloaded_bytes / (1024 * 1024), 2),
                            total_mb=total_mb,
                            speed_mbps=round(speed_mbps, 2),
                            eta_seconds=eta,
                            message="Ricezione pacchetto di aggiornamento...",
                        )
                    )

            # Phase 2: SHA-256 verification
            on_progress(
                DownloadProgress(
                    app_id=candidate.app_id,
                    app_name=candidate.name,
                    phase=UpdatePhase.VERIFYING,
                    percent=85.0,
                    downloaded_mb=total_mb,
                    total_mb=total_mb,
                    message="Verifica integrità SHA-256 del file scaricato...",
                )
            )
            if candidate.online.sha256:
                actual_hash = self._compute_sha256(dest_file)
                if actual_hash.lower() != candidate.online.sha256.lower():
                    raise ValueError("Checksum SHA-256 non corrispondente")

            # Phase 3: Silent execution
            on_progress(
                DownloadProgress(
                    app_id=candidate.app_id,
                    app_name=candidate.name,
                    phase=UpdatePhase.INSTALLING,
                    percent=92.0,
                    downloaded_mb=total_mb,
                    total_mb=total_mb,
                    message="Installazione pacchetto in corso...",
                )
            )
            self._run_silent_installer(dest_file)

            on_progress(
                DownloadProgress(
                    app_id=candidate.app_id,
                    app_name=candidate.name,
                    phase=UpdatePhase.COMPLETED,
                    percent=100.0,
                    downloaded_mb=total_mb,
                    total_mb=total_mb,
                    message=f"Aggiornamento completato alla v{candidate.online.latest_version}.",
                )
            )
            return self._build_record(candidate, "success", started_at)
        except Exception as exc:  # noqa: BLE001
            on_progress(
                DownloadProgress(
                    app_id=candidate.app_id,
                    app_name=candidate.name,
                    phase=UpdatePhase.FAILED,
                    percent=0.0,
                    message=f"Errore aggiornamento: {exc}",
                )
            )
            return self._build_record(candidate, "failed", started_at, str(exc))
        finally:
            try:
                if dest_file.exists():
                    os.remove(dest_file)
                tmp_dir.rmdir()
            except OSError:
                pass

    @staticmethod
    def _compute_sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as fh:
            for block in iter(lambda: fh.read(65536), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _run_silent_installer(installer_path: Path) -> None:
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if installer_path.suffix.lower() == ".msi":
            cmd = ["msiexec", "/i", str(installer_path), "/qn", "/norestart"]
        else:
            cmd = [str(installer_path), "/S", "/VERYSILENT", "/NORESTART"]
        subprocess.run(cmd, check=True, timeout=180, creationflags=creation_flags)
