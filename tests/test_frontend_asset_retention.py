from pathlib import Path

import pytest

from scripts.retain_frontend_assets import retain_assets


def build(tmp_path: Path, name: str, files: dict[str, bytes]) -> Path:
    root = tmp_path / name
    for relative, data in files.items():
        item = root / "static" / relative
        item.parent.mkdir(parents=True, exist_ok=True)
        item.write_bytes(data)
    return root


def test_retains_predecessor_dependencies_without_changing_active_assets(tmp_path):
    target = build(tmp_path, "new", {"chunks/new.js": b"new", "chunks/common.js": b"same"})
    old = build(tmp_path, "old", {"chunks/old.js": b"old", "chunks/common.js": b"same", "css/old.css": b"css"})
    (old / "server").mkdir()
    (old / "server" / "app.html").write_text("old html")
    assert retain_assets(target, [old]) == 2
    assert (target / "static/chunks/old.js").read_bytes() == b"old"
    assert (target / "static/chunks/new.js").read_bytes() == b"new"
    assert (target / "static/css/old.css").read_bytes() == b"css"
    assert not (target / "server").exists()
    assert retain_assets(target, [old]) == 0


@pytest.mark.parametrize("conflict_in_target", [False, True])
def test_preflights_all_conflicts_before_writing_any_assets(tmp_path, conflict_in_target):
    target = build(tmp_path, "new", {"chunks/current.js": b"current"})
    old = build(tmp_path, "old", {"chunks/a-addition.js": b"old", "chunks/z-conflict.js": b"first"})
    other = build(tmp_path, "other", {"chunks/z-conflict.js": b"different"})
    if conflict_in_target:
        (target / "static/chunks/z-conflict.js").write_bytes(b"different")
    with pytest.raises(ValueError, match="Conflicting static asset"):
        retain_assets(target, [old, other])
    assert not (target / "static/chunks/a-addition.js").exists()
    assert (target / "static/chunks/current.js").read_bytes() == b"current"


def test_rejects_missing_sources_and_symlinked_assets(tmp_path):
    target = build(tmp_path, "new", {"chunks/current.js": b"current"})
    with pytest.raises(ValueError, match="Missing"):
        retain_assets(target, [tmp_path / "missing"])
    old = build(tmp_path, "old", {"chunks/old.js": b"old"})
    (old / "static/chunks/link.js").symlink_to(target / "static/chunks/current.js")
    with pytest.raises(ValueError, match="Symlinked"):
        retain_assets(target, [old])
    assert not (target / "static/chunks/old.js").exists()
