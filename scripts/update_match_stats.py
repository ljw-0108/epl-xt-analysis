"""Fetch extra available *match-level* stats without changing verified scores.

Run on a computer with internet: python scripts/update_match_stats.py
Unfilled stats stay blank (never invented or set to zero).
"""
from pathlib import Path
from urllib.request import Request, urlopen
from io import BytesIO
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from epl_xt.match_results import load_match_results

URL = 'https://raw.githubusercontent.com/oladeeayo/open-matchday/master/data/ENG_1_premier-league/results_2627.csv'
RAW = ROOT / 'data/raw/epl_2627_rounds_1_10_results.csv'
DEST = ROOT / 'data/processed/epl_2627_rounds_1_10_with_available_stats.csv'
KEYS = ['gw', 'date', 'home', 'away']
STAT_COLS = [
    'home_shots', 'away_shots', 'home_target', 'away_target',
    'home_fouls', 'away_fouls', 'home_corners', 'away_corners',
    'home_yellow', 'away_yellow', 'home_red', 'away_red',
]


def combine_results(baseline: pd.DataFrame, fetched: pd.DataFrame) -> pd.DataFrame:
    """Keep trusted 100-result base; join ONLY when scores match; missing stats stay NA."""
    required = KEYS + ['ft_home', 'ft_away']
    missing = set(required) - set(fetched)
    if missing:
        raise ValueError(f'Upstream dataset missing key fields: {sorted(missing)}')
    fetched = fetched.copy()
    fetched['gw'] = pd.to_numeric(fetched['gw'], errors='raise').astype(int)
    fetched['date'] = pd.to_datetime(fetched['date'], errors='raise')
    fetched = fetched.loc[fetched.gw.between(1, 10)]
    if fetched.duplicated(KEYS).any():
        raise ValueError('Duplicated match keys from upstream')
    for col in ('ft_home', 'ft_away'):
        fetched[col] = pd.to_numeric(fetched[col], errors='raise').astype(int)
    available = [x for x in STAT_COLS if x in fetched.columns]
    joined = baseline.merge(fetched[KEYS + ['ft_home', 'ft_away'] + available], how='left', on=KEYS, suffixes=('', '_upstream'), validate='one_to_one')
    known = joined['ft_home_upstream'].notna()
    inconsistent = known & ((joined.ft_home != joined.ft_home_upstream) | (joined.ft_away != joined.ft_away_upstream))
    if inconsistent.any():
        examples = joined.loc[inconsistent, KEYS].to_dict('records')
        raise ValueError(f'Upstream score conflict; NO output created: {examples[:5]}')
    joined['stat_source'] = known.map({True: 'open-matchday', False: 'UNAVAILABLE'})
    joined = joined.drop(columns=['ft_home_upstream', 'ft_away_upstream'])
    for col in STAT_COLS:
        if col not in joined.columns:
            joined[col] = pd.NA
    return joined


def main():
    baseline = load_match_results(RAW)
    request = Request(URL, headers={'User-Agent': 'EPLStudentResearch/1.0'})
    with urlopen(request, timeout=25) as response:
        fetched = pd.read_csv(BytesIO(response.read()), low_memory=False)
    combined = combine_results(baseline, fetched)
    DEST.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(DEST, index=False, date_format='%Y-%m-%d')
    print(f'완료: {DEST} / 전체 {len(combined)}경기 / 통계 매칭 {sum(combined.stat_source != "UNAVAILABLE")}경기')
    print('주의: 통계가 없는 경기는 NA로 남겨둡니다. 패스 이벤트/좌표는 포함되지 않습니다.')


if __name__ == '__main__':
    main()
