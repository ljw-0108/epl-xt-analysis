"""Verified dataset loading for the Streamlit app (no UI code here, so it is unit-testable)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .passing import add_pass_geometry
from .provenance_2526 import read_verified_import
from .quality import match_index
from .xt import add_pass_xt


def data_paths(root: str | Path) -> dict:
    root = Path(root)
    return {"manifest": root / "config/source_manifest.json",
            "passes": root / "data/processed/passes.csv",
            "grid": root / "data/processed/xt_grid.csv"}


def load_dataset(root: str | Path) -> tuple[dict, pd.DataFrame, pd.DataFrame, np.ndarray]:
    """Checksum-verified passes scored with geometry and xT, plus a per-team match index.

    Raises ValueError/OSError when the import is missing, tampered with, or its match ids
    differ from the manifest; the app shows the error instead of any numbers.
    """
    paths = data_paths(root)
    manifest = read_verified_import(paths["manifest"], paths["passes"], paths["grid"])
    passes = pd.read_csv(paths["passes"], dtype={"match_id": str})
    grid = np.loadtxt(paths["grid"], delimiter=",")
    if set(passes["match_id"].astype(str).unique()) != {str(m) for m in manifest["match_ids"]}:
        raise ValueError("실제 패스 데이터 경기 ID와 출처 기록이 일치하지 않습니다")
    scored = add_pass_xt(add_pass_geometry(passes), grid)
    return manifest, scored, match_index(scored), grid


def match_options(matches: pd.DataFrame, team: str) -> list[tuple[str, str]]:
    """(match_id, label) for one team; labels show only data-derived opponent and id."""
    rows = matches.loc[matches["team"] == team].sort_values("match_id")
    return [(r.match_id, f"vs {r.opponent} · {r.match_id}") for r in rows.itertuples(index=False)]
