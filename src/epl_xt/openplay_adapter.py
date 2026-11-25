"""Only real OpenPlay (ENG, 2526) pass events to a canonical pass table.

OpenPlay does not document a recipient column. Never infer or fabricate it here.
"""
import pandas as pd

REQUIRED_SOURCE = {"comp", "season", "match_id", "team", "player", "type", "outcome", "x", "y", "end_x", "end_y"}
COORDS = ("x", "y", "end_x", "end_y")
# Provider qualifier flags marking dead-ball restart passes (OpenPlay DATA_DICTIONARY: q_ columns).
# Indirect free kicks are a subset of q_FreekickTaken in 2025/26. Kick-offs have no flag in the source.
SET_PIECE_FLAGS = ("q_CornerTaken", "q_FreekickTaken", "q_IndirectFreekickTaken", "q_ThrowIn", "q_GoalKick")


def convert_openplay_passes(events: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    missing = sorted(REQUIRED_SOURCE - set(events.columns))
    if missing:
        raise ValueError(f"OpenPlay source missing fields: {', '.join(missing)}")
    if events.empty:
        raise ValueError("No source events received")
    if not events["comp"].astype(str).eq("eng").all() or not events["season"].astype(str).eq("2526").all():
        raise ValueError("Source must contain only EPL (eng) 2025/26 (2526)")
    src = events.loc[events["type"].astype(str).eq("Pass")].copy()
    if src.empty:
        raise ValueError("Source contains no Pass events")
    outcomes = set(src["outcome"].dropna().astype(str).unique())
    if src["outcome"].isna().any() or not outcomes.issubset({"Successful", "Unsuccessful"}):
        raise ValueError(f"Unknown pass outcome(s): {outcomes}")
    for col in COORDS:
        src[col] = pd.to_numeric(src[col], errors="coerce")
    good = src[list(COORDS)].notna().all(axis=1)
    for col in COORDS:
        good &= src[col].between(0, 100)
    for col in ("match_id", "team", "player"):
        good &= src[col].notna() & src[col].astype(str).str.strip().ne("")
    dropped = int((~good).sum())
    src = src.loc[good].copy()
    if src.empty:
        raise ValueError("No valid pass events after coordinate/name checks")
    result = pd.DataFrame({
        "match_id": src["match_id"].astype(str),
        "team": src["team"].astype(str),
        "player": src["player"].astype(str),
        "recipient": pd.Series(pd.NA, index=src.index, dtype="string"),
        "x": src["x"].astype(float),
        "y": src["y"].astype(float),
        "end_x": src["end_x"].astype(float),
        "end_y": src["end_y"].astype(float),
        "is_successful": src["outcome"].astype(str).eq("Successful"),
        "is_open_play": _open_play(src),
    }).reset_index(drop=True)
    report = {"source_event_rows": len(events), "pass_rows": len(src), "dropped_pass_rows": dropped,
              "matches_with_passes": result["match_id"].nunique(), "recipient_status": "not provided by source"}
    if result["is_open_play"].isna().all():
        report["set_piece_flags"] = "unavailable in source; open-play filter disabled"
    else:
        report["set_piece_flags"] = list(SET_PIECE_FLAGS)
        report["set_piece_restart_pass_rows"] = int((~result["is_open_play"].astype(bool)).sum())
    return result, report


def _open_play(src: pd.DataFrame) -> pd.Series:
    """False for flagged restart passes, True otherwise; all-NA when any flag column is missing.

    Flags must be real booleans (missing values are not treated as False).
    """
    if not set(SET_PIECE_FLAGS) <= set(src.columns):
        return pd.Series(pd.NA, index=src.index, dtype="boolean")
    flags = src[list(SET_PIECE_FLAGS)]
    if flags.isna().any().any() or not all(pd.api.types.is_bool_dtype(flags[c]) for c in SET_PIECE_FLAGS):
        raise ValueError("Set-piece qualifier flags must be complete booleans")
    return ~flags.any(axis=1)
