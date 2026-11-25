import numpy as np
import pandas as pd
import pytest

from epl_xt.quality import audit_events, audit_xt_grid, match_index


def events():
    base = dict(comp="eng", season="2526", period="FirstHalf", minute=1, second=0, related_player_id=None)
    return pd.DataFrame([
        dict(base, match_id="SYNTHETIC_TEST_ONLY_1", event_id=1, team="A", player="P1", type="Pass", outcome="Successful", x=10, y=10, end_x=20, end_y=20),
        dict(base, match_id="SYNTHETIC_TEST_ONLY_1", event_id=2, team="B", player="Q1", type="Pass", outcome="Unsuccessful", x=50, y=50, end_x=60, end_y=60),
        dict(base, match_id="SYNTHETIC_TEST_ONLY_1", event_id=3, team="B", player="Q1", type="Tackle", outcome="Successful", x=50, y=50, end_x=None, end_y=None),
        dict(base, match_id="SYNTHETIC_TEST_ONLY_2", event_id=1, team="A", player="Q1", type="Pass", outcome="Successful", x=0, y=0, end_x=100, end_y=100),
        dict(base, match_id="SYNTHETIC_TEST_ONLY_2", event_id=2, team="C", player="R1", type="Pass", outcome="Successful", x=5, y=5, end_x=6, end_y=6),
    ])


def test_audit_counts_are_measured():
    r = audit_events(events())
    assert r["source_event_rows"] == 5
    assert r["pass_rows"] == 4
    assert r["pass_outcomes"] == {"Successful": 3, "Unsuccessful": 1}
    assert r["matches_with_passes"] == 2
    assert r["matches_without_exactly_two_passing_teams"] == 0
    assert r["pass_coord_out_of_0_100"] == 0
    assert r["players_on_multiple_teams"] == 1  # Q1 appears for B and A
    assert r["pass_related_player_id_non_null_share"] == 0.0
    assert r["pass_content_duplicates"] == 0
    assert r["event_key_duplicates_match_event_team"] == 0


def test_audit_detects_duplicates_and_out_of_bounds():
    ev = pd.concat([events(), events().iloc[[0]]], ignore_index=True)
    ev.loc[1, "end_x"] = 101
    r = audit_events(ev)
    assert r["full_row_duplicates"] == 1
    assert r["pass_content_duplicates"] == 1
    assert r["event_key_duplicates_match_event_team"] == 1
    assert r["pass_coord_out_of_0_100"] == 1


def test_grid_orientation_evidence():
    grid = np.tile(np.arange(12, dtype=float), (8, 1))
    r = audit_xt_grid(grid)
    assert r["last_col_mean_gt_first_col_mean"] is True
    assert r["max_vertical_asymmetry"] == 0.0
    with pytest.raises(ValueError, match="8-row"):
        audit_xt_grid(np.zeros((12, 8)))


def test_match_index_derives_opponent_from_data_only():
    passes = events().loc[lambda d: d.type == "Pass"]
    idx = match_index(passes)
    row = idx.set_index(["match_id", "team"]).loc[("SYNTHETIC_TEST_ONLY_1", "A")]
    assert row.opponent == "B"
    assert row.team_pass_rows == 1
    assert len(idx) == 4
    assert not {"date", "home", "away"} & set(idx.columns)  # not in source; never invented


def test_match_index_refuses_single_team_match():
    passes = events().loc[lambda d: (d.type == "Pass") & (d.team != "B")]
    with pytest.raises(ValueError, match="exactly two teams"):
        match_index(passes)


def test_categorical_source_columns_do_not_create_phantom_groups():
    ev = events()
    for col in ("match_id", "team", "player"):
        ev[col] = pd.Categorical(ev[col], categories=sorted(ev[col].unique()) + ["UNUSED"])
    r = audit_events(ev)
    assert r["matches_without_exactly_two_passing_teams"] == 0
    assert "UNUSED" not in r["matches_per_team"]
    passes = ev.loc[ev.type == "Pass"]
    assert len(match_index(passes)) == 4
