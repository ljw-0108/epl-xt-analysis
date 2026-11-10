"""EPL 2025/26 event-based pass-map and xT; no invented pass connections."""
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from epl_xt.provenance_2526 import read_verified_import
from epl_xt.xt import add_pass_xt, player_xt_ranking

st.set_page_config(page_title="EPL 25/26 패스 + xT", layout="wide")
st.title("EPL 2025/26 패스 및 xT 전술 분석")
st.caption("실제 OpenPlay 경기 이벤트 기반 · 데이터 저작자: openplay (Noah Bair), CC BY 4.0")
st.info("수신 선수 데이터가 없어 선수 간 패스 연결은 확정할 수 없습니다. 아래는 실제 패스 위치 및 선수별 패스 xT 분석입니다.")

passes_path = ROOT / "data/processed/passes.csv"
grid_path = ROOT / "data/processed/xt_grid.csv"
manifest_path = ROOT / "config/source_manifest.json"
try:
    manifest = read_verified_import(manifest_path, passes_path, grid_path)
    passes = pd.read_csv(passes_path, dtype={"match_id": str})
    grid = np.loadtxt(grid_path, delimiter=",")
    with_xt = add_pass_xt(passes, grid)
    found_ids = set(with_xt["match_id"].astype(str).unique())
    if found_ids != set(manifest["match_ids"]):
        raise ValueError("실제 패스 데이터 경기 ID와 출처 기록이 일치하지 않습니다")
except (OSError, ValueError, KeyError) as exc:
    st.warning(f"데이터 준비 전: {exc}")
    st.code("python scripts/download_openplay_2526.py", language="powershell")
    st.stop()

teams = sorted(with_xt["team"].dropna().unique())
team = st.selectbox("팀 선택", teams)
team_data = with_xt.loc[with_xt["team"] == team]
match_options = sorted(team_data["match_id"].astype(str).unique().tolist())
selected = st.multiselect("경기 선택", match_options, default=match_options)
filtered = team_data.loc[team_data["match_id"].astype(str).isin(selected)]
if filtered.empty:
    st.info("선택된 경기의 패스 데이터가 없습니다")
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric("선택한 경기", filtered.match_id.nunique())
c2.metric("성공 패스", int(filtered.is_successful.sum()))
c3.metric("패스 xT 합계 (부호 유지)", f"{filtered.pass_xt.sum():.3f}")
st.caption("xT = 성공 패스의 xT(도착) - xT(시작). 사용 그리드: Karun Singh 공개 12×8 (2017/18 EPL 기반). 25/26에 재학습한 그리드가 아님.")

st.subheader("패스 위치 지도 (실제 패스 이벤트)")
min_success = st.checkbox("성공 패스만", value=True)
shown = filtered.loc[filtered.is_successful] if min_success else filtered
# Deterministic sample for performance; do not misrepresent sampled points as all passes.
max_draw = 250
sample = shown.iloc[np.linspace(0, len(shown)-1, min(max_draw, len(shown)), dtype=int)] if len(shown) else shown
fig, ax = plt.subplots(figsize=(11, 6))
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.set_aspect("equal", adjustable="box")
ax.add_patch(plt.Rectangle((0, 0), 100, 100, fill=False, linewidth=2))
ax.axvline(50, linewidth=0.8, color="gray")
for _, p in sample.iterrows():
    ax.plot([p.x, p.end_x], [p.y, p.end_y], linewidth=0.65, alpha=0.2, color="tab:blue" if p.is_successful else "tab:red")
ax.set_xlabel("x (opponent goal = 100)")
ax.set_ylabel("y (OpenPlay pitch coordinates)")
ax.set_title(f"{team}: {len(sample):,} of {len(shown):,} selected passes plotted")
st.pyplot(fig)
plt.close(fig)

st.subheader("핵심 선수 탐색: 패스 기반 xT 합계")
ranking = player_xt_ranking(filtered)
st.dataframe(ranking, hide_index=True, use_container_width=True)
st.subheader("선수 비교")
players = sorted(filtered.player.dropna().unique().tolist())
if len(players) >= 2:
    chosen = st.multiselect("비교할 선수 (2명)", players, default=players[:2], max_selections=2)
    if len(chosen) == 2:
        st.dataframe(ranking.loc[ranking.player.isin(chosen)], hide_index=True, use_container_width=True)
else:
    st.caption("동일한 경기 필터에서 두 명 이상 선택할 수 없습니다")
st.warning("정확한 선수→선수 패스 네트워크는 원본에 수신자 필드가 없어 현재 비활성화했습니다. 좌표와 다음 이벤트로 추정하는 네트워크를 개발한다면 반드시 ‘추정’으로 표시하고 검증해야 합니다.")
st.caption("출처: https://github.com/nlbair/openplay | 그리드: https://karun.in/blog/data/open_xt_12x8_v1.json | 실제 제공된 데이터의 경기만 사용")
