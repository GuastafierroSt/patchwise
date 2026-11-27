"""PatchWise Desktop Software Updater — Portable Entry Point.

Supports both direct Python execution (`python main.py`) and frozen
PyInstaller `--onefile` portable executable bundles (`PatchWise_Portable.exe`).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def resolve_runtime_root() -> Path:
    """Return the runtime directory for bundled assets when running portable."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent


def main() -> int:
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    runtime_root = resolve_runtime_root()
    if str(runtime_root) not in sys.path:
        sys.path.insert(0, str(runtime_root))

    from PySide6.QtWidgets import QApplication

    from patchwise import __app_name__, __version__
    from patchwise.ui.main_window import PatchWiseMainWindow

    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)

    window = PatchWiseMainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
