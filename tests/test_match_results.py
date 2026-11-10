from pathlib import Path
import importlib.util
import pandas as pd
import pytest

from epl_xt.match_results import load_match_results, standings, validate_match_results

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/epl_2627_rounds_1_10_results.csv'


def test_real_2026_27_round_1_to_10_results_have_full_coverage():
    r = load_match_results(RAW)
    assert len(r) == 100
    assert set(r.gw) == set(range(1, 11))
    assert len(set(r.home) | set(r.away)) == 20
    assert len(standings(r)) == 20
    assert standings(r).P.eq(10).all()


def test_round_10_crosschecked_key_result():
    r = load_match_results(RAW)
    match = r.loc[(r.gw == 10) & (r.home == 'Man Utd') & (r.away == 'Aston Villa')].iloc[0]
    assert (match.ft_home, match.ft_away) == (4, 4)


def test_duplicate_team_in_round_rejected():
    r = load_match_results(RAW)
    r.loc[(r.gw == 1) & (r.home == 'Hull'), 'home'] = 'Arsenal'
    with pytest.raises(ValueError, match='duplicated'):
        validate_match_results(r)


def test_stat_enrichment_preserves_known_results_and_missing_as_na():
    spec = importlib.util.spec_from_file_location('update_stats', ROOT / 'scripts/update_match_stats.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    base = load_match_results(RAW)
    upstream = pd.DataFrame([{
        'gw': 1, 'date': '2026-08-21', 'home': 'Arsenal', 'away': 'Coventry',
        'ft_home': 3, 'ft_away': 0, 'home_shots': 20,
    }])
    combined = module.combine_results(base, upstream)
    assert len(combined) == 100
    assert combined.loc[0, 'home_shots'] == 20
    assert pd.isna(combined.loc[1, 'home_shots'])
    assert combined.stat_source.eq('UNAVAILABLE').sum() == 99


def test_stat_enrichment_refuses_score_conflicts():
    spec = importlib.util.spec_from_file_location('update_stats', ROOT / 'scripts/update_match_stats.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    base = load_match_results(RAW)
    conflicting = pd.DataFrame([{
        'gw': 1, 'date': '2026-08-21', 'home': 'Arsenal', 'away': 'Coventry',
        'ft_home': 9, 'ft_away': 0,
    }])
    with pytest.raises(ValueError, match='score conflict'):
        module.combine_results(base, conflicting)
