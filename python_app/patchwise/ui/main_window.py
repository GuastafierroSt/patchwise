"""Main desktop window class for PatchWise Software & Driver Updater."""

from __future__ import annotations

import ctypes
import sys
from typing import Dict, List, Optional

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QSize,
    Qt,
    QTimer,
)
from PySide6.QtGui import QCloseEvent, QKeyEvent, QResizeEvent
from PySide6.QtWidgets import (
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
from patchwise.core.drivers import (
    WindowsUpdateDriverChecker,
    WindowsUpdateDriverUpdater,
    create_default_driver_detector,
)
from patchwise.models import DownloadProgress, UpdateCandidate, UpdateRecord
from patchwise.ui.icons import (
    load_app_icon,
    load_brand_pixmap,
    make_dashboard_icon,
    make_download_icon,
    make_driver_icon,
    make_history_icon,
    make_refresh_icon,
    make_sidebar_toggle_icon,
    make_theme_icon,
)
from patchwise.ui.section_view import (
    APPS_SECTION_CONFIG,
    DRIVERS_SECTION_CONFIG,
    UpdateSectionView,
)
from patchwise.ui.theme import get_theme_qss, get_theme_tokens
from patchwise.ui.widgets import (
    ActiveDownloadBanner,
    AnimatedChevronButton,
    AppUpdateCard,
    HistoryRowWidget,
    LiquidGlassBackdrop,
    ModernToggleSwitch,
    NotificationBellButton,
    NotificationDetailDialog,
    NotificationItem,
    NotificationsPopover,
    StatusNotificationBanner,
)


class PatchWiseMainWindow(QMainWindow):
    """Primary PySide6 desktop shell coordinating Apps updates, Driver updates, and history."""

    SIDEBAR_WIDTH = 268
    MAX_NOTIFICATIONS = 50

    def __init__(
        self,
        controller: Optional[UpdateManagerController] = None,
        driver_controller: Optional[UpdateManagerController] = None,
    ) -> None:
        super().__init__()
        self.controller = controller or UpdateManagerController(item_type="app")
        self.driver_controller = driver_controller or UpdateManagerController(
            detector=create_default_driver_detector(),
            checker=WindowsUpdateDriverChecker(),
            updaters=[WindowsUpdateDriverUpdater()],
            history=self.controller.history,
            item_type="driver",
        )

        self._theme: str = "light"
        self._sidebar_open: bool = True
        self._sidebar_anim: Optional[QPropertyAnimation] = None
        self._page_fade_anim: Optional[QPropertyAnimation] = None
        self._theme_fade_overlay: Optional[QLabel] = None
        self._theme_fade_anim: Optional[QPropertyAnimation] = None
        self._notifications: List[NotificationItem] = []
        self._active_detail_dialog: Optional[NotificationDetailDialog] = None

        self.setWindowTitle(f"PatchWise v{__version__}")
        self.setWindowIcon(load_app_icon())
        self.resize(1240, 820)

        self._build_layout()
        self.notification_banner = StatusNotificationBanner(
            self,
            on_click=self.open_notification_detail,
        )
        self.notifications_popover = NotificationsPopover(
            on_clear=self.clear_notifications,
            on_select=self.open_notification_detail,
            parent=self,
        )
        self.set_theme("light", animate=False)
        self._refresh_history_views()
        self._sync_topbar_for_active_section()

    @property
    def current_theme(self) -> str:
        return self._theme

    @property
    def is_sidebar_open(self) -> bool:
        return self._sidebar_open

    @property
    def active_section(self) -> Optional[UpdateSectionView]:
        if not hasattr(self, "stack"):
            return None
        idx = self.stack.currentIndex()
        if idx == 0:
            return self.apps_section
        if idx == 1:
            return self.drivers_section
        return None

    # Compatibility accessors delegating to the primary Apps section
    @property
    def download_banner(self) -> ActiveDownloadBanner:
        return self.apps_section.download_banner

    @property
    def updates_body(self) -> QFrame:
        return self.apps_section.updates_card

    @property
    def is_updates_expanded(self) -> bool:
        return self.apps_section.is_expanded

    @property
    def expand_updates_btn(self) -> AnimatedChevronButton:
        return self.apps_section.expand_updates_btn

    @property
    def select_all_btn(self) -> QPushButton:
        return self.apps_section.select_all_btn

    @property
    def _card_map(self) -> Dict[str, AppUpdateCard]:
        return self.apps_section._card_map

    @property
    def _updates_anim(self) -> Optional[QPropertyAnimation]:
        return self.apps_section._updates_anim

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
        subtitle = QLabel(f"Software & Driver · v{__version__}")
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

        self.nav_dashboard = self._make_nav_button("Aggiorna App", 0, active=True)
        self.nav_drivers = self._make_nav_button("Aggiorna Driver", 1, active=False)
        self.nav_history = self._make_nav_button("Cronologia", 2, active=False)
        sb_layout.addWidget(self.nav_dashboard)
        sb_layout.addWidget(self.nav_drivers)
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

        self.apps_section = UpdateSectionView(
            controller=self.controller,
            config=APPS_SECTION_CONFIG,
            on_notify=self.show_notification,
            on_history_changed=self._refresh_history_views,
            on_controls_changed=self._sync_topbar_for_active_section,
            on_request_scan=lambda: self.start_scan(),
        )
        self.drivers_section = UpdateSectionView(
            controller=self.driver_controller,
            config=DRIVERS_SECTION_CONFIG,
            on_notify=self.show_notification,
            on_history_changed=self._refresh_history_views,
            on_controls_changed=self._sync_topbar_for_active_section,
            on_request_scan=lambda: self.start_driver_scan(),
        )

        self.stack = QStackedWidget()
        self.stack.setObjectName("GlassStack")
        self.stack.addWidget(self.apps_section)
        self.stack.addWidget(self.drivers_section)
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

        self.topbar_title = QLabel(APPS_SECTION_CONFIG.page_title)
        self.topbar_title.setObjectName("TopBarPageTitle")

        self.search_input = QLineEdit()
        self.search_input.setObjectName("SearchInput")
        self.search_input.setPlaceholderText(APPS_SECTION_CONFIG.search_placeholder)
        self.search_input.setMinimumWidth(240)
        self.search_input.setMaximumWidth(400)
        self.search_input.textChanged.connect(self._on_search_changed)

        self.scan_btn = QPushButton("Nuova Scansione")
        self.scan_btn.setObjectName("SecondaryButton")
        self.scan_btn.setIconSize(QSize(15, 15))
        self.scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_btn.clicked.connect(self._on_scan_clicked)

        self.update_all_btn = QPushButton("Aggiorna selezionate")
        self.update_all_btn.setObjectName("PrimaryButton")
        self.update_all_btn.setIconSize(QSize(15, 15))
        self.update_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_all_btn.clicked.connect(self._on_batch_update_clicked)

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
        for idx, btn in enumerate((self.nav_dashboard, self.nav_drivers, self.nav_history)):
            btn.setProperty("active", idx == index)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self._sync_topbar_for_active_section()
        self._refresh_icons()

        if index == 2:
            self._refresh_history_views()

        if previous != index and self.isVisible():
            self._animate_page_fade(self.stack.currentWidget())

    def _sync_topbar_for_active_section(self) -> None:
        if not hasattr(self, "stack"):
            return
        section = self.active_section
        if section is None:
            self.topbar_title.setText("Cronologia")
            self.search_input.setVisible(False)
            self.scan_btn.setVisible(False)
            self.update_all_btn.setVisible(False)
            return

        self.topbar_title.setText(section.config.page_title)
        self.search_input.setVisible(True)
        self.search_input.setPlaceholderText(section.config.search_placeholder)
        if self.search_input.text() != section.search_query:
            self.search_input.blockSignals(True)
            self.search_input.setText(section.search_query)
            self.search_input.blockSignals(False)

        scan_label, scan_enabled = section.get_scan_button_state()
        self.scan_btn.setVisible(True)
        self.scan_btn.setText(scan_label)
        self.scan_btn.setEnabled(scan_enabled)

        cta_label, cta_enabled = section.get_primary_cta_state()
        self.update_all_btn.setVisible(True)
        self.update_all_btn.setText(cta_label)
        self.update_all_btn.setEnabled(cta_enabled)

    def _on_search_changed(self, text: str) -> None:
        section = self.active_section
        if section is not None:
            section.set_search_query(text)

    def _on_scan_clicked(self) -> None:
        if self.stack.currentIndex() == 1:
            self.start_driver_scan()
        else:
            self.start_scan()

    def _on_batch_update_clicked(self) -> None:
        section = self.active_section
        if section is not None:
            section.start_batch_update()

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

    # Delegated Apps-section convenience methods (keep public API & tests compatible)
    def start_scan(self) -> None:
        self.apps_section.start_scan()

    def start_driver_scan(self) -> None:
        self.drivers_section.start_scan()

    def toggle_updates_list(self) -> None:
        self.apps_section.toggle_updates_list()

    def set_updates_expanded(self, expanded: bool, animate: bool = True) -> None:
        self.apps_section.set_updates_expanded(expanded, animate=animate)

    def _on_scan_finished(self, candidates: List[UpdateCandidate]) -> None:
        self.apps_section.on_scan_finished(candidates)

    def _on_progress_changed(self, progress: DownloadProgress) -> None:
        self.apps_section.on_progress_changed(progress)

    def _on_item_completed(self, record: UpdateRecord) -> None:
        self.apps_section.on_item_completed(record)

    def _on_batch_finished(self, records: List[UpdateRecord]) -> None:
        self.apps_section.on_batch_finished(records)

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
        self.apps_section.set_icon_color(icon_default)
        self.drivers_section.set_icon_color(icon_default)

        active_idx = self.stack.currentIndex()
        self.nav_dashboard.setIcon(
            make_dashboard_icon(icon_active if active_idx == 0 else icon_muted, size=16)
        )
        self.nav_drivers.setIcon(
            make_driver_icon(icon_active if active_idx == 1 else icon_muted, size=16)
        )
        self.nav_history.setIcon(
            make_history_icon(icon_active if active_idx == 2 else icon_muted, size=16)
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
        if not sys.platform.startswith("win"):
            return
        try:
            hwnd = int(self.winId())
            value = ctypes.c_int(1 if dark else 0)
            dwm = ctypes.windll.dwmapi  # type: ignore[attr-defined]
            dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
        except Exception:  # noqa: BLE001
            pass

    def _build_history_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("GlassPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(16)

        header = QLabel("Cronologia Aggiornamenti")
        header.setObjectName("Headline")
        desc = QLabel(
            "Mostra gli aggiornamenti di applicazioni e driver della sessione attiva e solo il riepilogo dell'ultima sessione chiusa."
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

    @property
    def active_detail_dialog(self) -> Optional[NotificationDetailDialog]:
        return self._active_detail_dialog

    def open_notification_detail(self, item: NotificationItem) -> NotificationDetailDialog:
        """Open the Liquid Glass diagnostic dialog for a clicked notification or error."""
        if hasattr(self, "notifications_popover") and self.notifications_popover.isVisible():
            self.notifications_popover.hide()
        if self._active_detail_dialog is not None:
            try:
                self._active_detail_dialog.close()
                self._active_detail_dialog.deleteLater()
            except RuntimeError:
                pass
        dialog = NotificationDetailDialog(item, theme=self._theme, parent=self)
        self._active_detail_dialog = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        return dialog

    def _open_record_detail(self, record: UpdateRecord) -> None:
        level = "success" if record.status == "success" else "warning"
        title = (
            "Dettagli aggiornamento driver"
            if record.item_type == "driver"
            else "Dettagli aggiornamento app"
        )
        category_label = (
            "Driver · Windows Update" if record.item_type == "driver" else "App · Winget"
        )
        message = (
            f"Impossibile aggiornare {record.app_name}: {record.error_message}"
            if record.status == "failed" and record.error_message
            else f"{record.app_name} ({record.from_version} → {record.to_version})"
        )
        details = record.error_details or (
            f"Elemento: {record.app_name} ({record.publisher})\n"
            f"Versione: {record.from_version} → {record.to_version}\n"
            f"Esito: {record.status}\n"
            f"Orario: {record.completed_at}\n"
            f"Durata: {record.duration_seconds:.1f}s\n\n"
            f"{record.error_message}"
        )
        self.open_notification_detail(
            NotificationItem(
                title=title,
                message=message,
                level=level,
                timestamp=record.completed_at.split(" ")[-1] if record.completed_at else "",
                details=details,
                category_label=category_label,
            )
        )

    def show_notification(
        self,
        title: str,
        message: str,
        level: str = "success",
        details: str = "",
        category_label: str = "",
    ) -> None:
        normalized = "success" if level == "success" else "warning"
        item = NotificationItem(
            title=title,
            message=message,
            level=normalized,
            details=details,
            category_label=category_label,
        )
        self._notifications.insert(0, item)
        if len(self._notifications) > self.MAX_NOTIFICATIONS:
            self._notifications = self._notifications[: self.MAX_NOTIFICATIONS]

        self.notifications_popover.set_notifications(self._notifications)
        if not self.notifications_popover.isVisible():
            self.notifications_btn.set_unread_count(self.notifications_btn.unread_count + 1)
        else:
            self._position_notifications_popover()

        self.notification_banner.show_message(
            title=title, message=message, level=normalized, item=item
        )
        target = self._compute_notification_pos()
        self.notification_banner.slide_to(target, animate=True)

    def _reposition_overlays(self) -> None:
        if hasattr(self, "notification_banner") and self.notification_banner.isVisible():
            self._position_notification()
        if hasattr(self, "notifications_popover") and self.notifications_popover.isVisible():
            self._position_notifications_popover()

    def _compute_notification_pos(self) -> QPoint:
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
                self.history_layout.addWidget(
                    HistoryRowWidget(rec, on_inspect=self._open_record_detail)
                )

        last_title = QLabel(f"Ultima Sessione Chiusa ({len(last)})")
        last_title.setObjectName("SectionTitle")
        self.history_layout.addWidget(last_title)
        if not last:
            lbl = QLabel("Nessun riepilogo dall'ultima sessione precedente.")
            lbl.setObjectName("MutedText")
            self.history_layout.addWidget(lbl)
        else:
            for rec in last:
                self.history_layout.addWidget(
                    HistoryRowWidget(rec, on_inspect=self._open_record_detail)
                )

        self.history_layout.addStretch()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.apps_section.shutdown_workers()
        self.drivers_section.shutdown_workers()
        self.driver_controller.cancel_active()
        self.controller.shutdown()
        super().closeEvent(event)
