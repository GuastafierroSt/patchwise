"""Reusable Liquid Glass update management view shared by Apps and Drivers sections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRect,
    Qt,
    QTimer,
)
from PySide6.QtGui import QPixmap, QRegion
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from patchwise.core.controller import UpdateManagerController
from patchwise.models import DownloadProgress, UpdateCandidate, UpdatePhase, UpdateRecord
from patchwise.ui.widgets import (
    ActiveDownloadBanner,
    AnimatedChevronButton,
    AppUpdateCard,
    GlassSheetTransitionOverlay,
)
from patchwise.ui.workers import ScanWorker, UpdateWorker


@dataclass(frozen=True)
class UpdateSectionConfig:
    """Copy & domain labels customizing an UpdateSectionView for Apps or Drivers."""

    page_title: str
    search_placeholder: str
    idle_headline: str
    idle_subtitle: str
    scanning_headline: str
    all_updated_headline: str
    found_headline_tpl: str
    installed_sub_word: str
    installed_chip_tpl: str
    updated_chip_tpl: str
    list_card_title: str
    empty_filter_text: str
    none_selected_text: str
    selected_summary_tpl: str
    update_all_label: str
    update_selected_label: str
    expand_tooltip: str
    collapse_tooltip: str
    single_success_title: str
    single_failed_title: str
    single_cancelled_title: str
    batch_success_tpl: str
    batch_mixed_tpl: str
    batch_failed_tpl: str


APPS_SECTION_CONFIG = UpdateSectionConfig(
    page_title="Aggiornamenti App",
    search_placeholder="Cerca programmi installati o aggiornamenti...",
    idle_headline="Pronto per la scansione delle applicazioni",
    idle_subtitle="Premi 'Nuova Scansione' per rilevare le app sul PC e confrontarle con le versioni online.",
    scanning_headline="Analisi applicazioni installate...",
    all_updated_headline="Tutte le applicazioni sono aggiornate",
    found_headline_tpl="{pending} aggiornamenti disponibili trovati",
    installed_sub_word="applicazioni rilevate sul PC",
    installed_chip_tpl="{n} app rilevate",
    updated_chip_tpl="{n} aggiornate",
    list_card_title="Applicazioni da aggiornare",
    empty_filter_text="Nessun aggiornamento in sospeso corrispondente al filtro.",
    none_selected_text="Nessuna app selezionata",
    selected_summary_tpl="{selected} di {total} selezionate",
    update_all_label="Aggiorna tutto",
    update_selected_label="Aggiorna selezionate",
    expand_tooltip="Espandi elenco applicazioni",
    collapse_tooltip="Nascondi elenco applicazioni",
    single_success_title="Aggiornamento completato",
    single_failed_title="Aggiornamento non riuscito",
    single_cancelled_title="Aggiornamento annullato",
    batch_success_tpl="{ok} applicazioni aggiornate con successo.",
    batch_mixed_tpl="{ok} completati, {fail} non riusciti o annullati.",
    batch_failed_tpl="Nessun aggiornamento completato ({fail} non riusciti o annullati).",
)


DRIVERS_SECTION_CONFIG = UpdateSectionConfig(
    page_title="Aggiorna Driver",
    search_placeholder="Cerca driver o periferiche hardware...",
    idle_headline="Pronto per la scansione dei driver",
    idle_subtitle="Premi 'Nuova Scansione' per rilevare i driver di sistema e verificare aggiornamenti ufficiali WHQL.",
    scanning_headline="Analisi driver di sistema in corso...",
    all_updated_headline="Tutti i driver sono aggiornati",
    found_headline_tpl="{pending} aggiornamenti driver disponibili",
    installed_sub_word="driver di sistema rilevati sul PC",
    installed_chip_tpl="{n} driver rilevati",
    updated_chip_tpl="{n} aggiornati",
    list_card_title="Driver da aggiornare",
    empty_filter_text="Nessun aggiornamento driver corrispondente al filtro.",
    none_selected_text="Nessun driver selezionato",
    selected_summary_tpl="{selected} di {total} selezionati",
    update_all_label="Aggiorna tutto",
    update_selected_label="Aggiorna selezionati",
    expand_tooltip="Espandi elenco driver",
    collapse_tooltip="Nascondi elenco driver",
    single_success_title="Driver aggiornato",
    single_failed_title="Aggiornamento driver non riuscito",
    single_cancelled_title="Aggiornamento driver annullato",
    batch_success_tpl="{ok} driver aggiornati con successo.",
    batch_mixed_tpl="{ok} driver aggiornati, {fail} non riusciti o annullati.",
    batch_failed_tpl="Nessun driver aggiornato ({fail} non riusciti o annullati).",
)


class UpdateSectionView(QWidget):
    """Two-section Apple Liquid Glass view for scanning and updating Apps or Drivers."""

    def __init__(
        self,
        controller: UpdateManagerController,
        config: UpdateSectionConfig,
        on_notify: Callable[..., None],
        on_history_changed: Callable[[], None],
        on_controls_changed: Callable[[], None],
        on_request_scan: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("GlassPage")
        self.controller = controller
        self.config = config
        self._on_notify = on_notify
        self._on_history_changed = on_history_changed
        self._on_controls_changed = on_controls_changed
        self._on_request_scan = on_request_scan

        self._scan_worker: Optional[ScanWorker] = None
        self._update_worker: Optional[UpdateWorker] = None
        self._card_map: Dict[str, AppUpdateCard] = {}
        self._pending_rescan: bool = False
        self._expanded: bool = False
        self._search_query: str = ""
        self._updates_anim: Optional[QPropertyAnimation] = None
        self._updates_anim_timer = QTimer(self)
        self._updates_anim_timer.setSingleShot(True)
        self._updates_anim_timer.timeout.connect(self._start_pending_updates_anim)

        self._build_ui()
        self.refresh_summary_chips()
        self.refresh_selection_controls()

    @property
    def is_expanded(self) -> bool:
        return self._expanded

    @property
    def search_query(self) -> str:
        return self._search_query

    @property
    def is_scanning(self) -> bool:
        return bool(self._scan_worker and self._scan_worker.isRunning())

    @property
    def is_updating(self) -> bool:
        return bool(self._update_worker and self._update_worker.isRunning())

    def _build_ui(self) -> None:
        self.section_layout = QVBoxLayout(self)
        self.section_layout.setContentsMargins(26, 22, 26, 22)
        self.section_layout.setSpacing(16)

        # SECTION 1: Compact Liquid Glass summary card
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
        self.hero_headline = QLabel(self.config.idle_headline)
        self.hero_headline.setObjectName("Headline")
        self.hero_subtitle = QLabel(self.config.idle_subtitle)
        self.hero_subtitle.setObjectName("MutedText")
        title_col.addWidget(self.hero_headline)
        title_col.addWidget(self.hero_subtitle)

        chips_row = QHBoxLayout()
        chips_row.setSpacing(8)
        self.chip_installed = QLabel(self.config.installed_chip_tpl.format(n=0))
        self.chip_installed.setObjectName("StatChip")
        self.chip_pending = QLabel("0 disponibili")
        self.chip_pending.setObjectName("StatChip")
        self.chip_updated = QLabel(self.config.updated_chip_tpl.format(n=0))
        self.chip_updated.setObjectName("StatChip")
        for chip in (self.chip_installed, self.chip_pending, self.chip_updated):
            chips_row.addWidget(chip, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.expand_updates_btn = AnimatedChevronButton()
        self.expand_updates_btn.setToolTip(self.config.expand_tooltip)
        self.expand_updates_btn.clicked.connect(self.toggle_updates_list)

        hero_header.addLayout(title_col, stretch=1)
        hero_header.addLayout(chips_row)
        hero_header.addWidget(self.expand_updates_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        hero_layout.addWidget(self.hero_header_widget)

        # Standalone active download section ABOVE the Summary recap, visible ONLY while running
        self.download_banner = ActiveDownloadBanner(
            on_pause_toggle=self.toggle_pause,
            on_cancel=self.cancel_active_update,
        )

        # SECTION 2: Separate Liquid Glass card dedicated to the items list
        self.updates_card = QFrame()
        self.updates_card.setObjectName("UpdatesListCard")
        self.updates_body = self.updates_card  # Compatibility alias
        list_card_layout = QVBoxLayout(self.updates_card)
        list_card_layout.setContentsMargins(20, 16, 20, 16)
        list_card_layout.setSpacing(12)

        selection_row = QHBoxLayout()
        selection_row.setSpacing(10)
        list_title = QLabel(self.config.list_card_title)
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

        self._bottom_spacer = QWidget()
        self._bottom_spacer.setObjectName("TransparentContainer")

        self.section_layout.addWidget(self.download_banner, stretch=0)
        self.section_layout.addWidget(self.hero_card, stretch=0)
        self.section_layout.addWidget(self.updates_card, stretch=0)
        self.section_layout.addWidget(self._bottom_spacer, stretch=1)

        # Floating zero-layout 60fps transition overlay
        self._updates_overlay = GlassSheetTransitionOverlay(self)

    def set_icon_color(self, color: str) -> None:
        self.expand_updates_btn.set_chevron_color(color)

    def set_search_query(self, text: str) -> None:
        self._search_query = text
        self.render_candidates()

    def get_primary_cta_state(self) -> tuple[str, bool]:
        """Return (label, enabled) for the TopBar primary batch-update CTA button."""
        actionable = self._actionable_candidates()
        total = len(actionable)
        selected_count = sum(1 for c in actionable if c.selected)
        all_selected = total > 0 and selected_count == total
        label = (
            self.config.update_all_label if all_selected else self.config.update_selected_label
        )
        enabled = selected_count > 0 and not self.is_updating
        return label, enabled

    def get_scan_button_state(self) -> tuple[str, bool]:
        """Return (label, enabled) for the TopBar scan button."""
        if self.is_scanning:
            return "Scansione in corso...", False
        return "Nuova Scansione", True

    def _compute_updates_card_rect(self) -> QRect:
        margins = self.section_layout.contentsMargins()
        spacing = self.section_layout.spacing()
        page_w = max(360, self.width())
        page_h = max(360, self.height())

        top_y = self.hero_card.geometry().bottom() + 1 + spacing
        w = max(320, page_w - margins.left() - margins.right())
        h = max(200, page_h - margins.bottom() - top_y)
        return QRect(margins.left(), top_y, w, h)

    def _capture_updates_card_snapshot(self, rect: QRect) -> QPixmap:
        w = max(1, rect.width())
        h = max(1, rect.height())
        dpr = max(1.0, float(self.devicePixelRatioF()))

        pixmap = QPixmap(int(round(w * dpr)), int(round(h * dpr)))
        pixmap.setDevicePixelRatio(dpr)
        pixmap.fill(Qt.GlobalColor.transparent)

        was_visible = self.updates_card.isVisible()
        if not was_visible:
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

    def toggle_updates_list(self) -> None:
        self.set_updates_expanded(not self._expanded, animate=True)

    def set_updates_expanded(self, expanded: bool, animate: bool = True) -> None:
        self._expanded = expanded
        use_anim = animate and self.isVisible()

        self._updates_anim_timer.stop()
        if self._updates_anim is not None:
            self._updates_anim.stop()

        self.expand_updates_btn.set_expanded(expanded, animate=use_anim)
        self.expand_updates_btn.setToolTip(
            self.config.collapse_tooltip if expanded else self.config.expand_tooltip
        )

        if not use_anim:
            self._updates_overlay.hide()
            self._updates_overlay.progress = 1.0 if expanded else 0.0
            self.updates_card.setVisible(expanded)
            self._bottom_spacer.setVisible(not expanded)
            self.section_layout.setStretchFactor(self.updates_card, 1 if expanded else 0)
            self.section_layout.setStretchFactor(self._bottom_spacer, 0 if expanded else 1)
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
            self._bottom_spacer.setVisible(True)
            self.section_layout.setStretchFactor(self.updates_card, 0)
            self.section_layout.setStretchFactor(self._bottom_spacer, 1)

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
                self._bottom_spacer.setVisible(True)
                self.section_layout.setStretchFactor(self.updates_card, 0)
                self.section_layout.setStretchFactor(self._bottom_spacer, 1)
                return

            self.updates_card.setVisible(False)
            self._bottom_spacer.setVisible(True)
            self.section_layout.setStretchFactor(self.updates_card, 0)
            self.section_layout.setStretchFactor(self._bottom_spacer, 1)
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
        if not self._expanded:
            return
        self._updates_overlay.hide()
        self._updates_overlay.progress = 1.0
        self._bottom_spacer.setVisible(False)
        self.updates_card.setVisible(True)
        self.section_layout.setStretchFactor(self.updates_card, 1)
        self.section_layout.setStretchFactor(self._bottom_spacer, 0)

    def _on_updates_collapse_finished(self) -> None:
        if self._expanded:
            return
        self._updates_overlay.hide()
        self._updates_overlay.progress = 0.0
        self.updates_card.setVisible(False)
        self._bottom_spacer.setVisible(True)
        self.section_layout.setStretchFactor(self.updates_card, 0)
        self.section_layout.setStretchFactor(self._bottom_spacer, 1)

    def refresh_summary_chips(self) -> None:
        metrics = self.controller.get_summary_metrics()
        self.chip_installed.setText(
            self.config.installed_chip_tpl.format(n=metrics["total_installed"])
        )
        self.chip_pending.setText(f"{metrics['pending_updates']} disponibili")
        self.chip_updated.setText(
            self.config.updated_chip_tpl.format(n=metrics["updated_this_session"])
        )

    def start_scan(self) -> None:
        if self._scan_worker and self._scan_worker.isRunning():
            return
        self.hero_headline.setText(self.config.scanning_headline)
        self._scan_worker = ScanWorker(self.controller)
        self._scan_worker.scan_finished.connect(self.on_scan_finished)
        self._scan_worker.scan_failed.connect(self.on_scan_failed)
        self._scan_worker.start()
        self._on_controls_changed()

    def on_scan_finished(self, candidates: List[UpdateCandidate]) -> None:
        total = len(self.controller.installed_apps)
        pending = len(candidates)
        self.hero_headline.setText(
            self.config.found_headline_tpl.format(pending=pending)
            if pending
            else self.config.all_updated_headline
        )
        self.hero_subtitle.setText(
            f"Ultima scansione: {self.controller.last_scan_at}  ·  "
            f"{total} {self.config.installed_sub_word}"
        )
        self.refresh_summary_chips()
        self.render_candidates()
        self.refresh_selection_controls()
        self._on_controls_changed()
        if self._pending_rescan:
            self._pending_rescan = False
            self._trigger_rescan()

    def on_scan_failed(self, error_msg: str) -> None:
        self.hero_headline.setText("Scansione non riuscita")
        self.hero_subtitle.setText(error_msg)
        self._on_controls_changed()
        if self._pending_rescan:
            self._pending_rescan = False
            self._trigger_rescan()

    def render_candidates(self) -> None:
        while self.updates_layout.count():
            item = self.updates_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

        self._card_map.clear()
        query = self._search_query.strip().lower()
        visible = [
            c
            for c in self.controller.candidates
            if not query
            or query in c.name.lower()
            or query in c.app.publisher.lower()
            or query in c.app.device_class.lower()
        ]

        if not visible:
            empty = QLabel(self.config.empty_filter_text)
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

    def refresh_selection_controls(self) -> None:
        actionable = self._actionable_candidates()
        total = len(actionable)
        selected_count = sum(1 for c in actionable if c.selected)
        all_selected = total > 0 and selected_count == total

        self.select_all_btn.setText("Deseleziona tutto" if all_selected else "Seleziona tutto")
        self.select_all_btn.setEnabled(total > 0 and not self.is_updating)

        if total == 0:
            self.selection_summary_label.setText("")
        elif selected_count == 0:
            self.selection_summary_label.setText(self.config.none_selected_text)
        else:
            self.selection_summary_label.setText(
                self.config.selected_summary_tpl.format(selected=selected_count, total=total)
            )

        self._on_controls_changed()

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
        self.refresh_selection_controls()

    def _on_candidate_selected(self, candidate: UpdateCandidate, selected: bool) -> None:
        candidate.selected = selected
        self.refresh_selection_controls()

    def start_single_update(self, candidate: UpdateCandidate) -> None:
        self._launch_update_worker([candidate])

    def start_batch_update(self) -> None:
        selected = [c for c in self._actionable_candidates() if c.selected]
        if selected:
            self._launch_update_worker(selected)

    def _launch_update_worker(self, candidates: List[UpdateCandidate]) -> None:
        if self._update_worker and self._update_worker.isRunning():
            return
        self.select_all_btn.setEnabled(False)
        self._update_worker = UpdateWorker(self.controller, candidates)
        self._update_worker.progress_changed.connect(self.on_progress_changed)
        self._update_worker.item_completed.connect(self.on_item_completed)
        self._update_worker.batch_finished.connect(self.on_batch_finished)
        self._update_worker.start()
        self._on_controls_changed()

    def on_progress_changed(self, progress: DownloadProgress) -> None:
        self.download_banner.update_progress(progress)
        card = self._card_map.get(progress.app_id)
        if card:
            card.set_updating_state(progress.phase)

    def on_item_completed(self, record: UpdateRecord) -> None:
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

        self._on_history_changed()
        self.refresh_summary_chips()
        self.refresh_selection_controls()

        category_label = (
            "Driver · Windows Update" if record.item_type == "driver" else "App · Winget"
        )
        if record.status == "success":
            success_details = (
                f"Elemento: {record.app_name} ({record.publisher})\n"
                f"Versione: {record.from_version} → {record.to_version}\n"
                f"Durata: {record.duration_seconds:.1f}s\n"
                f"Completato alle: {record.completed_at}"
            )
            self._on_notify(
                self.config.single_success_title,
                f"{record.app_name} aggiornato alla v{record.to_version}.",
                "success",
                success_details,
                category_label,
            )
        elif record.status == "cancelled":
            cancel_detail = record.error_details or (
                f"Elemento: {record.app_name} ({record.publisher})\n"
                f"Versione: {record.from_version} → {record.to_version}\n"
                f"Motivo: {record.error_message or 'Operazione annullata dall’utente.'}"
            )
            self._on_notify(
                self.config.single_cancelled_title,
                f"L'aggiornamento di {record.app_name} è stato annullato.",
                "warning",
                cancel_detail,
                category_label,
            )
        else:
            detail = f": {record.error_message}" if record.error_message else "."
            rich_details = record.error_details or (
                f"Elemento: {record.app_name} ({record.publisher})\n"
                f"Versione: {record.from_version} → {record.to_version}\n"
                f"Orario: {record.completed_at}\n"
                f"Durata: {record.duration_seconds:.1f}s\n\n"
                f"ERRORE RILEVATO\n{record.error_message or 'Errore sconosciuto.'}"
            )
            self._on_notify(
                self.config.single_failed_title,
                f"Impossibile aggiornare {record.app_name}{detail}",
                "warning",
                rich_details,
                category_label,
            )

    def on_batch_finished(self, records: List[UpdateRecord]) -> None:
        self.download_banner.reset()
        self.refresh_selection_controls()

        succeeded = [r for r in records if r.status == "success"]
        failed = [r for r in records if r.status != "success"]

        if len(records) > 1:
            if succeeded and not failed:
                self._on_notify(
                    "Aggiornamenti completati",
                    self.config.batch_success_tpl.format(ok=len(succeeded)),
                    "success",
                )
            elif succeeded and failed:
                self._on_notify(
                    "Aggiornamenti completati con avvisi",
                    self.config.batch_mixed_tpl.format(ok=len(succeeded), fail=len(failed)),
                    "warning",
                )
            elif failed:
                self._on_notify(
                    "Aggiornamenti non riusciti",
                    self.config.batch_failed_tpl.format(fail=len(failed)),
                    "warning",
                )

        if succeeded:
            if self._scan_worker and self._scan_worker.isRunning():
                self._pending_rescan = True
            else:
                self._trigger_rescan()

    def _trigger_rescan(self) -> None:
        if self._on_request_scan is not None:
            self._on_request_scan()
        else:
            self.start_scan()

    def toggle_pause(self) -> None:
        if not self._update_worker:
            return
        if self._update_worker.control.is_paused:
            self._update_worker.control.resume()
        else:
            self._update_worker.control.pause()

    def cancel_active_update(self) -> None:
        if self._update_worker:
            self._update_worker.control.cancel()

    def shutdown_workers(self) -> None:
        """Stop any running background scan/update QThreads cleanly when closing the window."""
        self.cancel_active_update()
        for worker in (self._scan_worker, self._update_worker):
            if worker is not None and worker.isRunning():
                worker.requestInterruption()
                if not worker.wait(400):
                    worker.terminate()
                    worker.wait(300)
