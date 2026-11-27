"""Background QThread workers keeping the PatchWise desktop GUI responsive."""

from __future__ import annotations

from typing import List, Sequence

from PySide6.QtCore import QThread, Signal

from patchwise.core.controller import UpdateManagerController
from patchwise.core.installer import UpdateControlToken
from patchwise.models import DownloadProgress, UpdateCandidate, UpdateRecord


class ScanWorker(QThread):
    """Runs system detection + online version comparison off the UI thread."""

    scan_finished = Signal(list)
    scan_failed = Signal(str)

    def __init__(self, controller: UpdateManagerController) -> None:
        super().__init__()
        self._controller = controller

    def run(self) -> None:
        try:
            candidates = self._controller.scan_system()
            self.scan_finished.emit(candidates)
        except Exception as exc:  # noqa: BLE001
            self.scan_failed.emit(str(exc))


class UpdateWorker(QThread):
    """Executes one or more manual updates sequentially while streaming progress signals."""

    progress_changed = Signal(object)  # DownloadProgress
    item_completed = Signal(object)  # UpdateRecord
    batch_finished = Signal(list)  # List[UpdateRecord]

    def __init__(
        self,
        controller: UpdateManagerController,
        candidates: Sequence[UpdateCandidate],
    ) -> None:
        super().__init__()
        self._controller = controller
        self._candidates: List[UpdateCandidate] = list(candidates)
        self.control = UpdateControlToken()

    def run(self) -> None:
        records: List[UpdateRecord] = []
        for candidate in self._candidates:
            if self.control.is_cancelled:
                break
            record = self._controller.update_single(
                candidate,
                on_progress=self._emit_progress,
                control=self.control,
            )
            records.append(record)
            self.item_completed.emit(record)
        self.batch_finished.emit(records)

    def _emit_progress(self, progress: DownloadProgress) -> None:
        self.progress_changed.emit(progress)
