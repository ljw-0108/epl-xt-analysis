"""Team/match pass filtering, direction classes and progressive passes.

Coordinates are OpenPlay's native 0..100 for both axes; every team attacks toward x=100.
Angles and distances are computed on a nominal 105 m x 68 m pitch so that one unit of x and
one unit of y are not treated as equal lengths. Real pitch sizes vary slightly by stadium;
the nominal size is a documented approximation, not a measured venue dimension.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from .validation import validate_passes

PITCH_LENGTH_M = 105.0
PITCH_WIDTH_M = 68.0
GOAL_CENTRE = (100.0, 50.0)
FORWARD_MAX_DEG = 45.0     # |angle| <  45  -> forward
BACKWARD_MIN_DEG = 135.0   # |angle| > 135  -> backward; otherwise lateral
PROGRESSIVE_REDUCTION = 0.25  # end must be >= 25% closer to the goal centre than the start
DIRECTIONS = ("forward", "lateral", "backward", "zero_length")


def filter_passes(df: pd.DataFrame, team: str | None = None,
                  match_ids: Iterable[str] | None = None) -> pd.DataFrame:
    """Validated subset for one team and/or a set of match ids (None = no restriction)."""
    result = validate_passes(df)
    if team is not None:
        result = result.loc[result["team"].astype(str) == str(team)]
    if match_ids is not None:
        wanted = {str(m) for m in match_ids}
        result = result.loc[result["match_id"].astype(str).isin(wanted)]
    return result.copy()


def _metres(dx, dy):
    return np.asarray(dx, dtype=float) * PITCH_LENGTH_M / 100.0, np.asarray(dy, dtype=float) * PITCH_WIDTH_M / 100.0


def distance_to_goal_m(x, y) -> np.ndarray:
    """Metric distance from (x, y) to the centre of the attacked goal at (100, 50)."""
    mx, my = _metres(np.asarray(x, dtype=float) - GOAL_CENTRE[0], np.asarray(y, dtype=float) - GOAL_CENTRE[1])
    return np.hypot(mx, my)


def add_pass_geometry(df: pd.DataFrame) -> pd.DataFrame:
    """Add length_m, angle_deg (0 = straight toward x=100), direction and is_progressive.

    is_progressive applies only to successful passes: an unsuccessful pass never reached
    its end location as a completed pass, so it is not counted as progressing the ball.
    """
    result = validate_passes(df)
    dx_m, dy_m = _metres(result["end_x"] - result["x"], result["end_y"] - result["y"])
    length = np.hypot(dx_m, dy_m)
    # Round to remove floating noise so that exact 45/135 degree passes classify deterministically.
    angle = np.round(np.degrees(np.arctan2(dy_m, dx_m)), 9)
    abs_angle = np.abs(angle)
    direction = np.where(abs_angle < FORWARD_MAX_DEG, "forward",
                         np.where(abs_angle > BACKWARD_MIN_DEG, "backward", "lateral"))
    direction = np.where(length == 0, "zero_length", direction)
    start_d = distance_to_goal_m(result["x"], result["y"])
    end_d = distance_to_goal_m(result["end_x"], result["end_y"])
    closer = np.round(end_d, 9) <= np.round(start_d * (1 - PROGRESSIVE_REDUCTION), 9)
    result["length_m"] = length
    result["angle_deg"] = np.where(length == 0, np.nan, angle)
    result["direction"] = pd.Categorical(direction, categories=DIRECTIONS)
    result["is_progressive"] = result["is_successful"].to_numpy() & (start_d > 0) & closer
    return result


def direction_distribution(df_geom: pd.DataFrame) -> pd.DataFrame:
    """Counts and shares of attempted and successful passes per direction class."""
    if "direction" not in df_geom.columns:
        raise ValueError("Call add_pass_geometry first")
    out = pd.DataFrame(index=pd.Index(DIRECTIONS, name="direction"))
    out["attempted"] = df_geom.groupby("direction", observed=False).size().reindex(DIRECTIONS, fill_value=0)
    succ = df_geom.loc[df_geom["is_successful"]]
    out["successful"] = succ.groupby("direction", observed=False).size().reindex(DIRECTIONS, fill_value=0)
    total = out["attempted"].sum()
    out["share_of_attempted"] = out["attempted"] / total if total else 0.0
    out["completion_rate"] = np.where(out["attempted"] > 0, out["successful"] / out["attempted"].where(out["attempted"] > 0, 1), np.nan)
    return out.reset_index()


def passing_summary(df_geom: pd.DataFrame) -> dict:
    """Headline counts for the filtered passes; rates are None when nothing was attempted."""
    attempted = int(len(df_geom))
    successful = int(df_geom["is_successful"].sum()) if attempted else 0
    return {
        "matches": int(df_geom["match_id"].nunique()) if attempted else 0,
        "attempted": attempted,
        "successful": successful,
        "completion_rate": successful / attempted if attempted else None,
        "progressive": int(df_geom["is_progressive"].sum()) if attempted else 0,
    }
