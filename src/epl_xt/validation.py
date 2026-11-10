"""Validation of the documented canonical pass-event schema."""

import pandas as pd

REQUIRED = ("match_id", "team", "player", "recipient", "x", "y", "end_x", "end_y", "is_successful")
COORDS = ("x", "y", "end_x", "end_y")


def validate_passes(df: pd.DataFrame) -> pd.DataFrame:
    """Return a validated copy; input must contain pass events only, already normalized."""
    missing = sorted(set(REQUIRED) - set(df.columns))
    if missing:
        raise ValueError(f"Missing columns: {', '.join(missing)}")
    result = df.copy()
    for col in COORDS:
        result[col] = pd.to_numeric(result[col], errors="raise")
        if result[col].isna().any() or not result[col].between(0, 100).all():
            raise ValueError(f"Invalid 0..100 coordinates in {col}")
    for col in ("match_id", "team", "player"):
        if result[col].isna().any() or result[col].astype(str).str.strip().eq("").any():
            raise ValueError(f"Missing required values in {col}")
    # Avoid truthiness pitfalls: 'False' is truthy in Python.
    if result["is_successful"].dtype == bool:
        pass
    elif result["is_successful"].dropna().map(lambda v: isinstance(v, str) and v.strip().lower() in ("true", "false")).all():
        result["is_successful"] = result["is_successful"].str.strip().str.lower().map({"true": True, "false": False})
    else:
        raise ValueError("is_successful must be boolean or literal 'true'/'false'")
    if result["is_successful"].isna().any():
        raise ValueError("Missing is_successful outcomes")
    return result
