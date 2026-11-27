"""Main desktop window class for PatchWise Software Updater."""

from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
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
from patchwise.ui.theme import ALEXANDRIA_QSS
from patchwise.ui.widgets import ActiveDownloadBanner, AppUpdateCard, HistoryRowWidget
from patchwise.ui.workers import ScanWorker, UpdateWorker


class PatchWiseMainWindow(QMainWindow):
    """Primary PySide6 desktop shell coordinating scan, updates, progress, and session history."""

    def __init__(self, controller: Optional[UpdateManagerController] = None) -> None:
        super().__init__()
        self.controller = controller or UpdateManagerController()
        self._scan_worker: Optional[ScanWorker] = None
        self._update_worker: Optional[UpdateWorker] = None
        self._card_map: Dict[str, AppUpdateCard] = {}

        self.setWindowTitle(f"PatchWise Desktop — Software Updater v{__version__} (Portable)")
        self.resize(1240, 820)
        self.setStyleSheet(ALEXANDRIA_QSS)

        self._build_layout()
        self._refresh_history_views()

    def _build_layout(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Sidebar navigation
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(260)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(16, 20, 16, 20)
        sb_layout.setSpacing(8)

        brand = QLabel("PatchWise")
        brand.setObjectName("SectionTitle")
        subtitle = QLabel("Software Updater · Portable")
        subtitle.setObjectName("MutedText")
        sb_layout.addWidget(brand)
        sb_layout.addWidget(subtitle)
        sb_layout.addSpacing(18)

        self.nav_dashboard = self._make_nav_button("Dashboard & Aggiornamenti", 0, active=True)
        self.nav_history = self._make_nav_button("Cronologia di Sessione", 1, active=False)
        sb_layout.addWidget(self.nav_dashboard)
        sb_layout.addWidget(self.nav_history)
        sb_layout.addStretch()

        policy_note = QLabel(
            "Modalità stateless attiva:\nnessun auto-update e nessun database permanente."
        )
        policy_note.setObjectName("MutedText")
        policy_note.setWordWrap(True)
        sb_layout.addWidget(policy_note)

        # Content stack
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_dashboard_page())
        self.stack.addWidget(self._build_history_page())

        outer.addWidget(sidebar)
        outer.addWidget(self.stack, stretch=1)

    def _make_nav_button(self, text: str, page_index: int, active: bool) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("NavButton")
        btn.setProperty("active", active)
        btn.clicked.connect(lambda: self._switch_page(page_index))
        return btn

    def _switch_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for idx, btn in enumerate((self.nav_dashboard, self.nav_history)):
            btn.setProperty("active", idx == index)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        if index == 1:
            self._refresh_history_views()

    def _build_dashboard_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        # Top search & controls
        top_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setObjectName("SearchInput")
        self.search_input.setPlaceholderText("Cerca programmi installati o aggiornamenti...")
        self.search_input.textChanged.connect(self._render_candidates)

        self.scan_btn = QPushButton("Nuova Scansione")
        self.scan_btn.setObjectName("SecondaryButton")
        self.scan_btn.clicked.connect(self.start_scan)

        self.update_all_btn = QPushButton("Aggiorna Selezionate")
        self.update_all_btn.setObjectName("PrimaryButton")
        self.update_all_btn.clicked.connect(self.start_batch_update)

        top_row.addWidget(self.search_input, stretch=1)
        top_row.addWidget(self.scan_btn)
        top_row.addWidget(self.update_all_btn)
        layout.addLayout(top_row)

        # Hero summary card
        hero = QFrame()
        hero.setObjectName("HeroCard")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(22, 20, 22, 20)
        hero_layout.setSpacing(12)

        self.hero_headline = QLabel("Pronto per la scansione del sistema")
        self.hero_headline.setObjectName("Headline")
        self.hero_subtitle = QLabel(
            "Premi 'Nuova Scansione' per rilevare le app sul PC e confrontarle con le versioni online."
        )
        self.hero_subtitle.setObjectName("MutedText")

        self.download_banner = ActiveDownloadBanner(
            on_pause_toggle=self._toggle_pause,
            on_cancel=self._cancel_active_update,
        )

        hero_layout.addWidget(self.hero_headline)
        hero_layout.addWidget(self.hero_subtitle)
        hero_layout.addWidget(self.download_banner)
        layout.addWidget(hero)

        # Scrollable updates list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.updates_container = QWidget()
        self.updates_layout = QVBoxLayout(self.updates_container)
        self.updates_layout.setContentsMargins(0, 0, 0, 0)
        self.updates_layout.setSpacing(10)
        self.updates_layout.addStretch()
        scroll.setWidget(self.updates_container)
        layout.addWidget(scroll, stretch=1)

        return page

    def _build_history_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
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
        self.history_layout.setContentsMargins(0, 0, 0, 0)
        self.history_layout.setSpacing(10)
        scroll.setWidget(self.history_container)
        layout.addWidget(scroll, stretch=1)

        return page

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
        self._render_candidates()

    def _on_scan_failed(self, error_msg: str) -> None:
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Nuova Scansione")
        self.hero_headline.setText("Scansione non riuscita")
        self.hero_subtitle.setText(error_msg)

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
        self._update_worker = UpdateWorker(self.controller, candidates)
        self._update_worker.progress_changed.connect(self._on_progress_changed)
        self._update_worker.item_completed.connect(self._on_item_completed)
        self._update_worker.start()

    def _on_progress_changed(self, progress: DownloadProgress) -> None:
        self.download_banner.update_progress(progress)
        card = self._card_map.get(progress.app_id)
        if card:
            card.set_updating_state(progress.phase)

    def _on_item_completed(self, _record: UpdateRecord) -> None:
        self._refresh_history_views()

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
