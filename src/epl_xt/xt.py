"""Pass-only signed expected-threat deltas for a sourced xT grid."""

import numpy as np
import pandas as pd
from .validation import validate_passes


GRID_ROWS, GRID_COLS = 8, 12


def grid_cells(x, y) -> tuple[np.ndarray, np.ndarray]:
    """(row, col) cell of 0..100 positions; x=100 / y=100 fall in the last cell."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if not np.isfinite(x).all() or not np.isfinite(y).all() or (x < 0).any() or (x > 100).any() or (y < 0).any() or (y > 100).any():
        raise ValueError("x/y must be finite coordinates in 0..100")
    cols = np.minimum((x / 100 * GRID_COLS).astype(int), GRID_COLS - 1)
    rows = np.minimum((y / 100 * GRID_ROWS).astype(int), GRID_ROWS - 1)
    return rows, cols


def grid_values_at(x: np.ndarray, y: np.ndarray, grid: np.ndarray) -> np.ndarray:
    """Sample grid at normalized (0..100) positions; grid rows=y, cols=x."""
    grid = np.asarray(grid, dtype=float)
    if grid.shape != (GRID_ROWS, GRID_COLS) or not np.isfinite(grid).all():
        raise ValueError("Expected a finite 8-row x 12-column xT grid")
    rows, cols = grid_cells(x, y)
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


def team_xt_summary(df_with_xt: pd.DataFrame) -> pd.DataFrame:
    """Per-team signed pass-xT for the rows given (apply team/match filters first).

    pass_xt_total = positive_xt + negative_xt, over successful passes only.
    """
    cols = ["team", "matches", "successful_passes", "pass_xt_total", "positive_xt", "negative_xt", "xt_per_successful_pass"]
    if "pass_xt" not in df_with_xt.columns:
        raise ValueError("Call add_pass_xt first")
    successful = df_with_xt.loc[df_with_xt["is_successful"]].copy()
    if successful.empty:
        return pd.DataFrame(columns=cols)
    successful["positive_xt"] = successful["pass_xt"].clip(lower=0)
    successful["negative_xt"] = successful["pass_xt"].clip(upper=0)
    out = (successful.groupby("team", as_index=False)
           .agg(matches=("match_id", "nunique"), successful_passes=("pass_xt", "size"),
                pass_xt_total=("pass_xt", "sum"), positive_xt=("positive_xt", "sum"),
                negative_xt=("negative_xt", "sum")))
    out["xt_per_successful_pass"] = out["pass_xt_total"] / out["successful_passes"]
    return out[cols].sort_values("pass_xt_total", ascending=False, kind="stable").reset_index(drop=True)


def xt_by_zone(df_with_xt: pd.DataFrame, location: str = "start", value: str = "sum") -> np.ndarray:
    """8x12 matrix (rows=y, cols=x toward the attacked goal) over successful passes.

    location: "start" attributes each pass's signed xT to the cell it was played from,
              "end" to the cell it arrived in.
    value:    "sum" = signed xT total per cell, "count" = number of successful passes.
    The "sum" matrix always adds up to the selection's total pass xT.
    """
    if location not in ("start", "end"):
        raise ValueError("location must be 'start' or 'end'")
    if value not in ("sum", "count"):
        raise ValueError("value must be 'sum' or 'count'")
    if "pass_xt" not in df_with_xt.columns:
        raise ValueError("Call add_pass_xt first")
    successful = df_with_xt.loc[df_with_xt["is_successful"]]
    xs, ys = ("x", "y") if location == "start" else ("end_x", "end_y")
    matrix = np.zeros((GRID_ROWS, GRID_COLS))
    if successful.empty:
        return matrix
    rows, cols = grid_cells(successful[xs].to_numpy(), successful[ys].to_numpy())
    weights = successful["pass_xt"].to_numpy(dtype=float) if value == "sum" else np.ones(len(successful))
    np.add.at(matrix, (rows, cols), weights)
    return matrix
