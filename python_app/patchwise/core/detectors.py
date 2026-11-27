"""OOP class hierarchy for detecting installed desktop applications."""

from __future__ import annotations

import platform
import re
import subprocess
import sys
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Sequence

from patchwise.models import InstalledApp


class AppDetector(ABC):
    """Abstract base class for local application discovery strategies."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Identifier of this detection source (e.g. 'registry', 'winget')."""

    @abstractmethod
    def detect(self) -> List[InstalledApp]:
        """Scan the local system and return detected applications."""

    def is_supported(self) -> bool:
        """Return True if this detector can run on the current OS."""
        return True

    @staticmethod
    def _slugify(name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
        return slug or "unknown-app"


class WindowsRegistryDetector(AppDetector):
    """Reads installed Win32/x64 programs from Windows Uninstall Registry hives."""

    REGISTRY_PATHS = (
        ("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ("HKLM", r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        ("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    )

    @property
    def provider_name(self) -> str:
        return "registry"

    def is_supported(self) -> bool:
        return sys.platform.startswith("win") or platform.system() == "Windows"

    def detect(self) -> List[InstalledApp]:
        if not self.is_supported():
            return []

        import winreg  # Windows-only standard library module

        hives = {
            "HKLM": winreg.HKEY_LOCAL_MACHINE,
            "HKCU": winreg.HKEY_CURRENT_USER,
        }
        discovered: Dict[str, InstalledApp] = {}

        for hive_name, subkey_path in self.REGISTRY_PATHS:
            hive = hives[hive_name]
            try:
                root_key = winreg.OpenKey(hive, subkey_path)
            except OSError:
                continue

            with root_key:
                index = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(root_key, index)
                        index += 1
                    except OSError:
                        break

                    app = self._read_subkey(winreg, root_key, subkey_name)
                    if app and app.app_id not in discovered:
                        discovered[app.app_id] = app

        return sorted(discovered.values(), key=lambda item: item.name.lower())

    def _read_subkey(self, winreg, root_key, subkey_name: str) -> Optional[InstalledApp]:
        try:
            with winreg.OpenKey(root_key, subkey_name) as key:
                name = self._query_str(winreg, key, "DisplayName")
                version = self._query_str(winreg, key, "DisplayVersion")
                if not name or not version:
                    return None

                # Filter out system components and Windows hotfixes
                system_component = self._query_int(winreg, key, "SystemComponent")
                if system_component == 1:
                    return None

                publisher = self._query_str(winreg, key, "Publisher") or "Editore sconosciuto"
                location = self._query_str(winreg, key, "InstallLocation") or ""

                return InstalledApp(
                    app_id=self._slugify(name),
                    name=name.strip(),
                    publisher=publisher.strip(),
                    installed_version=version.strip(),
                    source=self.provider_name,
                    install_location=location.strip(),
                )
        except OSError:
            return None

    @staticmethod
    def _query_str(winreg, key, value_name: str) -> str:
        try:
            value, _ = winreg.QueryValueEx(key, value_name)
            return str(value) if value is not None else ""
        except OSError:
            return ""

    @staticmethod
    def _query_int(winreg, key, value_name: str) -> int:
        try:
            value, _ = winreg.QueryValueEx(key, value_name)
            return int(value)
        except (OSError, ValueError, TypeError):
            return 0


class WingetDetector(AppDetector):
    """Detects installed applications via Windows Package Manager (`winget list`)."""

    @property
    def provider_name(self) -> str:
        return "winget"

    def is_supported(self) -> bool:
        return sys.platform.startswith("win") or platform.system() == "Windows"

    def detect(self) -> List[InstalledApp]:
        if not self.is_supported():
            return []

        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            result = subprocess.run(
                ["winget", "list", "--accept-source-agreements", "--disable-interactivity"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=35,
                creationflags=creation_flags,
            )
        except (FileNotFoundError, subprocess.SubprocessError):
            return []

        if result.returncode != 0:
            return []

        return self.parse_winget_list_output(result.stdout)

    def parse_winget_list_output(self, stdout: str) -> List[InstalledApp]:
        """Parse fixed-width `winget list` output into InstalledApp objects."""
        lines = [line.rstrip() for line in stdout.splitlines() if line.strip()]
        sep_idx = -1
        for idx, line in enumerate(lines):
            if set(line.strip()) == {"-"} and len(line.strip()) >= 10:
                sep_idx = idx
                break

        if sep_idx <= 0:
            return []

        header = lines[sep_idx - 1]
        col_starts = [m.start() for m in re.finditer(r"\S+", header)]

        apps: List[InstalledApp] = []
        for row in lines[sep_idx + 1 :]:
            if len(col_starts) >= 3:
                name = row[col_starts[0] : col_starts[1]].strip()
                winget_id = row[col_starts[1] : col_starts[2]].strip()
                ver_end = col_starts[3] if len(col_starts) >= 4 else len(row)
                version = row[col_starts[2] : ver_end].strip()
            else:
                columns = re.split(r"\s{2,}", row.strip())
                if len(columns) < 3:
                    continue
                name, winget_id, version = columns[0], columns[1], columns[2]

            if not name or not version or version.lower() in {"unknown", "<unknown>"}:
                continue
            publisher = winget_id.split(".")[0] if "." in winget_id else "Windows Package"
            apps.append(
                InstalledApp(
                    app_id=self._slugify(name),
                    name=name,
                    publisher=publisher,
                    installed_version=version,
                    source=self.provider_name,
                    winget_id=winget_id,
                )
            )
        return apps


class CompositeAppDetector(AppDetector):
    """Combines multiple AppDetector strategies and deduplicates by app_id.

    Prefers richer metadata (e.g., winget_id from WingetDetector + publisher
    and install_location from WindowsRegistryDetector).
    """

    def __init__(self, detectors: Sequence[AppDetector]) -> None:
        self._detectors = list(detectors)

    @property
    def provider_name(self) -> str:
        return "composite"

    def detect(self) -> List[InstalledApp]:
        merged: Dict[str, InstalledApp] = {}
        for detector in self._detectors:
            if not detector.is_supported():
                continue
            for app in detector.detect():
                existing = merged.get(app.app_id)
                if existing is None:
                    merged[app.app_id] = app
                else:
                    merged[app.app_id] = InstalledApp(
                        app_id=existing.app_id,
                        name=existing.name,
                        publisher=existing.publisher
                        if existing.publisher != "Editore sconosciuto"
                        else app.publisher,
                        installed_version=existing.installed_version or app.installed_version,
                        source=f"{existing.source}+{app.source}",
                        install_location=existing.install_location or app.install_location,
                        winget_id=existing.winget_id or app.winget_id,
                        github_repo=existing.github_repo or app.github_repo,
                    )
        return sorted(merged.values(), key=lambda item: item.name.lower())
