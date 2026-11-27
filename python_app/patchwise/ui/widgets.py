"""Reusable PySide6 widgets for PatchWise Desktop.

IMPORTANT DESIGN CONSTRAINT:
Auto-update toggles are strictly excluded from all cards and controls.
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from patchwise.models import (
    DownloadProgress,
    UpdateCandidate,
    UpdatePhase,
    UpdateRecord,
)


class ActiveDownloadBanner(QFrame):
    """Displays the currently updating app, phase, speed, ETA, and intuitive progress bar."""

    def __init__(
        self,
        on_pause_toggle: Callable[[], None],
        on_cancel: Callable[[], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ProgressBanner")
        self._paused = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(16)

        left_col = QVBoxLayout()
        left_col.setSpacing(4)

        title_row = QHBoxLayout()
        self.title_label = QLabel("Nessun download attivo")
        self.title_label.setStyleSheet("font-weight: 600; color: #1b1c1d; background: transparent;")
        self.percent_label = QLabel("0%")
        self.percent_label.setObjectName("MonoVersion")
        title_row.addWidget(self.title_label)
        title_row.addWidget(self.percent_label)
        title_row.addStretch()

        self.detail_label = QLabel(
            "Avvia manualmente un aggiornamento per monitorare avanzamento, velocità e verifica."
        )
        self.detail_label.setObjectName("MutedText")

        left_col.addLayout(title_row)
        left_col.addWidget(self.detail_label)

        right_col = QHBoxLayout()
        right_col.setSpacing(10)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("DownloadBar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedWidth(240)

        self.pause_btn = QPushButton("Pausa")
        self.pause_btn.setObjectName("SecondaryButton")
        self.pause_btn.clicked.connect(on_pause_toggle)
        self.pause_btn.setEnabled(False)

        self.cancel_btn = QPushButton("Annulla")
        self.cancel_btn.setObjectName("SecondaryButton")
        self.cancel_btn.clicked.connect(on_cancel)
        self.cancel_btn.setEnabled(False)

        right_col.addWidget(self.progress_bar)
        right_col.addWidget(self.pause_btn)
        right_col.addWidget(self.cancel_btn)

        layout.addLayout(left_col, stretch=1)
        layout.addLayout(right_col)

    def update_progress(self, progress: DownloadProgress) -> None:
        is_active = progress.phase in (
            UpdatePhase.DOWNLOADING,
            UpdatePhase.VERIFYING,
            UpdatePhase.INSTALLING,
            UpdatePhase.PAUSED,
        )
        self._paused = progress.phase == UpdatePhase.PAUSED
        self.pause_btn.setText("Riprendi" if self._paused else "Pausa")
        self.pause_btn.setEnabled(
            progress.phase in (UpdatePhase.DOWNLOADING, UpdatePhase.PAUSED)
        )
        self.cancel_btn.setEnabled(is_active)

        phase_labels = {
            UpdatePhase.DOWNLOADING: "Download in corso",
            UpdatePhase.VERIFYING: "Verifica SHA-256",
            UpdatePhase.INSTALLING: "Installazione silenziosa",
            UpdatePhase.PAUSED: "Download in pausa",
            UpdatePhase.COMPLETED: "Completato",
            UpdatePhase.FAILED: "Errore aggiornamento",
            UpdatePhase.CANCELLED: "Annullato",
        }
        prefix = phase_labels.get(progress.phase, "Stato")
        self.title_label.setText(f"{prefix}: {progress.app_name}")
        self.percent_label.setText(f"{int(round(progress.percent))}%")
        self.progress_bar.setValue(int(round(progress.percent)))

        metrics = []
        if progress.total_mb > 0:
            metrics.append(f"{progress.downloaded_mb:.1f} MB di {progress.total_mb:.1f} MB")
        if progress.speed_mbps > 0 and progress.phase == UpdatePhase.DOWNLOADING:
            metrics.append(f"{progress.speed_mbps:.1f} MB/s")
        if progress.eta_seconds is not None and progress.phase == UpdatePhase.DOWNLOADING:
            metrics.append(f"circa {progress.eta_seconds} sec. rimasti")

        suffix = f" ({' · '.join(metrics)})" if metrics else ""
        self.detail_label.setText(f"{progress.message}{suffix}")


class AppUpdateCard(QFrame):
    """Displays a single software update candidate. Contains NO auto-update toggle."""

    def __init__(
        self,
        candidate: UpdateCandidate,
        on_update_click: Callable[[UpdateCandidate], None],
        on_selection_change: Callable[[UpdateCandidate, bool], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.candidate = candidate

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(candidate.selected)
        self.checkbox.stateChanged.connect(
            lambda state: on_selection_change(candidate, state == Qt.CheckState.Checked.value)
        )
        layout.addWidget(self.checkbox)

        info_col = QVBoxLayout()
        info_col.setSpacing(4)

        category_label = {
            "security": "Sicurezza Critica",
            "features": "Nuove Funzionalità",
            "patch": "Bugfix",
        }.get(candidate.online.category.value, "Aggiornamento")

        header_label = QLabel(
            f"{candidate.name}  ·  {candidate.app.publisher}  ·  {category_label}"
        )
        header_label.setObjectName("CardTitle")

        size_text = f"  ·  {candidate.online.size_mb:.1f} MB" if candidate.online.size_mb else ""
        version_label = QLabel(
            f"Installata: {candidate.app.installed_version}  →  "
            f"Disponibile: {candidate.online.latest_version}{size_text}"
        )
        version_label.setObjectName("MonoVersion")

        notes_label = QLabel(candidate.online.release_notes or "Aggiornamento ufficiale verificato.")
        notes_label.setObjectName("MutedText")
        notes_label.setWordWrap(True)

        info_col.addWidget(header_label)
        info_col.addWidget(version_label)
        info_col.addWidget(notes_label)

        layout.addLayout(info_col, stretch=1)

        # Strictly manual trigger — NO auto-update switch!
        self.update_btn = QPushButton("Aggiorna Ora")
        self.update_btn.setObjectName("PrimaryButton")
        self.update_btn.clicked.connect(lambda: on_update_click(candidate))
        layout.addWidget(self.update_btn)

    def set_updating_state(self, phase: UpdatePhase) -> None:
        if phase in (UpdatePhase.DOWNLOADING, UpdatePhase.VERIFYING, UpdatePhase.INSTALLING):
            self.update_btn.setEnabled(False)
            self.update_btn.setText("In corso...")
        elif phase == UpdatePhase.COMPLETED:
            self.update_btn.setEnabled(False)
            self.update_btn.setText("Aggiornato")
        else:
            self.update_btn.setEnabled(True)
            self.update_btn.setText("Aggiorna Ora")


class HistoryRowWidget(QFrame):
    """Single row in the stateless session update history view."""

    def __init__(self, record: UpdateRecord, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        name_col = QVBoxLayout()
        title = QLabel(f"{record.app_name}  ·  {record.publisher}")
        title.setStyleSheet("font-weight: 600; background: transparent;")
        meta = QLabel(
            f"v{record.from_version} → v{record.to_version}  ·  "
            f"{record.completed_at}  ·  {record.duration_seconds:.1f}s"
        )
        meta.setObjectName("MutedText")
        name_col.addWidget(title)
        name_col.addWidget(meta)

        status_text = {
            "success": "Completato",
            "failed": f"Fallito ({record.error_message})",
            "cancelled": "Annullato",
        }.get(record.status, record.status)
        status_label = QLabel(status_text)
        status_label.setStyleSheet(
            "font-weight: 600; background: transparent; color: "
            + ("#6d5e00;" if record.status == "success" else "#ba1a1a;")
        )

        layout.addLayout(name_col, stretch=1)
        layout.addWidget(status_label)
