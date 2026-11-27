"""Main desktop window class for PatchWise Software Updater."""

from __future__ import annotations

import ctypes
import sys
from typing import Dict, List, Optional

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    QTimer,
)
from PySide6.QtGui import QCloseEvent, QKeyEvent, QPixmap, QRegion, QResizeEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from patchwise import __version__
from patchwise.core.controller import UpdateManagerController
from patchwise.models import DownloadProgress, UpdateCandidate, UpdatePhase, UpdateRecord
from patchwise.ui.icons import (
    load_app_icon,
    load_brand_pixmap,
    make_dashboard_icon,
    make_download_icon,
    make_history_icon,
    make_refresh_icon,
    make_sidebar_toggle_icon,
    make_theme_icon,
)
from patchwise.ui.theme import get_theme_qss, get_theme_tokens
from patchwise.ui.widgets import (
    ActiveDownloadBanner,
    AnimatedChevronButton,
    AppUpdateCard,
    GlassSheetTransitionOverlay,
    HistoryRowWidget,
    LiquidGlassBackdrop,
    ModernToggleSwitch,
    NotificationBellButton,
    NotificationItem,
    NotificationsPopover,
    StatusNotificationBanner,
)
from patchwise.ui.workers import ScanWorker, UpdateWorker


class PatchWiseMainWindow(QMainWindow):
    """Primary PySide6 desktop shell coordinating scan, updates, progress, and session history."""

    SIDEBAR_WIDTH = 268
    MAX_NOTIFICATIONS = 50

    def __init__(self, controller: Optional[UpdateManagerController] = None) -> None:
        super().__init__()
        self.controller = controller or UpdateManagerController()
        self._scan_worker: Optional[ScanWorker] = None
        self._update_worker: Optional[UpdateWorker] = None
        self._card_map: Dict[str, AppUpdateCard] = {}
        self._pending_rescan: bool = False
        self._theme: str = "light"
        self._sidebar_open: bool = True
        self._updates_expanded: bool = False
        self._sidebar_anim: Optional[QPropertyAnimation] = None
        self._updates_anim: Optional[QPropertyAnimation] = None
        self._updates_anim_timer = QTimer(self)
        self._updates_anim_timer.setSingleShot(True)
        self._updates_anim_timer.timeout.connect(self._start_pending_updates_anim)
        self._page_fade_anim: Optional[QPropertyAnimation] = None
        self._theme_fade_overlay: Optional[QLabel] = None
        self._theme_fade_anim: Optional[QPropertyAnimation] = None
        self._notifications: List[NotificationItem] = []

        self.setWindowTitle(f"PatchWise Desktop — Software Updater v{__version__} (Portable)")
        self.setWindowIcon(load_app_icon())
        self.resize(1240, 820)

        self._build_layout()
        self.notification_banner = StatusNotificationBanner(self)
        self.notifications_popover = NotificationsPopover(
            on_clear=self.clear_notifications,
            parent=self,
        )
        self.set_theme("light", animate=False)
        self._refresh_history_views()
        self._refresh_summary_chips()
        self._refresh_selection_controls()

    @property
    def current_theme(self) -> str:
        return self._theme

    @property
    def is_sidebar_open(self) -> bool:
        return self._sidebar_open

    @property
    def is_updates_expanded(self) -> bool:
        return self._updates_expanded

    @property
    def notification_items(self) -> List[NotificationItem]:
        return list(self._notifications)

    def _build_layout(self) -> None:
        self._glass_root = LiquidGlassBackdrop()
        self.setCentralWidget(self._glass_root)
        outer = QHBoxLayout(self._glass_root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Collapsible sidebar navigation with fixed-width inner content (zero reflow/squish)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(self.SIDEBAR_WIDTH)
        sidebar_clip_layout = QHBoxLayout(self.sidebar)
        sidebar_clip_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_clip_layout.setSpacing(0)

        self._sidebar_content = QWidget()
        self._sidebar_content.setObjectName("TransparentContainer")
        self._sidebar_content.setFixedWidth(self.SIDEBAR_WIDTH)
        sidebar_clip_layout.addWidget(self._sidebar_content, alignment=Qt.AlignmentFlag.AlignLeft)

        sb_layout = QVBoxLayout(self._sidebar_content)
        sb_layout.setContentsMargins(16, 20, 16, 18)
        sb_layout.setSpacing(10)

        # Brand identity row with official PatchWise hexagon logo
        brand_row = QHBoxLayout()
        brand_row.setSpacing(11)
        self.brand_logo = QLabel()
        self.brand_logo.setObjectName("BrandLogo")
        self.brand_logo.setFixedSize(42, 42)
        self.brand_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.brand_logo.setPixmap(load_brand_pixmap(42))

        brand_text_col = QVBoxLayout()
        brand_text_col.setSpacing(1)
        brand = QLabel("PatchWise")
        brand.setObjectName("BrandTitle")
        subtitle = QLabel("Portable Software Updater")
        subtitle.setObjectName("MutedText")
        brand_text_col.addWidget(brand)
        brand_text_col.addWidget(subtitle)

        brand_row.addWidget(self.brand_logo)
        brand_row.addLayout(brand_text_col)
        brand_row.addStretch()
        sb_layout.addLayout(brand_row)

        top_divider = QFrame()
        top_divider.setObjectName("SidebarDivider")
        sb_layout.addSpacing(4)
        sb_layout.addWidget(top_divider)
        sb_layout.addSpacing(6)

        nav_heading = QLabel("NAVIGAZIONE")
        nav_heading.setObjectName("NavGroupLabel")
        sb_layout.addWidget(nav_heading)

        self.nav_dashboard = self._make_nav_button("Dashboard && Aggiornamenti", 0, active=True)
        self.nav_history = self._make_nav_button("Cronologia di Sessione", 1, active=False)
        sb_layout.addWidget(self.nav_dashboard)
        sb_layout.addWidget(self.nav_history)
        sb_layout.addStretch()

        bottom_divider = QFrame()
        bottom_divider.setObjectName("SidebarDivider")
        sb_layout.addWidget(bottom_divider)
        sb_layout.addSpacing(4)

        # Direct Dark/Light theme switcher card inside sidebar
        theme_card = QFrame()
        theme_card.setObjectName("ThemeSwitchCard")
        theme_layout = QHBoxLayout(theme_card)
        theme_layout.setContentsMargins(12, 10, 12, 10)
        theme_layout.setSpacing(10)

        self.theme_icon_label = QLabel()
        self.theme_icon_label.setFixedSize(18, 18)
        self.theme_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.theme_icon_label.setStyleSheet("background: transparent;")

        self.theme_label = QLabel("Usa tema scuro")
        self.theme_label.setObjectName("ThemeSwitchLabel")

        self.dark_theme_toggle = ModernToggleSwitch()
        self.dark_theme_toggle.setToolTip("Passa tra tema chiaro e tema scuro")
        self.dark_theme_toggle.toggled.connect(self._on_dark_theme_toggled)

        theme_layout.addWidget(self.theme_icon_label)
        theme_layout.addWidget(self.theme_label, stretch=1)
        theme_layout.addWidget(self.dark_theme_toggle)
        sb_layout.addWidget(theme_card)

        # Right side: persistent TopBar + content stack over Liquid Glass backdrop
        self.right_container = QWidget()
        self.right_container.setObjectName("TransparentContainer")
        right_layout = QVBoxLayout(self.right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.top_bar = self._build_top_bar()
        right_layout.addWidget(self.top_bar)

        self.stack = QStackedWidget()
        self.stack.setObjectName("GlassStack")
        self.stack.addWidget(self._build_dashboard_page())
        self.stack.addWidget(self._build_history_page())
        right_layout.addWidget(self.stack, stretch=1)

        outer.addWidget(self.sidebar)
        outer.addWidget(self.right_container, stretch=1)

    def _build_top_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("TopBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 12, 24, 12)
        layout.setSpacing(12)

        self.sidebar_toggle_btn = QPushButton()
        self.sidebar_toggle_btn.setObjectName("IconButton")
        self.sidebar_toggle_btn.setFixedSize(36, 36)
        self.sidebar_toggle_btn.setIconSize(QSize(18, 18))
        self.sidebar_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sidebar_toggle_btn.setToolTip("Chiudi menu laterale")
        self.sidebar_toggle_btn.clicked.connect(lambda: self.toggle_sidebar(animate=True))

        self.topbar_logo = QLabel()
        self.topbar_logo.setObjectName("BrandLogo")
        self.topbar_logo.setFixedSize(28, 28)
        self.topbar_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.topbar_logo.setPixmap(load_brand_pixmap(28))
        self.topbar_logo.setVisible(False)

        self.topbar_title = QLabel("Dashboard & Aggiornamenti")
        self.topbar_title.setObjectName("TopBarPageTitle")

        self.search_input = QLineEdit()
        self.search_input.setObjectName("SearchInput")
        self.search_input.setPlaceholderText("Cerca programmi installati o aggiornamenti...")
        self.search_input.setMinimumWidth(240)
        self.search_input.setMaximumWidth(400)
        self.search_input.textChanged.connect(self._render_candidates)

        self.scan_btn = QPushButton("Nuova Scansione")
        self.scan_btn.setObjectName("SecondaryButton")
        self.scan_btn.setIconSize(QSize(15, 15))
        self.scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_btn.clicked.connect(self.start_scan)

        self.update_all_btn = QPushButton("Aggiorna selezionate")
        self.update_all_btn.setObjectName("PrimaryButton")
        self.update_all_btn.setIconSize(QSize(15, 15))
        self.update_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_all_btn.clicked.connect(self.start_batch_update)

        self.notifications_btn = NotificationBellButton()
        self.notifications_btn.clicked.connect(self.toggle_notifications_panel)

        layout.addWidget(self.sidebar_toggle_btn)
        layout.addWidget(self.topbar_logo)
        layout.addWidget(self.topbar_title)
        layout.addStretch()
        layout.addWidget(self.search_input, stretch=1)
        layout.addWidget(self.scan_btn)
        layout.addWidget(self.update_all_btn)
        layout.addWidget(self.notifications_btn)
        return bar

    def _make_nav_button(self, text: str, page_index: int, active: bool) -> QPushButton:
        btn = QPushButton(f" {text}")
        btn.setObjectName("NavButton")
        btn.setIconSize(QSize(16, 16))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setProperty("active", active)
        btn.clicked.connect(lambda: self._switch_page(page_index))
        return btn

    def _switch_page(self, index: int) -> None:
        previous = self.stack.currentIndex()
        self.stack.setCurrentIndex(index)
        for idx, btn in enumerate((self.nav_dashboard, self.nav_history)):
            btn.setProperty("active", idx == index)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        is_dashboard = index == 0
        self.topbar_title.setText(
            "Dashboard & Aggiornamenti" if is_dashboard else "Cronologia di Sessione"
        )
        self.search_input.setVisible(is_dashboard)
        self.scan_btn.setVisible(is_dashboard)
        self.update_all_btn.setVisible(is_dashboard)
        self._refresh_icons()

        if index == 1:
            self._refresh_history_views()

        if previous != index and self.isVisible():
            self._animate_page_fade(self.stack.currentWidget())

    def _animate_page_fade(self, page: Optional[QWidget]) -> None:
        if page is None:
            return
        if self._page_fade_anim is not None:
            self._page_fade_anim.stop()
        effect = QGraphicsOpacityEffect(page)
        effect.setOpacity(0.0)
        page.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(280)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        anim.finished.connect(lambda p=page: p.setGraphicsEffect(None))
        self._page_fade_anim = anim
        QTimer.singleShot(0, anim.start)

    def _get_sidebar_width(self) -> int:
        return self.sidebar.maximumWidth()

    def _set_sidebar_width(self, width: int) -> None:
        clamped = max(0, int(width))
        self.sidebar.setFixedWidth(clamped)
        if (
            (hasattr(self, "notification_banner") and self.notification_banner.isVisible())
            or (hasattr(self, "notifications_popover") and self.notifications_popover.isVisible())
        ):
            self._reposition_overlays()

    sidebar_width = Property(int, _get_sidebar_width, _set_sidebar_width)

    def toggle_sidebar(self, animate: bool = True) -> None:
        self.set_sidebar_open(not self._sidebar_open, animate=animate)

    def set_sidebar_open(self, opened: bool, animate: bool = True) -> None:
        if self._sidebar_open == opened and self.sidebar.maximumWidth() == (
            self.SIDEBAR_WIDTH if opened else 0
        ):
            return
        self._sidebar_open = opened
        target_w = self.SIDEBAR_WIDTH if opened else 0

        if self._sidebar_anim is not None:
            self._sidebar_anim.stop()

        if animate and self.isVisible():
            anim = QPropertyAnimation(self, b"sidebar_width", self)
            anim.setDuration(340)
            anim.setEasingCurve(QEasingCurve.Type.InOutQuart)
            anim.setStartValue(self.sidebar.width())
            anim.setEndValue(target_w)
            self._sidebar_anim = anim
            QTimer.singleShot(0, anim.start)
        else:
            self.sidebar.setFixedWidth(target_w)
            self._reposition_overlays()

        self.topbar_logo.setVisible(not self._sidebar_open)
        self.sidebar_toggle_btn.setToolTip(
            "Chiudi menu laterale" if self._sidebar_open else "Apri menu laterale"
        )
        self._refresh_icons()

    def toggle_updates_list(self) -> None:
        self.set_updates_expanded(not self._updates_expanded, animate=True)

    def _compute_updates_card_rect(self) -> QRect:
        """Compute the exact pixel rectangle where the separate UpdatesListCard sits."""
        margins = self.dashboard_layout.contentsMargins()
        spacing = self.dashboard_layout.spacing()
        page_w = max(360, self.dashboard_page.width())
        page_h = max(360, self.dashboard_page.height())

        top_y = self.hero_card.geometry().bottom() + 1 + spacing
        if self.download_banner.isVisible():
            dl_bottom = self.download_banner.geometry().bottom() + 1
            if dl_bottom > top_y:
                top_y = dl_bottom + spacing
            else:
                top_y += max(self.download_banner.height(), self.download_banner.sizeHint().height()) + spacing

        w = max(320, page_w - margins.left() - margins.right())
        h = max(200, page_h - margins.bottom() - top_y)
        return QRect(margins.left(), top_y, w, h)

    def _capture_updates_card_snapshot(self, rect: QRect) -> QPixmap:
        """Render the entire Liquid Glass UpdatesListCard once into a transparent HiDPI pixmap."""
        w = max(1, rect.width())
        h = max(1, rect.height())
        dpr = max(1.0, float(self.devicePixelRatioF()))

        pixmap = QPixmap(int(round(w * dpr)), int(round(h * dpr)))
        pixmap.setDevicePixelRatio(dpr)
        pixmap.fill(Qt.GlobalColor.transparent)

        was_visible = self.updates_card.isVisible()
        if not was_visible:
            # Synchronous show -> offscreen render -> hide within one tick (zero screen flash)
            self.updates_card.setFixedSize(w, h)
            self.updates_card.setVisible(True)
            if self.updates_card.layout() is not None:
                self.updates_card.layout().activate()
            self.updates_scroll.viewport().resize(
                max(1, self.updates_scroll.width()),
                max(1, self.updates_scroll.height()),
            )
            if self.updates_container.layout() is not None:
                self.updates_container.layout().activate()
            QApplication.sendPostedEvents(None, 0)
            self.updates_card.render(pixmap, QPoint(0, 0), QRegion(0, 0, w, h))
            self.updates_card.setVisible(False)
            self.updates_card.setMinimumSize(0, 0)
            self.updates_card.setMaximumSize(16777215, 16777215)
        else:
            self.updates_card.render(pixmap, QPoint(0, 0), QRegion(0, 0, w, h))

        return pixmap

    def set_updates_expanded(self, expanded: bool, animate: bool = True) -> None:
        self._updates_expanded = expanded
        use_anim = animate and self.isVisible()

        self._updates_anim_timer.stop()
        if self._updates_anim is not None:
            self._updates_anim.stop()

        self.expand_updates_btn.set_expanded(expanded, animate=use_anim)
        self.expand_updates_btn.setToolTip(
            "Nascondi elenco applicazioni" if expanded else "Espandi elenco applicazioni"
        )

        if not use_anim:
            self._updates_overlay.hide()
            self._updates_overlay.progress = 1.0 if expanded else 0.0
            self.updates_card.setVisible(expanded)
            self._dashboard_spacer.setVisible(not expanded)
            self.dashboard_layout.setStretchFactor(self.updates_card, 1 if expanded else 0)
            self.dashboard_layout.setStretchFactor(self._dashboard_spacer, 0 if expanded else 1)
            self._reposition_overlays()
            return

        if expanded:
            target_rect = self._compute_updates_card_rect()
            if self._updates_overlay.isVisible():
                start_p = self._updates_overlay.progress
            else:
                start_p = 0.0
                snapshot = self._capture_updates_card_snapshot(target_rect)
                self._updates_overlay.set_snapshot(snapshot)
                self._updates_overlay.progress = 0.0

            self.updates_card.setVisible(False)
            self._dashboard_spacer.setVisible(True)
            self.dashboard_layout.setStretchFactor(self.updates_card, 0)
            self.dashboard_layout.setStretchFactor(self._dashboard_spacer, 1)

            self._updates_overlay.setGeometry(target_rect)
            self._updates_overlay.show()
            self._updates_overlay.raise_()

            anim = QPropertyAnimation(self._updates_overlay, b"progress", self)
            anim.setDuration(380)
            anim.setStartValue(start_p)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutQuint)
            anim.finished.connect(self._on_updates_expand_finished)
            self._updates_anim = anim
            self._updates_anim_timer.start(0)
        else:
            if self._updates_overlay.isVisible():
                start_p = self._updates_overlay.progress
            elif self.updates_card.isVisible() and self.updates_card.height() > 0:
                card_rect = self.updates_card.geometry()
                snapshot = self._capture_updates_card_snapshot(card_rect)
                self._updates_overlay.set_snapshot(snapshot)
                self._updates_overlay.setGeometry(card_rect)
                self._updates_overlay.progress = 1.0
                start_p = 1.0
            else:
                self._updates_overlay.hide()
                self._updates_overlay.progress = 0.0
                self.updates_card.setVisible(False)
                self._dashboard_spacer.setVisible(True)
                self.dashboard_layout.setStretchFactor(self.updates_card, 0)
                self.dashboard_layout.setStretchFactor(self._dashboard_spacer, 1)
                self._reposition_overlays()
                return

            self.updates_card.setVisible(False)
            self._dashboard_spacer.setVisible(True)
            self.dashboard_layout.setStretchFactor(self.updates_card, 0)
            self.dashboard_layout.setStretchFactor(self._dashboard_spacer, 1)
            self._updates_overlay.show()
            self._updates_overlay.raise_()

            anim = QPropertyAnimation(self._updates_overlay, b"progress", self)
            anim.setDuration(310)
            anim.setStartValue(start_p)
            anim.setEndValue(0.0)
            anim.setEasingCurve(QEasingCurve.Type.InOutQuart)
            anim.finished.connect(self._on_updates_collapse_finished)
            self._updates_anim = anim
            self._updates_anim_timer.start(0)

    def _start_pending_updates_anim(self) -> None:
        if self._updates_anim is not None:
            self._updates_anim.start()

    def _on_updates_expand_finished(self) -> None:
        if not self._updates_expanded:
            return
        self._updates_overlay.hide()
        self._updates_overlay.progress = 1.0
        self._dashboard_spacer.setVisible(False)
        self.updates_card.setVisible(True)
        self.dashboard_layout.setStretchFactor(self.updates_card, 1)
        self.dashboard_layout.setStretchFactor(self._dashboard_spacer, 0)
        self._reposition_overlays()

    def _on_updates_collapse_finished(self) -> None:
        if self._updates_expanded:
            return
        self._updates_overlay.hide()
        self._updates_overlay.progress = 0.0
        self.updates_card.setVisible(False)
        self._dashboard_spacer.setVisible(True)
        self.dashboard_layout.setStretchFactor(self.updates_card, 0)
        self.dashboard_layout.setStretchFactor(self._dashboard_spacer, 1)
        self._reposition_overlays()

    def toggle_notifications_panel(self) -> None:
        if self.notifications_popover.isVisible():
            self.notifications_popover.hide()
        else:
            self.notifications_btn.set_unread_count(0)
            self.notifications_popover.set_notifications(self._notifications)
            target = self._compute_notifications_popover_pos()
            self.notifications_popover.animate_open(target)

    def clear_notifications(self) -> None:
        self._notifications.clear()
        self.notifications_btn.set_unread_count(0)
        self.notifications_popover.set_notifications(self._notifications)
        if self.notifications_popover.isVisible():
            self._position_notifications_popover()

    def _on_dark_theme_toggled(self, checked: bool) -> None:
        self.set_theme("dark" if checked else "light", animate=True)

    def set_theme(self, theme: str, animate: bool = False) -> None:
        normalized = "dark" if theme == "dark" else "light"
        theme_changed = normalized != self._theme
        self._theme = normalized

        if self.dark_theme_toggle.isChecked() != (normalized == "dark"):
            self.dark_theme_toggle.blockSignals(True)
            self.dark_theme_toggle.setChecked(normalized == "dark")
            self.dark_theme_toggle.blockSignals(False)

        snapshot = None
        if animate and theme_changed and self.isVisible() and self.width() > 0 and self.height() > 0:
            snapshot = self.grab()

        self._glass_root.set_theme(normalized)
        self.setStyleSheet(get_theme_qss(normalized))
        self._refresh_icons()
        self._apply_windows_titlebar_theme(normalized == "dark")

        if hasattr(self, "notification_banner") and self.notification_banner.isVisible():
            self.notification_banner.refresh_style()
        if hasattr(self, "notifications_popover"):
            self.notifications_popover.refresh_style()
        self._reposition_overlays()

        if snapshot is not None:
            self._play_theme_crossfade(snapshot)

        self.update()

    def _play_theme_crossfade(self, old_snapshot) -> None:
        """Crossfade smoothly from the previous theme snapshot into the new theme."""
        if self._theme_fade_anim is not None:
            self._theme_fade_anim.stop()
        if self._theme_fade_overlay is not None:
            self._theme_fade_overlay.hide()
            self._theme_fade_overlay.deleteLater()
            self._theme_fade_overlay = None

        overlay = QLabel(self)
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        overlay.setPixmap(old_snapshot)
        overlay.setGeometry(self.rect())

        effect = QGraphicsOpacityEffect(overlay)
        effect.setOpacity(1.0)
        overlay.setGraphicsEffect(effect)
        overlay.show()
        overlay.raise_()

        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(380)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        anim.finished.connect(self._cleanup_theme_crossfade)

        self._theme_fade_overlay = overlay
        self._theme_fade_anim = anim
        QTimer.singleShot(0, anim.start)

    def _cleanup_theme_crossfade(self) -> None:
        if self._theme_fade_overlay is not None:
            self._theme_fade_overlay.hide()
            self._theme_fade_overlay.deleteLater()
            self._theme_fade_overlay = None

    def _refresh_icons(self) -> None:
        tokens = get_theme_tokens(self._theme)
        icon_default = tokens["icon_color"]
        icon_active = tokens["icon_active"]
        icon_muted = tokens["icon_muted"]

        self.sidebar_toggle_btn.setIcon(
            make_sidebar_toggle_icon(icon_default, sidebar_open=self._sidebar_open, size=18)
        )
        self.notifications_btn.set_bell_color(icon_default)
        self.expand_updates_btn.set_chevron_color(icon_default)

        is_dash = self.stack.currentIndex() == 0
        self.nav_dashboard.setIcon(
            make_dashboard_icon(icon_active if is_dash else icon_muted, size=16)
        )
        self.nav_history.setIcon(
            make_history_icon(icon_muted if is_dash else icon_active, size=16)
        )
        self.scan_btn.setIcon(make_refresh_icon(icon_default, size=15))
        self.update_all_btn.setIcon(make_download_icon("#ffffff", size=15))

        theme_icon = make_theme_icon(
            icon_active if self._theme == "dark" else icon_default,
            dark_mode=self._theme == "dark",
            size=16,
        )
        self.theme_icon_label.setPixmap(theme_icon.pixmap(16, 16))

    def _apply_windows_titlebar_theme(self, dark: bool) -> None:
        """Sync native Windows 10/11 window title bar with Light/Dark theme."""
        if not sys.platform.startswith("win"):
            return
        try:
            hwnd = int(self.winId())
            value = ctypes.c_int(1 if dark else 0)
            dwm = ctypes.windll.dwmapi  # type: ignore[attr-defined]
            dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
        except Exception:  # noqa: BLE001
            pass

    def _build_dashboard_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("GlassPage")
        self.dashboard_page = page
        self.dashboard_layout = QVBoxLayout(page)
        self.dashboard_layout.setContentsMargins(26, 22, 26, 22)
        self.dashboard_layout.setSpacing(16)

        # SECTION 1: Compact Liquid Glass summary card (fixed height — never thrashes layout)
        self.hero_card = QFrame()
        self.hero_card.setObjectName("HeroCard")
        hero_layout = QVBoxLayout(self.hero_card)
        hero_layout.setContentsMargins(22, 18, 22, 18)
        hero_layout.setSpacing(0)

        self.hero_header_widget = QWidget()
        self.hero_header_widget.setObjectName("TransparentContainer")
        hero_header = QHBoxLayout(self.hero_header_widget)
        hero_header.setContentsMargins(0, 0, 0, 0)
        hero_header.setSpacing(14)

        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        self.hero_headline = QLabel("Pronto per la scansione del sistema")
        self.hero_headline.setObjectName("Headline")
        self.hero_subtitle = QLabel(
            "Premi 'Nuova Scansione' per rilevare le app sul PC e confrontarle con le versioni online."
        )
        self.hero_subtitle.setObjectName("MutedText")
        title_col.addWidget(self.hero_headline)
        title_col.addWidget(self.hero_subtitle)

        chips_row = QHBoxLayout()
        chips_row.setSpacing(8)
        self.chip_installed = QLabel("0 app rilevate")
        self.chip_installed.setObjectName("StatChip")
        self.chip_pending = QLabel("0 disponibili")
        self.chip_pending.setObjectName("StatChip")
        self.chip_updated = QLabel("0 aggiornate")
        self.chip_updated.setObjectName("StatChip")
        for chip in (self.chip_installed, self.chip_pending, self.chip_updated):
            chips_row.addWidget(chip, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.expand_updates_btn = AnimatedChevronButton()
        self.expand_updates_btn.setToolTip("Espandi elenco applicazioni")
        self.expand_updates_btn.clicked.connect(self.toggle_updates_list)

        hero_header.addLayout(title_col, stretch=1)
        hero_header.addLayout(chips_row)
        hero_header.addWidget(self.expand_updates_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        hero_layout.addWidget(self.hero_header_widget)

        # Standalone active download section directly below the summary card,
        # visible ONLY while a download/update is in progress.
        self.download_banner = ActiveDownloadBanner(
            on_pause_toggle=self._toggle_pause,
            on_cancel=self._cancel_active_update,
        )

        # SECTION 2: Separate Liquid Glass card dedicated to the apps list
        self.updates_card = QFrame()
        self.updates_card.setObjectName("UpdatesListCard")
        self.updates_body = self.updates_card  # Alias for compatibility
        list_card_layout = QVBoxLayout(self.updates_card)
        list_card_layout.setContentsMargins(20, 16, 20, 16)
        list_card_layout.setSpacing(12)

        selection_row = QHBoxLayout()
        selection_row.setSpacing(10)
        list_title = QLabel("Applicazioni da aggiornare")
        list_title.setObjectName("SectionTitle")

        self.select_all_btn = QPushButton("Seleziona tutto")
        self.select_all_btn.setObjectName("CompactButton")
        self.select_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_all_btn.clicked.connect(self.toggle_select_all)

        self.selection_summary_label = QLabel("")
        self.selection_summary_label.setObjectName("MutedText")

        selection_row.addWidget(list_title)
        selection_row.addSpacing(6)
        selection_row.addWidget(self.selection_summary_label)
        selection_row.addStretch()
        selection_row.addWidget(self.select_all_btn)
        list_card_layout.addLayout(selection_row)

        list_divider = QFrame()
        list_divider.setObjectName("SidebarDivider")
        list_card_layout.addWidget(list_divider)

        self.updates_scroll = QScrollArea()
        self.updates_scroll.setWidgetResizable(True)
        self.updates_container = QWidget()
        self.updates_layout = QVBoxLayout(self.updates_container)
        self.updates_layout.setContentsMargins(0, 2, 4, 2)
        self.updates_layout.setSpacing(10)
        self.updates_layout.addStretch()
        self.updates_scroll.setWidget(self.updates_container)
        list_card_layout.addWidget(self.updates_scroll, stretch=1)

        self.updates_card.setVisible(False)

        self._dashboard_spacer = QWidget()
        self._dashboard_spacer.setObjectName("TransparentContainer")

        self.dashboard_layout.addWidget(self.hero_card, stretch=0)
        self.dashboard_layout.addWidget(self.download_banner, stretch=0)
        self.dashboard_layout.addWidget(self.updates_card, stretch=0)
        self.dashboard_layout.addWidget(self._dashboard_spacer, stretch=1)

        # Floating zero-layout 60fps transition overlay for UpdatesListCard
        self._updates_overlay = GlassSheetTransitionOverlay(page)

        return page

    def _build_history_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("GlassPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(16)

        header = QLabel("Cronologia Aggiornamenti (Stateless)")
        header.setObjectName("Headline")
        desc = QLabel(
            "Mostra gli aggiornamenti della sessione attiva in RAM e, al riavvio, "
            "solo il riepilogo dell'ultima sessione chiusa."
        )
        desc.setObjectName("MutedText")
        layout.addWidget(header)
        layout.addWidget(desc)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.history_container = QWidget()
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.setContentsMargins(0, 0, 4, 0)
        self.history_layout.setSpacing(10)
        scroll.setWidget(self.history_container)
        layout.addWidget(scroll, stretch=1)

        return page

    def _refresh_summary_chips(self) -> None:
        metrics = self.controller.get_summary_metrics()
        self.chip_installed.setText(f"{metrics['total_installed']} app rilevate")
        self.chip_pending.setText(f"{metrics['pending_updates']} disponibili")
        self.chip_updated.setText(f"{metrics['updated_this_session']} aggiornate")

    def start_scan(self) -> None:
        if self._scan_worker and self._scan_worker.isRunning():
            return
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("Scansione in corso...")
        self.hero_headline.setText("Analisi applicazioni installate...")
        self._scan_worker = ScanWorker(self.controller)
        self._scan_worker.scan_finished.connect(self._on_scan_finished)
        self._scan_worker.scan_failed.connect(self._on_scan_failed)
        self._scan_worker.start()

    def _on_scan_finished(self, candidates: List[UpdateCandidate]) -> None:
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Nuova Scansione")
        total = len(self.controller.installed_apps)
        pending = len(candidates)
        self.hero_headline.setText(
            f"{pending} aggiornamenti disponibili trovati"
            if pending
            else "Tutte le applicazioni sono aggiornate"
        )
        self.hero_subtitle.setText(
            f"Ultima scansione: {self.controller.last_scan_at}  ·  "
            f"{total} applicazioni rilevate sul PC"
        )
        self._refresh_summary_chips()
        self._render_candidates()
        self._refresh_selection_controls()
        if self._pending_rescan:
            self._pending_rescan = False
            self.start_scan()

    def _on_scan_failed(self, error_msg: str) -> None:
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Nuova Scansione")
        self.hero_headline.setText("Scansione non riuscita")
        self.hero_subtitle.setText(error_msg)
        if self._pending_rescan:
            self._pending_rescan = False
            self.start_scan()

    def _render_candidates(self) -> None:
        while self.updates_layout.count():
            item = self.updates_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

        self._card_map.clear()
        query = self.search_input.text().strip().lower()
        visible = [
            c
            for c in self.controller.candidates
            if not query or query in c.name.lower() or query in c.app.publisher.lower()
        ]

        if not visible:
            empty = QLabel("Nessun aggiornamento in sospeso corrispondente al filtro.")
            empty.setObjectName("MutedText")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setContentsMargins(0, 20, 0, 20)
            self.updates_layout.addWidget(empty)
        else:
            for candidate in visible:
                card = AppUpdateCard(
                    candidate=candidate,
                    on_update_click=self.start_single_update,
                    on_selection_change=self._on_candidate_selected,
                )
                card.set_updating_state(candidate.status)
                self._card_map[candidate.app_id] = card
                self.updates_layout.addWidget(card)

        self.updates_layout.addStretch()

    def _actionable_candidates(self) -> List[UpdateCandidate]:
        return [
            c
            for c in self.controller.candidates
            if c.status != UpdatePhase.COMPLETED and not c.skipped
        ]

    def _refresh_selection_controls(self) -> None:
        actionable = self._actionable_candidates()
        total = len(actionable)
        selected_count = sum(1 for c in actionable if c.selected)
        all_selected = total > 0 and selected_count == total
        is_updating = bool(self._update_worker and self._update_worker.isRunning())

        self.select_all_btn.setText("Deseleziona tutto" if all_selected else "Seleziona tutto")
        self.select_all_btn.setEnabled(total > 0 and not is_updating)

        if total == 0:
            self.selection_summary_label.setText("")
        elif selected_count == 0:
            self.selection_summary_label.setText("Nessuna app selezionata")
        else:
            self.selection_summary_label.setText(f"{selected_count} di {total} selezionate")

        self.update_all_btn.setText("Aggiorna tutto" if all_selected else "Aggiorna selezionate")
        self.update_all_btn.setEnabled(selected_count > 0 and not is_updating)

    def toggle_select_all(self) -> None:
        actionable = self._actionable_candidates()
        if not actionable:
            return
        should_select = not all(c.selected for c in actionable)
        for candidate in actionable:
            candidate.selected = should_select
            card = self._card_map.get(candidate.app_id)
            if card is not None:
                card.checkbox.blockSignals(True)
                card.checkbox.setChecked(should_select)
                card.checkbox.blockSignals(False)
        self._refresh_selection_controls()

    def _on_candidate_selected(self, candidate: UpdateCandidate, selected: bool) -> None:
        candidate.selected = selected
        self._refresh_selection_controls()

    def start_single_update(self, candidate: UpdateCandidate) -> None:
        self._launch_update_worker([candidate])

    def start_batch_update(self) -> None:
        selected = [c for c in self._actionable_candidates() if c.selected]
        if selected:
            self._launch_update_worker(selected)

    def _launch_update_worker(self, candidates: List[UpdateCandidate]) -> None:
        if self._update_worker and self._update_worker.isRunning():
            return
        self.update_all_btn.setEnabled(False)
        self.select_all_btn.setEnabled(False)
        self._update_worker = UpdateWorker(self.controller, candidates)
        self._update_worker.progress_changed.connect(self._on_progress_changed)
        self._update_worker.item_completed.connect(self._on_item_completed)
        self._update_worker.batch_finished.connect(self._on_batch_finished)
        self._update_worker.start()

    def _on_progress_changed(self, progress: DownloadProgress) -> None:
        self.download_banner.update_progress(progress)
        card = self._card_map.get(progress.app_id)
        if card:
            card.set_updating_state(progress.phase)
        self._reposition_overlays()

    def _on_item_completed(self, record: UpdateRecord) -> None:
        self.download_banner.reset()
        card = self._card_map.get(record.app_id)
        if card:
            phase = (
                UpdatePhase.COMPLETED
                if record.status == "success"
                else UpdatePhase.CANCELLED
                if record.status == "cancelled"
                else UpdatePhase.FAILED
            )
            card.set_updating_state(phase)

        self._refresh_history_views()
        self._refresh_summary_chips()
        self._refresh_selection_controls()

        if record.status == "success":
            self.show_notification(
                title="Aggiornamento completato",
                message=f"{record.app_name} aggiornato alla v{record.to_version}.",
                level="success",
            )
        elif record.status == "cancelled":
            self.show_notification(
                title="Aggiornamento annullato",
                message=f"L'aggiornamento di {record.app_name} è stato annullato.",
                level="warning",
            )
        else:
            detail = f": {record.error_message}" if record.error_message else "."
            self.show_notification(
                title="Aggiornamento non riuscito",
                message=f"Impossibile aggiornare {record.app_name}{detail}",
                level="warning",
            )

    def _on_batch_finished(self, records: List[UpdateRecord]) -> None:
        self.download_banner.reset()
        self._refresh_selection_controls()

        succeeded = [r for r in records if r.status == "success"]
        failed = [r for r in records if r.status != "success"]

        if len(records) > 1:
            if succeeded and not failed:
                self.show_notification(
                    title="Aggiornamenti completati",
                    message=f"{len(succeeded)} applicazioni aggiornate con successo.",
                    level="success",
                )
            elif succeeded and failed:
                self.show_notification(
                    title="Aggiornamenti completati con avvisi",
                    message=(
                        f"{len(succeeded)} completati, {len(failed)} non riusciti o annullati."
                    ),
                    level="warning",
                )
            elif failed:
                self.show_notification(
                    title="Aggiornamenti non riusciti",
                    message=f"Nessun aggiornamento completato ({len(failed)} non riusciti o annullati).",
                    level="warning",
                )

        if succeeded:
            if self._scan_worker and self._scan_worker.isRunning():
                self._pending_rescan = True
            else:
                self.start_scan()

    def show_notification(self, title: str, message: str, level: str = "success") -> None:
        normalized = "success" if level == "success" else "warning"
        item = NotificationItem(title=title, message=message, level=normalized)
        self._notifications.insert(0, item)
        if len(self._notifications) > self.MAX_NOTIFICATIONS:
            self._notifications = self._notifications[: self.MAX_NOTIFICATIONS]

        self.notifications_popover.set_notifications(self._notifications)
        if not self.notifications_popover.isVisible():
            self.notifications_btn.set_unread_count(self.notifications_btn.unread_count + 1)
        else:
            self._position_notifications_popover()

        self.notification_banner.show_message(title=title, message=message, level=normalized)
        target = self._compute_notification_pos()
        self.notification_banner.slide_to(target, animate=True)

    def _reposition_overlays(self) -> None:
        if hasattr(self, "notification_banner") and self.notification_banner.isVisible():
            self._position_notification()
        if hasattr(self, "notifications_popover") and self.notifications_popover.isVisible():
            self._position_notifications_popover()

    def _compute_notification_pos(self) -> QPoint:
        """Compute anchored bottom-right position for the discreet feedback toast."""
        content_rect = self.right_container.geometry()
        if content_rect.width() <= 0 or content_rect.height() <= 0:
            content_rect = self.rect()
        max_w = max(320, min(440, content_rect.width() - 40))
        self.notification_banner.setMaximumWidth(max_w)
        self.notification_banner.setMinimumWidth(min(340, max_w))
        self.notification_banner.adjustSize()

        x = content_rect.right() - self.notification_banner.width() - 22
        y = content_rect.bottom() - self.notification_banner.height() - 20
        return QPoint(max(12, x), max(12, y))

    def _position_notification(self) -> None:
        target = self._compute_notification_pos()
        self.notification_banner.slide_to(target, animate=False)

    def _compute_notifications_popover_pos(self) -> QPoint:
        """Compute anchored position directly below the top-bar bell icon."""
        self.notifications_popover.adjustSize()
        bell_bottom_right = self.notifications_btn.mapTo(
            self, self.notifications_btn.rect().bottomRight()
        )
        pop_w = self.notifications_popover.width()
        x = bell_bottom_right.x() - pop_w
        y = bell_bottom_right.y() + 10
        x = max(12, min(x, self.width() - pop_w - 16))
        y = max(12, y)
        return QPoint(x, y)

    def _position_notifications_popover(self) -> None:
        self.notifications_popover.move(self._compute_notifications_popover_pos())
        self.notifications_popover.raise_()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._theme_fade_overlay is not None:
            self._theme_fade_overlay.setGeometry(self.rect())
        self._reposition_overlays()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if (
            event.key() == Qt.Key.Key_Escape
            and hasattr(self, "notifications_popover")
            and self.notifications_popover.isVisible()
        ):
            self.notifications_popover.hide()
            return
        super().keyPressEvent(event)

    def _toggle_pause(self) -> None:
        if not self._update_worker:
            return
        if self._update_worker.control.is_paused:
            self._update_worker.control.resume()
        else:
            self._update_worker.control.pause()

    def _cancel_active_update(self) -> None:
        if self._update_worker:
            self._update_worker.control.cancel()

    def _refresh_history_views(self) -> None:
        while self.history_layout.count():
            item = self.history_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

        current = self.controller.history.get_current_session_records()
        last = self.controller.history.get_last_session_records()

        curr_title = QLabel(f"Sessione Corrente ({len(current)})")
        curr_title.setObjectName("SectionTitle")
        self.history_layout.addWidget(curr_title)
        if not current:
            lbl = QLabel("Nessun aggiornamento eseguito nella sessione corrente.")
            lbl.setObjectName("MutedText")
            self.history_layout.addWidget(lbl)
        else:
            for rec in current:
                self.history_layout.addWidget(HistoryRowWidget(rec))

        last_title = QLabel(f"Ultima Sessione Chiusa ({len(last)})")
        last_title.setObjectName("SectionTitle")
        self.history_layout.addWidget(last_title)
        if not last:
            lbl = QLabel("Nessun riepilogo dall'ultima sessione precedente.")
            lbl.setObjectName("MutedText")
            self.history_layout.addWidget(lbl)
        else:
            for rec in last:
                self.history_layout.addWidget(HistoryRowWidget(rec))

        self.history_layout.addStretch()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.controller.shutdown()
        super().closeEvent(event)
