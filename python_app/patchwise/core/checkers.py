"""OOP class hierarchy for checking latest software versions online."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Sequence

from patchwise.core.version_utils import is_update_available
from patchwise.models import (
    InstalledApp,
    OnlineVersionInfo,
    UpdateCandidate,
    UpdateCategory,
)


class VersionChecker(ABC):
    """Abstract base class for comparing installed apps against online releases."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Short identifier for this remote catalog provider."""

    @abstractmethod
    def fetch_latest_versions(
        self, installed_apps: Sequence[InstalledApp]
    ) -> Dict[str, OnlineVersionInfo]:
        """Return a mapping of `app_id -> OnlineVersionInfo` for known packages."""

    def find_updates(
        self, installed_apps: Sequence[InstalledApp]
    ) -> List[UpdateCandidate]:
        """Compare installed apps with fetched online versions and return candidates."""
        remote_map = self.fetch_latest_versions(installed_apps)
        candidates: List[UpdateCandidate] = []
        for app in installed_apps:
            remote = remote_map.get(app.app_id)
            if remote and is_update_available(app.installed_version, remote.latest_version):
                candidates.append(UpdateCandidate(app=app, online=remote))
        return candidates


class WingetVersionChecker(VersionChecker):
    """Queries Microsoft Winget (`winget upgrade`) for online version updates."""

    @property
    def provider_name(self) -> str:
        return "winget"

    def fetch_latest_versions(
        self, installed_apps: Sequence[InstalledApp]
    ) -> Dict[str, OnlineVersionInfo]:
        if not sys.platform.startswith("win"):
            return {}

        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            result = subprocess.run(
                [
                    "winget",
                    "upgrade",
                    "--accept-source-agreements",
                    "--disable-interactivity",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=45,
                creationflags=creation_flags,
            )
        except (FileNotFoundError, subprocess.SubprocessError):
            return {}

        if result.returncode != 0:
            return {}

        return self.parse_winget_upgrade_output(result.stdout, installed_apps)

    def parse_winget_upgrade_output(
        self, stdout: str, installed_apps: Sequence[InstalledApp]
    ) -> Dict[str, OnlineVersionInfo]:
        """Parse `winget upgrade` table and map rows back to local InstalledApp IDs."""
        by_winget_id = {
            app.winget_id.lower(): app.app_id
            for app in installed_apps
            if app.winget_id
        }
        by_name = {app.name.lower(): app.app_id for app in installed_apps}

        lines = [line.rstrip() for line in stdout.splitlines() if line.strip()]
        sep_idx = -1
        for idx, line in enumerate(lines):
            if set(line.strip()) == {"-"} and len(line.strip()) >= 10:
                sep_idx = idx
                break

        if sep_idx <= 0:
            return {}

        header = lines[sep_idx - 1]
        col_starts = [m.start() for m in re.finditer(r"\S+", header)]

        updates: Dict[str, OnlineVersionInfo] = {}
        for row in lines[sep_idx + 1 :]:
            if len(col_starts) >= 4:
                name = row[col_starts[0] : col_starts[1]].strip()
                winget_id = row[col_starts[1] : col_starts[2]].strip()
                avail_end = col_starts[4] if len(col_starts) >= 5 else len(row)
                available = row[col_starts[3] : avail_end].strip()
            else:
                cols = re.split(r"\s{2,}", row.strip())
                if len(cols) < 4:
                    continue
                name, winget_id, available = cols[0], cols[1], cols[3]

            matched_id = by_winget_id.get(winget_id.lower()) or by_name.get(name.lower())
            if not matched_id or not available:
                continue
            updates[matched_id] = OnlineVersionInfo(
                app_id=matched_id,
                latest_version=available,
                category=UpdateCategory.PATCH,
                release_notes=f"Aggiornamento ufficiale disponibile tramite catalogo Winget ({winget_id}).",
                provider=self.provider_name,
            )
        return updates


class GitHubReleasesChecker(VersionChecker):
    """Checks latest releases for open-source apps via GitHub REST API."""

    API_TEMPLATE = "https://api.github.com/repos/{repo}/releases/latest"

    def __init__(self, timeout_seconds: float = 8.0) -> None:
        self._timeout = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "github"

    def fetch_latest_versions(
        self, installed_apps: Sequence[InstalledApp]
    ) -> Dict[str, OnlineVersionInfo]:
        results: Dict[str, OnlineVersionInfo] = {}
        for app in installed_apps:
            if not app.github_repo:
                continue
            info = self._query_repo(app.app_id, app.github_repo)
            if info:
                results[app.app_id] = info
        return results

    def _query_repo(self, app_id: str, repo: str) -> Optional[OnlineVersionInfo]:
        url = self.API_TEMPLATE.format(repo=repo)
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "PatchWise-Desktop-Updater/2.5",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            return None

        tag = str(payload.get("tag_name", "")).lstrip("vV")
        if not tag:
            return None

        download_url = ""
        size_mb = 0.0
        for asset in payload.get("assets", []):
            asset_name = str(asset.get("name", "")).lower()
            if asset_name.endswith((".exe", ".msi")):
                download_url = str(asset.get("browser_download_url", ""))
                size_mb = round(float(asset.get("size", 0)) / (1024 * 1024), 2)
                break

        notes = str(payload.get("body", "")).strip()
        summary = notes.splitlines()[0][:220] if notes else "Nuova release ufficiale su GitHub."
        lower_notes = notes.lower()
        category = (
            UpdateCategory.SECURITY
            if any(k in lower_notes for k in ("cve-", "security", "vulnerability", "sicurezza"))
            else UpdateCategory.FEATURES
            if any(k in lower_notes for k in ("feature", "added", "new "))
            else UpdateCategory.PATCH
        )

        return OnlineVersionInfo(
            app_id=app_id,
            latest_version=tag,
            download_url=download_url,
            size_mb=size_mb,
            category=category,
            release_notes=summary,
            provider=self.provider_name,
            published_at=payload.get("published_at"),
        )


class CompositeVersionChecker(VersionChecker):
    """Aggregates multiple VersionChecker providers in priority order."""

    def __init__(self, checkers: Sequence[VersionChecker]) -> None:
        self._checkers = list(checkers)

    @property
    def provider_name(self) -> str:
        return "composite"

    def fetch_latest_versions(
        self, installed_apps: Sequence[InstalledApp]
    ) -> Dict[str, OnlineVersionInfo]:
        combined: Dict[str, OnlineVersionInfo] = {}
        for checker in self._checkers:
            for app_id, info in checker.fetch_latest_versions(installed_apps).items():
                if app_id not in combined:
                    combined[app_id] = info
        return combined
