"""Directed pass-network edges and passer-node locations."""

import pandas as pd
from .validation import validate_passes


def build_pass_network(df: pd.DataFrame, min_passes: int = 1) -> tuple[pd.DataFrame, pd.DataFrame]:
    if min_passes < 1:
        raise ValueError("min_passes must be >= 1")
    valid = validate_passes(df)
    passes = valid.loc[valid["is_successful"]].copy()
    passes = passes.loc[passes["recipient"].notna() & passes["recipient"].astype(str).str.strip().ne("")]
    edges = (passes.groupby(["team", "player", "recipient"], as_index=False)
             .size().rename(columns={"size": "pass_count"}))
    edges = edges.loc[edges["pass_count"] >= min_passes].reset_index(drop=True)
    nodes = (passes.groupby(["team", "player"], as_index=False)
             .agg(x=("x", "mean"), y=("y", "mean"), passes_made=("x", "size")))
    return nodes, edges
