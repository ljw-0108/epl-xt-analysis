"""EPL Tactical Lab — 2025/26 OpenPlay passes, xT and player comparison.

Only checksum-verified real events are shown; no invented receivers, minutes or values.
EPL_DATA_ROOT (optional) points at another project root holding config/ and data/ (tests).
"""
from pathlib import Path
import os
import sys

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from epl_xt.app_data import load_dataset, match_options  # noqa: E402
from epl_xt.charts import pass_map_figure, zone_heatmap_figure  # noqa: E402
from epl_xt.passing import direction_distribution, passing_summary  # noqa: E402
from epl_xt.players import RANKABLE, compare_players, player_table, rank_players  # noqa: E402
from epl_xt.xt import team_xt_summary, xt_by_zone  # noqa: E402

DATA_ROOT = Path(os.environ.get("EPL_DATA_ROOT", ROOT))
DIRECTION_KO = {"forward": "전진", "lateral": "횡", "backward": "후진", "zero_length": "길이 0"}
METRIC_KO = {"attempted": "패스 시도", "successful": "성공 패스", "completion_rate": "성공률",
             "progressive": "전진 패스", "pass_xt": "패스 xT 합계", "positive_xt": "+xT 합계",
             "xt_per_successful_pass": "성공 패스당 xT", "matches": "패스 기록 경기 수"}

st.set_page_config(page_title="EPL Tactical Lab 25/26", layout="wide")
st.title("EPL Tactical Lab · 2025/26 패스 · xT · 선수 비교")
st.caption("실제 OpenPlay 경기 이벤트 기반 · Event data: openplay (Noah Bair), CC BY 4.0 · "
           "xT grid: Karun Singh (open_xt_12x8_v1)")


@st.cache_data(show_spinner="검증된 25/26 데이터를 불러오는 중…")
def _load(root: str):
    return load_dataset(root)


try:
    manifest, scored, matches, grid = _load(str(DATA_ROOT))
except (OSError, ValueError, KeyError) as exc:
    st.warning(f"데이터 준비 전: {exc}")
    st.code("python scripts/download_openplay_2526.py", language="powershell")
    st.stop()

# ---- Filters (shared by every tab) ----
with st.sidebar:
    st.header("필터")
    team = st.selectbox("팀", sorted(scored["team"].unique()))
    options = match_options(matches, team)
    scope = st.radio("경기 범위", ["시즌 전체", "경기 선택"], horizontal=True)
    if scope == "시즌 전체":
        selected_ids = [m for m, _ in options]
    else:
        labels = {label: m for m, label in options}
        picked = st.multiselect("경기 (상대팀 · match_id)", list(labels), default=list(labels)[:1], key=f"matches_{team}")
        selected_ids = [labels[x] for x in picked]
    st.caption(f"선택: {len(selected_ids)} / {len(options)} 경기. 원본에 경기 날짜·홈/원정 정보가 없어 상대팀과 ID만 표시합니다.")

if not selected_ids:
    st.info("선택된 경기가 없습니다. 사이드바에서 경기를 한 개 이상 고르세요.")
    st.stop()

in_matches = scored.loc[scored["match_id"].isin(selected_ids)]
filtered = in_matches.loc[in_matches["team"] == team]
if filtered.empty:
    st.info("선택한 경기에 이 팀의 패스 데이터가 없습니다.")
    st.stop()

tab_pass, tab_xt, tab_players = st.tabs(["① 패스 분석", "② xT 분석", "③ 선수 비교"])

# ---- 1. Passing ----
with tab_pass:
    s = passing_summary(filtered)
    c = st.columns(5)
    c[0].metric("경기", s["matches"])
    c[1].metric("패스 시도", f"{s['attempted']:,}")
    c[2].metric("성공 패스", f"{s['successful']:,}")
    c[3].metric("성공률", f"{s['completion_rate']:.1%}")
    c[4].metric("전진 패스", f"{s['progressive']:,}")
    st.caption("전진 패스 = 성공 패스 중 상대 골문 중앙까지 거리가 25% 이상 줄어든 패스 (105×68m 환산). "
               "세트피스(코너·프리킥·스로인) 패스 포함.")

    show = st.radio("지도에 표시할 패스", ["전체", "성공", "실패", "전진 패스"], horizontal=True)
    shown = {"전체": filtered, "성공": filtered.loc[filtered["is_successful"]],
             "실패": filtered.loc[~filtered["is_successful"]],
             "전진 패스": filtered.loc[filtered["is_progressive"]]}[show]
    if shown.empty:
        st.info("이 조건에 해당하는 패스가 없습니다.")
    else:
        fig = pass_map_figure(shown, f"{team}: all {len(shown):,} passes plotted ({len(selected_ids)} match(es))")
        st.pyplot(fig)
        plt.close(fig)
        if len(shown) > 2000:
            st.caption("패스가 많아 선이 겹칩니다. 경기 선택이나 성공/실패/전진 필터, 또는 xT 탭의 위치별 히트맵을 함께 보세요.")

    st.subheader("패스 방향 분포")
    dist = direction_distribution(filtered)
    dist["방향"] = dist["direction"].map(DIRECTION_KO)
    left, right = st.columns([3, 2])
    left.bar_chart(dist.set_index("방향")[["attempted"]].rename(columns={"attempted": "패스 시도"}),
                   color="#2a78d6", horizontal=True, sort=False)
    right.dataframe(dist[["방향", "attempted", "successful", "share_of_attempted", "completion_rate"]]
                    .rename(columns={"attempted": "시도", "successful": "성공", "share_of_attempted": "비중",
                                     "completion_rate": "성공률"}),
                    hide_index=True, width="stretch",
                    column_config={"비중": st.column_config.NumberColumn(format="percent"),
                                   "성공률": st.column_config.NumberColumn(format="percent")})
    st.caption("각도(105×68m 기준, 0° = 공격 방향): |각도| < 45° 전진, > 135° 후진, 그 사이 횡.")

# ---- 2. xT ----
with tab_xt:
    tx = team_xt_summary(filtered)
    row = tx.iloc[0] if not tx.empty else None
    c = st.columns(4)
    c[0].metric("패스 xT 합계 (부호 유지)", f"{row.pass_xt_total:.3f}" if row is not None else "—")
    c[1].metric("+xT 합계", f"{row.positive_xt:.3f}" if row is not None else "—")
    c[2].metric("−xT 합계", f"{row.negative_xt:.3f}" if row is not None else "—")
    c[3].metric("성공 패스당 xT", f"{row.xt_per_successful_pass:.4f}" if row is not None else "—")
    st.caption("xT = 성공 패스의 xT(도착 칸) − xT(출발 칸), 실패 패스는 0. 그리드: Karun Singh 공개 12×8 "
               "(과거 EPL 시즌으로 만든 모델, 2025/26으로 재학습하지 않음). 득점·승리 확률 예측이 아닙니다.")

    view = st.radio("히트맵", ["출발 위치별 xT 합계", "도착 위치별 xT 합계", "출발 위치별 성공 패스 수", "사용한 xT 그리드"],
                    horizontal=True)
    if view == "사용한 xT 그리드":
        fig = zone_heatmap_figure(grid, "Karun Singh open xT grid (12 x 8): value of possession per zone", signed=False, fmt="{:.3f}")
        matrix = grid
    elif view == "출발 위치별 성공 패스 수":
        matrix = xt_by_zone(filtered, "start", "count")
        fig = zone_heatmap_figure(matrix, f"{team}: successful passes by start zone", signed=False, fmt="{:.0f}")
    else:
        loc = "start" if view.startswith("출발") else "end"
        matrix = xt_by_zone(filtered, loc, "sum")
        fig = zone_heatmap_figure(matrix, f"{team}: signed pass xT by {loc} zone (blue +, red −)", signed=True)
    st.pyplot(fig)
    plt.close(fig)
    with st.expander("히트맵 수치 표 (행 = y 구간 0→100, 열 = x 구간 0→100)"):
        st.dataframe(pd.DataFrame(matrix, index=[f"y{r}" for r in range(8)], columns=[f"x{c_}" for c_ in range(12)]).round(4),
                     width="stretch")

    st.subheader("같은 경기 안의 팀별 xT (상대팀 포함)")
    st.dataframe(team_xt_summary(in_matches).round(4).rename(columns={
        "team": "팀", "matches": "경기", "successful_passes": "성공 패스", "pass_xt_total": "xT 합계",
        "positive_xt": "+xT", "negative_xt": "−xT", "xt_per_successful_pass": "성공 패스당 xT"}),
        hide_index=True, width="stretch")
    st.caption("선택한 경기들에 실제로 등장한 팀만 집계합니다. 상대팀 행은 그 팀이 이 경기들에서 기록한 값입니다.")

# ---- 3. Players ----
with tab_players:
    table = player_table(filtered)
    st.caption("같은 팀·경기 필터 기준입니다. 출전 시간 데이터가 없어 90분당 지표는 제공하지 않으며, "
               "‘경기 수’는 패스를 1회 이상 시도한 경기 수입니다.")
    st.subheader("선수 순위")
    c = st.columns(2)
    metric = c[0].selectbox("순위 기준", list(RANKABLE), index=list(RANKABLE).index("pass_xt"), format_func=METRIC_KO.get)
    min_att = c[1].number_input("최소 패스 시도", min_value=0, value=0, step=10)
    ranking = rank_players(table, metric, min_attempted=int(min_att))
    if ranking.empty:
        st.info("조건에 맞는 선수가 없습니다.")
    else:
        st.dataframe(ranking.rename(columns={"rank": "순위", "team": "팀", "player": "선수", **METRIC_KO}).round(4),
                     hide_index=True, width="stretch")

    st.subheader("두 선수 비교")
    players = table.sort_values("attempted", ascending=False)["player"].tolist()
    if len(players) < 2:
        st.info("이 필터에서는 패스 기록이 있는 선수가 2명 미만이라 비교할 수 없습니다.")
    else:
        c = st.columns(2)
        a = c[0].selectbox("선수 A", players, index=0, key=f"pa_{team}")
        b = c[1].selectbox("선수 B", players, index=1, key=f"pb_{team}")
        if a == b:
            st.warning("서로 다른 두 선수를 선택하세요.")
        else:
            result = compare_players(table, [(team, a), (team, b)])
            for t_, p_ in result["missing"]:
                st.warning(f"{p_} ({t_}): 선택한 경기 범위에 패스 기록이 없습니다.")
            found = result["found"].set_index("player")
            if len(found) == 2:
                metrics = ["matches", "attempted", "successful", "completion_rate", "progressive",
                           "pass_xt", "positive_xt", "xt_per_successful_pass"]
                comp = found[metrics].T
                comp.index = [METRIC_KO[m] for m in metrics]
                comp["차이 (A − B)"] = comp[a] - comp[b]
                st.dataframe(comp.round(4), width="stretch")
                bars = found[["attempted", "successful", "progressive"]].rename(columns=METRIC_KO).T
                st.bar_chart(bars, stack=False, color=["#2a78d6", "#eb6834"], horizontal=True, sort=False)
                st.caption("막대: 같은 단위(패스 건수)인 지표만 함께 표시. xT·성공률은 단위가 달라 표로 비교합니다.")

st.divider()
st.warning("원본에 패스 수신자 필드가 없어 선수→선수 패스 네트워크는 표시하지 않습니다 (추정 연결 없음).")
st.caption(f"출처: {manifest.get('source_reference', '')} · 이벤트 SHA-256 {str(manifest.get('event_asset_sha256', ''))[:12]}… · "
           f"검증 방식: {manifest.get('verification_method', '')} · 26/27 결과는 별도 보관 페이지에만 있으며 이 분석과 합치지 않습니다.")
