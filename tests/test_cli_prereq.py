from pathlib import Path

from research.__main__ import _require


def test_require_raises_when_missing(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    try:
        _require(missing, "missing")
    except SystemExit as exc:
        assert "Missing prerequisite" in str(exc)
    else:
        raise AssertionError("Expected SystemExit")
