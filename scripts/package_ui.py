"""Package the active UI source without dependencies, build outputs or secrets."""
from pathlib import Path
import hashlib
import os
import zipfile

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "frontend"
TARGET = ROOT / "incoming/mesh-nextjs-final.zip"
EXCLUDED = {"node_modules", ".next", ".npm-cache", ".browser-cache", "test-results", "playwright-report", ".git", ".lovable"}

with zipfile.ZipFile(TARGET, "w", zipfile.ZIP_DEFLATED, strict_timestamps=False) as archive:
    for directory, names, files in os.walk(UI):
        names[:] = sorted(name for name in names if name not in EXCLUDED and not (Path(directory)/name).is_symlink())
        for name in sorted(files):
            path = Path(directory)/name
            if path.is_symlink() or name.startswith(".env") or name.endswith(".tsbuildinfo"):
                continue
            archive.write(path, "frontend/" + path.relative_to(UI).as_posix())

with zipfile.ZipFile(TARGET) as archive:
    assert archive.testzip() is None
    print(f"Packaged {len(archive.namelist())} source files: {TARGET.relative_to(ROOT)}")
print(f"SHA-256: {hashlib.sha256(TARGET.read_bytes()).hexdigest()}")
