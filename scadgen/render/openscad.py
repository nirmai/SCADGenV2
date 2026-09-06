"""Locate and drive the OpenSCAD binary — render-checking and preview images."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

# stderr lines that indicate the source will not render correctly. OpenSCAD
# reports undefined references and empty output as WARNINGs (exit 0), so those
# patterns are treated as failures alongside any ERROR.
_ERROR_PATTERNS = (
    "ERROR:",
    "Ignoring unknown",
    "is not defined",
    "WARNING: Can't",
    "Unable to",
    "No top level geometry",
    "Parser error",
    "syntax error",
)

_COMMON_PATHS = (
    r"C:\Program Files\OpenSCAD\openscad.exe",
    r"C:\Program Files\OpenSCAD (Nightly)\openscad.exe",
    r"C:\Program Files (x86)\OpenSCAD\openscad.exe",
    "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD",
    "/usr/bin/openscad",
    "/usr/local/bin/openscad",
    "/snap/bin/openscad",
)


def find_openscad(config=None) -> str | None:
    """Locate the OpenSCAD executable.

    Order: config.openscad_path → OPENSCAD_PATH env → PATH → common install
    locations. Returns an absolute path, or None if not found.
    """
    candidates: list[str] = []
    if config is not None and getattr(config, "openscad_path", ""):
        candidates.append(config.openscad_path)
    if os.environ.get("OPENSCAD_PATH"):
        candidates.append(os.environ["OPENSCAD_PATH"])
    for name in ("openscad", "openscad.exe", "OpenSCAD"):
        found = shutil.which(name)
        if found:
            candidates.append(found)
    candidates.extend(_COMMON_PATHS)

    for c in candidates:
        if c and Path(c).is_file():
            return str(Path(c))
    return None


def check_scad(source: str, openscad_bin: str, timeout: int = 30) -> list[str]:
    """Render-check OpenSCAD source. Returns a list of error strings (empty = OK).

    Exports to STL (forcing full geometry evaluation) and scans stderr for
    failure patterns. Raises FileNotFoundError if the binary is missing.
    """
    if not openscad_bin or not Path(openscad_bin).is_file():
        raise FileNotFoundError(f"OpenSCAD binary not found: {openscad_bin!r}")

    with tempfile.TemporaryDirectory() as tmp:
        scad_path = Path(tmp) / "check.scad"
        out_path = Path(tmp) / "check.stl"
        scad_path.write_text(source, encoding="utf-8")

        try:
            proc = subprocess.run(
                [openscad_bin, "-o", str(out_path), str(scad_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return [f"OpenSCAD render timed out after {timeout}s"]

        stderr = proc.stderr or ""
        errors = [
            line.strip()
            for line in stderr.splitlines()
            if any(pat in line for pat in _ERROR_PATTERNS)
        ]

        if proc.returncode != 0 and not errors:
            tail = stderr.strip().splitlines()[-3:]
            errors.append(
                "OpenSCAD exited with code "
                f"{proc.returncode}: {' | '.join(tail) or 'no diagnostics'}"
            )
        # Successful exit but no geometry file written also means nothing rendered.
        if proc.returncode == 0 and not out_path.exists() and not errors:
            errors.append("OpenSCAD produced no output (empty geometry)")

        return _dedupe(errors)


def render_png(
    source: str,
    out_path: str,
    openscad_bin: str,
    size: tuple[int, int] = (800, 600),
    timeout: int = 60,
) -> None:
    """Render OpenSCAD source to a PNG preview image.

    Groundwork for a pre-rendered view; not yet wired into the pipeline.
    Raises FileNotFoundError if the binary is missing, RuntimeError on failure.
    """
    if not openscad_bin or not Path(openscad_bin).is_file():
        raise FileNotFoundError(f"OpenSCAD binary not found: {openscad_bin!r}")

    w, h = size
    with tempfile.TemporaryDirectory() as tmp:
        scad_path = Path(tmp) / "preview.scad"
        scad_path.write_text(source, encoding="utf-8")
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        try:
            proc = subprocess.run(
                [
                    openscad_bin, "-o", out_path,
                    "--imgsize", f"{w},{h}",
                    "--autocenter", "--viewall",
                    str(scad_path),
                ],
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"OpenSCAD preview timed out after {timeout}s") from e
        if proc.returncode != 0:
            raise RuntimeError(f"OpenSCAD preview failed: {proc.stderr.strip()[:300]}")


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
