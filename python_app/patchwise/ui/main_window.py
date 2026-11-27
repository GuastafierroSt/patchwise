"""Main desktop window class for PatchWise Software Updater."""

from __future__ import annotations

import ctypes
import sys
from typing import Dict, List, Optional

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QSize,
    Qt,
)
from PySide6.QtGui import QCloseEvent, QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
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
    AppUpdateCard,
    HistoryRowWidget,
    ModernToggleSwitch,
    StatusNotificationBanner,
)
from patchwise.ui.workers import ScanWorker, UpdateWorker


class PatchWiseMainWindow(QMainWindow):
    """Primary PySide6 desktop shell coordinating scan, updates, progress, and session history."""

    SIDEBAR_WIDTH = 268

    def __init__(self, controller: Optional[UpdateManagerController] = None) -> None:
        super().__init__()
        self.controller = controller or UpdateManagerController()
        self._scan_worker: Optional[ScanWorker] = None
        self._update_worker: Optional[UpdateWorker] = None
        self._card_map: Dict[str, AppUpdateCard] = {}
        self._pending_rescan: bool = False
        self._theme: str = "light"
        self._sidebar_open: bool = True
        self._sidebar_anim: Optional[QParallelAnimationGroup] = None

        self.setWindowTitle(f"PatchWise Desktop — Software Updater v{__version__} (Portable)")
        self.setWindowIcon(load_app_icon())
        self.resize(1240, 820)

        self._build_layout()
        self.notification_banner = StatusNotificationBanner(self)
        self.set_theme("light")
        self._refresh_history_views()
        self._refresh_summary_chips()

    @property
    def current_theme(self) -> str:
        return self._theme

    @property
    def is_sidebar_open(self) -> bool:
        return self._sidebar_open

    def _build_layout(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Collapsible sidebar navigation
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setMinimumWidth(self.SIDEBAR_WIDTH)
        self.sidebar.setMaximumWidth(self.SIDEBAR_WIDTH)
        sb_layout = QVBoxLayout(self.sidebar)
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

        # Right side: persistent TopBar + content stack
        self.right_container = QWidget()
        right_layout = QVBoxLayout(self.right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.top_bar = self._build_top_bar()
        right_layout.addWidget(self.top_bar)

        self.stack = QStackedWidget()
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
        self.search_input.setMinimumWidth(260)
        self.search_input.setMaximumWidth(420)
        self.search_input.textChanged.connect(self._render_candidates)

        self.scan_btn = QPushButton("Nuova Scansione")
        self.scan_btn.setObjectName("SecondaryButton")
        self.scan_btn.setIconSize(QSize(15, 15))
        self.scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_btn.clicked.connect(self.start_scan)

        self.update_all_btn = QPushButton("Aggiorna Selezionate")
        self.update_all_btn.setObjectName("PrimaryButton")
        self.update_all_btn.setIconSize(QSize(15, 15))
        self.update_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_all_btn.clicked.connect(self.start_batch_update)

        layout.addWidget(self.sidebar_toggle_btn)
        layout.addWidget(self.topbar_logo)
        layout.addWidget(self.topbar_title)
        layout.addStretch()
        layout.addWidget(self.search_input, stretch=1)
        layout.addWidget(self.scan_btn)
        layout.addWidget(self.update_all_btn)
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

        if animate:
            group = QParallelAnimationGroup(self)
            for prop in (b"minimumWidth", b"maximumWidth"):
                anim = QPropertyAnimation(self.sidebar, prop, group)
                anim.setDuration(200)
                anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                anim.setStartValue(self.sidebar.width())
                anim.setEndValue(target_w)
                if prop == b"maximumWidth":
                    anim.valueChanged.connect(self._on_sidebar_anim_step)
                group.addAnimation(anim)
            self._sidebar_anim = group
            group.start()
        else:
            self.sidebar.setMinimumWidth(target_w)
            self.sidebar.setMaximumWidth(target_w)
            self._on_sidebar_anim_step()

        self.topbar_logo.setVisible(not self._sidebar_open)
        self.sidebar_toggle_btn.setToolTip(
            "Chiudi menu laterale" if self._sidebar_open else "Apri menu laterale"
        )
        self._refresh_icons()

    def _on_sidebar_anim_step(self) -> None:
        if hasattr(self, "notification_banner") and self.notification_banner.isVisible():
            self._position_notification()

    def _on_dark_theme_toggled(self, checked: bool) -> None:
        self.set_theme("dark" if checked else "light")

    def set_theme(self, theme: str) -> None:
        normalized = "dark" if theme == "dark" else "light"
        self._theme = normalized

        self.dark_theme_toggle.blockSignals(True)
        self.dark_theme_toggle.setChecked(normalized == "dark")
        self.dark_theme_toggle.blockSignals(False)

        self.setStyleSheet(get_theme_qss(normalized))
        self._refresh_icons()
        self._apply_windows_titlebar_theme(normalized == "dark")

        if hasattr(self, "notification_banner") and self.notification_banner.isVisible():
            self.notification_banner.refresh_style()
            self._position_notification()

        self.update()

    def _refresh_icons(self) -> None:
        tokens = get_theme_tokens(self._theme)
        icon_default = tokens["icon_color"]
        icon_active = tokens["icon_active"]
        icon_muted = tokens["icon_muted"]

        self.sidebar_toggle_btn.setIcon(
            make_sidebar_toggle_icon(icon_default, sidebar_open=self._sidebar_open, size=18)
        )
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
            # 20 = DWMWA_USE_IMMERSIVE_DARK_MODE (Win10 2004+ / Win11)
            dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
        except Exception:  # noqa: BLE001
            pass

    def _build_dashboard_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(18)

        # Hero summary card
        hero = QFrame()
        hero.setObjectName("HeroCard")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(22, 20, 22, 20)
        hero_layout.setSpacing(14)

        hero_header = QHBoxLayout()
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

        hero_header.addLayout(title_col, stretch=1)
        hero_header.addLayout(chips_row)

        self.download_banner = ActiveDownloadBanner(
            on_pause_toggle=self._toggle_pause,
            on_cancel=self._cancel_active_update,
        )

        hero_layout.addLayout(hero_header)
        hero_layout.addWidget(self.download_banner)
        layout.addWidget(hero)

        # Scrollable updates list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.updates_container = QWidget()
        self.updates_layout = QVBoxLayout(self.updates_container)
        self.updates_layout.setContentsMargins(0, 0, 4, 0)
        self.updates_layout.setSpacing(10)
        self.updates_layout.addStretch()
        scroll.setWidget(self.updates_container)
        layout.addWidget(scroll, stretch=1)

        return page

    def _build_history_page(self) -> QWidget:
        page = QWidget()
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
            if item.widget():
                item.widget().deleteLater()

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

    @staticmethod
    def _on_candidate_selected(candidate: UpdateCandidate, selected: bool) -> None:
        candidate.selected = selected

    def start_single_update(self, candidate: UpdateCandidate) -> None:
        self._launch_update_worker([candidate])

    def start_batch_update(self) -> None:
        selected = [
            c
            for c in self.controller.candidates
            if c.selected and c.status != UpdatePhase.COMPLETED
        ]
        if selected:
            self._launch_update_worker(selected)

    def _launch_update_worker(self, candidates: List[UpdateCandidate]) -> None:
        if self._update_worker and self._update_worker.isRunning():
            return
        self.update_all_btn.setEnabled(False)
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
        self.update_all_btn.setEnabled(True)
        self.download_banner.reset()

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
        self.notification_banner.show_message(title=title, message=message, level=level)
        self._position_notification()

    def _position_notification(self) -> None:
        content_rect = self.right_container.geometry()
        if content_rect.width() <= 0:
            content_rect = self.rect()
        max_w = max(340, min(640, content_rect.width() - 48))
        self.notification_banner.setMaximumWidth(max_w)
        self.notification_banner.setMinimumWidth(min(420, max_w))
        self.notification_banner.adjustSize()
        x = content_rect.x() + (content_rect.width() - self.notification_banner.width()) // 2
        top_offset = self.top_bar.height() + 10 if self.top_bar.height() > 0 else 16
        y = content_rect.y() + top_offset
        self.notification_banner.move(max(12, x), max(12, y))
        self.notification_banner.raise_()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if hasattr(self, "notification_banner") and self.notification_banner.isVisible():
            self._position_notification()

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
            if item.widget():
                item.widget().deleteLater()

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
