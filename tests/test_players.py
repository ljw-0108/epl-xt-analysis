import numpy as np
import pandas as pd
import pytest

from epl_xt.passing import add_pass_geometry, filter_passes
from epl_xt.players import compare_players, player_table, rank_players
from epl_xt.xt import add_pass_xt

GRID = np.tile(np.arange(12, dtype=float), (8, 1))  # +1 per column toward x=100
M1, M2 = "SYNTHETIC_TEST_ONLY_1", "SYNTHETIC_TEST_ONLY_2"


def p(player, x, end_x, ok=True, team="A", match=M1):
    return dict(match_id=match, team=team, player=player, recipient=None,
                x=x, y=50, end_x=end_x, end_y=50, is_successful=ok)


def passes():
    return pd.DataFrame([
        p("P1", 10, 60), p("P1", 60, 10), p("P1", 10, 90, ok=False),   # M1
        p("P1", 30, 80, match=M2),                                     # M2
        p("P2", 50, 55), p("P2", 50, 55, match=M2),
        p("P3", 10, 20, ok=False),                                     # no successful pass
        p("P1", 10, 60, team="B", match=M2),                           # same name, other club
    ])


def table(df):
    return player_table(add_pass_xt(add_pass_geometry(df), GRID))


def test_player_table_values():
    t = table(passes()).set_index(["team", "player"])
    p1 = t.loc[("A", "P1")]
    assert (p1.matches, p1.attempted, p1.successful) == (2, 4, 3)
    assert p1.completion_rate == 0.75
    # cols: 10->60 = 1->7 (+6), 60->10 = 7->1 (-6), 30->80 = 3->9 (+6); failed pass = 0
    assert p1.pass_xt == 6 and p1.positive_xt == 12
    assert p1.xt_per_successful_pass == 2
    assert p1.progressive == 2  # both forward successful passes are >=25% closer; failed one excluded
    assert np.isnan(t.loc[("A", "P3"), "xt_per_successful_pass"])
    assert t.loc[("A", "P3"), "completion_rate"] == 0
    assert ("B", "P1") in t.index and t.loc[("B", "P1"), "attempted"] == 1  # not merged across clubs


def test_match_filter_changes_both_players_consistently():
    full = table(filter_passes(passes(), team="A"))
    only_m1 = table(filter_passes(passes(), team="A", match_ids=[M1]))
    cmp_full = compare_players(full, [("A", "P1"), ("A", "P2")])["found"].set_index("player")
    cmp_m1 = compare_players(only_m1, [("A", "P1"), ("A", "P2")])["found"].set_index("player")
    assert cmp_full.loc["P1", "attempted"] == 4 and cmp_m1.loc["P1", "attempted"] == 3
    assert cmp_full.loc["P2", "matches"] == 2 and cmp_m1.loc["P2", "matches"] == 1
    assert cmp_m1.loc["P1", "pass_xt"] == 0  # +6 and -6 within M1 only


def test_missing_player_is_reported_not_zero_filled():
    t = table(filter_passes(passes(), team="A", match_ids=[M2]))
    result = compare_players(t, [("A", "P1"), ("A", "P3")])
    assert result["missing"] == [("A", "P3")]
    assert result["found"]["player"].tolist() == ["P1"]
    none = compare_players(t, [("A", "X"), ("A", "Y")])
    assert none["found"].empty and len(none["missing"]) == 2


def test_compare_requires_two_distinct_players():
    t = table(passes())
    with pytest.raises(ValueError, match="exactly two"):
        compare_players(t, [("A", "P1")])
    with pytest.raises(ValueError, match="exactly two"):
        compare_players(t, [("A", "P1"), ("A", "P1")])


def test_ranking_threshold_and_nan():
    t = table(passes())
    r = rank_players(t, "pass_xt", min_attempted=2)
    assert r["player"].tolist() == ["P1", "P2"]  # P1 6 > P2 0; P3 and B/P1 below threshold
    assert r["rank"].tolist() == [1, 2]
    r2 = rank_players(t, "xt_per_successful_pass")
    assert ("A", "P3") not in set(zip(r2.team, r2.player))  # NaN excluded, not ranked as 0
    assert len(rank_players(t, "attempted", top=1)) == 1
    with pytest.raises(ValueError, match="metric"):
        rank_players(t, "goals")


def test_empty_selection():
    empty = table(passes()).iloc[0:0]
    assert rank_players(empty).empty
    assert compare_players(empty, [("A", "P1"), ("A", "P2")])["found"].empty
    assert player_table(add_pass_xt(add_pass_geometry(passes()), GRID).iloc[0:0]).empty
