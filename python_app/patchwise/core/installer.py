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
        )


class WingetAppUpdater(AppUpdater):
    """Installs updates using `winget upgrade --id <id> --silent` with live progress parsing."""

    _PERCENT_RE = re.compile(r"(\d{1,3})\s*%")

    def can_handle(self, candidate: UpdateCandidate) -> bool:
        return bool(candidate.app.winget_id)

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

        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        cmd = [
            "winget",
            "upgrade",
            "--id",
            winget_id,
            "--exact",
            "--silent",
            "--accept-package-agreements",
            "--accept-source-agreements",
        ]

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
            on_progress(
                DownloadProgress(
                    app_id=candidate.app_id,
                    app_name=candidate.name,
                    phase=UpdatePhase.FAILED,
                    percent=0.0,
                    message=f"Errore avvio Winget: {exc}",
                )
            )
            return self._build_record(candidate, "failed", started_at, str(exc))

        assert proc.stdout is not None
        last_percent = 5.0
        for raw_line in proc.stdout:
            if control.is_cancelled:
                proc.terminate()
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

            line = raw_line.strip()
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
                        downloaded_mb=round(candidate.online.size_mb * (last_percent / 100.0), 1),
                        total_mb=candidate.online.size_mb,
                        message=f"Download pacchetto in corso ({int(last_percent)}%)...",
                    )
                )
            elif "verif" in line.lower() or "hash" in line.lower():
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
            elif "install" in line.lower():
                last_percent = max(last_percent, 93.0)
                on_progress(
                    DownloadProgress(
                        app_id=candidate.app_id,
                        app_name=candidate.name,
                        phase=UpdatePhase.INSTALLING,
                        percent=93.0,
                        downloaded_mb=candidate.online.size_mb,
                        total_mb=candidate.online.size_mb,
                        message="Installazione silenziosa in corso...",
                    )
                )

        rc = proc.wait()
        if rc == 0:
            on_progress(
                DownloadProgress(
                    app_id=candidate.app_id,
                    app_name=candidate.name,
                    phase=UpdatePhase.COMPLETED,
                    percent=100.0,
                    downloaded_mb=candidate.online.size_mb,
                    total_mb=candidate.online.size_mb,
                    message=f"{candidate.name} aggiornato alla v{candidate.online.latest_version}.",
                )
            )
            return self._build_record(candidate, "success", started_at)

        err = f"Winget terminato con codice {rc}"
        on_progress(
            DownloadProgress(
                app_id=candidate.app_id,
                app_name=candidate.name,
                phase=UpdatePhase.FAILED,
                percent=last_percent,
                message=err,
            )
        )
        return self._build_record(candidate, "failed", started_at, err)


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
                url, headers={"User-Agent": "PatchWise-Desktop-Updater/2.5"}
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
