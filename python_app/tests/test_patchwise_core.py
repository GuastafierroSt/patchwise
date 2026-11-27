"""Unit test suite for PatchWise Python OOP core hierarchy and build config."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Optional, Sequence
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from build_portable import build_pyinstaller_command
from patchwise import __auto_update_allowed__
from patchwise.core.checkers import VersionChecker, WingetVersionChecker
from patchwise.core.controller import UpdateManagerController
from patchwise.core.detectors import AppDetector, CompositeAppDetector, WingetDetector
from patchwise.core.installer import AppUpdater, ProgressCallback, UpdateControlToken
from patchwise.core.session_history import StatelessSessionHistoryManager
from patchwise.core.version_utils import compare_versions, is_update_available
from patchwise.models import (
    DownloadProgress,
    InstalledApp,
    OnlineVersionInfo,
    UpdateCandidate,
    UpdateCategory,
    UpdatePhase,
    UpdateRecord,
)


class StubDetector(AppDetector):
    def __init__(self, name: str, apps: List[InstalledApp]) -> None:
        self._name = name
        self._apps = apps

    @property
    def provider_name(self) -> str:
        return self._name

    def detect(self) -> List[InstalledApp]:
        return list(self._apps)


class StubVersionChecker(VersionChecker):
    def __init__(self, remote: Dict[str, OnlineVersionInfo]) -> None:
        self._remote = remote

    @property
    def provider_name(self) -> str:
        return "stub-remote"

    def fetch_latest_versions(
        self, installed_apps: Sequence[InstalledApp]
    ) -> Dict[str, OnlineVersionInfo]:
        return dict(self._remote)


class StubUpdater(AppUpdater):
    def can_handle(self, candidate: UpdateCandidate) -> bool:
        return True

    def execute_update(
        self,
        candidate: UpdateCandidate,
        on_progress: ProgressCallback,
        control: Optional[UpdateControlToken] = None,
    ) -> UpdateRecord:
        for pct, phase in (
            (25.0, UpdatePhase.DOWNLOADING),
            (75.0, UpdatePhase.DOWNLOADING),
            (90.0, UpdatePhase.VERIFYING),
            (100.0, UpdatePhase.COMPLETED),
        ):
            on_progress(
                DownloadProgress(
                    app_id=candidate.app_id,
                    app_name=candidate.name,
                    phase=phase,
                    percent=pct,
                    downloaded_mb=round(candidate.online.size_mb * pct / 100.0, 2),
                    total_mb=candidate.online.size_mb,
                )
            )
        return self._build_record(candidate, "success", started_at=0.0)


class PatchWiseCoreTests(unittest.TestCase):
    def test_auto_update_is_strictly_disabled(self) -> None:
        self.assertFalse(__auto_update_allowed__)
        self.assertFalse(UpdateManagerController.AUTO_UPDATE_ALLOWED)
        self.assertFalse(AppUpdater.AUTO_UPDATE_SUPPORTED)

    def test_version_comparison_handles_multi_segment_versions(self) -> None:
        self.assertEqual(compare_versions("123.0.6312.86", "124.0.6367.60"), -1)
        self.assertEqual(compare_versions("3.0.21", "3.0.21"), 0)
        self.assertEqual(compare_versions("24.05", "23.01"), 1)
        self.assertTrue(is_update_available("v1.88.1", "1.89.0"))
        self.assertFalse(is_update_available("3.0.21", "3.0.18"))

    def test_composite_detector_deduplicates_and_merges_metadata(self) -> None:
        reg = StubDetector(
            "registry",
            [
                InstalledApp(
                    app_id="google-chrome",
                    name="Google Chrome",
                    publisher="Google LLC",
                    installed_version="123.0.6312.86",
                    source="registry",
                    install_location=r"C:\Program Files\Google\Chrome",
                )
            ],
        )
        winget = StubDetector(
            "winget",
            [
                InstalledApp(
                    app_id="google-chrome",
                    name="Google Chrome",
                    publisher="Google",
                    installed_version="123.0.6312.86",
                    source="winget",
                    winget_id="Google.Chrome",
                )
            ],
        )
        merged = CompositeAppDetector([reg, winget]).detect()
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].winget_id, "Google.Chrome")
        self.assertEqual(merged[0].publisher, "Google LLC")

    def test_winget_parsers_extract_apps_and_upgrades(self) -> None:
        sample_list = (
            "Name                  Id                  Version       Source\n"
            "---------------------------------------------------------------\n"
            "Google Chrome         Google.Chrome       123.0.6312.86 winget\n"
            "7-Zip 23.01           7zip.7zip           23.01         winget\n"
        )
        apps = WingetDetector().parse_winget_list_output(sample_list)
        self.assertEqual(len(apps), 2)
        self.assertEqual(apps[0].winget_id, "Google.Chrome")

        sample_upgrade = (
            "Name                  Id                  Version       Available     Source\n"
            "----------------------------------------------------------------------------\n"
            "Google Chrome         Google.Chrome       123.0.6312.86 124.0.6367.60 winget\n"
        )
        found = WingetVersionChecker().parse_winget_upgrade_output(sample_upgrade, apps)
        self.assertIn("google-chrome", found)
        self.assertEqual(found["google-chrome"].latest_version, "124.0.6367.60")

    def test_stateless_session_history_keeps_only_last_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot_file = Path(tmp) / "patchwise_last_session.json"

            # Session 1: update Chrome
            s1 = StatelessSessionHistoryManager(snapshot_path=snapshot_file)
            s1.record_update(
                UpdateRecord(
                    record_id="r1",
                    app_id="google-chrome",
                    app_name="Google Chrome",
                    publisher="Google LLC",
                    from_version="123.0",
                    to_version="124.0",
                    size_mb=136.0,
                    category=UpdateCategory.SECURITY,
                    status="success",
                    duration_seconds=4.2,
                )
            )
            s1.finalize_session()

            # Session 2: sees Chrome from Session 1 in last_session, updates 7-Zip
            s2 = StatelessSessionHistoryManager(snapshot_path=snapshot_file)
            self.assertEqual(len(s2.get_current_session_records()), 0)
            self.assertEqual(len(s2.get_last_session_records()), 1)
            self.assertEqual(s2.get_last_session_records()[0].app_name, "Google Chrome")

            s2.record_update(
                UpdateRecord(
                    record_id="r2",
                    app_id="7-zip",
                    app_name="7-Zip",
                    publisher="Igor Pavlov",
                    from_version="23.01",
                    to_version="24.05",
                    size_mb=1.8,
                    category=UpdateCategory.PATCH,
                    status="success",
                    duration_seconds=1.1,
                )
            )
            s2.finalize_session()

            # Session 3: sees ONLY Session 2 (7-Zip); Session 1 (Chrome) is gone!
            s3 = StatelessSessionHistoryManager(snapshot_path=snapshot_file)
            last_names = [r.app_name for r in s3.get_last_session_records()]
            self.assertEqual(last_names, ["7-Zip"])

    def test_controller_scan_and_manual_update_emits_progress_and_records_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            history = StatelessSessionHistoryManager(Path(tmp) / "snap.json")
            apps = [
                InstalledApp(
                    app_id="vlc",
                    name="VLC Media Player",
                    publisher="VideoLAN",
                    installed_version="3.0.18",
                    source="winget",
                    winget_id="VideoLAN.VLC",
                )
            ]
            remote = {
                "vlc": OnlineVersionInfo(
                    app_id="vlc",
                    latest_version="3.0.21",
                    size_mb=42.0,
                    category=UpdateCategory.SECURITY,
                )
            }
            controller = UpdateManagerController(
                detector=StubDetector("stub", apps),
                checker=StubVersionChecker(remote),
                updaters=[StubUpdater()],
                history=history,
            )
            candidates = controller.scan_system()
            self.assertEqual(len(candidates), 1)

            progress_events: List[DownloadProgress] = []
            record = controller.update_single(candidates[0], progress_events.append)
            self.assertEqual(record.status, "success")
            self.assertEqual(progress_events[-1].percent, 100.0)
            self.assertEqual(len(controller.history.get_current_session_records()), 1)

    def test_portable_exe_build_script_configures_onefile_windowed(self) -> None:
        cmd = build_pyinstaller_command(PROJECT_ROOT, exe_name="PatchWise_Portable")
        self.assertIn("--onefile", cmd)
        self.assertIn("--windowed", cmd)
        self.assertIn("PatchWise_Portable", cmd)
        self.assertIn("--icon", cmd)
        self.assertIn("--add-data", cmd)
        self.assertTrue(any("patchwise.ico" in arg for arg in cmd))


try:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from patchwise.ui.main_window import PatchWiseMainWindow
    from patchwise.ui.widgets import ActiveDownloadBanner

    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False


@unittest.skipUnless(HAS_PYSIDE6, "PySide6 non disponibile nell'ambiente di test")
class PatchWiseUiFeedbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def _make_window(self, tmp_dir: str) -> "PatchWiseMainWindow":
        history = StatelessSessionHistoryManager(Path(tmp_dir) / "snap.json")
        controller = UpdateManagerController(
            detector=StubDetector("stub", []),
            checker=StubVersionChecker({}),
            updaters=[StubUpdater()],
            history=history,
        )
        window = PatchWiseMainWindow(controller=controller)
        self.addCleanup(window.close)
        return window

    def test_active_download_banner_resets_after_completion_or_failure(self) -> None:
        banner = ActiveDownloadBanner(on_pause_toggle=lambda: None, on_cancel=lambda: None)
        self.addCleanup(banner.deleteLater)

        banner.update_progress(
            DownloadProgress(
                app_id="teams",
                app_name="Microsoft Teams",
                phase=UpdatePhase.DOWNLOADING,
                percent=55.0,
                message="Download in corso...",
            )
        )
        self.assertIn("Microsoft Teams", banner.title_label.text())
        self.assertEqual(banner.progress_bar.value(), 55)
        self.assertTrue(banner.cancel_btn.isEnabled())

        banner.update_progress(
            DownloadProgress(
                app_id="teams",
                app_name="Microsoft Teams",
                phase=UpdatePhase.COMPLETED,
                percent=100.0,
                message="Completato",
            )
        )
        self.assertEqual(banner.title_label.text(), ActiveDownloadBanner.IDLE_TITLE)
        self.assertEqual(banner.progress_bar.value(), 0)
        self.assertFalse(banner.cancel_btn.isEnabled())
        self.assertFalse(banner.pause_btn.isEnabled())

        banner.update_progress(
            DownloadProgress(
                app_id="chrome",
                app_name="Google Chrome",
                phase=UpdatePhase.DOWNLOADING,
                percent=30.0,
                message="Download in corso...",
            )
        )
        banner.update_progress(
            DownloadProgress(
                app_id="chrome",
                app_name="Google Chrome",
                phase=UpdatePhase.FAILED,
                percent=30.0,
                message="Errore",
            )
        )
        self.assertEqual(banner.title_label.text(), ActiveDownloadBanner.IDLE_TITLE)
        self.assertEqual(banner.progress_bar.value(), 0)
        self.assertFalse(banner.cancel_btn.isEnabled())

    def test_successful_update_shows_success_toast_clears_banner_and_starts_rescan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            window = self._make_window(tmp)
            window.show()
            record = UpdateRecord(
                record_id="r-ok",
                app_id="teams",
                app_name="Microsoft Teams",
                publisher="Microsoft",
                from_version="1.0",
                to_version="2.0",
                size_mb=90.0,
                category=UpdateCategory.PATCH,
                status="success",
                duration_seconds=3.5,
            )

            window._on_progress_changed(
                DownloadProgress(
                    app_id="teams",
                    app_name="Microsoft Teams",
                    phase=UpdatePhase.DOWNLOADING,
                    percent=70.0,
                    message="Download...",
                )
            )
            with patch.object(window, "start_scan") as mock_scan:
                window._on_item_completed(record)
                window._on_batch_finished([record])

                self.assertEqual(
                    window.download_banner.title_label.text(), ActiveDownloadBanner.IDLE_TITLE
                )
                self.assertEqual(window.download_banner.progress_bar.value(), 0)
                self.assertTrue(window.notification_banner.isVisible())
                self.assertEqual(window.notification_banner.level, "success")
                self.assertIn("Microsoft Teams", window.notification_banner.message_label.text())
                mock_scan.assert_called_once()

    def test_failed_update_shows_warning_toast_clears_banner_without_rescan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            window = self._make_window(tmp)
            window.show()
            record = UpdateRecord(
                record_id="r-err",
                app_id="chrome",
                app_name="Google Chrome",
                publisher="Google",
                from_version="158.0",
                to_version="159.0",
                size_mb=120.0,
                category=UpdateCategory.SECURITY,
                status="failed",
                duration_seconds=2.1,
                error_message="Winget terminato con codice 1",
            )

            window._on_progress_changed(
                DownloadProgress(
                    app_id="chrome",
                    app_name="Google Chrome",
                    phase=UpdatePhase.DOWNLOADING,
                    percent=40.0,
                    message="Download...",
                )
            )
            with patch.object(window, "start_scan") as mock_scan:
                window._on_item_completed(record)
                window._on_batch_finished([record])

                self.assertEqual(
                    window.download_banner.title_label.text(), ActiveDownloadBanner.IDLE_TITLE
                )
                self.assertEqual(window.download_banner.progress_bar.value(), 0)
                self.assertTrue(window.notification_banner.isVisible())
                self.assertEqual(window.notification_banner.level, "warning")
                self.assertIn("Google Chrome", window.notification_banner.message_label.text())
                self.assertIn(
                    "Winget terminato con codice 1",
                    window.notification_banner.message_label.text(),
                )
                mock_scan.assert_not_called()

            window.notification_banner.dismiss()
            self.assertFalse(window.notification_banner.isVisible())

    def test_sidebar_collapses_and_expands_via_toggle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            window = self._make_window(tmp)
            self.assertTrue(window.is_sidebar_open)
            self.assertEqual(window.sidebar.maximumWidth(), window.SIDEBAR_WIDTH)
            self.assertTrue(window.topbar_logo.isHidden())

            window.toggle_sidebar(animate=False)
            self.assertFalse(window.is_sidebar_open)
            self.assertEqual(window.sidebar.maximumWidth(), 0)
            self.assertFalse(window.topbar_logo.isHidden())
            self.assertIn("Apri", window.sidebar_toggle_btn.toolTip())

            window.toggle_sidebar(animate=False)
            self.assertTrue(window.is_sidebar_open)
            self.assertEqual(window.sidebar.maximumWidth(), window.SIDEBAR_WIDTH)
            self.assertTrue(window.topbar_logo.isHidden())
            self.assertIn("Chiudi", window.sidebar_toggle_btn.toolTip())

    def test_dark_and_light_theme_switch_and_sans_serif_typography(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            window = self._make_window(tmp)
            self.assertEqual(window.current_theme, "light")
            self.assertFalse(window.dark_theme_toggle.isChecked())
            self.assertFalse(window.windowIcon().isNull())
            self.assertFalse(window.brand_logo.pixmap().isNull())
            self.assertIn("Helvetica", window.styleSheet())
            self.assertNotIn("Noto Serif", window.styleSheet())

            window.dark_theme_toggle.setChecked(True)
            self.assertEqual(window.current_theme, "dark")
            self.assertIn("#0e0b1d", window.styleSheet())
            self.assertIn("#3bdbf6", window.styleSheet())
            self.assertIn("Helvetica", window.styleSheet())

            window.dark_theme_toggle.setChecked(False)
            self.assertEqual(window.current_theme, "light")
            self.assertIn("#f6f5fc", window.styleSheet())
            self.assertIn("#5c4fd6", window.styleSheet())


if __name__ == "__main__":
    unittest.main()
