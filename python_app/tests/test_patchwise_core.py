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

from build_portable import build_pyinstaller_command, ensure_output_writable
from patchwise import __auto_update_allowed__, __version__
from patchwise.core.checkers import VersionChecker, WingetVersionChecker
from patchwise.core.controller import UpdateManagerController
from patchwise.core.detectors import AppDetector, CompositeAppDetector, WingetDetector
from patchwise.core.drivers import (
    WindowsCimDriverDetector,
    WindowsDriverRegistryDetector,
    WindowsUpdateDriverChecker,
    WindowsUpdateDriverUpdater,
)
from patchwise.core.installer import (
    AppUpdater,
    ProgressCallback,
    UpdateControlToken,
    WingetAppUpdater,
)
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

    def test_winget_upgrade_parses_explicit_targeting_table_such_as_discord(self) -> None:
        sample_italian_multi_table = (
            "Nome                                            Id                               Versione      Disponibile   Origine\n"
            "--------------------------------------------------------------------------------------------------------------------\n"
            "Epic Online Services                            EpicGames.EpicOnlineServices     2.8.1         5.8.0         winget\n"
            "Google Chrome                                   Google.Chrome.EXE                158.0.8127.37 158.0.8127.89 winget\n"
            "7 aggiornamenti disponibili.\n"
            "\n"
            "Per i pacchetti seguenti è disponibile un aggiornamento, ma è necessario un targeting esplicito per l'aggiornamento:\n"
            "Nome    Id              Versione Disponibile Origine\n"
            "----------------------------------------------------\n"
            "Discord Discord.Discord 1.0.9269 1.0.9270    winget\n"
            "1 pacchetti contengono numeri di versione che non possono essere determinati. Usare --include-unknown per visualizzare tutti i risultati.\n"
        )
        installed = [
            InstalledApp(
                app_id="epic-online-services",
                name="Epic Online Services",
                publisher="EpicGames",
                installed_version="2.8.1",
                source="winget",
                winget_id="EpicGames.EpicOnlineServices",
            ),
            InstalledApp(
                app_id="google-chrome",
                name="Google Chrome",
                publisher="Google",
                installed_version="158.0.8127.37",
                source="winget",
                winget_id="Google.Chrome.EXE",
            ),
            # Discord detected via Registry only (no winget_id initially)
            InstalledApp(
                app_id="discord",
                name="Discord",
                publisher="Discord Inc.",
                installed_version="1.0.9269",
                source="registry",
                winget_id=None,
            ),
        ]
        checker = WingetVersionChecker()
        found = checker.parse_winget_upgrade_output(sample_italian_multi_table, installed)
        self.assertIn("discord", found)
        self.assertEqual(found["discord"].latest_version, "1.0.9270")
        self.assertIn("targeting esplicito", found["discord"].release_notes)

        candidates = checker.parse_winget_upgrade_candidates(
            sample_italian_multi_table, installed
        )
        by_id = {c.app_id: c for c in candidates}
        self.assertEqual(set(by_id.keys()), {"epic-online-services", "google-chrome", "discord"})
        self.assertEqual(by_id["discord"].app.winget_id, "Discord.Discord")
        self.assertEqual(by_id["discord"].online.latest_version, "1.0.9270")

        # Also works even if Discord was missing from local installed_apps list
        synthesized = checker.parse_winget_upgrade_candidates(
            sample_italian_multi_table, installed[:2]
        )
        self.assertIn("discord", {c.app_id for c in synthesized})
        self.assertTrue(is_update_available("< 1.0.9270", "1.0.9270"))

    def test_winget_updater_falls_back_to_interactive_on_uninstall_error_2316632112(
        self,
    ) -> None:
        candidate = UpdateCandidate(
            app=InstalledApp(
                app_id="epic-online-services",
                name="Epic Online Services",
                publisher="EpicGames",
                installed_version="2.8.1",
                source="winget",
                winget_id="EpicGames.EpicOnlineServices",
            ),
            online=OnlineVersionInfo(
                app_id="epic-online-services",
                latest_version="5.8.0",
                size_mb=45.0,
            ),
        )

        class _FakeProc:
            def __init__(self, lines: List[str], rc: int) -> None:
                self.stdout = iter(lines)
                self._rc = rc

            def wait(self) -> int:
                return self._rc

            def terminate(self) -> None:
                pass

        # Case 1: --silent fails with 2316632112 (0x8A150030), --interactive retry succeeds
        invoked_cmds: List[List[str]] = []

        def _fake_popen_recover(cmd, **kwargs):
            invoked_cmds.append(list(cmd))
            if "--silent" in cmd:
                return _FakeProc(
                    [
                        "Verifica dell'hash di installazione completata\n",
                        "Avvio disinstallazione pacchetto in corso...\n",
                    ],
                    2316632112,
                )
            return _FakeProc(
                [
                    "Avvio disinstallazione pacchetto in corso...\n",
                    "Avvio installazione pacchetto in corso...\n",
                ],
                0,
            )

        events: List[DownloadProgress] = []
        with patch("patchwise.core.installer.subprocess.Popen", side_effect=_fake_popen_recover):
            record = WingetAppUpdater().execute_update(candidate, events.append)

        self.assertEqual(record.status, "success")
        self.assertEqual(len(invoked_cmds), 2)
        self.assertIn("--silent", invoked_cmds[0])
        self.assertIn("--interactive", invoked_cmds[1])
        self.assertNotIn("--silent", invoked_cmds[1])
        self.assertTrue(
            any("Disinstallazione versione precedente" in e.message for e in events)
        )
        self.assertTrue(any("interattiva" in e.message for e in events))

        # Case 2: both --silent and --interactive fail with 2316632112 -> friendly Italian message
        def _fake_popen_fail(cmd, **kwargs):
            return _FakeProc(["Avvio disinstallazione pacchetto in corso...\n"], 2316632112)

        fail_events: List[DownloadProgress] = []
        with patch("patchwise.core.installer.subprocess.Popen", side_effect=_fake_popen_fail):
            fail_record = WingetAppUpdater().execute_update(candidate, fail_events.append)

        self.assertEqual(fail_record.status, "failed")
        self.assertIn("0x8A150030", fail_record.error_message)
        self.assertIn("Disinstallazione della versione precedente", fail_record.error_message)

        # Case 3: user cancels interactive wizard (1602) -> status is cancelled, not failed
        def _fake_popen_cancel(cmd, **kwargs):
            if "--silent" in cmd:
                return _FakeProc([], 2316632112)
            return _FakeProc([], 1602)

        with patch("patchwise.core.installer.subprocess.Popen", side_effect=_fake_popen_cancel):
            cancel_record = WingetAppUpdater().execute_update(candidate, lambda _: None)
        self.assertEqual(cancel_record.status, "cancelled")

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

        with tempfile.TemporaryDirectory() as tmp:
            fake_exe = Path(tmp) / "PatchWise_Portable.exe"
            self.assertTrue(ensure_output_writable(fake_exe, kill_running=False))
            fake_exe.write_bytes(b"stub")
            self.assertTrue(ensure_output_writable(fake_exe, kill_running=False))
            self.assertFalse(fake_exe.exists())

    def test_major_version_is_v3_and_driver_engine_parses_wua_and_cim(self) -> None:
        self.assertTrue(__version__.startswith("3."))
        self.assertFalse(WindowsUpdateDriverUpdater.AUTO_UPDATE_SUPPORTED)

        cim_json = (
            '[{"DeviceName": "NVIDIA GeForce RTX 4070", "Manufacturer": "NVIDIA", '
            '"DriverVersion": "32.0.15.6094", "DeviceClass": "DISPLAY", '
            '"HardWareID": "PCI\\\\VEN_10DE&DEV_2786", "InfName": "oem12.inf"}]'
        )
        detected = WindowsCimDriverDetector().parse_cim_json(cim_json)
        self.assertEqual(len(detected), 1)
        self.assertEqual(detected[0].item_type, "driver")
        self.assertEqual(detected[0].device_class, "DISPLAY")

        wua_json = (
            '[{"UpdateID": "uid-nv-001", '
            '"Title": "NVIDIA - Display - 32.0.15.6636", '
            '"Description": "Driver grafico ufficiale WHQL", '
            '"DriverManufacturer": "NVIDIA", '
            '"DriverModel": "NVIDIA GeForce RTX 4070", '
            '"DriverClass": "Display", '
            '"DriverHardwareID": "PCI\\\\VEN_10DE&DEV_2786", '
            '"DriverVerDate": "2026.10.01", '
            '"MaxDownloadSize": 524288000, '
            '"MsrcSeverity": ""}, '
            '{"UpdateID": "uid-fw-002", '
            '"Title": "Intel System Firmware 2.4.1", '
            '"Description": "Aggiornamento sicurezza firmware", '
            '"DriverManufacturer": "Intel", '
            '"DriverModel": "System Firmware", '
            '"DriverClass": "Firmware", '
            '"DriverHardwareID": "UEFI\\\\RES_001", '
            '"DriverVerDate": "2026.11.01", '
            '"MaxDownloadSize": 10485760, '
            '"MsrcSeverity": "Important"}]'
        )
        candidates = WindowsUpdateDriverChecker().parse_wua_driver_updates(wua_json, detected)
        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0].app.installed_version, "32.0.15.6094")
        self.assertEqual(candidates[0].online.latest_version, "32.0.15.6636")
        self.assertEqual(candidates[0].online.category, UpdateCategory.FEATURES)
        self.assertTrue(WindowsUpdateDriverUpdater().can_handle(candidates[0]))
        self.assertEqual(candidates[1].online.category, UpdateCategory.SECURITY)

        if sys.platform.startswith("win"):
            reg_drivers = WindowsDriverRegistryDetector().detect()
            self.assertGreater(len(reg_drivers), 0)
            self.assertTrue(all(d.item_type == "driver" for d in reg_drivers[:5]))

    def test_wua_driver_error_decoder_and_uac_elevation_flow(self) -> None:
        candidate = UpdateCandidate(
            app=InstalledApp(
                app_id="drv-razer",
                name="Razer Synapse4",
                publisher="Razer Inc",
                installed_version="Installata",
                source="windows-update-driver",
                item_type="driver",
                device_class="Extension",
                hardware_id="HID\\VID_1532",
                driver_update_id="uid-razer-001",
            ),
            online=OnlineVersionInfo(
                app_id="drv-razer",
                latest_version="1.20.0.694",
                size_mb=0.0,
                provider="windows-update-driver",
            ),
        )

        # 1. Decode WUA ResultCode 4 with E_ACCESSDENIED (0x80070005)
        summary, details = WindowsUpdateDriverUpdater.decode_wua_failure(
            candidate=candidate,
            meta={
                "phase": "download",
                "result_code": "4",
                "hresult": "0x80240022",
                "update_hresult": "0x80070005",
                "elevated": "False",
                "update_id": "uid-razer-001",
            },
            error_lines=["Download driver fallito (codice WUA 4, HResult 0x80070005)."],
            returncode=3,
        )
        self.assertIn("0x80070005", summary)
        self.assertIn("amministratore", summary.lower())
        self.assertIn("E_ACCESSDENIED", details)
        self.assertIn("uid-razer-001", details)
        self.assertIn("SOLUZIONI CONSIGLIATE", details)

        # 2. Decode WUA ResultCode 4 with 0x80070103 (already installed / redundant)
        summary_103, details_103 = WindowsUpdateDriverUpdater.decode_wua_failure(
            candidate=candidate,
            meta={
                "phase": "install",
                "result_code": "4",
                "update_hresult": "0x80070103",
                "elevated": "True",
            },
            error_lines=[],
            returncode=4,
        )
        self.assertIn("0x80070103", summary_103)
        self.assertIn("ERROR_NO_MORE_ITEMS", details_103)

        # 3. Non-elevated process requests UAC elevation; UAC cancel returns cancelled cleanly
        updater = WindowsUpdateDriverUpdater(use_uac_elevation=True)
        with (
            patch("patchwise.core.drivers.is_process_elevated", return_value=False),
            patch.object(
                updater,
                "_execute_elevated_uac",
                return_value=(None, True, "Autorizzazione Amministratore (UAC) annullata dall'utente."),
            ) as mock_uac,
        ):
            rec = updater.execute_update(candidate, lambda _: None)
            self.assertEqual(rec.status, "cancelled")
            self.assertIn("UAC", rec.error_message)
            mock_uac.assert_called_once()

        # 4. Elevated execution produces rich error_details when WUA returns code 4
        class _FakePsProc:
            def __init__(self, lines: List[str], rc: int) -> None:
                self.stdout = iter(lines)
                self._rc = rc

            def wait(self) -> int:
                return self._rc

            def terminate(self) -> None:
                pass

        with (
            patch("patchwise.core.drivers.is_process_elevated", return_value=True),
            patch(
                "patchwise.core.drivers.subprocess.Popen",
                return_value=_FakePsProc(
                    [
                        "META:elevated=True\n",
                        "META:phase=download\n",
                        "META:result_code=4\n",
                        "META:hresult=0x80240022\n",
                        "META:update_hresult=0x80246007\n",
                        "ERROR:Download driver fallito (codice WUA 4, HResult 0x80246007).\n",
                    ],
                    3,
                ),
            ),
        ):
            rec_fail = updater.execute_update(candidate, lambda _: None)
            self.assertEqual(rec_fail.status, "failed")
            self.assertIn("0x80246007", rec_fail.error_message)
            self.assertIn("WU_E_DM_NOTDOWNLOADED", rec_fail.error_details)
            self.assertIn("BITS", rec_fail.error_details)

        # 5. Elevated temp dir helper uses inherited %TEMP% ACLs (no mkdtemp 0o700 lockout)
        import inspect

        uac_code_lines = [
            ln for ln in inspect.getsource(WindowsUpdateDriverUpdater._execute_elevated_uac).splitlines()
            if not ln.lstrip().startswith("#")
        ]
        uac_code = "\n".join(uac_code_lines)
        self.assertNotIn("mkdtemp(", uac_code)
        self.assertIn("tempfile.gettempdir()", uac_code)
        self.assertIn("ShellExecuteExW.argtypes", uac_code)
        self.assertIn("WaitForSingleObject.argtypes", uac_code)


try:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QAbstractAnimation, QEventLoop, QTimer
    from PySide6.QtWidgets import QApplication

    from patchwise.ui.main_window import PatchWiseMainWindow
    from patchwise.ui.widgets import ActiveDownloadBanner, parse_qcolor

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
            item_type="app",
        )
        driver_controller = UpdateManagerController(
            detector=StubDetector("stub-drv", []),
            checker=StubVersionChecker({}),
            updaters=[StubUpdater()],
            history=history,
            item_type="driver",
        )
        window = PatchWiseMainWindow(
            controller=controller,
            driver_controller=driver_controller,
        )
        self.addCleanup(window.close)
        return window

    def test_active_download_banner_resets_after_completion_or_failure(self) -> None:
        banner = ActiveDownloadBanner(on_pause_toggle=lambda: None, on_cancel=lambda: None)
        self.addCleanup(banner.deleteLater)
        self.assertTrue(banner.isHidden())

        banner.update_progress(
            DownloadProgress(
                app_id="teams",
                app_name="Microsoft Teams",
                phase=UpdatePhase.DOWNLOADING,
                percent=55.0,
                message="Download in corso...",
            )
        )
        self.assertFalse(banner.isHidden())
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
        self.assertTrue(banner.isHidden())
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
        self.assertFalse(banner.isHidden())
        banner.update_progress(
            DownloadProgress(
                app_id="chrome",
                app_name="Google Chrome",
                phase=UpdatePhase.FAILED,
                percent=30.0,
                message="Errore",
            )
        )
        self.assertTrue(banner.isHidden())
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
            self.assertIn("QScrollBar:horizontal", window.styleSheet())
            self.assertIn("QScrollBar::handle:horizontal", window.styleSheet())

    def test_updates_card_starts_collapsed_and_expands_on_click(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            window = self._make_window(tmp)
            self.assertFalse(window.is_updates_expanded)
            self.assertTrue(window.updates_body.isHidden())
            self.assertTrue(window.download_banner.isHidden())

            candidate = UpdateCandidate(
                app=InstalledApp("chrome", "Google Chrome", "Google", "1.0", "winget"),
                online=OnlineVersionInfo("chrome", "2.0"),
            )
            window.controller.candidates = [candidate]
            window._on_scan_finished([candidate])
            # Must stay collapsed initially after scan until user clicks expand icon
            self.assertFalse(window.is_updates_expanded)
            self.assertTrue(window.updates_body.isHidden())

            window.expand_updates_btn.click()
            self.assertTrue(window.is_updates_expanded)
            self.assertFalse(window.updates_body.isHidden())

            window.expand_updates_btn.click()
            self.assertFalse(window.is_updates_expanded)
            self.assertTrue(window.updates_body.isHidden())

    def test_notification_center_tracks_unread_badge_and_clears_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            window = self._make_window(tmp)
            window.show()
            self.assertEqual(window.notifications_btn.unread_count, 0)
            self.assertEqual(len(window.notification_items), 0)

            window.show_notification("Aggiornamento completato", "Teams aggiornato", level="success")
            window.show_notification("Aggiornamento non riuscito", "Chrome fallito", level="warning")
            self.assertEqual(len(window.notification_items), 2)
            self.assertEqual(window.notifications_btn.unread_count, 2)
            self.assertTrue(window.notification_banner.isVisible())

            # Opening the notification center marks all notifications as read
            window.notifications_btn.click()
            self.assertTrue(window.notifications_popover.isVisible())
            self.assertEqual(window.notifications_btn.unread_count, 0)

            window.clear_notifications()
            self.assertEqual(len(window.notification_items), 0)

    def test_select_all_and_deselect_all_updates_cta_label(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            window = self._make_window(tmp)
            self.assertEqual(window.update_all_btn.text(), "Aggiorna selezionate")
            self.assertFalse(window.update_all_btn.isEnabled())
            self.assertEqual(window.select_all_btn.text(), "Seleziona tutto")
            self.assertFalse(window.select_all_btn.isEnabled())

            candidates = [
                UpdateCandidate(
                    app=InstalledApp("chrome", "Google Chrome", "Google", "1.0", "winget"),
                    online=OnlineVersionInfo("chrome", "2.0"),
                ),
                UpdateCandidate(
                    app=InstalledApp("teams", "Microsoft Teams", "Microsoft", "1.0", "winget"),
                    online=OnlineVersionInfo("teams", "2.0"),
                ),
                UpdateCandidate(
                    app=InstalledApp("vlc", "VLC", "VideoLAN", "3.0", "winget"),
                    online=OnlineVersionInfo("vlc", "3.1"),
                ),
            ]
            window.controller.candidates = candidates
            window._on_scan_finished(candidates)

            # All selected initially -> "Aggiorna tutto" + "Deseleziona tutto"
            self.assertEqual(window.update_all_btn.text(), "Aggiorna tutto")
            self.assertTrue(window.update_all_btn.isEnabled())
            self.assertEqual(window.select_all_btn.text(), "Deseleziona tutto")
            self.assertTrue(window.select_all_btn.isEnabled())

            # Click "Deseleziona tutto" -> none selected
            window.select_all_btn.click()
            self.assertTrue(all(not c.selected for c in candidates))
            self.assertEqual(window.select_all_btn.text(), "Seleziona tutto")
            self.assertEqual(window.update_all_btn.text(), "Aggiorna selezionate")
            self.assertFalse(window.update_all_btn.isEnabled())

            # Select a single app -> "Aggiorna selezionate" enabled
            window._card_map["chrome"].checkbox.setChecked(True)
            self.assertEqual(window.update_all_btn.text(), "Aggiorna selezionate")
            self.assertTrue(window.update_all_btn.isEnabled())
            self.assertEqual(window.select_all_btn.text(), "Seleziona tutto")

            # Click "Seleziona tutto" -> back to "Aggiorna tutto"
            window.select_all_btn.click()
            self.assertTrue(all(c.selected for c in candidates))
            self.assertEqual(window.update_all_btn.text(), "Aggiorna tutto")
            self.assertTrue(window.update_all_btn.isEnabled())
            self.assertEqual(window.select_all_btn.text(), "Deseleziona tutto")

    @staticmethod
    def _wait_qt(ms: int) -> None:
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    def test_ui_animations_run_and_complete_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            window = self._make_window(tmp)
            window.show()
            self._wait_qt(30)

            # 1. Theme toggle switch + crossfade overlay animation
            window.dark_theme_toggle.click()
            self.assertEqual(window.current_theme, "dark")
            self.assertIsNotNone(window._theme_fade_anim)
            self._wait_qt(40)
            self.assertEqual(window.dark_theme_toggle._anim.state(), QAbstractAnimation.State.Running)
            self._wait_qt(460)
            self.assertIsNone(window._theme_fade_overlay)
            self.assertAlmostEqual(window.dark_theme_toggle.thumb_position, 1.0, places=2)

            # 2. Expandable updates card accordion + 180° rotating chevron
            window.expand_updates_btn.click()
            self.assertTrue(window.is_updates_expanded)
            self.assertIsNotNone(window._updates_anim)
            self._wait_qt(480)
            self.assertFalse(window.updates_body.isHidden())
            self.assertAlmostEqual(window.expand_updates_btn.rotation_angle, 180.0, places=1)

            window.expand_updates_btn.click()
            self.assertFalse(window.is_updates_expanded)
            self._wait_qt(440)
            self.assertTrue(window.updates_body.isHidden())
            self.assertAlmostEqual(window.expand_updates_btn.rotation_angle, 0.0, places=1)

            # 3. Bell ring wiggle + toast slide + popover slide
            window.show_notification("Test OK", "Animazione notifica", level="success")
            self.assertIsNotNone(window.notifications_btn._ring_group)
            window.toggle_notifications_panel()
            self._wait_qt(360)
            self.assertTrue(window.notifications_popover.isVisible())

    def test_light_theme_checkbox_rgba_parses_to_bright_white(self) -> None:
        from patchwise.ui.theme import get_theme_tokens

        light_bg = parse_qcolor(get_theme_tokens("light")["checkbox_bg"])
        self.assertTrue(light_bg.isValid())
        self.assertEqual((light_bg.red(), light_bg.green(), light_bg.blue()), (255, 255, 255))
        self.assertGreater(light_bg.alpha(), 220)

    def test_drivers_section_matches_apps_workflow_notifications_and_rescan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            window = self._make_window(tmp)
            window.show()

            # Switch to Aggiornamenti Driver tab
            window.nav_drivers.click()
            self.assertEqual(window.stack.currentIndex(), 1)
            self.assertEqual(window.topbar_title.text(), "Aggiornamenti Driver")
            self.assertFalse(window.drivers_section.is_expanded)
            self.assertTrue(window.drivers_section.download_banner.isHidden())

            drivers = [
                UpdateCandidate(
                    app=InstalledApp(
                        "drv-nvidia",
                        "NVIDIA GeForce RTX 4070",
                        "NVIDIA",
                        "32.0.15.6094",
                        "driver-registry",
                        item_type="driver",
                        device_class="DISPLAY",
                        driver_update_id="uid-nv-1",
                    ),
                    online=OnlineVersionInfo("drv-nvidia", "32.0.15.6636", size_mb=512.0),
                ),
                UpdateCandidate(
                    app=InstalledApp(
                        "drv-realtek",
                        "Realtek High Definition Audio",
                        "Realtek",
                        "6.0.9500.1",
                        "driver-registry",
                        item_type="driver",
                        device_class="MEDIA",
                        driver_update_id="uid-rtk-2",
                    ),
                    online=OnlineVersionInfo("drv-realtek", "6.0.9710.1", size_mb=38.0),
                ),
            ]
            window.driver_controller.installed_apps = [d.app for d in drivers]
            window.driver_controller.candidates = drivers
            window.drivers_section.on_scan_finished(drivers)

            # TopBar CTA syncs to Drivers section
            self.assertEqual(window.update_all_btn.text(), "Aggiorna tutto")
            self.assertTrue(window.update_all_btn.isEnabled())
            window.drivers_section.select_all_btn.click()
            self.assertEqual(window.update_all_btn.text(), "Aggiorna selezionati")
            self.assertFalse(window.update_all_btn.isEnabled())
            window.drivers_section.select_all_btn.click()
            self.assertEqual(window.update_all_btn.text(), "Aggiorna tutto")

            # Active download banner appears during driver download and clears on completion
            window.drivers_section.on_progress_changed(
                DownloadProgress(
                    app_id="drv-nvidia",
                    app_name="NVIDIA GeForce RTX 4070",
                    phase=UpdatePhase.DOWNLOADING,
                    percent=45.0,
                    message="Download driver...",
                )
            )
            self.assertFalse(window.drivers_section.download_banner.isHidden())

            ok_record = UpdateRecord(
                record_id="drv-ok",
                app_id="drv-nvidia",
                app_name="NVIDIA GeForce RTX 4070",
                publisher="NVIDIA",
                from_version="32.0.15.6094",
                to_version="32.0.15.6636",
                size_mb=512.0,
                category=UpdateCategory.FEATURES,
                status="success",
                duration_seconds=8.0,
                item_type="driver",
            )
            window.driver_controller.history.record_update(ok_record)
            with patch.object(window, "start_driver_scan") as mock_drv_scan:
                window.drivers_section.on_item_completed(ok_record)
                window.drivers_section.on_batch_finished([ok_record])
                self.assertTrue(window.drivers_section.download_banner.isHidden())
                self.assertEqual(window.notifications_btn.unread_count, 1)
                self.assertIn("NVIDIA", window.notification_banner.message_label.text())
                mock_drv_scan.assert_called_once()

    def test_clicking_error_notification_opens_detail_dialog_with_diagnostics(self) -> None:
        from PySide6.QtCore import QPointF, Qt
        from PySide6.QtGui import QMouseEvent

        with tempfile.TemporaryDirectory() as tmp:
            window = self._make_window(tmp)
            window.show()

            failed_record = UpdateRecord(
                record_id="drv-err-4",
                app_id="drv-razer",
                app_name="Razer Synapse4",
                publisher="Razer Inc",
                from_version="Installata",
                to_version="1.20.0.694",
                size_mb=0.0,
                category=UpdateCategory.PATCH,
                status="failed",
                duration_seconds=2.4,
                error_message="Download driver fallito (WUA 4 · 0x80070005): permessi di amministratore richiesti.",
                item_type="driver",
                error_details=(
                    "Driver: Razer Synapse4 (Razer Inc)\n"
                    "HRESULT specifico: 0x80070005\n"
                    "SOLUZIONI CONSIGLIATE\n• Accetta la richiesta UAC."
                ),
            )
            window.drivers_section.on_item_completed(failed_record)

            # Open notifications popover and click the error notification row
            window.notifications_btn.click()
            self.assertTrue(window.notifications_popover.isVisible())
            rows = window.notifications_popover.row_widgets
            self.assertEqual(len(rows), 1)

            click_ev = QMouseEvent(
                QMouseEvent.Type.MouseButtonPress,
                QPointF(10.0, 10.0),
                QPointF(10.0, 10.0),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )
            rows[0].mousePressEvent(click_ev)

            dialog = window.active_detail_dialog
            self.assertIsNotNone(dialog)
            assert dialog is not None
            self.assertTrue(dialog.isVisible())
            self.assertFalse(window.notifications_popover.isVisible())
            self.assertIn("0x80070005", dialog.details_box.toPlainText())
            self.assertIn("SOLUZIONI CONSIGLIATE", dialog.details_box.toPlainText())

            dialog.copy_btn.click()
            self.assertEqual(dialog.copy_btn.text(), "Copiato")
            self.assertFalse(dialog.copy_btn.icon().isNull())
            dialog.close()

    def test_download_banner_is_above_recap_and_cards_have_no_avatar_icons(self) -> None:
        from patchwise.ui.widgets import AppAvatarBadge, AppUpdateCard, HistoryRowWidget

        with tempfile.TemporaryDirectory() as tmp:
            window = self._make_window(tmp)
            for section in (window.apps_section, window.drivers_section):
                dl_idx = section.section_layout.indexOf(section.download_banner)
                hero_idx = section.section_layout.indexOf(section.hero_card)
                list_idx = section.section_layout.indexOf(section.updates_card)
                self.assertGreaterEqual(dl_idx, 0)
                self.assertLess(dl_idx, hero_idx)
                self.assertLess(hero_idx, list_idx)

            candidate = UpdateCandidate(
                app=InstalledApp("chrome", "Google Chrome", "Google", "1.0", "winget"),
                online=OnlineVersionInfo("chrome", "2.0"),
            )
            card = AppUpdateCard(
                candidate=candidate,
                on_update_click=lambda _: None,
                on_selection_change=lambda _c, _s: None,
            )
            self.addCleanup(card.deleteLater)
            self.assertEqual(len(card.findChildren(AppAvatarBadge)), 0)
            self.assertEqual(card.update_btn.text(), "Aggiorna")
            self.assertFalse(card.update_btn.icon().isNull())

            rec = UpdateRecord(
                record_id="h1",
                app_id="chrome",
                app_name="Google Chrome",
                publisher="Google",
                from_version="1.0",
                to_version="2.0",
                size_mb=50.0,
                category=UpdateCategory.PATCH,
                status="success",
                duration_seconds=1.5,
            )
            row = HistoryRowWidget(rec)
            self.addCleanup(row.deleteLater)
            self.assertEqual(len(row.findChildren(AppAvatarBadge)), 0)


if __name__ == "__main__":
    unittest.main()
