"""Real EPL 2026/27 results through round 10 (separate from pass events)."""
from pathlib import Path
import pandas as pd

REQUIRED = ("gw", "date", "home", "away", "ft_home", "ft_away", "source")


def validate_match_results(df: pd.DataFrame, through_round: int = 10) -> pd.DataFrame:
    """Validate 10 games per round, exactly 20 teams, no future fixtures."""
    missing = sorted(set(REQUIRED) - set(df.columns))
    if missing:
        raise ValueError(f"Missing match columns: {missing}")
    result = df.copy()
    for col in ("gw", "ft_home", "ft_away"):
        result[col] = pd.to_numeric(result[col], errors="raise")
        if result[col].isna().any() or (result[col] != result[col].astype(int)).any():
            raise ValueError(f"Invalid integer values in {col}")
        result[col] = result[col].astype(int)
    if not result["gw"].between(1, through_round).all():
        raise ValueError("Round out of specified range")
    if (result[["ft_home", "ft_away"]] < 0).any().any():
        raise ValueError("Negative score")
    for col in ("home", "away", "source"):
        if result[col].isna().any() or result[col].astype(str).str.strip().eq("").any():
            raise ValueError(f"Missing {col}")
    result["date"] = pd.to_datetime(result["date"], errors="raise")
    if len(result) != through_round * 10:
        raise ValueError(f"Expected {through_round * 10} matches; found {len(result)}")
    teams = sorted(set(result["home"]) | set(result["away"]))
    if len(teams) != 20:
        raise ValueError("Expected exactly 20 distinct teams")
    for gw in range(1, through_round + 1):
        week = result.loc[result["gw"] == gw]
        if len(week) != 10:
            raise ValueError(f"Round {gw}: expected 10 matches")
        all_teams = list(week["home"]) + list(week["away"])
        if len(set(all_teams)) != 20:
            raise ValueError(f"Round {gw}: a team is missing or duplicated")
    if result.duplicated(["gw", "home", "away"]).any():
        raise ValueError("Duplicate match")
    return result


def load_match_results(path: str | Path) -> pd.DataFrame:
    return validate_match_results(pd.read_csv(path))


def standings(results: pd.DataFrame) -> pd.DataFrame:
    """Calculate verified standings from match scores; no pass/xT estimates."""
    per_team = {}
    for r in results.itertuples(index=False):
        for team, gf, ga in [(r.home, r.ft_home, r.ft_away), (r.away, r.ft_away, r.ft_home)]:
            s = per_team.setdefault(team, {"team": team, "P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "Pts": 0})
            s["P"] += 1
            s["GF"] += gf
            s["GA"] += ga
            s["GD"] += gf - ga
            if gf > ga:
                s["W"] += 1
                s["Pts"] += 3
            elif gf == ga:
                s["D"] += 1
                s["Pts"] += 1
            else:
                s["L"] += 1
    return pd.DataFrame(per_team.values()).sort_values(["Pts", "GD", "GF", "team"], ascending=[False, False, False, True]).reset_index(drop=True)
