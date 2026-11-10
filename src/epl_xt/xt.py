"""Pass-only signed expected-threat deltas for a sourced xT grid."""

import numpy as np
import pandas as pd
from .validation import validate_passes


def grid_values_at(x: np.ndarray, y: np.ndarray, grid: np.ndarray) -> np.ndarray:
    """Sample grid at normalized (0..100) positions; grid rows=y, cols=x."""
    grid = np.asarray(grid, dtype=float)
    if grid.shape != (8, 12) or not np.isfinite(grid).all():
        raise ValueError("Expected a finite 8-row x 12-column xT grid")
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if not np.isfinite(x).all() or not np.isfinite(y).all() or (x < 0).any() or (x > 100).any() or (y < 0).any() or (y > 100).any():
        raise ValueError("x/y must be finite coordinates in 0..100")
    cols = np.minimum((x / 100 * 12).astype(int), 11)
    rows = np.minimum((y / 100 * 8).astype(int), 7)
    return grid[rows, cols]


def add_pass_xt(df: pd.DataFrame, grid: np.ndarray) -> pd.DataFrame:
    """Successful pass: signed xT(end)-xT(start); failed pass: 0 by MVP definition."""
    result = validate_passes(df)
    start = grid_values_at(result["x"].to_numpy(), result["y"].to_numpy(), grid)
    end = grid_values_at(result["end_x"].to_numpy(), result["end_y"].to_numpy(), grid)
    result["pass_xt"] = np.where(result["is_successful"].to_numpy(), end - start, 0.0)
    return result


def player_xt_ranking(df_with_xt: pd.DataFrame) -> pd.DataFrame:
    """Signed pass-xT sums, among successful passes only, by team/player."""
    successful = df_with_xt.loc[df_with_xt["is_successful"]].copy()
    if successful.empty:
        return pd.DataFrame(columns=["team", "player", "pass_xt", "successful_passes"])
    return (successful.groupby(["team", "player"], as_index=False)
            .agg(pass_xt=("pass_xt", "sum"), successful_passes=("pass_xt", "size"))
            .sort_values("pass_xt", ascending=False, kind="stable")
            .reset_index(drop=True))
