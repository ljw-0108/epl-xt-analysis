"""Pipeline tests with a fake downloader and a SYNTHETIC parquet (no network, never real data)."""
import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from epl_xt.app_data import load_dataset
from epl_xt.pipeline import EVENT_FILE, GRID_URL, RELEASE, build_verified_dataset

M1 = "SYNTHETIC_TEST_ONLY_1"


@pytest.fixture()
def sources(tmp_path):
    src = tmp_path / "sources"
    src.mkdir()
    rows = []
    for team, opp in (("Alpha", "Beta"), ("Beta", "Alpha")):
        for i in range(3):
            rows.append(dict(comp="eng", season="2526", match_id=M1, team=team, player=f"{team}_P{i}", type="Pass",
                             outcome="Successful" if i else "Unsuccessful", x=10.0 + i, y=50.0, end_x=60.0, end_y=40.0))
    pd.DataFrame(rows).to_parquet(src / EVENT_FILE, index=False)
    (src / "grid.json").write_text(json.dumps([[0.01 * (c + 1) for c in range(12)] for _ in range(8)]), encoding="utf-8")
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
    (src / "checksums.json").write_text(json.dumps({EVENT_FILE: {"sha256": digest(src / EVENT_FILE)}}), encoding="utf-8")
    return src, digest(src / "grid.json")


def fake_fetch(src: Path):
    mapping = {f"{RELEASE}/checksums.json": "checksums.json", f"{RELEASE}/{EVENT_FILE}": EVENT_FILE, GRID_URL: "grid.json"}

    def fetch(url, dest, max_bytes):
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src / mapping[url], dest)
    return fetch


def test_pipeline_builds_loadable_verified_dataset(tmp_path, sources):
    src, grid_sha = sources
    root = tmp_path / "app"
    logs = []
    manifest = build_verified_dataset(root, fetch=fake_fetch(src), grid_sha256=grid_sha, log=logs.append)
    assert manifest["match_ids"] == [M1]
    assert manifest["quality_report"]["pass_rows"] == 6
    assert manifest["verified_by_user"] is False
    _, scored, matches, _ = load_dataset(root)
    assert len(scored) == 6 and set(matches["opponent"]) == {"Alpha", "Beta"}
    assert logs and logs[-1].startswith("완료")


def test_event_checksum_mismatch_stops_and_leaves_no_manifest(tmp_path, sources):
    src, grid_sha = sources
    root = tmp_path / "app"
    build_verified_dataset(root, fetch=fake_fetch(src), grid_sha256=grid_sha)  # an earlier good run
    (src / "checksums.json").write_text(json.dumps({EVENT_FILE: {"sha256": "0" * 64}}), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256"):
        build_verified_dataset(root, fetch=fake_fetch(src), grid_sha256=grid_sha)
    assert not (root / "config/source_manifest.json").exists()  # old manifest cannot vouch for anything
    assert not (root / "data/raw" / EVENT_FILE).exists()
    with pytest.raises(ValueError):
        load_dataset(root)


def test_grid_hash_mismatch_stops(tmp_path, sources):
    src, _ = sources
    root = tmp_path / "app"
    with pytest.raises(ValueError, match="pinned SHA-256"):
        build_verified_dataset(root, fetch=fake_fetch(src), grid_sha256="f" * 64)
    assert not (root / "config/source_manifest.json").exists()
    assert not (root / "data/processed/passes.csv").exists()


def test_wrong_season_source_is_rejected(tmp_path, sources):
    src, grid_sha = sources
    df = pd.read_parquet(src / EVENT_FILE)
    df["season"] = "2627"
    df.to_parquet(src / EVENT_FILE, index=False)
    digest = hashlib.sha256((src / EVENT_FILE).read_bytes()).hexdigest()
    (src / "checksums.json").write_text(json.dumps({EVENT_FILE: {"sha256": digest}}), encoding="utf-8")
    with pytest.raises(ValueError, match="2025/26"):
        build_verified_dataset(tmp_path / "app", fetch=fake_fetch(src), grid_sha256=grid_sha)
    assert not (tmp_path / "app/config/source_manifest.json").exists()


# ---- App: no-data path ----
AppTest = pytest.importorskip("streamlit.testing.v1").AppTest
APP = Path(__file__).resolve().parents[1] / "app.py"


def test_app_offers_button_without_auto_prepare(monkeypatch, tmp_path):
    monkeypatch.setenv("EPL_DATA_ROOT", str(tmp_path))
    monkeypatch.delenv("EPL_AUTO_PREPARE", raising=False)
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not at.exception
    assert [b.label for b in at.button] == ["원본 내려받기 및 검증"]
    assert not at.metric


def test_app_auto_prepare_success_and_failure(monkeypatch, tmp_path, sources):
    import epl_xt.pipeline as pipeline
    src, grid_sha = sources
    real_build = pipeline.build_verified_dataset
    monkeypatch.setenv("EPL_DATA_ROOT", str(tmp_path / "app"))
    monkeypatch.setenv("EPL_AUTO_PREPARE", "1")

    def failing(root, log=print, **_):
        raise ValueError("Downloaded event data failed official SHA-256 verification")
    monkeypatch.setattr(pipeline, "build_verified_dataset", failing)
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not at.exception and not at.metric  # failure shown, no numbers
    at.run()  # second run must not retry automatically (no loop on a failing source)
    assert not at.metric

    monkeypatch.setattr(pipeline, "build_verified_dataset",
                        lambda root, log=print, **_: real_build(root, fetch=fake_fetch(src), grid_sha256=grid_sha, log=log))
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not at.exception
    assert any(m.label == "패스 시도" and m.value == "3" for m in at.metric)
