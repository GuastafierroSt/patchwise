"""Crisp HiDPI vector icons rendered with QPainter (zero external asset files required)."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


def resolve_asset_path(filename: str) -> Path:
    """Resolve a bundled asset path in both development and PyInstaller --onefile builds."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_dir = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base_dir = Path(__file__).resolve().parents[2]
    return base_dir / "assets" / filename


def load_brand_pixmap(size: int = 40) -> QPixmap:
    """Load the official PatchWise logo as a crisp HiDPI pixmap."""
    png_path = resolve_asset_path("patchwise.png")
    ico_path = resolve_asset_path("patchwise.ico")
    source = png_path if png_path.exists() else ico_path
    if source.exists():
        raw = QPixmap(str(source))
        if not raw.isNull():
            scale = 2
            scaled = raw.scaled(
                size * scale,
                size * scale,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            scaled.setDevicePixelRatio(scale)
            return scaled
    # Fallback monogram if asset file is absent
    pixmap, painter = _make_canvas(size)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#685bd9"))
    painter.drawRoundedRect(QRectF(0, 0, size, size), 10, 10)
    painter.end()
    return pixmap


def load_app_icon() -> QIcon:
    """Load the PatchWise window/taskbar QIcon from bundled ICO/PNG assets."""
    ico_path = resolve_asset_path("patchwise.ico")
    if ico_path.exists():
        icon = QIcon(str(ico_path))
        if not icon.isNull():
            return icon
    png_path = resolve_asset_path("patchwise.png")
    if png_path.exists():
        icon = QIcon(str(png_path))
        if not icon.isNull():
            return icon
    return QIcon(load_brand_pixmap(64))


def _make_canvas(size: int) -> tuple[QPixmap, QPainter]:
    scale = 2  # 2x HiDPI rendering for sharp edges
    pixmap = QPixmap(size * scale, size * scale)
    pixmap.setDevicePixelRatio(scale)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    return pixmap, painter


def _stroke_pen(color: str, width: float = 1.8) -> QPen:
    pen = QPen(QColor(color))
    pen.setWidthF(width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def make_sidebar_toggle_icon(color: str, sidebar_open: bool = True, size: int = 18) -> QIcon:
    """Draw a modern sidebar panel-toggle icon."""
    pixmap, painter = _make_canvas(size)
    painter.setPen(_stroke_pen(color, 1.7))
    painter.setBrush(Qt.BrushStyle.NoBrush)

    outer = QRectF(2.2, 3.0, size - 4.4, size - 6.0)
    painter.drawRoundedRect(outer, 3.0, 3.0)

    divider_x = 7.2
    painter.drawLine(QPointF(divider_x, 3.2), QPointF(divider_x, size - 3.2))

    if sidebar_open:
        # Subtle filled left rail indicator when open
        fill = QColor(color)
        fill.setAlpha(45)
        painter.fillRect(QRectF(3.0, 3.8, divider_x - 3.6, size - 7.6), fill)
        # Small left chevron on the right pane
        painter.drawLine(QPointF(12.8, 7.2), QPointF(10.6, size / 2.0))
        painter.drawLine(QPointF(10.6, size / 2.0), QPointF(12.8, size - 7.2))
    else:
        # Small right chevron indicating open action
        painter.drawLine(QPointF(10.6, 7.2), QPointF(12.8, size / 2.0))
        painter.drawLine(QPointF(12.8, size / 2.0), QPointF(10.6, size - 7.2))

    painter.end()
    return QIcon(pixmap)


def make_dashboard_icon(color: str, size: int = 16) -> QIcon:
    """Draw a clean 4-tile dashboard grid icon."""
    pixmap, painter = _make_canvas(size)
    painter.setPen(_stroke_pen(color, 1.6))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    gap = 2.2
    tile = (size - 4.0 - gap) / 2.0
    for row in range(2):
        for col in range(2):
            rect = QRectF(2.0 + col * (tile + gap), 2.0 + row * (tile + gap), tile, tile)
            painter.drawRoundedRect(rect, 1.8, 1.8)
    painter.end()
    return QIcon(pixmap)


def make_history_icon(color: str, size: int = 16) -> QIcon:
    """Draw a crisp clock/session-history icon."""
    pixmap, painter = _make_canvas(size)
    painter.setPen(_stroke_pen(color, 1.6))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(QRectF(2.2, 2.2, size - 4.4, size - 4.4))
    cx, cy = size / 2.0, size / 2.0
    painter.drawLine(QPointF(cx, cy), QPointF(cx, 5.2))
    painter.drawLine(QPointF(cx, cy), QPointF(cx + 3.0, cy + 1.8))
    painter.end()
    return QIcon(pixmap)


def make_refresh_icon(color: str, size: int = 16) -> QIcon:
    """Draw a sleek circular scan/refresh icon."""
    pixmap, painter = _make_canvas(size)
    painter.setPen(_stroke_pen(color, 1.7))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    rect = QRectF(2.6, 2.6, size - 5.2, size - 5.2)
    painter.drawArc(rect, 35 * 16, 290 * 16)
    # Arrowhead at top-right
    painter.drawLine(QPointF(size - 3.6, 3.0), QPointF(size - 3.0, 6.2))
    painter.drawLine(QPointF(size - 6.2, 5.6), QPointF(size - 3.0, 6.2))
    painter.end()
    return QIcon(pixmap)


def make_download_icon(color: str, size: int = 16) -> QIcon:
    """Draw a minimalist download/update arrow icon."""
    pixmap, painter = _make_canvas(size)
    painter.setPen(_stroke_pen(color, 1.7))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    cx = size / 2.0
    painter.drawLine(QPointF(cx, 2.6), QPointF(cx, 10.2))
    painter.drawLine(QPointF(cx - 3.2, 7.2), QPointF(cx, 10.4))
    painter.drawLine(QPointF(cx + 3.2, 7.2), QPointF(cx, 10.4))
    path = QPainterPath()
    path.moveTo(2.8, 10.8)
    path.lineTo(2.8, 12.6)
    path.quadTo(2.8, 13.4, 3.8, 13.4)
    path.lineTo(size - 3.8, 13.4)
    path.quadTo(size - 2.8, 13.4, size - 2.8, 12.6)
    path.lineTo(size - 2.8, 10.8)
    painter.drawPath(path)
    painter.end()
    return QIcon(pixmap)


def make_theme_icon(color: str, dark_mode: bool, size: int = 16) -> QIcon:
    """Draw a crescent moon (dark) or clean sun (light) icon."""
    pixmap, painter = _make_canvas(size)
    painter.setPen(_stroke_pen(color, 1.6))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    if dark_mode:
        path = QPainterPath()
        path.addEllipse(QRectF(2.8, 2.6, 10.4, 10.8))
        cut = QPainterPath()
        cut.addEllipse(QRectF(6.8, 1.6, 8.8, 8.8))
        crescent = path.subtracted(cut)
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(crescent)
    else:
        cx, cy = size / 2.0, size / 2.0
        painter.drawEllipse(QRectF(cx - 2.8, cy - 2.8, 5.6, 5.6))
        for dx, dy in (
            (0, -1),
            (0, 1),
            (-1, 0),
            (1, 0),
            (-0.7, -0.7),
            (0.7, -0.7),
            (-0.7, 0.7),
            (0.7, 0.7),
        ):
            painter.drawLine(
                QPointF(cx + dx * 4.5, cy + dy * 4.5),
                QPointF(cx + dx * 6.0, cy + dy * 6.0),
            )
    painter.end()
    return QIcon(pixmap)


def make_bell_icon(color: str, size: int = 18) -> QIcon:
    """Draw a sleek notification bell vector icon."""
    pixmap, painter = _make_canvas(size)
    painter.setPen(_stroke_pen(color, 1.7))
    painter.setBrush(Qt.BrushStyle.NoBrush)

    cx = size / 2.0
    # Top stem
    painter.drawLine(QPointF(cx, 2.2), QPointF(cx, 3.6))
    # Bell dome
    path = QPainterPath()
    path.moveTo(4.0, 12.8)
    path.cubicTo(4.8, 11.4, 5.0, 9.6, 5.0, 7.6)
    path.cubicTo(5.0, 4.9, 6.8, 3.6, cx, 3.6)
    path.cubicTo(11.2, 3.6, 13.0, 4.9, 13.0, 7.6)
    path.cubicTo(13.0, 9.6, 13.2, 11.4, 14.0, 12.8)
    path.closeSubpath()
    painter.drawPath(path)

    # Bottom clapper arc
    painter.drawArc(QRectF(cx - 2.0, 12.4, 4.0, 3.2), 190 * 16, 160 * 16)
    painter.end()
    return QIcon(pixmap)


def make_chevron_icon(color: str, expanded: bool = False, size: int = 16) -> QIcon:
    """Draw an expand (down) or collapse (up) chevron vector icon."""
    pixmap, painter = _make_canvas(size)
    painter.setPen(_stroke_pen(color, 1.9))
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if expanded:
        painter.drawLine(QPointF(4.0, 10.2), QPointF(size / 2.0, 5.8))
        painter.drawLine(QPointF(size / 2.0, 5.8), QPointF(size - 4.0, 10.2))
    else:
        painter.drawLine(QPointF(4.0, 5.8), QPointF(size / 2.0, 10.2))
        painter.drawLine(QPointF(size / 2.0, 10.2), QPointF(size - 4.0, 5.8))
    painter.end()
    return QIcon(pixmap)
