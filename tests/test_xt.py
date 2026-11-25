import numpy as np
import pandas as pd
import pytest
from epl_xt.xt import grid_values_at, add_pass_xt, player_xt_ranking


def rows():
    return pd.DataFrame([
        dict(match_id="SYNTHETIC_TEST_ONLY", team="A", player="P1", recipient="P2", x=0, y=10, end_x=100, end_y=10, is_successful=True),
        dict(match_id="SYNTHETIC_TEST_ONLY", team="A", player="P2", recipient="P1", x=100, y=10, end_x=0, end_y=10, is_successful=True),
        dict(match_id="SYNTHETIC_TEST_ONLY", team="A", player="P1", recipient=None, x=0, y=10, end_x=100, end_y=10, is_successful=False),
    ])


def test_grid_edges_zero_and_hundred():
    grid = np.tile(np.arange(12, dtype=float), (8, 1))
    np.testing.assert_array_equal(grid_values_at([0, 100], [0, 100], grid), [0, 11])


def test_forward_backward_failed_pass():
    grid = np.tile(np.arange(12, dtype=float), (8, 1))
    scored = add_pass_xt(rows(), grid)
    assert scored["pass_xt"].tolist() == [11, -11, 0]
    ranked = player_xt_ranking(scored)
    assert ranked.set_index("player").loc["P1", "pass_xt"] == 11
    assert ranked.set_index("player").loc["P2", "pass_xt"] == -11


def test_out_of_range_is_rejected():
    grid = np.zeros((8, 12))
    bad = rows()
    bad.loc[0, "x"] = 101
    with pytest.raises(ValueError, match="coordinates"):
        add_pass_xt(bad, grid)


def test_grid_shape_is_checked():
    with pytest.raises(ValueError, match="8-row"):
        grid_values_at([1], [1], np.zeros((3, 3)))


def test_string_false_not_truthy():
    grid = np.tile(np.arange(12, dtype=float), (8, 1))
    df = rows()
    df["is_successful"] = ["true", "true", "false"]
    assert add_pass_xt(df, grid)["pass_xt"].tolist() == [11, -11, 0]


from epl_xt.xt import team_xt_summary, xt_by_zone


def scored_two_teams():
    grid = np.tile(np.arange(12, dtype=float), (8, 1))
    df = pd.concat([rows(), rows().assign(team="B", match_id="SYNTHETIC_TEST_ONLY_2")], ignore_index=True)
    df.loc[3, "end_x"] = 50  # B's forward pass: col 0 -> col 6 = +6
    return add_pass_xt(df, grid)


def test_team_summary_signed_parts():
    s = team_xt_summary(scored_two_teams()).set_index("team")
    assert s.loc["A", "pass_xt_total"] == 0  # +11 and -11
    assert s.loc["A", "positive_xt"] == 11 and s.loc["A", "negative_xt"] == -11
    assert s.loc["A", "successful_passes"] == 2  # failed pass excluded
    assert s.loc["B", "pass_xt_total"] == -5  # +6 and -11
    assert s.loc["B", "xt_per_successful_pass"] == -2.5
    assert list(s.index) == ["A", "B"]  # sorted by total


def test_team_summary_empty():
    scored = scored_two_teams()
    assert team_xt_summary(scored.loc[~scored.is_successful]).empty


def test_zone_matrix_start_end_and_count():
    a = scored_two_teams().loc[lambda d: d.team == "A"]
    start = xt_by_zone(a, "start")
    end = xt_by_zone(a, "end")
    count = xt_by_zone(a, "start", "count")
    # y=10 -> row 0; P1 from col 0 (+11), P2 from col 11 (-11)
    assert start[0, 0] == 11 and start[0, 11] == -11
    assert end[0, 11] == 11 and end[0, 0] == -11
    assert count.sum() == 2 and count[0, 0] == 1
    assert start.shape == (8, 12)
    with pytest.raises(ValueError, match="location"):
        xt_by_zone(a, "middle")


def test_independent_reimplementation_matches_on_synthetic_sample():
    """Synthetic random passes (not real data): compare against a np.digitize implementation."""
    rng = np.random.default_rng(2526)
    n = 5000
    grid = rng.random((8, 12))
    df = pd.DataFrame({
        "match_id": rng.choice(["SYNTHETIC_TEST_ONLY_1", "SYNTHETIC_TEST_ONLY_2"], n),
        "team": rng.choice(["A", "B"], n), "player": "P", "recipient": None,
        "x": rng.uniform(0, 100, n), "y": rng.uniform(0, 100, n),
        "end_x": rng.uniform(0, 100, n), "end_y": rng.uniform(0, 100, n),
        "is_successful": rng.random(n) < 0.8,
    })
    df.loc[:9, ["x", "end_x", "y", "end_y"]] = 100.0  # edges must land in the last cell
    scored = add_pass_xt(df, grid)

    def cell_value(x, y):
        c = np.digitize(x, np.linspace(0, 100, 13)[1:-1])
        r = np.digitize(y, np.linspace(0, 100, 9)[1:-1])
        return grid[r, c]

    ok = df["is_successful"].to_numpy()
    expected = np.where(ok, cell_value(df.end_x, df.end_y) - cell_value(df.x, df.y), 0.0)
    np.testing.assert_allclose(scored["pass_xt"].to_numpy(), expected, atol=1e-12)
    summary = team_xt_summary(scored).set_index("team")
    for team in ("A", "B"):
        mask = (df.team == team).to_numpy()
        assert summary.loc[team, "pass_xt_total"] == pytest.approx(expected[mask].sum(), abs=1e-9)
        assert xt_by_zone(scored.loc[mask]).sum() == pytest.approx(expected[mask].sum(), abs=1e-9)
