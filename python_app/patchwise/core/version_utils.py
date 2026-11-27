"""Version normalization and comparison utilities."""

from __future__ import annotations

import re
from typing import Tuple

_VERSION_TOKEN_RE = re.compile(r"\d+")


def parse_version_tuple(raw_version: str) -> Tuple[int, ...]:
    """Extract numeric version segments from arbitrary software version strings.

    Examples:
        'v124.0.6367.60' -> (124, 0, 6367, 60)
        '24.05-beta'     -> (24, 5)
        '3.0.21'         -> (3, 0, 21)
    """
    cleaned = (raw_version or "").strip()
    tokens = _VERSION_TOKEN_RE.findall(cleaned)
    if not tokens:
        return (0,)
    return tuple(int(tok) for tok in tokens)


def compare_versions(current: str, candidate: str) -> int:
    """Compare two version strings.

    Returns:
        -1 if current < candidate (update available)
         0 if current == candidate
         1 if current > candidate
    """
    a = list(parse_version_tuple(current))
    b = list(parse_version_tuple(candidate))
    max_len = max(len(a), len(b))
    a.extend([0] * (max_len - len(a)))
    b.extend([0] * (max_len - len(b)))
    if a < b:
        return -1
    if a > b:
        return 1
    return 0


def is_update_available(installed_version: str, latest_version: str) -> bool:
    """Return True strictly when latest_version is newer than installed_version."""
    if not installed_version or not latest_version:
        return False
    return compare_versions(installed_version, latest_version) < 0
