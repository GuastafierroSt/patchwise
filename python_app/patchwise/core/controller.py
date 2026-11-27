"""Application controller coordinating detection, online comparison, manual updates & history."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Sequence

from patchwise.core.checkers import (
    CompositeVersionChecker,
    GitHubReleasesChecker,
    VersionChecker,
    WingetVersionChecker,
)
from patchwise.core.detectors import (
    AppDetector,
    CompositeAppDetector,
    WindowsRegistryDetector,
    WingetDetector,
)
from patchwise.core.installer import (
    AppUpdater,
    DirectHttpInstaller,
    ProgressCallback,
    UpdateControlToken,
    WingetAppUpdater,
)
from patchwise.core.session_history import StatelessSessionHistoryManager
from patchwise.models import (
    InstalledApp,
    UpdateCandidate,
    UpdatePhase,
    UpdateRecord,
)


class UpdateManagerController:
    """Facade orchestrating PatchWise's scan, compare, manual update, and session history.

    Auto-update is strictly disabled by architecture (`AUTO_UPDATE_ALLOWED = False`).
    """

    AUTO_UPDATE_ALLOWED: bool = False

    def __init__(
        self,
        detector: Optional[AppDetector] = None,
        checker: Optional[VersionChecker] = None,
        updaters: Optional[Sequence[AppUpdater]] = None,
        history: Optional[StatelessSessionHistoryManager] = None,
    ) -> None:
        self._detector = detector or CompositeAppDetector(
            [WingetDetector(), WindowsRegistryDetector()]
        )
        self._checker = checker or CompositeVersionChecker(
            [WingetVersionChecker(), GitHubReleasesChecker()]
        )
        self._updaters: List[AppUpdater] = list(
            updaters or [WingetAppUpdater(), DirectHttpInstaller()]
        )
        self._history = history or StatelessSessionHistoryManager()

        self.installed_apps: List[InstalledApp] = []
        self.candidates: List[UpdateCandidate] = []
        self.last_scan_at: Optional[str] = None
        self._active_control: Optional[UpdateControlToken] = None

    @property
    def history(self) -> StatelessSessionHistoryManager:
        return self._history

    def scan_system(self) -> List[UpdateCandidate]:
        """Scan installed programs and compare against online versions."""
        self.installed_apps = self._detector.detect()
        self.candidates = self._checker.find_updates(self.installed_apps)
        self.last_scan_at = datetime.now().strftime("%H:%M:%S")
        return list(self.candidates)

    def get_up_to_date_apps(self) -> List[InstalledApp]:
        pending_ids = {c.app_id for c in self.candidates if c.status != UpdatePhase.COMPLETED}
        return [app for app in self.installed_apps if app.app_id not in pending_ids]

    def update_single(
        self,
        candidate: UpdateCandidate,
        on_progress: ProgressCallback,
        control: Optional[UpdateControlToken] = None,
    ) -> UpdateRecord:
        """Manually execute a single update and record it in the active session history."""
        self._active_control = control or UpdateControlToken()
        updater = self._resolve_updater(candidate)
        if updater is None:
            record = UpdateRecord(
                record_id="no-driver",
                app_id=candidate.app_id,
                app_name=candidate.name,
                publisher=candidate.app.publisher,
                from_version=candidate.app.installed_version,
                to_version=candidate.online.latest_version,
                size_mb=candidate.online.size_mb,
                category=candidate.online.category,
                status="failed",
                duration_seconds=0.1,
                error_message="Nessun provider di installazione compatibile trovato.",
            )
            self._history.record_update(record)
            return record

        candidate.status = UpdatePhase.DOWNLOADING
        record = updater.execute_update(candidate, on_progress, self._active_control)
        candidate.status = (
            UpdatePhase.COMPLETED if record.status == "success" else UpdatePhase.FAILED
        )
        self._history.record_update(record)
        self._active_control = None
        return record

    def update_batch(
        self,
        candidates: Sequence[UpdateCandidate],
        on_progress: ProgressCallback,
        control: Optional[UpdateControlToken] = None,
    ) -> List[UpdateRecord]:
        """Sequentially install user-selected updates while reporting live progress."""
        shared_control = control or UpdateControlToken()
        records: List[UpdateRecord] = []
        for candidate in candidates:
            if shared_control.is_cancelled:
                break
            if candidate.skipped or candidate.status == UpdatePhase.COMPLETED:
                continue
            records.append(self.update_single(candidate, on_progress, shared_control))
        return records

    def pause_active(self) -> None:
        if self._active_control:
            self._active_control.pause()

    def resume_active(self) -> None:
        if self._active_control:
            self._active_control.resume()

    def cancel_active(self) -> None:
        if self._active_control:
            self._active_control.cancel()

    def shutdown(self) -> None:
        """Persist only the current session snapshot on exit (stateless policy)."""
        self.cancel_active()
        self._history.finalize_session()

    def get_summary_metrics(self) -> Dict[str, int]:
        pending = [c for c in self.candidates if c.status != UpdatePhase.COMPLETED and not c.skipped]
        critical = sum(1 for c in pending if c.online.category.value == "security")
        return {
            "total_installed": len(self.installed_apps),
            "pending_updates": len(pending),
            "critical_updates": critical,
            "updated_this_session": sum(
                1 for r in self._history.get_current_session_records() if r.status == "success"
            ),
        }

    def _resolve_updater(self, candidate: UpdateCandidate) -> Optional[AppUpdater]:
        for updater in self._updaters:
            if updater.can_handle(candidate):
                return updater
        return None
