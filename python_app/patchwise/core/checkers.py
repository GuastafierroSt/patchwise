"""OOP class hierarchy for checking latest software versions online."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
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


@dataclass(frozen=True)
class _WingetUpgradeRow:
    """Single parsed package upgrade entry from `winget upgrade` output."""

    name: str
    winget_id: str
    installed_version: str
    available_version: str
    explicit_targeting: bool = False


class WingetVersionChecker(VersionChecker):
    """Queries Microsoft Winget (`winget upgrade`) for online version updates.

    Handles both the primary upgrade table and secondary explicit-targeting tables
    (e.g. packages such as Discord that require `--id <id>` targeting).
    """

    @property
    def provider_name(self) -> str:
        return "winget"

    @staticmethod
    def _slugify(name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
        return slug or "unknown-app"

    def _run_winget_upgrade(self) -> Optional[str]:
        if not sys.platform.startswith("win"):
            return None

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
            return None

        if result.returncode != 0:
            return None

        return result.stdout

    def fetch_latest_versions(
        self, installed_apps: Sequence[InstalledApp]
    ) -> Dict[str, OnlineVersionInfo]:
        stdout = self._run_winget_upgrade()
        if not stdout:
            return {}
        return self.parse_winget_upgrade_output(stdout, installed_apps)

    def find_updates(
        self, installed_apps: Sequence[InstalledApp]
    ) -> List[UpdateCandidate]:
        stdout = self._run_winget_upgrade()
        if not stdout:
            return []
        return self.parse_winget_upgrade_candidates(stdout, installed_apps)

    def parse_winget_upgrade_rows(self, stdout: str) -> List[_WingetUpgradeRow]:
        """Parse all tables emitted by `winget upgrade`, including explicit-targeting sections."""
        lines = [line.rstrip() for line in stdout.splitlines() if line.strip()]
        sep_indices = [
            idx
            for idx, line in enumerate(lines)
            if idx > 0 and set(line.strip()) == {"-"} and len(line.strip()) >= 10
        ]
        if not sep_indices:
            return []

        parsed: List[_WingetUpgradeRow] = []
        seen_ids: set[str] = set()

        for table_idx, sep_idx in enumerate(sep_indices):
            header = lines[sep_idx - 1]
            col_starts = [m.start() for m in re.finditer(r"\S+", header)]
            preceding = lines[sep_idx - 2].lower() if sep_idx >= 2 else ""
            is_explicit = (
                table_idx > 0
                or "explicit" in preceding
                or "esplicit" in preceding
            )

            row_end = (
                sep_indices[table_idx + 1] - 1
                if table_idx + 1 < len(sep_indices)
                else len(lines)
            )
            for row in lines[sep_idx + 1 : row_end]:
                source = ""
                if len(col_starts) >= 4:
                    name = row[col_starts[0] : col_starts[1]].strip()
                    winget_id = row[col_starts[1] : col_starts[2]].strip()
                    installed_ver = row[col_starts[2] : col_starts[3]].strip()
                    avail_end = col_starts[4] if len(col_starts) >= 5 else len(row)
                    available = row[col_starts[3] : avail_end].strip()
                    if len(col_starts) >= 5:
                        source = row[col_starts[4] :].strip()
                else:
                    cols = re.split(r"\s{2,}", row.strip())
                    if len(cols) < 4:
                        continue
                    name, winget_id, installed_ver, available = (
                        cols[0],
                        cols[1],
                        cols[2],
                        cols[3],
                    )
                    source = cols[4] if len(cols) >= 5 else ""

                # Reject summary, disclaimer, and prose lines between or after tables
                if not name or not winget_id or any(ch.isspace() for ch in winget_id):
                    continue
                if not available or any(ch.isspace() for ch in available):
                    continue
                if available.lower() in {"unknown", "<unknown>"} or not any(
                    ch.isdigit() for ch in available
                ):
                    continue
                if not installed_ver or (
                    not any(ch.isdigit() for ch in installed_ver)
                    and "unknown" not in installed_ver.lower()
                ):
                    continue
                if source and any(ch.isspace() for ch in source):
                    continue

                key = winget_id.lower()
                if key in seen_ids:
                    continue
                seen_ids.add(key)
                parsed.append(
                    _WingetUpgradeRow(
                        name=name,
                        winget_id=winget_id,
                        installed_version=installed_ver,
                        available_version=available,
                        explicit_targeting=is_explicit,
                    )
                )

        return parsed

    def _build_online_info(
        self, app_id: str, row: _WingetUpgradeRow
    ) -> OnlineVersionInfo:
        suffix = " · targeting esplicito" if row.explicit_targeting else ""
        return OnlineVersionInfo(
            app_id=app_id,
            latest_version=row.available_version,
            category=UpdateCategory.PATCH,
            release_notes=(
                f"Aggiornamento ufficiale disponibile tramite catalogo Winget "
                f"({row.winget_id}{suffix})."
            ),
            provider=self.provider_name,
        )

    def parse_winget_upgrade_output(
        self, stdout: str, installed_apps: Sequence[InstalledApp]
    ) -> Dict[str, OnlineVersionInfo]:
        """Parse `winget upgrade` tables and map rows back to local InstalledApp IDs."""
        by_winget_id = {
            app.winget_id.lower(): app.app_id
            for app in installed_apps
            if app.winget_id
        }
        by_name = {app.name.lower(): app.app_id for app in installed_apps}
        by_slug = {self._slugify(app.name): app.app_id for app in installed_apps}

        updates: Dict[str, OnlineVersionInfo] = {}
        for row in self.parse_winget_upgrade_rows(stdout):
            matched_id = (
                by_winget_id.get(row.winget_id.lower())
                or by_name.get(row.name.lower())
                or by_slug.get(self._slugify(row.name))
            )
            if not matched_id:
                continue
            updates[matched_id] = self._build_online_info(matched_id, row)
        return updates

    def parse_winget_upgrade_candidates(
        self, stdout: str, installed_apps: Sequence[InstalledApp]
    ) -> List[UpdateCandidate]:
        """Build UpdateCandidates from all `winget upgrade` tables.

        Enriches matched apps with `winget_id` when missing and synthesizes a candidate
        if Winget reports an upgradable package that wasn't matched in `installed_apps`.
        """
        by_winget_id = {
            app.winget_id.lower(): app
            for app in installed_apps
            if app.winget_id
        }
        by_name = {app.name.lower(): app for app in installed_apps}
        by_slug = {self._slugify(app.name): app for app in installed_apps}

        candidates: List[UpdateCandidate] = []
        seen_app_ids: set[str] = set()

        for row in self.parse_winget_upgrade_rows(stdout):
            matched = (
                by_winget_id.get(row.winget_id.lower())
                or by_name.get(row.name.lower())
                or by_slug.get(self._slugify(row.name))
            )

            if matched is not None:
                installed_ver = matched.installed_version
                if not is_update_available(installed_ver, row.available_version):
                    if is_update_available(row.installed_version, row.available_version):
                        installed_ver = row.installed_version
                    else:
                        continue
                app_obj = (
                    replace(
                        matched,
                        winget_id=matched.winget_id or row.winget_id,
                        installed_version=installed_ver,
                    )
                    if (not matched.winget_id or installed_ver != matched.installed_version)
                    else matched
                )
            else:
                if not is_update_available(row.installed_version, row.available_version):
                    continue
                publisher = (
                    row.winget_id.split(".")[0]
                    if "." in row.winget_id
                    else "Windows Package"
                )
                app_obj = InstalledApp(
                    app_id=self._slugify(row.name),
                    name=row.name,
                    publisher=publisher,
                    installed_version=row.installed_version,
                    source=self.provider_name,
                    winget_id=row.winget_id,
                )

            if app_obj.app_id in seen_app_ids:
                continue
            seen_app_ids.add(app_obj.app_id)
            candidates.append(
                UpdateCandidate(
                    app=app_obj,
                    online=self._build_online_info(app_obj.app_id, row),
                )
            )
        return candidates


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
                "User-Agent": "PatchWise/1.0",
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

    def find_updates(
        self, installed_apps: Sequence[InstalledApp]
    ) -> List[UpdateCandidate]:
        combined: List[UpdateCandidate] = []
        seen_ids: set[str] = set()
        seen_winget_ids: set[str] = set()
        for checker in self._checkers:
            for candidate in checker.find_updates(installed_apps):
                winget_key = (candidate.app.winget_id or "").lower()
                if candidate.app_id in seen_ids:
                    continue
                if winget_key and winget_key in seen_winget_ids:
                    continue
                seen_ids.add(candidate.app_id)
                if winget_key:
                    seen_winget_ids.add(winget_key)
                combined.append(candidate)
        return combined
