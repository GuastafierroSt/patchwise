"""Build script that compiles PatchWise into a standalone portable Windows .EXE.

Usage:
    python build_portable.py
    python build_portable.py --name PatchWise_Portable --clean

Output:
    dist/PatchWise_Portable.exe

The generated binary uses PyInstaller `--onefile --windowed --noupx` so it can be
copied onto a USB drive or another Windows 10/11 PC and executed directly with
zero installation, zero registry modifications, and zero external Python runtime.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List


def build_pyinstaller_command(
    project_root: Path,
    exe_name: str = "PatchWise_Portable",
    clean: bool = True,
    icon_path: Path | None = None,
) -> List[str]:
    """Construct the exact PyInstaller CLI arguments for a single-file portable .exe."""
    entry_script = project_root / "main.py"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name",
        exe_name,
        "--paths",
        str(project_root),
        "--distpath",
        str(project_root / "dist"),
        "--workpath",
        str(project_root / "build"),
        "--specpath",
        str(project_root / "build"),
        # Exclude unused heavy Qt modules to keep the portable .exe compact
        "--exclude-module",
        "PySide6.QtWebEngineCore",
        "--exclude-module",
        "PySide6.QtWebEngineWidgets",
        "--exclude-module",
        "PySide6.Qt3DCore",
        "--exclude-module",
        "PySide6.QtQml",
        "--exclude-module",
        "PySide6.QtQuick",
        "--exclude-module",
        "tkinter",
        "--exclude-module",
        "unittest",
    ]
    if clean:
        cmd.append("--clean")
    assets_dir = project_root / "assets"
    if assets_dir.exists():
        sep = ";" if sys.platform.startswith("win") else ":"
        cmd.extend(["--add-data", f"{assets_dir}{sep}assets"])
    if icon_path is None:
        default_icon = assets_dir / "patchwise.ico"
        if default_icon.exists():
            icon_path = default_icon
    if icon_path and icon_path.exists():
        cmd.extend(["--icon", str(icon_path)])

    cmd.append(str(entry_script))
    return cmd


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compila PatchWise Desktop in un eseguibile Windows .EXE portable."
    )
    parser.add_argument(
        "--name",
        default="PatchWise_Portable",
        help="Nome del file eseguibile finale (senza estensione .exe).",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Riutilizza la cache di PyInstaller senza pulire la cartella build/.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Stampa il comando PyInstaller senza eseguire la compilazione.",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    icon_candidate = project_root / "assets" / "patchwise.ico"
    cmd = build_pyinstaller_command(
        project_root=project_root,
        exe_name=args.name,
        clean=not args.no_clean,
        icon_path=icon_candidate if icon_candidate.exists() else None,
    )

    print("Comando PyInstaller generato:")
    print(" ".join(cmd))

    if args.dry_run:
        return 0

    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        print("Errore: PyInstaller non trovato. Esegui: pip install -r requirements.txt")
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"Compilazione fallita con codice {exc.returncode}.")
        return exc.returncode

    ext = ".exe" if sys.platform.startswith("win") else ""
    output_bin = project_root / "dist" / f"{args.name}{ext}"
    if output_bin.exists():
        size_mb = output_bin.stat().st_size / (1024 * 1024)
        print(f"\nBuild completata con successo: {output_bin} ({size_mb:.1f} MB)")
        print("Puoi copiare questo file su qualsiasi PC Windows ed eseguirlo senza installazione.")

    # Optional cleanup of temporary spec/build directory after successful build
    build_dir = project_root / "build"
    if not args.no_clean and build_dir.exists():
        shutil.rmtree(build_dir, ignore_errors=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
