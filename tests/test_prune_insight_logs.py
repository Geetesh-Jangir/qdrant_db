from pathlib import Path

from ai_insight.tools.prune_insight_logs import prune_insight_logs


def test_prune_keeps_latest_artifact_and_matching_flat_log(tmp_path: Path) -> None:
    root = tmp_path / "logs"
    old = root / "2026-11-16" / "demo" / "aaaaaa"
    new = root / "2026-11-16" / "demo" / "bbbbbb"
    old.mkdir(parents=True)
    new.mkdir(parents=True)
    (old / "run.log").write_text("old", encoding="utf-8")
    (new / "run.log").write_text("new", encoding="utf-8")
    flat = root / "demo"
    flat.mkdir(parents=True)
    (flat / "2026-11-16_120000_aaaaaa.log").write_text("old flat", encoding="utf-8")
    (flat / "2026-11-16_130000_bbbbbb.log").write_text("new flat", encoding="utf-8")
    (flat / "2026-11-16_100000_legacy.log").write_text("orphan", encoding="utf-8")
    (new / "run.log").touch()

    stats = prune_insight_logs(root, execute=True)
    assert stats["removed_run_dirs"] == 1
    assert not old.exists()
    assert new.is_dir()
    assert not (flat / "2026-11-16_120000_aaaaaa.log").exists()
    assert (flat / "2026-11-16_130000_bbbbbb.log").is_file()
    assert not (flat / "2026-11-16_100000_legacy.log").exists()