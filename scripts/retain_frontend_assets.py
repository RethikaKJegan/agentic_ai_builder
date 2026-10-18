#!/usr/bin/env python3
"""Retain immutable Next static assets before activating a replacement build."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil


def retain_assets(target_build: Path, source_builds: list[Path]) -> int:
    target = target_build / "static"
    roots = [target, *(source / "static" for source in source_builds)]
    files: dict[Path, Path] = {}
    additions: dict[Path, Path] = {}
    # Preflight every source before any writes, including conflicts between sources.
    for root in roots:
        if not root.is_dir() or root.is_symlink():
            raise ValueError(f"Missing or symlinked static directory: {root}")
        for item in sorted(root.rglob("*")):
            if item.is_symlink():
                raise ValueError(f"Symlinked static asset: {item}")
            if not item.is_file():
                continue
            relative = item.relative_to(root)
            previous = files.get(relative)
            if previous is not None:
                if previous.read_bytes() != item.read_bytes():
                    raise ValueError(f"Conflicting static asset: {relative}")
            else:
                files[relative] = item
                if root != target:
                    additions[relative] = item
    for relative, source in additions.items():
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return len(additions)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path, help="Replacement .next directory")
    parser.add_argument("--source", required=True, action="append", type=Path, help="Previous .next directory; repeatable")
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[1]
    for path in [args.target, *args.source]:
        if not path.resolve().is_relative_to(repository):
            parser.error("Build directories must remain within this repository")
    try:
        copied = retain_assets(args.target, args.source)
    except ValueError as error:
        parser.exit(1, f"Asset retention stopped: {error}\n")
    print(f"Retained {copied} static assets; existing files unchanged.")


if __name__ == "__main__":
    main()
