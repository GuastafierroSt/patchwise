"""Stateless session-scoped update history manager.

Design policy:
- Never maintains a permanent multi-session database or growing log archive.
- Keeps all updates performed during the CURRENT running session in RAM.
- On clean shutdown (`finalize_session`), overwrites a single ephemeral temp file
  with ONLY the current session's records so that if the user reopens the app,
  they can inspect what was updated in the LAST session — while every session
  before that is permanently discarded.
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from patchwise.models import UpdateRecord


class StatelessSessionHistoryManager:
    """Manages current-session history in memory plus a single volatile last-session snapshot."""

    DEFAULT_FILENAME = "patchwise_last_session.json"

    def __init__(self, snapshot_path: Optional[Path] = None) -> None:
        self._snapshot_path = snapshot_path or (
            Path(tempfile.gettempdir()) / self.DEFAULT_FILENAME
        )
        self._session_started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._current_session: List[UpdateRecord] = []
        self._last_session_started_at: Optional[str] = None
        self._last_session: List[UpdateRecord] = []
        self._load_last_session_snapshot()

    @property
    def session_started_at(self) -> str:
        return self._session_started_at

    @property
    def last_session_started_at(self) -> Optional[str]:
        return self._last_session_started_at

    def record_update(self, record: UpdateRecord) -> None:
        """Append a completed/failed update to the active session (RAM only)."""
        self._current_session.insert(0, record)

    def get_current_session_records(self) -> List[UpdateRecord]:
        return list(self._current_session)

    def get_last_session_records(self) -> List[UpdateRecord]:
        return list(self._last_session)

    def clear_all(self) -> None:
        """Clear both active RAM records and the ephemeral last-session snapshot."""
        self._current_session.clear()
        self._last_session.clear()
        self._last_session_started_at = None
        if self._snapshot_path.exists():
            try:
                self._snapshot_path.unlink()
            except OSError:
                pass

    def finalize_session(self) -> None:
        """Called on app close: overwrites the single temp snapshot with ONLY this session.

        If no updates occurred in the current session, the older last-session
        snapshot is discarded so stale multi-session history never lingers.
        """
        if not self._current_session:
            if self._snapshot_path.exists():
                try:
                    self._snapshot_path.unlink()
                except OSError:
                    pass
            return

        payload = {
            "session_started_at": self._session_started_at,
            "session_closed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "records": [rec.to_dict() for rec in self._current_session],
        }
        try:
            self._snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            self._snapshot_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass

    def _load_last_session_snapshot(self) -> None:
        if not self._snapshot_path.exists():
            return
        try:
            raw = json.loads(self._snapshot_path.read_text(encoding="utf-8"))
            self._last_session_started_at = raw.get("session_started_at")
            self._last_session = [
                UpdateRecord.from_dict(item) for item in raw.get("records", [])
            ]
        except (OSError, ValueError, KeyError, TypeError):
            self._last_session = []
            self._last_session_started_at = None
