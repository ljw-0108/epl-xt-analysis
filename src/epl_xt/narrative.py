"""Plain-language summaries built only from already-computed numbers (no model, no new claims).

Every sentence is a fixed template filled with values from passing_summary,
direction_distribution, team_xt_summary, xt_by_zone or player_table, so the text can never
state anything the numbers on screen do not show. English names are followed by neutral
phrasing ("쪽이", "의 기록") to avoid wrong Korean particles.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DIRECTION_PLAIN = {"forward": "앞(상대 골문 쪽)", "lateral": "옆", "backward": "뒤(우리 골문 쪽)"}


def pass_story(team: str, summary: dict) -> str:
    if not summary["attempted"]:
        return "선택한 범위에 패스 기록이 없습니다."
    return (f"{team}의 기록: 선택한 {summary['matches']}경기에서 패스를 {summary['attempted']:,}번 시도해 "
            f"{summary['successful']:,}번 성공했습니다(성공률 {summary['completion_rate']:.0%}). "
            f"그중 상대 골문에 크게 다가간 ‘전진 패스’는 {summary['progressive']:,}번입니다.")


def direction_story(dist: pd.DataFrame) -> str:
    """Which way most passes went, and which direction was hardest to complete."""
    d = dist.loc[dist["direction"].isin(DIRECTION_PLAIN.keys()) & (dist["attempted"] > 0)]
    if d.empty:
        return ""
    most = d.loc[d["attempted"].idxmax()]
    hardest = d.loc[d["completion_rate"].idxmin()]
    text = (f"패스의 {most['share_of_attempted']:.0%}는 {DIRECTION_PLAIN[most['direction']]}으로 향했습니다. ")
    if len(d) > 1:
        text += (f"{DIRECTION_PLAIN[hardest['direction']]}으로 보낸 패스의 성공률이 "
                 f"{hardest['completion_rate']:.0%}로 가장 낮았습니다.")
    return text


def zone_phrase(row: int, col: int) -> str:
    third = "우리 진영" if col < 4 else ("중앙" if col < 8 else "상대 진영")
    lane = "측면" if row in (0, 1, 6, 7) else "중앙 통로"
    return f"{third}의 {lane}"


def xt_story(team: str, row, start_matrix: np.ndarray) -> str:
    """row = one team_xt_summary row (or None); start_matrix = signed xT by start zone."""
    if row is None:
        return "성공한 패스가 없어 위협 점수를 계산할 수 없습니다."
    text = (f"{team}의 패스가 만든 위협 점수(xT)는 총 {row.pass_xt_total:.2f}점입니다. "
            f"위협을 높인 패스가 +{row.positive_xt:.2f}점, 공을 뒤로 돌려 위협을 낮춘 패스가 "
            f"{row.negative_xt:.2f}점이었습니다.")
    m = np.asarray(start_matrix, dtype=float)
    if m.max() > 0:
        r, c = np.unravel_index(m.argmax(), m.shape)
        text += f" 위협을 가장 많이 만든 출발 구역은 {zone_phrase(r, c)}({m[r, c]:.2f}점)입니다."
    return text


def compare_story(found: pd.DataFrame, a: str, b: str) -> str:
    """Two-player comparison in words, using the same table rows shown on screen."""
    pa, pb = found.loc[a], found.loc[b]

    def more(metric: str, unit: str, fmt: str) -> str:
        va, vb = pa[metric], pb[metric]
        if va == vb:
            return f"두 선수가 같습니다({fmt.format(va)}{unit})"
        lead, diff = (a, va - vb) if va > vb else (b, vb - va)
        return f"{lead} 쪽이 {fmt.format(diff)}{unit} 더 많습니다"

    return (f"패스 시도는 {more('attempted', '번', '{:,.0f}')}. "
            f"전진 패스는 {more('progressive', '번', '{:,.0f}')}. "
            f"위협 점수(xT)는 {more('pass_xt', '점', '{:.3f}')}.")
