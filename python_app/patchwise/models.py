"""Domain data models for PatchWise Software Updater."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class UpdateCategory(str, Enum):
    SECURITY = "security"
    FEATURES = "features"
    PATCH = "patch"


class UpdatePhase(str, Enum):
    IDLE = "idle"
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    INSTALLING = "installing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class InstalledApp:
    """Represents an application or hardware driver detected on the local machine."""

    app_id: str
    name: str
    publisher: str
    installed_version: str
    source: str  # "registry" | "winget" | "driver-registry" | "driver-cim" | "windows-update-driver"
    install_location: str = ""
    winget_id: Optional[str] = None
    github_repo: Optional[str] = None
    item_type: str = "app"  # "app" | "driver"
    device_class: str = ""
    hardware_id: str = ""
    driver_update_id: Optional[str] = None


@dataclass(frozen=True)
class OnlineVersionInfo:
    """Represents the latest release metadata retrieved from an online source."""

    app_id: str
    latest_version: str
    download_url: str = ""
    sha256: Optional[str] = None
    size_mb: float = 0.0
    category: UpdateCategory = UpdateCategory.PATCH
    release_notes: str = ""
    provider: str = "winget"
    published_at: Optional[str] = None


@dataclass
class UpdateCandidate:
    """Pairs an installed local app with its available online update.

    Auto-update is intentionally omitted by design: every update requires
    explicit user initiation.
    """

    app: InstalledApp
    online: OnlineVersionInfo
    selected: bool = True
    skipped: bool = False
    status: UpdatePhase = UpdatePhase.IDLE

    @property
    def app_id(self) -> str:
        return self.app.app_id

    @property
    def name(self) -> str:
        return self.app.name


@dataclass
class DownloadProgress:
    """Live progress payload emitted to the GUI progress bar."""

    app_id: str
    app_name: str
    phase: UpdatePhase
    percent: float = 0.0
    downloaded_mb: float = 0.0
    total_mb: float = 0.0
    speed_mbps: float = 0.0
    eta_seconds: Optional[int] = None
    message: str = ""


@dataclass(frozen=True)
class UpdateRecord:
    """Single completed/failed update event recorded within a session."""

    record_id: str
    app_id: str
    app_name: str
    publisher: str
    from_version: str
    to_version: str
    size_mb: float
    category: UpdateCategory
    status: str  # "success" | "failed" | "cancelled"
    duration_seconds: float
    completed_at: str = field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    error_message: str = ""
    item_type: str = "app"  # "app" | "driver"
    error_details: str = ""

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "app_id": self.app_id,
            "app_name": self.app_name,
            "publisher": self.publisher,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "size_mb": self.size_mb,
            "category": self.category.value,
            "status": self.status,
            "duration_seconds": self.duration_seconds,
            "completed_at": self.completed_at,
            "error_message": self.error_message,
            "item_type": self.item_type,
            "error_details": self.error_details,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UpdateRecord":
        return cls(
            record_id=str(data["record_id"]),
            app_id=str(data["app_id"]),
            app_name=str(data["app_name"]),
            publisher=str(data.get("publisher", "")),
            from_version=str(data["from_version"]),
            to_version=str(data["to_version"]),
            size_mb=float(data.get("size_mb", 0.0)),
            category=UpdateCategory(data.get("category", UpdateCategory.PATCH.value)),
            status=str(data.get("status", "success")),
            duration_seconds=float(data.get("duration_seconds", 0.0)),
            completed_at=str(data.get("completed_at", "")),
            error_message=str(data.get("error_message", "")),
            item_type=str(data.get("item_type", "app")),
            error_details=str(data.get("error_details", "")),
        )
