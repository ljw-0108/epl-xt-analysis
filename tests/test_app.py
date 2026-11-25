"""App-level tests on a SYNTHETIC fixture (never real data); hashes are computed like the downloader."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from matplotlib.collections import LineCollection

from epl_xt.app_data import load_dataset, match_options
from epl_xt.charts import pass_map_figure, zone_heatmap_figure
from epl_xt.provenance_2526 import ALLOWED_SOURCE

APP = Path(__file__).resolve().parents[1] / "app.py"
M1, M2 = "SYNTHETIC_TEST_ONLY_1", "SYNTHETIC_TEST_ONLY_2"


def synthetic_passes():
    rows = []
    for match, home, away in ((M1, "Alpha", "Beta"), (M2, "Alpha", "Gamma")):
        for team in (home, away):
            for i, player in enumerate(("P1", "P2", "P3")):
                rows.append(dict(match_id=match, team=team, player=f"{team}_{player}", recipient=None,
                                 x=10 + 10 * i, y=50, end_x=60 + 10 * i, end_y=40, is_successful=True))
                rows.append(dict(match_id=match, team=team, player=f"{team}_{player}", recipient=None,
                                 x=70, y=30, end_x=50, end_y=30, is_successful=i != 2))
    return pd.DataFrame(rows)


@pytest.fixture()
def data_root(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "data/processed").mkdir(parents=True)
    passes = tmp_path / "data/processed/passes.csv"
    grid = tmp_path / "data/processed/xt_grid.csv"
    synthetic_passes().to_csv(passes, index=False)
    np.savetxt(grid, np.tile(np.linspace(0.01, 0.12, 12), (8, 1)), delimiter=",", fmt="%.8f")
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
    manifest = dict(competition="EPL", season="2025/26", source_reference=ALLOWED_SOURCE,
                    verification_method="source_release_sha256", match_ids=[M1, M2],
                    processed_passes_sha256=sha(passes), xt_grid_sha256=sha(grid))
    (tmp_path / "config/source_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path


def test_load_dataset_scores_and_indexes(data_root):
    manifest, scored, matches, grid = load_dataset(data_root)
    assert {"pass_xt", "is_progressive", "direction"} <= set(scored.columns)
    assert len(scored) == 24 and grid.shape == (8, 12)
    assert match_options(matches, "Alpha") == [(M1, f"vs Beta · {M1}"), (M2, f"vs Gamma · {M2}")]
    assert match_options(matches, "Beta") == [(M1, f"vs Alpha · {M1}")]


def test_load_dataset_rejects_tampering_and_id_mismatch(data_root):
    passes = data_root / "data/processed/passes.csv"
    passes.write_text(passes.read_text() + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="무결성"):
        load_dataset(data_root)


def test_load_dataset_rejects_manifest_match_ids_mismatch(data_root):
    path = data_root / "config/source_manifest.json"
    m = json.loads(path.read_text())
    m["match_ids"] = [M1]
    path.write_text(json.dumps(m))
    with pytest.raises(ValueError, match="경기 ID"):
        load_dataset(data_root)


def test_pass_map_draws_every_pass():
    df = synthetic_passes()
    fig = pass_map_figure(df, "t")
    segs = sum(len(c.get_segments()) for c in fig.axes[0].collections if isinstance(c, LineCollection))
    assert segs == len(df)


def test_heatmap_signed_is_centred_on_zero():
    m = np.zeros((8, 12))
    m[0, 0], m[3, 11] = -0.5, 2.0
    fig = zone_heatmap_figure(m, "t", signed=True)
    norm = fig.axes[0].images[0].norm
    assert norm.vcenter == 0 and norm.vmin == -2.0 and norm.vmax == 2.0
    with pytest.raises(ValueError, match="8 x 12"):
        zone_heatmap_figure(np.zeros((3, 3)), "t", signed=False)


# ---- Streamlit AppTest smoke tests ----
AppTest = pytest.importorskip("streamlit.testing.v1").AppTest


def run_app(monkeypatch, root):
    monkeypatch.setenv("EPL_DATA_ROOT", str(root))
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    return at


def metric(at, label):
    return next(m.value for m in at.metric if m.label == label)


def test_app_demo_path_and_filters_change_numbers(monkeypatch, data_root):
    at = run_app(monkeypatch, data_root)
    assert at.sidebar.selectbox[0].value == "Alpha"
    assert metric(at, "경기") == "2" and metric(at, "패스 시도") == "12"
    assert len(at.get("download_button")) == 1
    direction_table = at.dataframe[0].value
    assert "방향" in direction_table.columns and direction_table["성공률"].notna().all()
    assert "길이 0" not in direction_table["방향"].tolist()  # empty class hidden, not shown as None
    # Season -> one match: every tab's numbers follow the same filter.
    at.sidebar.radio[0].set_value("경기 선택").run()
    assert not at.exception
    assert at.sidebar.multiselect[0].value == [f"vs Beta · {M1}"]
    assert metric(at, "경기") == "1" and metric(at, "패스 시도") == "6"
    at.sidebar.multiselect[0].set_value([]).run()
    assert any("선택된 경기가 없습니다" in i.value for i in at.info)
    # Other team
    at.sidebar.radio[0].set_value("시즌 전체").run()
    at.sidebar.selectbox[0].set_value("Gamma").run()
    assert not at.exception
    assert metric(at, "경기") == "1" and metric(at, "패스 시도") == "6"


def test_app_player_comparison_same_player_warns(monkeypatch, data_root):
    at = run_app(monkeypatch, data_root)
    a = next(s for s in at.selectbox if s.label == "선수 A")
    b = next(s for s in at.selectbox if s.label == "선수 B")
    assert a.value != b.value
    b.set_value(a.value).run()
    assert any("서로 다른 두 선수" in w.value for w in at.warning)


def test_app_without_data_shows_instructions(monkeypatch, tmp_path):
    at = run_app(monkeypatch, tmp_path)
    assert any("데이터 준비 전" in w.value for w in at.warning)
    assert not at.metric


def test_heatmap_labels_never_show_negative_zero():
    m = np.zeros((8, 12))
    m[0, 0], m[1, 1] = -0.0001, 0.5
    texts = [t.get_text() for t in zone_heatmap_figure(m, "t", signed=True).axes[0].texts]
    assert "-0.00" not in texts and "0.00" in texts and "0.50" in texts
