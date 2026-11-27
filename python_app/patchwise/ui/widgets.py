"""Reusable modern animated PySide6 widgets for PatchWise Desktop.

IMPORTANT DESIGN CONSTRAINT:
Auto-update toggles are strictly excluded from all cards and controls.
"""

from __future__ import annotations

import ctypes
import math
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional, Sequence

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSequentialAnimationGroup,
    QSize,
    Qt,
    QTimer,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from patchwise.models import (
    DownloadProgress,
    UpdateCandidate,
    UpdatePhase,
    UpdateRecord,
)
from patchwise.ui.icons import (
    make_alert_icon,
    make_check_icon,
    make_close_icon,
    make_copy_icon,
    make_download_icon,
)
from patchwise.ui.theme import get_theme_qss, get_theme_tokens

_AVATAR_GRADIENTS = (
    ("#0ea5e9", "#685bd9"),  # Logo Cyan -> Violet
    ("#685bd9", "#a451d6"),  # Logo Violet -> Purple
    ("#a451d6", "#e83061"),  # Logo Purple -> Magenta
    ("#06b6d4", "#3b82f6"),  # Electric Cyan -> Blue
    ("#7c3aed", "#ec4899"),  # Deep Violet -> Pink
    ("#0891b2", "#6366f1"),  # Deep Cyan -> Indigo
)


@dataclass(frozen=True)
class NotificationItem:
    """Single feedback notification stored in the in-memory session notification center."""

    title: str
    message: str
    level: str = "success"  # "success" | "warning"
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
    details: str = ""
    category_label: str = ""


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


_RGBA_RE = re.compile(
    r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([0-9.]+)\s*)?\)",
    re.IGNORECASE,
)


def parse_qcolor(value: str) -> QColor:
    """Parse both hex strings (#RRGGBB) and CSS rgba(r, g, b, a) strings into a valid QColor."""
    match = _RGBA_RE.fullmatch(value.strip())
    if match:
        r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
        alpha_raw = match.group(4)
        if alpha_raw is None:
            return QColor(r, g, b)
        alpha_f = float(alpha_raw)
        alpha_int = int(round(alpha_f * 255)) if alpha_f <= 1.0 else int(round(alpha_f))
        return QColor(r, g, b, max(0, min(255, alpha_int)))
    color = QColor(value)
    return color if color.isValid() else QColor("#ffffff")


def _lerp_color(c1: QColor, c2: QColor, t: float) -> QColor:
    clamped = max(0.0, min(1.0, t))
    return QColor(
        int(round(c1.red() + (c2.red() - c1.red()) * clamped)),
        int(round(c1.green() + (c2.green() - c1.green()) * clamped)),
        int(round(c1.blue() + (c2.blue() - c1.blue()) * clamped)),
        int(round(c1.alpha() + (c2.alpha() - c1.alpha()) * clamped)),
    )


class LiquidGlassBackdrop(QWidget):
    """Cached Apple Liquid Glass ambient aurora mesh background (zero per-frame gradient cost)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._theme: str = "light"
        self._cached_bg: Optional[QPixmap] = None
        self._cached_key: tuple[int, int, str, float] = (0, 0, "", 1.0)

    def set_theme(self, theme: str) -> None:
        normalized = "dark" if theme == "dark" else "light"
        if normalized != self._theme:
            self._theme = normalized
            self._cached_bg = None
            self.update()

    def _rebuild_cache(self, width: int, height: int, dpr: float) -> QPixmap:
        pw = max(1, int(round(width * dpr)))
        ph = max(1, int(round(height * dpr)))
        pixmap = QPixmap(pw, ph)
        pixmap.setDevicePixelRatio(dpr)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Base luminous gradient matching the PatchWise logo palette
        base = QLinearGradient(0, 0, width, height)
        if self._theme == "dark":
            base.setColorAt(0.0, QColor("#090717"))
            base.setColorAt(0.45, QColor("#120d29"))
            base.setColorAt(1.0, QColor("#0b1329"))
            orbs = (
                (0.14, 0.16, 0.48, QColor(104, 91, 217, 118), QColor(104, 91, 217, 0)),
                (0.84, 0.14, 0.44, QColor(17, 210, 242, 84), QColor(17, 210, 242, 0)),
                (0.24, 0.86, 0.46, QColor(232, 48, 97, 74), QColor(232, 48, 97, 0)),
                (0.78, 0.80, 0.50, QColor(164, 81, 214, 96), QColor(164, 81, 214, 0)),
                (0.52, 0.48, 0.42, QColor(59, 219, 246, 36), QColor(59, 219, 246, 0)),
            )
        else:
            base.setColorAt(0.0, QColor("#eef1ff"))
            base.setColorAt(0.5, QColor("#f6f1ff"))
            base.setColorAt(1.0, QColor("#e9faff"))
            orbs = (
                (0.14, 0.18, 0.48, QColor(139, 92, 246, 86), QColor(139, 92, 246, 0)),
                (0.85, 0.15, 0.46, QColor(34, 211, 238, 86), QColor(34, 211, 238, 0)),
                (0.22, 0.86, 0.44, QColor(244, 114, 182, 68), QColor(244, 114, 182, 0)),
                (0.80, 0.84, 0.48, QColor(168, 85, 247, 74), QColor(168, 85, 247, 0)),
                (0.52, 0.46, 0.38, QColor(56, 189, 248, 42), QColor(56, 189, 248, 0)),
            )

        painter.fillRect(0, 0, width, height, base)

        max_dim = max(width, height)
        for rx, ry, rr, c_in, c_out in orbs:
            cx = width * rx
            cy = height * ry
            radius = max_dim * rr
            grad = QRadialGradient(QPointF(cx, cy), radius)
            grad.setColorAt(0.0, c_in)
            grad.setColorAt(0.55, QColor(c_in.red(), c_in.green(), c_in.blue(), c_in.alpha() // 3))
            grad.setColorAt(1.0, c_out)
            painter.fillRect(0, 0, width, height, grad)

        painter.end()
        self._cached_bg = pixmap
        self._cached_key = (width, height, self._theme, dpr)
        return pixmap

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return
        dpr = max(1.0, float(self.devicePixelRatioF()))
        if self._cached_bg is None or self._cached_key != (w, h, self._theme, dpr):
            self._rebuild_cache(w, h, dpr)
        painter = QPainter(self)
        if self._cached_bg is not None:
            painter.drawPixmap(0, 0, self._cached_bg)
        painter.end()


class GlassSheetTransitionOverlay(QWidget):
    """Zero-layout 60fps composited slide/unfold overlay for the Liquid Glass updates card.

    Because this overlay lives outside any QLayout and keeps a fixed geometry during the
    entire transition, animating `progress` triggers ZERO layout passes, ZERO QSS gradient
    recalculations, and ZERO QScrollArea re-wraps.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._snapshot: Optional[QPixmap] = None
        self._progress: float = 0.0
        self.hide()

    def set_snapshot(self, pixmap: QPixmap) -> None:
        self._snapshot = pixmap

    def _get_progress(self) -> float:
        return self._progress

    def _set_progress(self, value: float) -> None:
        clamped = max(0.0, min(1.0, float(value)))
        if abs(clamped - self._progress) > 1e-4:
            self._progress = clamped
            self.update()

    progress = Property(float, _get_progress, _set_progress)

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        if self._snapshot is None or self._progress <= 0.005:
            return

        w = float(self.width())
        h = float(self.height())
        if w <= 0 or h <= 0:
            return

        p = self._progress
        # Smooth glass sheet reveal: gentle downward glide + rounded vertical unfold + fade
        y_shift = -18.0 * (1.0 - p)
        reveal_h = max(36.0, h * (0.14 + 0.86 * p))
        opacity = min(1.0, 0.12 + 0.88 * math.pow(p, 0.72))

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setOpacity(opacity)

        clip_rect = QRectF(0.0, max(0.0, y_shift), w, min(h, reveal_h))
        clip_path = QPainterPath()
        clip_path.addRoundedRect(clip_rect, 20.0, 20.0)
        painter.setClipPath(clip_path)

        dpr = self._snapshot.devicePixelRatio() or 1.0
        painter.drawPixmap(
            QRectF(0.0, y_shift, w, h),
            self._snapshot,
            QRectF(0.0, 0.0, self._snapshot.width(), self._snapshot.height()),
        )
        painter.end()


# Backward-compatible alias
AccordionRevealProxy = GlassSheetTransitionOverlay


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
    """Crisp custom-painted checkbox with smooth animated fill and vector checkmark."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(22, 22)
        self._check_progress: float = 0.0
        self._anim = QPropertyAnimation(self, b"check_progress", self)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.toggled.connect(self._on_toggled)

    def _get_check_progress(self) -> float:
        return self._check_progress

    def _set_check_progress(self, value: float) -> None:
        self._check_progress = value
        self.update()

    check_progress = Property(float, _get_check_progress, _set_check_progress)

    def _on_toggled(self, checked: bool) -> None:
        self._anim.stop()
        if not self.isVisible():
            self._check_progress = 1.0 if checked else 0.0
            self.update()
            return
        self._anim.setStartValue(self._check_progress)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def setChecked(self, checked: bool) -> None:  # type: ignore[override]
        was_checked = self.isChecked()
        super().setChecked(checked)
        if not self.isVisible() or self.signalsBlocked() or was_checked == checked:
            self._anim.stop()
            self._check_progress = 1.0 if checked else 0.0
            self.update()

    def sizeHint(self) -> QSize:
        return QSize(22, 22)

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        tokens = get_theme_tokens("dark" if _is_dark_context(self) else "light")
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(2.0, 2.0, 18.0, 18.0)
        p = max(0.0, min(1.0, self._check_progress))

        # Unchecked base box (uses parse_qcolor so rgba() light/dark fills render accurately)
        border_color = tokens["checkbox_hover"] if self.underMouse() else tokens["checkbox_border"]
        pen = QPen(parse_qcolor(border_color))
        pen.setWidthF(1.6)
        painter.setPen(pen)
        painter.setBrush(parse_qcolor(tokens["checkbox_bg"]))
        painter.drawRoundedRect(rect, 5.5, 5.5)

        if p > 0.01:
            painter.save()
            painter.setOpacity(p)
            grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
            grad.setColorAt(0.0, parse_qcolor(tokens["primary"]))
            grad.setColorAt(1.0, parse_qcolor(tokens["primary_end"]))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(grad)
            painter.drawRoundedRect(rect, 5.5, 5.5)

            # Progressive vector checkmark draw
            check_pen = QPen(QColor("#ffffff"))
            check_pen.setWidthF(2.1)
            check_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            check_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(check_pen)

            p0 = QPointF(6.3, 11.2)
            p1 = QPointF(9.5, 14.3)
            p2 = QPointF(15.7, 7.7)
            path = QPainterPath()
            path.moveTo(p0)
            if p <= 0.45:
                t1 = p / 0.45
                path.lineTo(
                    QPointF(p0.x() + (p1.x() - p0.x()) * t1, p0.y() + (p1.y() - p0.y()) * t1)
                )
            else:
                path.lineTo(p1)
                t2 = (p - 0.45) / 0.55
                path.lineTo(
                    QPointF(p1.x() + (p2.x() - p1.x()) * t2, p1.y() + (p2.y() - p1.y()) * t2)
                )
            painter.drawPath(path)
            painter.restore()

        painter.end()


class ModernToggleSwitch(QCheckBox):
    """Silky-smooth animated pill toggle switch with gradual track color morphing."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(46, 24)
        self._thumb_pos: float = 0.0
        self._anim = QPropertyAnimation(self, b"thumb_position", self)
        self._anim.setDuration(320)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.toggled.connect(self._animate_thumb)

    def _get_thumb_position(self) -> float:
        return self._thumb_pos

    def _set_thumb_position(self, value: float) -> None:
        self._thumb_pos = value
        self.update()

    thumb_position = Property(float, _get_thumb_position, _set_thumb_position)

    def _animate_thumb(self, checked: bool) -> None:
        self._anim.stop()
        if not self.isVisible():
            self._thumb_pos = 1.0 if checked else 0.0
            self.update()
            return
        self._anim.setStartValue(self._thumb_pos)
        self._anim.setEndValue(1.0 if checked else 0.0)
        QTimer.singleShot(0, self._anim.start)

    def setChecked(self, checked: bool) -> None:  # type: ignore[override]
        was_checked = self.isChecked()
        super().setChecked(checked)
        if not self.isVisible() or self.signalsBlocked():
            self._anim.stop()
            self._thumb_pos = 1.0 if checked else 0.0
            self.update()
        elif was_checked == checked:
            return

    def hitButton(self, pos) -> bool:  # type: ignore[override]
        return self.rect().contains(pos)

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        tokens = get_theme_tokens("dark" if _is_dark_context(self) else "light")
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        track_rect = QRectF(1.0, 1.0, self.width() - 2.0, self.height() - 2.0)
        radius = track_rect.height() / 2.0
        painter.setPen(Qt.PenStyle.NoPen)

        t = max(0.0, min(1.0, self._thumb_pos))
        off_col = parse_qcolor(tokens["switch_track_off"])
        grad = QLinearGradient(track_rect.topLeft(), track_rect.topRight())
        grad.setColorAt(0.0, _lerp_color(off_col, parse_qcolor(tokens["primary"]), t))
        grad.setColorAt(1.0, _lerp_color(off_col, parse_qcolor(tokens["primary_end"]), t))
        painter.setBrush(grad)
        painter.drawRoundedRect(track_rect, radius, radius)

        # Gentle organic pill glide without abrupt overshoot
        margin = 3.0
        thumb_h = track_rect.height() - margin * 2.0
        stretch = math.sin(t * math.pi) * 1.8
        thumb_w = thumb_h + stretch
        min_x = track_rect.left() + margin
        max_x = track_rect.right() - margin - thumb_w
        x = min_x + (max_x - min_x) * t
        thumb_rect = QRectF(x, track_rect.top() + margin, thumb_w, thumb_h)

        painter.setBrush(parse_qcolor(tokens["switch_thumb"]))
        painter.drawRoundedRect(thumb_rect, thumb_h / 2.0, thumb_h / 2.0)
        painter.end()


class AnimatedChevronButton(QPushButton):
    """Expand/collapse button whose chevron smoothly rotates 180°."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("ExpandButton")
        self.setFixedSize(36, 36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._rotation: float = 0.0
        self._chevron_color: str = "#3d355e"
        self._anim = QPropertyAnimation(self, b"rotation_angle", self)
        self._anim.setDuration(360)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def _get_rotation(self) -> float:
        return self._rotation

    def _set_rotation(self, angle: float) -> None:
        self._rotation = angle
        self.update()

    rotation_angle = Property(float, _get_rotation, _set_rotation)

    def set_chevron_color(self, color: str) -> None:
        self._chevron_color = color
        self.update()

    def set_expanded(self, expanded: bool, animate: bool = True) -> None:
        target = 180.0 if expanded else 0.0
        self._anim.stop()
        if animate and self.isVisible():
            self._anim.setStartValue(self._rotation)
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self._rotation = target
            self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.translate(self.width() / 2.0, self.height() / 2.0)
        painter.rotate(self._rotation)

        pen = QPen(QColor(self._chevron_color))
        pen.setWidthF(1.9)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(QPointF(-4.5, -2.0), QPointF(0.0, 2.5))
        painter.drawLine(QPointF(0.0, 2.5), QPointF(4.5, -2.0))
        painter.end()


class NotificationBellButton(QPushButton):
    """Top-bar notification bell icon button with ring wiggle animation and unread badge."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("IconButton")
        self.setFixedSize(36, 36)
        self.setIconSize(QSize(18, 18))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Notifiche")
        self._unread_count: int = 0
        self._bell_color: str = "#3d355e"
        self._ring_angle: float = 0.0
        self._badge_scale: float = 1.0
        self._ring_group: Optional[QSequentialAnimationGroup] = None
        self._badge_anim = QPropertyAnimation(self, b"badge_scale", self)
        self._badge_anim.setDuration(300)
        self._badge_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _get_ring_angle(self) -> float:
        return self._ring_angle

    def _set_ring_angle(self, angle: float) -> None:
        self._ring_angle = angle
        self.update()

    ring_angle = Property(float, _get_ring_angle, _set_ring_angle)

    def _get_badge_scale(self) -> float:
        return self._badge_scale

    def _set_badge_scale(self, scale: float) -> None:
        self._badge_scale = scale
        self.update()

    badge_scale = Property(float, _get_badge_scale, _set_badge_scale)

    def set_bell_color(self, color: str) -> None:
        self._bell_color = color
        self.update()

    @property
    def unread_count(self) -> int:
        return self._unread_count

    def set_unread_count(self, count: int) -> None:
        previous = self._unread_count
        self._unread_count = max(0, count)
        self.setToolTip(
            f"Notifiche ({self._unread_count} non lette)" if self._unread_count else "Notifiche"
        )
        if self._unread_count > previous and self.isVisible():
            self.trigger_ring_animation()
        else:
            self._badge_scale = 1.0
            self.update()

    def trigger_ring_animation(self) -> None:
        if self._ring_group is not None:
            self._ring_group.stop()
        seq = QSequentialAnimationGroup(self)
        for target, ms in ((11.0, 95), (-9.0, 105), (6.0, 100), (-3.0, 90), (0.0, 85)):
            step = QPropertyAnimation(self, b"ring_angle", seq)
            step.setDuration(ms)
            step.setEndValue(target)
            step.setEasingCurve(QEasingCurve.Type.InOutSine)
            seq.addAnimation(step)
        self._ring_group = seq
        seq.start()

        self._badge_anim.stop()
        self._badge_anim.setStartValue(0.55)
        self._badge_anim.setEndValue(1.0)
        self._badge_anim.start()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Draw crisp vector bell rotated around top pivot for subtle ring animation
        painter.save()
        painter.translate(self.width() / 2.0, self.height() / 2.0 - 5.0)
        painter.rotate(self._ring_angle)
        painter.translate(-9.0, -4.0)

        pen = QPen(QColor(self._bell_color))
        pen.setWidthF(1.7)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        cx = 9.0
        painter.drawLine(QPointF(cx, 2.2), QPointF(cx, 3.6))
        path = QPainterPath()
        path.moveTo(4.0, 12.8)
        path.cubicTo(4.8, 11.4, 5.0, 9.6, 5.0, 7.6)
        path.cubicTo(5.0, 4.9, 6.8, 3.6, cx, 3.6)
        path.cubicTo(11.2, 3.6, 13.0, 4.9, 13.0, 7.6)
        path.cubicTo(13.0, 9.6, 13.2, 11.4, 14.0, 12.8)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawArc(QRectF(cx - 2.0, 12.4, 4.0, 3.2), 190 * 16, 160 * 16)
        painter.restore()

        if self._unread_count <= 0:
            painter.end()
            return

        text = "9+" if self._unread_count > 9 else str(self._unread_count)
        badge_w = 18.0 if len(text) > 1 else 15.0
        badge_h = 15.0
        cx_b = self.width() - badge_w / 2.0 - 1.5
        cy_b = 1.5 + badge_h / 2.0

        painter.save()
        painter.translate(cx_b, cy_b)
        scale = max(0.2, min(1.25, self._badge_scale))
        painter.scale(scale, scale)
        rect = QRectF(-badge_w / 2.0, -badge_h / 2.0, badge_w, badge_h)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#e83061"))
        painter.drawRoundedRect(rect, badge_h / 2.0, badge_h / 2.0)

        font = QFont(self.font())
        font.setPixelSize(9)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()
        painter.end()


class NotificationRowWidget(QFrame):
    """Clickable row inside the NotificationsPopover opening technical details on click."""

    def __init__(
        self,
        item: NotificationItem,
        on_click: Optional[Callable[[NotificationItem], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.item = item
        self._on_click = on_click
        normalized = "success" if item.level == "success" else "warning"
        self.setObjectName("NotificationRow")
        self.setProperty("level", normalized)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Clicca per visualizzare tutti i dettagli")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        icon = QLabel()
        icon.setObjectName("ToastIcon")
        icon.setProperty("level", normalized)
        icon.setFixedSize(22, 22)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_icon = (
            make_check_icon("#ffffff", size=13)
            if normalized == "success"
            else make_alert_icon("#ffffff", size=13)
        )
        icon.setPixmap(badge_icon.pixmap(13, 13))

        col = QVBoxLayout()
        col.setSpacing(3)
        top = QHBoxLayout()
        top.setSpacing(6)
        title_lbl = QLabel(item.title)
        title_lbl.setObjectName("BannerTitle")
        time_lbl = QLabel(item.timestamp)
        time_lbl.setObjectName("MutedText")
        top.addWidget(title_lbl, stretch=1)
        top.addWidget(time_lbl)

        msg_lbl = QLabel(item.message)
        msg_lbl.setObjectName("MutedText")
        msg_lbl.setWordWrap(True)

        col.addLayout(top)
        col.addWidget(msg_lbl)

        if item.details or normalized == "warning":
            hint_text = (
                "Clicca per dettagli e soluzioni ›"
                if normalized == "warning"
                else "Clicca per dettagli ›"
            )
            hint = QLabel(hint_text)
            hint.setObjectName("DetailLinkHint")
            col.addWidget(hint)

        layout.addWidget(icon, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(col, stretch=1)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton and self._on_click is not None:
            self._on_click(self.item)
            event.accept()
            return
        super().mousePressEvent(event)


class NotificationDetailDialog(QDialog):
    """Liquid Glass dialog displaying full error/notification diagnostics and suggested fixes."""

    def __init__(
        self,
        item: NotificationItem,
        theme: str = "light",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.item = item
        self._theme = "dark" if theme == "dark" else "light"
        self.setObjectName("NotificationDetailDialog")
        self.setWindowTitle(f"PatchWise — {item.title}")
        self.setMinimumSize(540, 420)
        self.resize(620, 500)
        self.setModal(True)

        normalized = "success" if item.level == "success" else "warning"

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(12)

        card = QFrame()
        card.setObjectName("DetailCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        icon = QLabel()
        icon.setObjectName("ToastIcon")
        icon.setProperty("level", normalized)
        icon.setFixedSize(30, 30)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dlg_icon = (
            make_check_icon("#ffffff", size=16)
            if normalized == "success"
            else make_alert_icon("#ffffff", size=16)
        )
        icon.setPixmap(dlg_icon.pixmap(16, 16))

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self.title_label = QLabel(item.title)
        self.title_label.setObjectName("SectionTitle")
        meta_parts = [item.timestamp]
        if item.category_label:
            meta_parts.append(item.category_label)
        self.meta_label = QLabel("  ·  ".join(meta_parts))
        self.meta_label.setObjectName("MutedText")
        title_col.addWidget(self.title_label)
        title_col.addWidget(self.meta_label)

        header_row.addWidget(icon, alignment=Qt.AlignmentFlag.AlignTop)
        header_row.addLayout(title_col, stretch=1)
        card_layout.addLayout(header_row)

        self.summary_label = QLabel(item.message)
        self.summary_label.setObjectName("BannerTitle")
        self.summary_label.setWordWrap(True)
        self.summary_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        card_layout.addWidget(self.summary_label)

        detail_heading = QLabel("Dettagli tecnici e azioni consigliate")
        detail_heading.setObjectName("NavGroupLabel")
        card_layout.addWidget(detail_heading)

        self.details_box = QTextEdit()
        self.details_box.setObjectName("DetailLogBox")
        self.details_box.setReadOnly(True)
        body_text = item.details.strip() if item.details.strip() else (
            f"Titolo: {item.title}\n"
            f"Orario: {item.timestamp}\n"
            f"Esito: {'Completato' if normalized == 'success' else 'Avviso / Errore'}\n\n"
            f"{item.message}"
        )
        self.details_box.setPlainText(body_text)
        card_layout.addWidget(self.details_box, stretch=1)

        footer = QHBoxLayout()
        footer.setSpacing(10)
        footer.addStretch()

        tokens = get_theme_tokens(self._theme)
        self._copy_icon = make_copy_icon(tokens["icon_color"], size=15)
        self._copied_icon = make_check_icon("#10b981", size=15)

        self.copy_btn = QPushButton("Copia dettagli")
        self.copy_btn.setObjectName("SecondaryButton")
        self.copy_btn.setIcon(self._copy_icon)
        self.copy_btn.setIconSize(QSize(15, 15))
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.clicked.connect(self._copy_details)

        self._copy_reset_timer = QTimer(self)
        self._copy_reset_timer.setSingleShot(True)
        self._copy_reset_timer.timeout.connect(self._reset_copy_button)

        self.close_btn = QPushButton("Chiudi")
        self.close_btn.setObjectName("PrimaryButton")
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.accept)

        footer.addWidget(self.copy_btn)
        footer.addWidget(self.close_btn)
        card_layout.addLayout(footer)

        outer.addWidget(card, stretch=1)
        self.setStyleSheet(get_theme_qss(self._theme))
        self._apply_windows_titlebar_theme(self._theme == "dark")

    def _copy_details(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self.details_box.toPlainText())
        self.copy_btn.setIcon(self._copied_icon)
        self.copy_btn.setText("Copiato")
        self._copy_reset_timer.start(1800)

    def _reset_copy_button(self) -> None:
        self.copy_btn.setIcon(self._copy_icon)
        self.copy_btn.setText("Copia dettagli")

    def _apply_windows_titlebar_theme(self, dark: bool) -> None:
        if not sys.platform.startswith("win"):
            return
        try:
            hwnd = int(self.winId())
            value = ctypes.c_int(1 if dark else 0)
            dwm = ctypes.windll.dwmapi  # type: ignore[attr-defined]
            dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
        except Exception:  # noqa: BLE001
            pass


class NotificationsPopover(QFrame):
    """Floating notification center panel with smooth slide-down reveal."""

    def __init__(
        self,
        on_clear: Callable[[], None],
        on_select: Optional[Callable[[NotificationItem], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._on_select = on_select
        self.setObjectName("NotificationsPopover")
        self.setFixedWidth(396)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(14, 11, 29, 85))
        self.setGraphicsEffect(shadow)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(8)
        title = QLabel("Notifiche")
        title.setObjectName("SectionTitle")
        self.count_badge = QLabel("0")
        self.count_badge.setObjectName("StatChip")

        self.clear_btn = QPushButton("Pulisci")
        self.clear_btn.setObjectName("GhostLinkButton")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(on_clear)

        self.close_btn = QPushButton()
        self.close_btn.setObjectName("ToastCloseButton")
        self.close_btn.setFixedSize(26, 26)
        self.close_btn.setIconSize(QSize(12, 12))
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setToolTip("Chiudi notifiche")
        self.close_btn.clicked.connect(self.hide)
        self._update_close_icon()

        header.addWidget(title)
        header.addWidget(self.count_badge)
        header.addStretch()
        header.addWidget(self.clear_btn)
        header.addWidget(self.close_btn)
        root.addLayout(header)

        divider = QFrame()
        divider.setObjectName("SidebarDivider")
        root.addWidget(divider)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setMaximumHeight(360)
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 2, 4, 2)
        self.list_layout.setSpacing(8)
        self.scroll.setWidget(self.list_container)
        root.addWidget(self.scroll)

        self._slide_anim = QPropertyAnimation(self, b"pos", self)
        self._slide_anim.setDuration(290)
        self._slide_anim.setEasingCurve(QEasingCurve.Type.OutQuart)

        self._items: list[NotificationItem] = []
        self._row_widgets: list[NotificationRowWidget] = []
        self.set_notifications([])
        self.hide()

    @property
    def row_widgets(self) -> list[NotificationRowWidget]:
        return list(self._row_widgets)

    def animate_open(self, target_pos: QPoint) -> None:
        self._slide_anim.stop()
        parent = self.parentWidget()
        if parent is not None and parent.isVisible():
            self.move(QPoint(target_pos.x(), max(6, target_pos.y() - 16)))
            self.show()
            self.raise_()
            self._slide_anim.setStartValue(self.pos())
            self._slide_anim.setEndValue(target_pos)
            QTimer.singleShot(0, self._slide_anim.start)
        else:
            self.move(target_pos)
            self.show()
            self.raise_()

    def set_notifications(self, items: Sequence[NotificationItem]) -> None:
        self._items = list(items)
        self._row_widgets = []
        self.count_badge.setText(str(len(self._items)))
        self.clear_btn.setEnabled(bool(self._items))

        while self.list_layout.count():
            child = self.list_layout.takeAt(0)
            widget = child.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

        if not self._items:
            empty = QLabel("Nessuna notifica in questa sessione.")
            empty.setObjectName("MutedText")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setContentsMargins(12, 26, 12, 26)
            self.list_layout.addWidget(empty)
            self.scroll.setFixedHeight(90)
        else:
            for item in self._items:
                row = NotificationRowWidget(item, on_click=self._on_select)
                self._row_widgets.append(row)
                self.list_layout.addWidget(row)
            desired_h = min(350, max(106, len(self._items) * 96 + 14))
            self.scroll.setFixedHeight(desired_h)

        self.list_layout.addStretch()
        self.adjustSize()

    def _update_close_icon(self) -> None:
        theme = "dark" if _is_dark_context(self) else "light"
        color = get_theme_tokens(theme)["toast_close_text"]
        self.close_btn.setIcon(make_close_icon(color, size=12))

    def refresh_style(self) -> None:
        self._update_close_icon()
        self.set_notifications(self._items)
        self.style().unpolish(self)
        self.style().polish(self)


class StatusNotificationBanner(QFrame):
    """Discreet bottom-right toast notification with smooth slide-in entrance and click-to-inspect."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        on_click: Optional[Callable[[NotificationItem], None]] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("StatusToast")
        self._level = "success"
        self._on_click = on_click
        self._current_item: Optional[NotificationItem] = None

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(15, 23, 42, 65))
        self.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 12, 12)
        layout.setSpacing(12)

        self.icon_label = QLabel()
        self.icon_label.setObjectName("ToastIcon")
        self.icon_label.setFixedSize(26, 26)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setPixmap(make_check_icon("#ffffff", size=14).pixmap(14, 14))

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self.title_label = QLabel("")
        self.title_label.setObjectName("ToastTitle")
        self.message_label = QLabel("")
        self.message_label.setObjectName("ToastMessage")
        self.message_label.setWordWrap(True)
        self.hint_label = QLabel("Clicca per visualizzare i dettagli ›")
        self.hint_label.setObjectName("DetailLinkHint")
        self.hint_label.hide()
        text_col.addWidget(self.title_label)
        text_col.addWidget(self.message_label)
        text_col.addWidget(self.hint_label)

        self.close_btn = QPushButton()
        self.close_btn.setObjectName("ToastCloseButton")
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setIconSize(QSize(12, 12))
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setToolTip("Chiudi notifica")
        self.close_btn.clicked.connect(self.dismiss)
        self._update_close_icon()

        layout.addWidget(self.icon_label, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(text_col, stretch=1)
        layout.addWidget(self.close_btn, alignment=Qt.AlignmentFlag.AlignTop)

        self._slide_anim = QPropertyAnimation(self, b"pos", self)
        self._slide_anim.setDuration(330)
        self._slide_anim.setEasingCurve(QEasingCurve.Type.OutQuart)
        self._slide_start_timer = QTimer(self)
        self._slide_start_timer.setSingleShot(True)
        self._slide_start_timer.timeout.connect(self._slide_anim.start)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.dismiss)

        self.hide()

    @property
    def level(self) -> str:
        return self._level

    def _update_close_icon(self) -> None:
        theme = "dark" if _is_dark_context(self) else "light"
        color = get_theme_tokens(theme)["toast_close_text"]
        self.close_btn.setIcon(make_close_icon(color, size=12))

    def refresh_style(self) -> None:
        self._update_close_icon()
        for widget in (self, self.icon_label, self.title_label, self.message_label):
            widget.setProperty("level", self._level)
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def slide_to(self, target_pos: QPoint, animate: bool = True) -> None:
        self._slide_start_timer.stop()
        self._slide_anim.stop()
        parent = self.parentWidget()
        if animate and parent is not None and parent.isVisible():
            start_pos = QPoint(target_pos.x() + 36, target_pos.y())
            self.move(start_pos)
            self._slide_anim.setStartValue(start_pos)
            self._slide_anim.setEndValue(target_pos)
            self._slide_start_timer.start(0)
        else:
            self.move(target_pos)
        self.raise_()

    def show_message(
        self,
        title: str,
        message: str,
        level: str = "success",
        duration_ms: Optional[int] = None,
        item: Optional[NotificationItem] = None,
    ) -> None:
        normalized = "success" if level == "success" else "warning"
        self._level = normalized
        self._current_item = item or NotificationItem(
            title=title, message=message, level=normalized
        )
        toast_icon = (
            make_check_icon("#ffffff", size=14)
            if normalized == "success"
            else make_alert_icon("#ffffff", size=14)
        )
        self.icon_label.setPixmap(toast_icon.pixmap(14, 14))
        self.title_label.setText(title)
        self.message_label.setText(message)
        show_hint = bool(
            self._on_click is not None
            and (normalized == "warning" or bool(self._current_item.details))
        )
        self.hint_label.setVisible(show_hint)
        self.setCursor(
            Qt.CursorShape.PointingHandCursor
            if self._on_click is not None
            else Qt.CursorShape.ArrowCursor
        )
        self.refresh_style()

        self.show()
        self.raise_()

        timeout = duration_ms if duration_ms is not None else (4500 if normalized == "success" else 7500)
        self._hide_timer.stop()
        if timeout > 0:
            self._hide_timer.start(timeout)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._on_click is not None
            and self._current_item is not None
        ):
            target = self._current_item
            self.dismiss()
            self._on_click(target)
            event.accept()
            return
        super().mousePressEvent(event)

    def dismiss(self) -> None:
        self._hide_timer.stop()
        self._slide_start_timer.stop()
        self._slide_anim.stop()
        self.hide()


class ActiveDownloadBanner(QFrame):
    """Standalone download progress section with smooth bar animation, visible only when active."""

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
        layout.setContentsMargins(18, 15, 18, 15)
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

        self._bar_anim = QPropertyAnimation(self.progress_bar, b"value", self)
        self._bar_anim.setDuration(420)
        self._bar_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._reveal_anim = QPropertyAnimation(self, b"maximumHeight", self)
        self._reveal_anim.setDuration(340)
        self._reveal_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._reveal_anim.finished.connect(self._on_reveal_finished)

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

        # Hidden by default — displayed only while a download/update is running
        self.hide()

    def _on_reveal_finished(self) -> None:
        if self.isVisible():
            self.setMaximumHeight(16777215)

    def reset(self) -> None:
        """Clear any completed or failed item and hide the download section."""
        self._paused = False
        self._bar_anim.stop()
        self._reveal_anim.stop()
        self.setMaximumHeight(16777215)
        self.title_label.setText(self.IDLE_TITLE)
        self.percent_label.setText("0%")
        self.progress_bar.setValue(0)
        self.detail_label.setText(self.IDLE_DETAIL)
        self.pause_btn.setText("Pausa")
        self.pause_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.hide()

    def update_progress(self, progress: DownloadProgress) -> None:
        if progress.phase in (
            UpdatePhase.IDLE,
            UpdatePhase.COMPLETED,
            UpdatePhase.FAILED,
            UpdatePhase.CANCELLED,
        ):
            self.reset()
            return

        was_hidden = self.isHidden()
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
        target_pct = max(0, min(100, int(round(progress.percent))))
        self.percent_label.setText(f"{target_pct}%")

        metrics = []
        if progress.total_mb > 0:
            metrics.append(f"{progress.downloaded_mb:.1f} MB di {progress.total_mb:.1f} MB")
        if progress.speed_mbps > 0 and progress.phase == UpdatePhase.DOWNLOADING:
            metrics.append(f"{progress.speed_mbps:.1f} MB/s")
        if progress.eta_seconds is not None and progress.phase == UpdatePhase.DOWNLOADING:
            metrics.append(f"circa {progress.eta_seconds} sec. rimasti")

        suffix = f" ({' · '.join(metrics)})" if metrics else ""
        self.detail_label.setText(f"{progress.message}{suffix}")

        parent = self.parentWidget()
        if was_hidden and parent is not None and parent.isVisible():
            self._reveal_anim.stop()
            self.setMaximumHeight(16777215)
            target_h = max(76, self.sizeHint().height())
            self.setMaximumHeight(0)
            self.show()
            self._reveal_anim.setStartValue(0)
            self._reveal_anim.setEndValue(target_h)
            self._reveal_anim.start()
            self.progress_bar.setValue(target_pct)
        else:
            self.show()
            if self.isVisible() and not was_hidden and self.progress_bar.value() != target_pct:
                self._bar_anim.stop()
                self._bar_anim.setStartValue(self.progress_bar.value())
                self._bar_anim.setEndValue(target_pct)
                self._bar_anim.start()
            else:
                self._bar_anim.stop()
                self.progress_bar.setValue(target_pct)


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
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)

        self.checkbox = ModernCheckBox()
        self.checkbox.setChecked(candidate.selected)
        self.checkbox.stateChanged.connect(
            lambda state: on_selection_change(candidate, state == Qt.CheckState.Checked.value)
        )
        layout.addWidget(self.checkbox)

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
        self._download_icon = make_download_icon("#ffffff", size=14)
        self.update_btn = QPushButton("Aggiorna")
        self.update_btn.setObjectName("PrimaryButton")
        self.update_btn.setIcon(self._download_icon)
        self.update_btn.setIconSize(QSize(14, 14))
        self.update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_btn.clicked.connect(lambda: on_update_click(candidate))
        layout.addWidget(self.update_btn)

    def set_updating_state(self, phase: UpdatePhase) -> None:
        if phase in (UpdatePhase.DOWNLOADING, UpdatePhase.VERIFYING, UpdatePhase.INSTALLING):
            self.update_btn.setEnabled(False)
            self.update_btn.setIcon(QIcon())
            self.update_btn.setText("In corso...")
            self.checkbox.setEnabled(False)
        elif phase == UpdatePhase.COMPLETED:
            self.update_btn.setEnabled(False)
            self.update_btn.setIcon(QIcon())
            self.update_btn.setText("Aggiornato")
            self.checkbox.setEnabled(False)
        else:
            self.update_btn.setEnabled(True)
            self.update_btn.setIcon(self._download_icon)
            self.update_btn.setText("Aggiorna")
            self.checkbox.setEnabled(True)


class HistoryRowWidget(QFrame):
    """Single row in the stateless session update history view."""

    def __init__(
        self,
        record: UpdateRecord,
        on_inspect: Optional[Callable[[UpdateRecord], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._record = record
        self._on_inspect = on_inspect
        self.setObjectName("Card")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        name_col = QVBoxLayout()
        name_col.setSpacing(2)
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title = QLabel(f"{record.app_name}  ·  {record.publisher}")
        title.setObjectName("CardTitle")
        type_badge = QLabel("Driver" if record.item_type == "driver" else "App")
        type_badge.setObjectName("HistoryTypeBadge")
        type_badge.setProperty(
            "item_type", "driver" if record.item_type == "driver" else "app"
        )
        title_row.addWidget(title)
        title_row.addWidget(type_badge)
        title_row.addStretch()

        meta = QLabel(
            f"v{record.from_version} → v{record.to_version}  ·  "
            f"{record.completed_at}  ·  {record.duration_seconds:.1f}s"
        )
        meta.setObjectName("MutedText")
        name_col.addLayout(title_row)
        name_col.addWidget(meta)

        if record.status == "failed" and record.error_message:
            err_preview = QLabel(record.error_message)
            err_preview.setObjectName("MutedText")
            err_preview.setWordWrap(True)
            name_col.addWidget(err_preview)

        status_text = {
            "success": "Completato",
            "failed": "Fallito",
            "cancelled": "Annullato",
        }.get(record.status, record.status)
        status_label = QLabel(status_text)
        status_label.setObjectName("HistoryStatusBadge")
        status_label.setProperty(
            "status",
            record.status if record.status in ("success", "failed", "cancelled") else "failed",
        )

        layout.addLayout(name_col, stretch=1)
        layout.addWidget(status_label, alignment=Qt.AlignmentFlag.AlignVCenter)

        if on_inspect is not None and (record.status == "failed" or record.error_details):
            self.details_btn = QPushButton("Dettagli")
            self.details_btn.setObjectName("GhostLinkButton")
            self.details_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.details_btn.clicked.connect(lambda: on_inspect(record))
            layout.addWidget(self.details_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._on_inspect is not None
            and (self._record.status == "failed" or self._record.error_details)
        ):
            self._on_inspect(self._record)
            event.accept()
            return
        super().mousePressEvent(event)
