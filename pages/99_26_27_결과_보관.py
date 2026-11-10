"""Real match-result page; deliberately separate from event-level tactical analytics."""
from pathlib import Path
import sys
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from epl_xt.match_results import load_match_results, standings

st.set_page_config(page_title="EPL 26/27 1~10R 실제 경기 결과", layout="wide")
st.title("[별도 참고] EPL 2026/27 · 1~10라운드 경기 결과")
st.caption("자료 기준일: 2026-11-09 · 결과 100경기 · 실제 패스 이벤트 데이터 없음")
st.info("이 페이지는 별도 26/27 시즌 결과 보관용입니다. 메인 분석 시즌 25/26의 패스 이벤트와 절대 합치지 않습니다.")
source = ROOT / "data" / "raw" / "epl_2627_rounds_1_10_results.csv"
try:
    data = load_match_results(source)
except (OSError, ValueError) as exc:
    st.error(f"경기 결과 파일을 확인할 수 없습니다: {exc}")
    st.stop()

round_pick = st.slider("라운드 범위", 1, 10, (1, 10))
subset = data.loc[data.gw.between(*round_pick)].copy()
all_teams = sorted(set(data.home) | set(data.away))
team = st.selectbox("팀", ["전체"] + all_teams)
if team != "전체":
    subset = subset.loc[(subset.home == team) | (subset.away == team)]

c1, c2, c3 = st.columns(3)
c1.metric("경기", len(subset))
c2.metric("참여 팀", len(set(subset.home) | set(subset.away)))
c3.metric("총 득점", int(subset.ft_home.sum() + subset.ft_away.sum()))
subset["date"] = subset["date"].dt.strftime("%Y-%m-%d")
st.subheader("경기별 결과")
st.dataframe(subset[["gw", "date", "home", "ft_home", "ft_away", "away", "source"]], hide_index=True, use_container_width=True)
if round_pick == (1, 10) and team == "전체":
    st.subheader("1~10라운드 성적표 (승점·골득실 기준, 기본 정렬)")
    st.dataframe(standings(data), hide_index=True, use_container_width=True)
st.caption("출처: open-matchday (1~9R), plstats.uk / Ahram Online / footballmatchstats (10R 교차 확인). 10R 일부 세부 슈팅 통계는 확보되지 않아 표시하지 않습니다.")
