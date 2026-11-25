"""Measured data-quality audit of OpenPlay EPL 2025/26 events and the xT grid.

Every number returned here is computed from the input; nothing is assumed or imputed.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

PASS_KEY = ["match_id", "team", "player", "period", "minute", "second", "x", "y", "end_x", "end_y"]
COORDS = ["x", "y", "end_x", "end_y"]


def audit_events(events: pd.DataFrame) -> dict:
    """Return schema/coverage/quality counts for raw OpenPlay events."""
    required = {"comp", "season", "match_id", "team", "player", "type", "outcome", *COORDS}
    missing = sorted(required - set(events.columns))
    if missing:
        raise ValueError(f"Audit input missing fields: {', '.join(missing)}")
    passes = events.loc[events["type"].astype(str).eq("Pass")]
    report: dict = {
        "source_event_rows": int(len(events)),
        "comp_values": sorted(events["comp"].astype(str).unique().tolist()),
        "season_values": sorted(events["season"].astype(str).unique().tolist()),
        "full_row_duplicates": int(events.duplicated().sum()),
        "matches": int(events["match_id"].nunique()),
        "teams": int(events["team"].dropna().nunique()),
        "pass_rows": int(len(passes)),
        "pass_outcomes": {str(k): int(v) for k, v in passes["outcome"].value_counts(dropna=False).items()},
        "pass_nulls": {c: int(passes[c].isna().sum()) for c in ["match_id", "team", "player", "outcome", *COORDS]},
    }
    if "event_id" in events.columns:
        report["event_key_duplicates_match_event_team"] = int(events.duplicated(["match_id", "event_id", "team"]).sum())
    key = [c for c in PASS_KEY if c in passes.columns]
    report["pass_content_duplicates"] = int(passes.duplicated(key).sum())
    report["pass_content_duplicate_key"] = key
    coords = passes[COORDS].apply(pd.to_numeric, errors="coerce")
    report["pass_coord_min"] = {c: float(coords[c].min()) for c in COORDS}
    report["pass_coord_max"] = {c: float(coords[c].max()) for c in COORDS}
    report["pass_coord_out_of_0_100"] = int((~coords.apply(lambda s: s.between(0, 100))).any(axis=1).sum())
    if "period" in passes.columns:
        report["pass_periods"] = {str(k): int(v) for k, v in passes["period"].value_counts().items() if v}
    teams_per_match = passes.groupby("match_id")["team"].nunique()
    report["matches_with_passes"] = int(passes["match_id"].nunique())
    report["matches_without_exactly_two_passing_teams"] = int((teams_per_match != 2).sum())
    report["matches_per_team"] = {str(k): int(v) for k, v in passes.groupby("team")["match_id"].nunique().items()}
    report["players_with_passes"] = int(passes["player"].nunique())
    report["players_on_multiple_teams"] = int(passes.groupby("player")["team"].nunique().gt(1).sum())
    if "related_player_id" in passes.columns:
        report["pass_related_player_id_non_null_share"] = float(passes["related_player_id"].notna().mean()) if len(passes) else 0.0
    return report


def audit_xt_grid(grid) -> dict:
    """Shape, range and orientation evidence for an 8x12 xT grid (rows=y, cols=x)."""
    g = np.asarray(grid, dtype=float)
    if g.shape != (8, 12) or not np.isfinite(g).all():
        raise ValueError("Expected a finite 8-row x 12-column xT grid")
    return {
        "shape": list(g.shape),
        "min": float(g.min()),
        "max": float(g.max()),
        "argmax_row_col": [int(i) for i in np.unravel_index(g.argmax(), g.shape)],
        # Attack is toward x=100 (col 11): the final column should dominate the first.
        "last_col_mean_gt_first_col_mean": bool(g[:, -1].mean() > g[:, 0].mean()),
        # Max |row r - row 7-r|; 0 means the y orientation cannot change any value.
        "max_vertical_asymmetry": float(np.abs(g - g[::-1]).max()),
    }


def match_index(passes: pd.DataFrame) -> pd.DataFrame:
    """One row per (match, team) with the opponent derived from the same match's passes.

    Only teams actually present in the data are used; matches whose pass rows do not
    contain exactly two teams raise instead of guessing an opponent. No dates or
    home/away flags are produced because the source columns do not contain them.
    """
    for col in ("match_id", "team"):
        if col not in passes.columns:
            raise ValueError(f"Missing column: {col}")
    pairs = passes.groupby("match_id")["team"].agg(lambda s: sorted(s.astype(str).unique()))
    bad = pairs[pairs.map(len) != 2]
    if not bad.empty:
        raise ValueError(f"Matches without exactly two teams: {bad.index.astype(str).tolist()[:5]}")
    counts = passes.groupby(["match_id", "team"]).size()
    rows = []
    for match_id, (a, b) in pairs.items():
        for team, opp in ((a, b), (b, a)):
            rows.append({"match_id": str(match_id), "team": team, "opponent": opp,
                         "team_pass_rows": int(counts.loc[(match_id, team)])})
    return pd.DataFrame(rows).sort_values(["team", "match_id"]).reset_index(drop=True)
