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
