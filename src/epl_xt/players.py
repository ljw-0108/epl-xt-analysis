"""Player pass/xT tables, rankings and two-player comparison on an already-filtered selection.

Players are keyed by (team, player): a player who changed clubs appears once per club and
is never merged across teams. No minutes are available in the source, so nothing here is
per-90; `matches` counts matches in the selection where the player attempted a pass.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

KEY = ["team", "player"]
TABLE_COLUMNS = KEY + ["matches", "attempted", "successful", "completion_rate", "progressive",
                       "pass_xt", "positive_xt", "xt_per_successful_pass"]
RANKABLE = ("attempted", "successful", "completion_rate", "progressive", "pass_xt",
            "positive_xt", "xt_per_successful_pass")


def player_table(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (team, player). Input needs `pass_xt` (add_pass_xt) and `is_progressive` (add_pass_geometry)."""
    missing = sorted({"pass_xt", "is_progressive", "is_successful", "match_id", *KEY} - set(df.columns))
    if missing:
        raise ValueError(f"Missing columns for player table: {', '.join(missing)}")
    if df.empty:
        return pd.DataFrame(columns=TABLE_COLUMNS)
    work = df[KEY + ["match_id", "is_successful", "is_progressive", "pass_xt"]].copy()
    ok = work["is_successful"].astype(bool)
    work["succ_xt"] = np.where(ok, work["pass_xt"], 0.0)
    work["succ_pos_xt"] = np.where(ok, work["pass_xt"].clip(lower=0), 0.0)
    out = (work.groupby(KEY, as_index=False)
           .agg(matches=("match_id", "nunique"), attempted=("match_id", "size"),
                successful=("is_successful", "sum"), progressive=("is_progressive", "sum"),
                pass_xt=("succ_xt", "sum"), positive_xt=("succ_pos_xt", "sum")))
    out["successful"] = out["successful"].astype(int)
    out["progressive"] = out["progressive"].astype(int)
    out["completion_rate"] = out["successful"] / out["attempted"]
    out["xt_per_successful_pass"] = np.where(out["successful"] > 0,
                                             out["pass_xt"] / out["successful"].where(out["successful"] > 0, 1),
                                             np.nan)
    return out[TABLE_COLUMNS].sort_values(KEY).reset_index(drop=True)


def rank_players(table: pd.DataFrame, metric: str = "pass_xt", min_attempted: int = 0,
                 top: int | None = None) -> pd.DataFrame:
    """Descending ranking; players below `min_attempted` and NaN metric values are excluded."""
    if metric not in RANKABLE:
        raise ValueError(f"metric must be one of {RANKABLE}")
    if min_attempted < 0:
        raise ValueError("min_attempted must be >= 0")
    ranked = table.loc[(table["attempted"] >= min_attempted) & table[metric].notna()]
    ranked = ranked.sort_values([metric, "team", "player"], ascending=[False, True, True], kind="stable")
    ranked = ranked.reset_index(drop=True)
    ranked.insert(0, "rank", ranked.index + 1)
    return ranked.head(top) if top is not None else ranked


def player_label(team: str, player: str) -> str:
    return f"{player} ({team})"


def compare_players(table: pd.DataFrame, keys: list[tuple[str, str]]) -> dict:
    """Compare exactly two distinct (team, player) keys from the same filtered table.

    Returns {"found": DataFrame of found players in the requested order,
             "missing": list of keys with no passes in this selection}.
    A missing player is reported, never filled with zeros.
    """
    keys = [(str(t), str(p)) for t, p in keys]
    if len(keys) != 2 or keys[0] == keys[1]:
        raise ValueError("Select exactly two different players")
    indexed = table.set_index(KEY)
    found = [k for k in keys if k in indexed.index]
    missing = [k for k in keys if k not in indexed.index]
    rows = indexed.loc[found].reset_index() if found else pd.DataFrame(columns=TABLE_COLUMNS)
    return {"found": rows[TABLE_COLUMNS].reset_index(drop=True), "missing": missing}
