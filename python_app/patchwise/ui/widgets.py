"""Reusable modern PySide6 widgets for PatchWise Desktop.

IMPORTANT DESIGN CONSTRAINT:
Auto-update toggles are strictly excluded from all cards and controls.
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
)
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGraphicsDropShadowEffect,
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
from patchwise.ui.theme import get_theme_tokens

_AVATAR_GRADIENTS = (
    ("#0ea5e9", "#685bd9"),  # Logo Cyan -> Violet
    ("#685bd9", "#a451d6"),  # Logo Violet -> Purple
    ("#a451d6", "#e83061"),  # Logo Purple -> Magenta
    ("#06b6d4", "#3b82f6"),  # Electric Cyan -> Blue
    ("#7c3aed", "#ec4899"),  # Deep Violet -> Pink
    ("#0891b2", "#6366f1"),  # Deep Cyan -> Indigo
)


def _extract_initials(name: str) -> str:
    cleaned = [part for part in name.replace("-", " ").split() if part]
    if not cleaned:
        return "PW"
    if len(cleaned) == 1:
        return cleaned[0][:2].upper()
    return (cleaned[0][0] + cleaned[1][0]).upper()


def _is_dark_context(widget: QWidget) -> bool:
    win = widget.window()
    return getattr(win, "current_theme", "light") == "dark"


class AppAvatarBadge(QLabel):
    """Colorful rounded-square monogram badge for software items."""

    def __init__(self, app_name: str, size: int = 40, parent: Optional[QWidget] = None) -> None:
        super().__init__(_extract_initials(app_name), parent)
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        palette_idx = sum(ord(ch) for ch in app_name) % len(_AVATAR_GRADIENTS)
        start, end = _AVATAR_GRADIENTS[palette_idx]
        radius = max(8, size // 4)
        font_px = max(11, int(size * 0.34))
        self.setStyleSheet(
            f"background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {start}, stop:1 {end});"
            f"color: #ffffff; border-radius: {radius}px; border: none;"
            f"font-weight: 800; font-size: {font_px}px;"
        )


class ModernCheckBox(QCheckBox):
    """Crisp custom-painted checkbox with vector checkmark for both light and dark themes."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(22, 22)

    def sizeHint(self) -> QSize:
        return QSize(22, 22)

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        tokens = get_theme_tokens("dark" if _is_dark_context(self) else "light")
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(2.0, 2.0, 18.0, 18.0)
        if self.isChecked():
            grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
            grad.setColorAt(0.0, QColor(tokens["primary"]))
            grad.setColorAt(1.0, QColor(tokens["primary_end"]))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(grad)
            painter.drawRoundedRect(rect, 5.5, 5.5)

            pen = QPen(QColor("#ffffff"))
            pen.setWidthF(2.1)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            path = QPainterPath()
            path.moveTo(QPointF(6.3, 11.2))
            path.lineTo(QPointF(9.5, 14.3))
            path.lineTo(QPointF(15.7, 7.7))
            painter.drawPath(path)
        else:
            border_color = tokens["checkbox_hover"] if self.underMouse() else tokens["checkbox_border"]
            pen = QPen(QColor(border_color))
            pen.setWidthF(1.6)
            painter.setPen(pen)
            painter.setBrush(QColor(tokens["checkbox_bg"]))
            painter.drawRoundedRect(rect, 5.5, 5.5)

        painter.end()


class ModernToggleSwitch(QCheckBox):
    """Smooth animated pill toggle switch (used for the Light/Dark theme switcher)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(44, 24)
        self._thumb_pos: float = 0.0
        self._anim = QPropertyAnimation(self, b"thumb_position", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate_thumb)

    def _get_thumb_position(self) -> float:
        return self._thumb_pos

    def _set_thumb_position(self, value: float) -> None:
        self._thumb_pos = value
        self.update()

    thumb_position = Property(float, _get_thumb_position, _set_thumb_position)

    def _animate_thumb(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._thumb_pos)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def setChecked(self, checked: bool) -> None:  # type: ignore[override]
        super().setChecked(checked)
        self._anim.stop()
        self._thumb_pos = 1.0 if checked else 0.0
        self.update()

    def hitButton(self, pos) -> bool:  # type: ignore[override]
        return self.rect().contains(pos)

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        tokens = get_theme_tokens("dark" if _is_dark_context(self) else "light")
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        track_rect = QRectF(1.0, 1.0, self.width() - 2.0, self.height() - 2.0)
        radius = track_rect.height() / 2.0
        painter.setPen(Qt.PenStyle.NoPen)

        if self.isChecked():
            grad = QLinearGradient(track_rect.topLeft(), track_rect.topRight())
            grad.setColorAt(0.0, QColor(tokens["primary"]))
            grad.setColorAt(1.0, QColor(tokens["primary_end"]))
            painter.setBrush(grad)
        else:
            painter.setBrush(QColor(tokens["switch_track_off"]))
        painter.drawRoundedRect(track_rect, radius, radius)

        margin = 3.0
        thumb_d = track_rect.height() - margin * 2.0
        min_x = track_rect.left() + margin
        max_x = track_rect.right() - margin - thumb_d
        x = min_x + (max_x - min_x) * self._thumb_pos
        thumb_rect = QRectF(x, track_rect.top() + margin, thumb_d, thumb_d)

        painter.setBrush(QColor(tokens["switch_thumb"]))
        painter.drawEllipse(thumb_rect)
        painter.end()


class StatusNotificationBanner(QFrame):
    """Floating top-of-screen toast notification for update success or warning states."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("StatusToast")
        self._level = "success"

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(15, 23, 42, 60))
        self.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 12, 12)
        layout.setSpacing(12)

        self.icon_label = QLabel("✓")
        self.icon_label.setObjectName("ToastIcon")
        self.icon_label.setFixedSize(26, 26)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self.title_label = QLabel("")
        self.title_label.setObjectName("ToastTitle")
        self.message_label = QLabel("")
        self.message_label.setObjectName("ToastMessage")
        self.message_label.setWordWrap(True)
        text_col.addWidget(self.title_label)
        text_col.addWidget(self.message_label)

        self.close_btn = QPushButton("×")
        self.close_btn.setObjectName("ToastCloseButton")
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setToolTip("Chiudi notifica")
        self.close_btn.clicked.connect(self.dismiss)

        layout.addWidget(self.icon_label, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(text_col, stretch=1)
        layout.addWidget(self.close_btn, alignment=Qt.AlignmentFlag.AlignTop)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

        self.hide()

    @property
    def level(self) -> str:
        return self._level

    def refresh_style(self) -> None:
        for widget in (self, self.icon_label, self.title_label, self.message_label):
            widget.setProperty("level", self._level)
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def show_message(
        self,
        title: str,
        message: str,
        level: str = "success",
        duration_ms: Optional[int] = None,
    ) -> None:
        normalized = "success" if level == "success" else "warning"
        self._level = normalized
        self.icon_label.setText("✓" if normalized == "success" else "!")
        self.title_label.setText(title)
        self.message_label.setText(message)
        self.refresh_style()

        self.show()
        self.raise_()

        timeout = duration_ms if duration_ms is not None else (6000 if normalized == "success" else 9000)
        self._hide_timer.stop()
        if timeout > 0:
            self._hide_timer.start(timeout)

    def dismiss(self) -> None:
        self._hide_timer.stop()
        self.hide()


class ActiveDownloadBanner(QFrame):
    """Displays the currently updating app, phase, speed, ETA, and intuitive progress bar."""

    IDLE_TITLE = "Nessun download attivo"
    IDLE_DETAIL = (
        "Avvia manualmente un aggiornamento per monitorare avanzamento, velocità e verifica."
    )

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
        title_row.setSpacing(8)
        self.title_label = QLabel(self.IDLE_TITLE)
        self.title_label.setObjectName("BannerTitle")
        self.percent_label = QLabel("0%")
        self.percent_label.setObjectName("PercentBadge")
        title_row.addWidget(self.title_label)
        title_row.addWidget(self.percent_label)
        title_row.addStretch()

        self.detail_label = QLabel(self.IDLE_DETAIL)
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
        self.progress_bar.setFixedWidth(220)

        self.pause_btn = QPushButton("Pausa")
        self.pause_btn.setObjectName("SecondaryButton")
        self.pause_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pause_btn.clicked.connect(on_pause_toggle)
        self.pause_btn.setEnabled(False)

        self.cancel_btn = QPushButton("Annulla")
        self.cancel_btn.setObjectName("SecondaryButton")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(on_cancel)
        self.cancel_btn.setEnabled(False)

        right_col.addWidget(self.progress_bar)
        right_col.addWidget(self.pause_btn)
        right_col.addWidget(self.cancel_btn)

        layout.addLayout(left_col, stretch=1)
        layout.addLayout(right_col)

    def reset(self) -> None:
        """Clear any completed or failed item from the active download section."""
        self._paused = False
        self.title_label.setText(self.IDLE_TITLE)
        self.percent_label.setText("0%")
        self.progress_bar.setValue(0)
        self.detail_label.setText(self.IDLE_DETAIL)
        self.pause_btn.setText("Pausa")
        self.pause_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)

    def update_progress(self, progress: DownloadProgress) -> None:
        if progress.phase in (
            UpdatePhase.IDLE,
            UpdatePhase.COMPLETED,
            UpdatePhase.FAILED,
            UpdatePhase.CANCELLED,
        ):
            self.reset()
            return

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
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(14)

        self.checkbox = ModernCheckBox()
        self.checkbox.setChecked(candidate.selected)
        self.checkbox.stateChanged.connect(
            lambda state: on_selection_change(candidate, state == Qt.CheckState.Checked.value)
        )
        layout.addWidget(self.checkbox)

        avatar = AppAvatarBadge(candidate.name, size=40)
        layout.addWidget(avatar)

        info_col = QVBoxLayout()
        info_col.setSpacing(6)

        category_key = candidate.online.category.value
        category_label = {
            "security": "Sicurezza Critica",
            "features": "Nuove Funzionalità",
            "patch": "Bugfix",
        }.get(category_key, "Aggiornamento")

        header_row = QHBoxLayout()
        header_row.setSpacing(8)
        name_label = QLabel(candidate.name)
        name_label.setObjectName("CardTitle")
        publisher_label = QLabel(f"·  {candidate.app.publisher}")
        publisher_label.setObjectName("MutedText")
        category_pill = QLabel(category_label)
        category_pill.setObjectName("CategoryPill")
        category_pill.setProperty("category", category_key)

        header_row.addWidget(name_label)
        header_row.addWidget(publisher_label)
        header_row.addWidget(category_pill)
        header_row.addStretch()

        version_row = QHBoxLayout()
        version_row.setSpacing(8)
        version_chip = QLabel(
            f"{candidate.app.installed_version}  →  {candidate.online.latest_version}"
        )
        version_chip.setObjectName("MonoVersion")
        version_row.addWidget(version_chip)
        if candidate.online.size_mb:
            size_label = QLabel(f"{candidate.online.size_mb:.1f} MB")
            size_label.setObjectName("MutedText")
            version_row.addWidget(size_label)
        version_row.addStretch()

        notes_label = QLabel(candidate.online.release_notes or "Aggiornamento ufficiale verificato.")
        notes_label.setObjectName("MutedText")
        notes_label.setWordWrap(True)

        info_col.addLayout(header_row)
        info_col.addLayout(version_row)
        info_col.addWidget(notes_label)

        layout.addLayout(info_col, stretch=1)

        # Strictly manual trigger — NO auto-update switch!
        self.update_btn = QPushButton("Aggiorna Ora")
        self.update_btn.setObjectName("PrimaryButton")
        self.update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
        layout.setSpacing(12)

        avatar = AppAvatarBadge(record.app_name, size=34)
        layout.addWidget(avatar)

        name_col = QVBoxLayout()
        name_col.setSpacing(2)
        title = QLabel(f"{record.app_name}  ·  {record.publisher}")
        title.setObjectName("CardTitle")
        meta = QLabel(
            f"v{record.from_version} → v{record.to_version}  ·  "
            f"{record.completed_at}  ·  {record.duration_seconds:.1f}s"
        )
        meta.setObjectName("MutedText")
        name_col.addWidget(title)
        name_col.addWidget(meta)

        status_text = {
            "success": "Completato",
            "failed": f"Fallito ({record.error_message})" if record.error_message else "Fallito",
            "cancelled": "Annullato",
        }.get(record.status, record.status)
        status_label = QLabel(status_text)
        status_label.setObjectName("HistoryStatusBadge")
        status_label.setProperty(
            "status",
            record.status if record.status in ("success", "failed", "cancelled") else "failed",
        )

        layout.addLayout(name_col, stretch=1)
        layout.addWidget(status_label)
