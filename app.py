"""EPL Tactical Lab — 2025/26 OpenPlay passes, xT and player comparison.

Only checksum-verified real events are shown; no invented receivers, minutes or values.
EPL_DATA_ROOT (optional) points at another project root holding config/ and data/ (tests).
EPL_AUTO_PREPARE=1 runs the verified download pipeline automatically when data is missing (deployment).
"""
from pathlib import Path
import os
import sys
import threading

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from epl_xt.app_data import load_dataset, match_options, open_play_available  # noqa: E402
from epl_xt.charts import compare_bar_figure, direction_bar_figure, pass_map_figure, zone_heatmap_figure  # noqa: E402
from epl_xt.narrative import compare_story, direction_story, pass_story, xt_story  # noqa: E402
from epl_xt.passing import direction_distribution, passing_summary  # noqa: E402
from epl_xt.pipeline import build_verified_dataset  # noqa: E402
from epl_xt.players import RANKABLE, compare_players, player_table, rank_players  # noqa: E402
from epl_xt.xt import team_xt_summary, xt_by_zone  # noqa: E402

DATA_ROOT = Path(os.environ.get("EPL_DATA_ROOT", ROOT))
DIRECTION_KO = {"forward": "전진 (앞으로)", "lateral": "횡 (옆으로)", "backward": "후진 (뒤로)", "zero_length": "길이 0"}
METRIC_KO = {"attempted": "패스 시도", "successful": "성공 패스", "completion_rate": "성공률",
             "progressive": "전진 패스", "pass_xt": "위협 점수 합계 (xT)", "positive_xt": "+위협 점수",
             "xt_per_successful_pass": "성공 패스당 위협 점수", "matches": "패스 기록 경기 수"}
HELP = {
    "matches": "선택한 범위에 들어간 경기 수입니다.",
    "attempted": "패스를 보낸 횟수입니다. 받은 선수가 공을 잡았는지와 상관없이 셉니다.",
    "successful": "같은 팀 선수에게 제대로 연결된 패스 수입니다.",
    "completion_rate": "성공 패스 ÷ 패스 시도. 높을수록 공을 잘 지켰다는 뜻입니다.",
    "progressive": "성공한 패스 중 상대 골문까지 거리가 25% 이상 줄어든 패스, 즉 공격을 크게 전진시킨 패스입니다.",
    "xt": "xT(Expected Threat, 기대 위협)는 공이 있는 위치가 골로 이어질 가능성을 점수로 나타낸 것입니다. "
          "패스로 공을 더 위험한 곳으로 옮기면 +, 뒤로 돌리면 − 점수가 됩니다. 실패한 패스는 0점입니다.",
    "positive_xt": "위협을 높인 패스들의 점수만 더한 값입니다.",
    "negative_xt": "공을 뒤나 덜 위험한 곳으로 옮겨 위협이 줄어든 패스들의 점수입니다. 안전하게 공을 돌리는 것이라 나쁜 것만은 아닙니다.",
    "xt_per": "성공한 패스 한 번이 평균적으로 만든 위협 점수입니다.",
}


def story(text: str) -> None:
    """A highlighted plain-language summary box (numbers come from the calculations above it)."""
    if text:
        with st.container(border=True):
            st.markdown(f"💡 **한눈에 보기** · {text}")

st.set_page_config(page_title="EPL Tactical Lab 25/26", page_icon="⚽", layout="wide")
st.title("⚽ EPL Tactical Lab")
st.markdown("##### 2025/26 프리미어리그 **실제 경기 기록**으로 팀의 패스와 공격 위협을 쉽게 살펴봅니다")
st.caption("Event data: openplay (Noah Bair), CC BY 4.0 · xT grid: Karun Singh (open_xt_12x8_v1)")


@st.cache_data(show_spinner="검증된 25/26 데이터를 불러오는 중…")
def _load(root: str):
    return load_dataset(root)


@st.cache_resource
def _prepare_lock():
    return threading.Lock()


def _prepare_data() -> bool:
    """Run the same checksum-verified pipeline as the CLI script; one run at a time."""
    with _prepare_lock(), st.status("공식 원본을 내려받아 검증하는 중…", expanded=True) as status:
        try:
            build_verified_dataset(DATA_ROOT, log=status.write)
        except Exception as exc:  # network, checksum or conversion failure: show it, never substitute data
            status.update(label=f"데이터 준비 실패: {exc}", state="error")
            return False
        status.update(label="데이터 준비 완료", state="complete")
    _load.clear()
    return True


def _auto_prepare_enabled() -> bool:
    """EPL_AUTO_PREPARE=1 from the environment or a root-level Streamlit secret."""
    if os.environ.get("EPL_AUTO_PREPARE") == "1":
        return True
    try:
        return str(st.secrets.get("EPL_AUTO_PREPARE", "")) == "1"
    except Exception:  # no secrets file configured
        return False


try:
    manifest, scored, matches, grid = _load(str(DATA_ROOT))
except (OSError, ValueError, KeyError) as exc:
    st.warning(f"데이터 준비 전: {exc}")
    st.caption("공식 OpenPlay 릴리스(약 11.5MB)와 xT 그리드를 내려받아 SHA-256을 확인한 뒤 변환합니다. "
               "체크섬이 다르면 중단하며 대체 데이터를 만들지 않습니다.")
    auto = _auto_prepare_enabled() and not st.session_state.get("auto_prepare_tried")
    if auto:
        st.session_state["auto_prepare_tried"] = True  # never loop on a failing source
    if auto or st.button("원본 내려받기 및 검증"):
        if _prepare_data():
            st.rerun()
    st.code("python scripts/download_openplay_2526.py", language="powershell")
    st.stop()

# ---- Filters (shared by every tab) ----
with st.sidebar:
    st.header("🔎 보고 싶은 것 고르기")
    team = st.selectbox("팀", sorted(scored["team"].unique()), help="2025/26 프리미어리그 20개 팀 중 하나를 고르세요.")
    options = match_options(matches, team)
    scope = st.radio("경기 범위", ["시즌 전체", "경기 선택"], horizontal=True,
                     help="시즌 전체 38경기를 합쳐 보거나, 특정 경기만 골라 볼 수 있습니다.")
    if scope == "시즌 전체":
        selected_ids = [m for m, _ in options]
    else:
        labels = {label: m for m, label in options}
        picked = st.multiselect("경기 (상대팀 · 경기 번호)", list(labels), default=list(labels)[:1], key=f"matches_{team}")
        selected_ids = [labels[x] for x in picked]
    st.caption(f"선택: {len(selected_ids)} / {len(options)} 경기 · 원본에 경기 날짜와 홈/원정 정보가 없어 상대팀과 경기 번호로 표시합니다.")
    can_filter = open_play_available(scored)
    pass_scope = st.radio("패스 범위", ["전체 패스", "오픈플레이만"], horizontal=True, disabled=not can_filter,
                          help="오픈플레이만 = 코너킥·프리킥·스로인·골킥처럼 경기가 멈췄다가 다시 시작하는 패스를 빼고, "
                               "흐르는 플레이 중의 패스만 봅니다.")
    if not can_filter:
        st.caption("현재 데이터에 세트피스 표시가 없어 이 필터를 쓸 수 없습니다. 다운로드 스크립트를 다시 실행하세요.")
    open_play_only = can_filter and pass_scope == "오픈플레이만"
    SCOPE_NOTE = ("오픈플레이 패스만 (코너·프리킥·스로인·골킥 재개 패스 제외, 킥오프는 원본 표시가 없어 포함)"
                  if open_play_only else "세트피스(코너·프리킥·스로인·골킥) 재개 패스 포함")
    st.divider()
    st.caption("필터는 모든 탭에 똑같이 적용됩니다.")

with st.expander("👋 처음이라면: 이 사이트 읽는 법 (1분)", expanded=True):
    g = st.columns(4)
    g[0].markdown("**1. 팀 고르기**  \n왼쪽에서 팀과 경기를 고릅니다. 시즌 전체도 볼 수 있어요.")
    g[1].markdown("**2. 패스 지도**  \n선 하나가 패스 하나입니다. 파랑은 성공, 주황은 실패예요.")
    g[2].markdown("**3. 위협 지도**  \n어느 구역에서 보낸 패스가 골 가능성을 키웠는지 색으로 보여줘요.")
    g[3].markdown("**4. 선수 비교**  \n두 선수를 골라 같은 조건에서 비교합니다.")
    st.caption("모르는 단어는 ‘📖 쉬운 용어 설명’ 탭이나 숫자 옆 ⓘ에 마우스를 올려 확인하세요. "
               "오른쪽은 항상 상대 골문 방향입니다.")

if not selected_ids:
    st.info("선택된 경기가 없습니다. 사이드바에서 경기를 한 개 이상 고르세요.")
    st.stop()

in_scope = scored.loc[scored["is_open_play"].astype(bool)] if open_play_only else scored
in_matches = in_scope.loc[in_scope["match_id"].isin(selected_ids)]
filtered = in_matches.loc[in_matches["team"] == team]
if filtered.empty:
    st.info("선택한 경기에 이 팀의 패스 데이터가 없습니다.")
    st.stop()

tab_pass, tab_xt, tab_players, tab_help = st.tabs(["① 패스 지도", "② 위협 지도 (xT)", "③ 선수 비교", "📖 쉬운 용어 설명"])

# ---- 1. Passing ----
with tab_pass:
    s = passing_summary(filtered)
    story(pass_story(team, s))
    c = st.columns(5)
    c[0].metric("경기", s["matches"], help=HELP["matches"], border=True)
    c[1].metric("패스 시도", f"{s['attempted']:,}", help=HELP["attempted"], border=True)
    c[2].metric("성공 패스", f"{s['successful']:,}", help=HELP["successful"], border=True)
    c[3].metric("성공률", f"{s['completion_rate']:.1%}", help=HELP["completion_rate"], border=True)
    c[4].metric("전진 패스", f"{s['progressive']:,}", help=HELP["progressive"], border=True)

    show = st.radio("지도에 표시할 패스", ["전체", "성공", "실패", "전진 패스"], horizontal=True)
    shown = {"전체": filtered, "성공": filtered.loc[filtered["is_successful"]],
             "실패": filtered.loc[~filtered["is_successful"]],
             "전진 패스": filtered.loc[filtered["is_progressive"]]}[show]
    if shown.empty:
        st.info("이 조건에 해당하는 패스가 없습니다.")
    else:
        st.plotly_chart(pass_map_figure(shown, f"{team} · 패스 {len(shown):,}개 ({len(selected_ids)}경기)"),
                        width="stretch", config={"displayModeBar": False})
        if len(shown) > 2000:
            st.caption("패스가 많아 선이 겹칩니다. 경기 하나를 고르거나 ‘전진 패스’만 보면 더 선명합니다.")

    st.subheader("패스는 주로 어느 방향으로 갔나요?")
    dist = direction_distribution(filtered)
    dist["방향"] = dist["direction"].map(DIRECTION_KO)
    empty_classes = dist.loc[dist["attempted"] == 0, "방향"].tolist()
    dist = dist.loc[dist["attempted"] > 0]  # no rate is shown for a class with no passes
    story(direction_story(dist))
    st.plotly_chart(direction_bar_figure(dist.rename(columns={"방향": "label"})), width="stretch",
                    config={"displayModeBar": False})
    with st.expander("표로 보기 · 방향을 나눈 기준"):
        st.dataframe(dist[["방향", "attempted", "successful", "share_of_attempted", "completion_rate"]]
                     .rename(columns={"attempted": "시도", "successful": "성공", "share_of_attempted": "비중",
                                      "completion_rate": "성공률"}),
                     hide_index=True, width="stretch",
                     column_config={"비중": st.column_config.NumberColumn(format="percent"),
                                    "성공률": st.column_config.NumberColumn(format="percent")})
        st.caption("상대 골문 방향을 0°로 두고, 실제 경기장 비율(105×68m)로 각도를 잽니다. "
                   "45°보다 앞이면 전진, 135°보다 뒤면 후진, 그 사이는 횡(옆)입니다."
                   + (f" 해당 패스 없음: {', '.join(empty_classes)}." if empty_classes else "")
                   + f" 패스 범위: {SCOPE_NOTE}.")

    with st.expander("⬇️ 데이터 내려받기 (CSV)"):
        export_cols = ["match_id", "team", "player", "x", "y", "end_x", "end_y", "is_successful",
                       "is_open_play", "direction", "is_progressive", "length_m", "pass_xt"]
        st.download_button(
            "현재 필터의 패스 CSV 내려받기",
            filtered[export_cols].to_csv(index=False).encode("utf-8-sig"),
            file_name=f"epl2526_{team.replace(' ', '_')}_{len(selected_ids)}matches_{'openplay' if open_play_only else 'all'}_passes.csv",
            mime="text/csv")
        st.caption("원본 이벤트에서 변환한 실제 패스 행과 이 앱의 계산 열입니다. 받은 선수 열은 원본에 없어 포함하지 않습니다. "
                   "Event data: openplay (Noah Bair), CC BY 4.0 — 재배포 시 출처 표기 필요.")

# ---- 2. xT ----
with tab_xt:
    st.markdown("**위협 점수(xT)란?** 공이 상대 골문에 가까운 위험한 곳으로 갈수록 골 가능성이 커집니다. "
                "패스가 공을 더 위험한 곳으로 옮기면 **+점수**, 뒤로 돌리면 **−점수**를 받습니다.")
    tx = team_xt_summary(filtered)
    row = tx.iloc[0] if not tx.empty else None
    start_sum = xt_by_zone(filtered, "start", "sum")
    story(xt_story(team, row, start_sum))
    c = st.columns(4)
    c[0].metric("위협 점수 합계 (xT)", f"{row.pass_xt_total:.3f}" if row is not None else "—", help=HELP["xt"], border=True)
    c[1].metric("+ 위협을 높인 패스", f"{row.positive_xt:.3f}" if row is not None else "—", help=HELP["positive_xt"], border=True)
    c[2].metric("− 위협을 낮춘 패스", f"{row.negative_xt:.3f}" if row is not None else "—", help=HELP["negative_xt"], border=True)
    c[3].metric("성공 패스당 위협 점수", f"{row.xt_per_successful_pass:.4f}" if row is not None else "—", help=HELP["xt_per"], border=True)

    view = st.radio("지도에서 볼 것", ["어디서 보낸 패스가 위협을 만들었나", "어디로 도착한 패스가 위협을 만들었나",
                                     "어디서 패스를 많이 했나", "구역별 기본 위협 값 (xT 그리드)"], horizontal=True)
    if view.startswith("구역별"):
        matrix = grid
        fig = zone_heatmap_figure(grid, "구역별 기본 위협 값: 상대 골문 앞이 가장 높습니다", signed=False, fmt="{:.3f}",
                                  value_name="기본 위협 값")
    elif view.startswith("어디서 패스를"):
        matrix = xt_by_zone(filtered, "start", "count")
        fig = zone_heatmap_figure(matrix, f"{team} · 성공 패스를 보낸 위치 (횟수)", signed=False, fmt="{:.0f}",
                                  value_name="성공 패스 수")
    else:
        loc = "start" if view.startswith("어디서 보낸") else "end"
        matrix = start_sum if loc == "start" else xt_by_zone(filtered, "end", "sum")
        what = "보낸" if loc == "start" else "도착한"
        fig = zone_heatmap_figure(matrix, f"{team} · 패스를 {what} 위치별 위협 점수 (파랑 +, 빨강 −)", signed=True,
                                  value_name="위협 점수")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption("경기장을 가로 12칸 × 세로 8칸으로 나눴습니다. 칸에 마우스를 올리면 구역 이름과 값이 보입니다. "
               "그리드: Karun Singh 공개 모델(과거 EPL 시즌으로 만든 것, 2025/26으로 다시 학습하지 않음). "
               f"득점·승리 확률 예측이 아닙니다. 패스 범위: {SCOPE_NOTE}.")
    with st.expander("히트맵 수치 표 (행 = 세로 구간, 열 = 가로 구간 → 상대 골문)"):
        st.dataframe(pd.DataFrame(matrix, index=[f"y{r}" for r in range(8)], columns=[f"x{c_}" for c_ in range(12)]).round(4),
                     width="stretch")

    st.subheader("같은 경기의 상대팀과 비교")
    st.dataframe(team_xt_summary(in_matches).round(4).rename(columns={
        "team": "팀", "matches": "경기", "successful_passes": "성공 패스", "pass_xt_total": "위협 점수 합계",
        "positive_xt": "+위협", "negative_xt": "−위협", "xt_per_successful_pass": "성공 패스당 위협"}),
        hide_index=True, width="stretch")
    st.caption("선택한 경기에 실제로 나온 팀만 집계합니다. 상대팀 행은 그 팀이 같은 경기들에서 기록한 값입니다.")

# ---- 3. Players ----
with tab_players:
    table = player_table(filtered)
    st.caption("왼쪽 필터(팀·경기·패스 범위)가 그대로 적용됩니다. 출전 시간 데이터가 없어 90분당 지표는 만들지 않았고, "
               "‘패스 기록 경기 수’는 패스를 1번 이상 한 경기 수입니다.")
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
                story(compare_story(found, a, b))
                st.plotly_chart(compare_bar_figure(found, a, b, METRIC_KO), width="stretch",
                                config={"displayModeBar": False})
                st.caption("막대에는 단위가 같은 ‘횟수’ 지표만 넣었습니다. 위협 점수와 성공률은 아래 표에서 비교하세요.")
                metrics = ["matches", "attempted", "successful", "completion_rate", "progressive",
                           "pass_xt", "positive_xt", "xt_per_successful_pass"]
                comp = found[metrics].T
                comp.index = [METRIC_KO[m] for m in metrics]
                comp["차이 (A − B)"] = comp[a] - comp[b]
                st.dataframe(comp.round(4), width="stretch")

    st.subheader("선수 순위")
    c = st.columns(2)
    metric = c[0].selectbox("순위 기준", list(RANKABLE), index=list(RANKABLE).index("pass_xt"), format_func=METRIC_KO.get)
    min_att = c[1].number_input("최소 패스 시도", min_value=0, value=0, step=10,
                                help="패스를 아주 적게 한 선수가 비율 지표에서 1등이 되는 것을 막으려면 숫자를 올리세요.")
    ranking = rank_players(table, metric, min_attempted=int(min_att))
    if ranking.empty:
        st.info("조건에 맞는 선수가 없습니다.")
    else:
        st.dataframe(ranking.rename(columns={"rank": "순위", "team": "팀", "player": "선수", **METRIC_KO}).round(4),
                     hide_index=True, width="stretch")

# ---- 4. Plain-language glossary ----
with tab_help:
    st.subheader("📖 쉬운 용어 설명")
    terms = [
        ("패스", "같은 팀 선수에게 공을 차서(또는 던져서) 보내는 것. 이 사이트의 선 하나가 패스 하나입니다."),
        ("성공 / 실패", "같은 팀 선수에게 연결되면 성공, 상대에게 빼앗기거나 밖으로 나가면 실패입니다."),
        ("전진 패스", "성공한 패스 중 상대 골문까지 거리가 25% 이상 줄어든 패스. 공격을 크게 앞으로 끌고 간 패스입니다."),
        ("전진 · 횡 · 후진", "패스가 향한 방향입니다. 앞(상대 골문 쪽), 옆, 뒤(우리 골문 쪽)."),
        ("위협 점수 (xT)", "Expected Threat. 공이 있는 위치가 골로 이어질 가능성을 점수로 만든 것입니다. "
                         "상대 골문 앞일수록 높고, 패스로 공을 더 위험한 곳에 옮기면 + 점수를 받습니다."),
        ("세트피스", "코너킥·프리킥·스로인·골킥처럼 경기가 멈췄다가 다시 시작하는 장면입니다."),
        ("오픈플레이", "세트피스가 아닌, 공이 계속 굴러가는 일반 플레이입니다."),
        ("측면 / 중앙 통로", "경기장을 세로로 봤을 때 터치라인에 가까운 바깥쪽이 측면, 가운데가 중앙 통로입니다."),
    ]
    for term, desc in terms:
        st.markdown(f"**{term}** — {desc}")
    st.subheader("이 사이트가 하지 않는 것")
    st.markdown(
        "- **누가 누구에게 패스했는지는 보여주지 않습니다.** 원본 데이터에 ‘받은 선수’ 정보가 없어서, 추측해서 선을 잇지 않습니다.\n"
        "- **90분당 기록은 없습니다.** 선수별 출전 시간 정보가 없기 때문입니다.\n"
        "- **승패나 득점을 예측하지 않습니다.** 위협 점수는 공의 위치 가치를 나타낼 뿐입니다.\n"
        "- **위협 점수 기준표는 공개된 기존 모델을 그대로 썼습니다.** 2025/26 시즌으로 새로 만든 것이 아닙니다.")
    st.subheader("데이터 출처")
    st.markdown(f"- 경기 이벤트: openplay (Noah Bair), CC BY 4.0 · {manifest.get('source_reference', '')}\n"
                "- 위협 점수 기준표: Karun Singh, https://karun.in/blog/expected-threat.html\n"
                "- 원본 파일은 공식 체크섬(SHA-256)으로 확인한 뒤에만 사용합니다."
                + (f" {qr['matches_with_passes']}경기 · 패스 {qr['pass_rows']:,}건."
                   if (qr := manifest.get("quality_report")) and {"matches_with_passes", "pass_rows"} <= set(qr) else ""))

st.divider()
st.caption("ⓘ 원본에 ‘받은 선수’ 정보가 없어 선수→선수 패스 네트워크는 표시하지 않습니다 (추정 연결 없음). "
           f"출처: {manifest.get('source_reference', '')} · 이벤트 SHA-256 {str(manifest.get('event_asset_sha256', ''))[:12]}… · "
           f"검증 방식: {manifest.get('verification_method', '')} · 26/27 결과는 별도 보관 페이지에만 있으며 이 분석과 합치지 않습니다.")
