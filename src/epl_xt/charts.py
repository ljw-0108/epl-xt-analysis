"""Interactive Plotly pitch charts (Korean labels render in the browser; hover shows the data).

Colours follow a validated reference palette: categorical slot 1 blue / slot 2 orange,
sequential blue, diverging red–gray–blue around zero. The pitch is a light grass tint so the
data colours keep their contrast.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

SUCCESS = "#2a78d6"   # categorical slot 1
FAIL = "#eb6834"      # categorical slot 2
INK = "#1f2a24"
INK_2 = "#52514e"
GRASS = ("#eef6ee", "#e5f0e5")   # alternating mowing stripes
LINE = "#9fbfa3"
SEQUENTIAL = [[0, "#f0efec"], [0.2, "#cde2fb"], [0.45, "#86b6ef"], [0.7, "#3987e5"], [0.85, "#1c5cab"], [1, "#0d366b"]]
DIVERGING = [[0, "#a83232"], [0.25, "#e34948"], [0.5, "#f0efec"], [0.75, "#2a78d6"], [1, "#104281"]]
ASPECT = 68 / 105  # pitch height / length, so the drawing keeps true proportions
FONT = dict(family="Pretendard, 'Noto Sans KR', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif", color=INK, size=13)


def _pitch_shapes() -> list[dict]:
    shapes = [dict(type="rect", x0=i * 100 / 12, x1=(i + 1) * 100 / 12, y0=0, y1=100, line_width=0,
                   fillcolor=GRASS[i % 2], layer="below") for i in range(12)]
    line = dict(color=LINE, width=1.5)
    shapes += [
        dict(type="rect", x0=0, x1=100, y0=0, y1=100, line=line, layer="below"),
        dict(type="line", x0=50, x1=50, y0=0, y1=100, line=line, layer="below"),
        dict(type="circle", x0=50 - 9.15 / 1.05, x1=50 + 9.15 / 1.05, y0=50 - 9.15 / 0.68, y1=50 + 9.15 / 0.68,
             line=line, layer="below"),
    ]
    for x0, x1 in ((0, 15.7), (100, 84.3)):           # penalty areas (16.5 m x 40.3 m)
        shapes.append(dict(type="rect", x0=x0, x1=x1, y0=20.4, y1=79.6, line=line, layer="below"))
    for x0, x1 in ((0, 5.2), (100, 94.8)):            # six-yard boxes
        shapes.append(dict(type="rect", x0=x0, x1=x1, y0=36.5, y1=63.5, line=line, layer="below"))
    return shapes


def _pitch_layout(fig: go.Figure, title: str, height: int = 640, above: str | None = None) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=16)),
        shapes=_pitch_shapes(), font=FONT, height=height, margin=dict(l=10, r=10, t=60, b=70),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="top", y=-0.08, x=0, bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    fig.update_xaxes(range=[-1, 101], showgrid=False, zeroline=False, showticklabels=False, ticks="", showline=False,
                     fixedrange=True)
    fig.update_yaxes(range=[-1, 101], showgrid=False, zeroline=False, showticklabels=False, ticks="", showline=False,
                     fixedrange=True,
                     scaleanchor="x", scaleratio=ASPECT)
    notes = [
        dict(x=0, y=-0.02, xref="x", yref="paper", text="◀ 우리 골문", showarrow=False, xanchor="left", yanchor="top",
             font=dict(color=INK_2, size=12)),
        dict(x=100, y=-0.02, xref="x", yref="paper", text="상대 골문 ▶", showarrow=False, xanchor="right", yanchor="top",
             font=dict(color=INK_2, size=12)),
        dict(x=50, y=-0.02, xref="x", yref="paper", text="공격 방향 →", showarrow=False, yanchor="top",
             font=dict(color=INK_2, size=12)),
    ]
    if above:
        notes.append(dict(x=0, y=1.0, xref="paper", yref="paper", text=above, showarrow=False, xanchor="left",
                          yanchor="bottom", font=dict(color=INK_2, size=12)))
    fig.update_layout(annotations=notes)
    return fig


def _segments(part: pd.DataFrame) -> tuple[list, list]:
    """x/y arrays drawing one line per pass, separated by None (a single fast trace)."""
    xs = np.column_stack([part["x"], part["end_x"], np.full(len(part), np.nan)]).ravel()
    ys = np.column_stack([part["y"], part["end_y"], np.full(len(part), np.nan)]).ravel()
    return [None if np.isnan(v) else float(v) for v in xs], [None if np.isnan(v) else float(v) for v in ys]


def pass_map_figure(passes: pd.DataFrame, title: str) -> go.Figure:
    """Every pass is drawn (no sampling): a line from start to end and a dot where it arrived.

    Hovering a dot shows the player, result, length and xT change of that pass.
    """
    fig = go.Figure()
    n = len(passes)
    opacity = float(np.clip(12 / max(n, 1) ** 0.5, 0.05, 0.85))
    width = 1.4 if n <= 2000 else 0.6
    for ok, colour, label in ((True, SUCCESS, "성공한 패스"), (False, FAIL, "실패한 패스")):
        part = passes.loc[passes["is_successful"] == ok]
        if part.empty:
            continue
        xs, ys = _segments(part)
        fig.add_trace(go.Scattergl(x=xs, y=ys, mode="lines", line=dict(color=colour, width=width), opacity=opacity,
                                   hoverinfo="skip", name=f"{label} ({len(part):,})", legendgroup=label))
        xt = part["pass_xt"] if "pass_xt" in part else pd.Series(0.0, index=part.index)
        length = part["length_m"] if "length_m" in part else pd.Series(np.nan, index=part.index)
        fig.add_trace(go.Scattergl(
            x=part["end_x"], y=part["end_y"], mode="markers", legendgroup=label, showlegend=False,
            marker=dict(color=colour, size=5 if n <= 2000 else 3, opacity=min(1.0, opacity * 1.6)),
            customdata=np.column_stack([part["player"].astype(str), length.round(1), xt.round(3)]),
            hovertemplate=f"<b>%{{customdata[0]}}</b><br>{label}<br>길이 %{{customdata[1]}} m<br>"
                          "위협 변화(xT) %{customdata[2]}<extra></extra>",
            name=label))
    return _pitch_layout(fig, title, above="점에 마우스를 올리면 누가 보낸 패스인지 보입니다")


def zone_labels(matrix: np.ndarray, fmt: str) -> np.ndarray:
    """Cell labels; cells that round to zero are left blank (no '0.00' clutter, never '-0.00').

    Exact values stay available in the hover and in the table under the chart.
    """
    out = np.empty(matrix.shape, dtype=object)
    for idx, v in np.ndenumerate(matrix):
        if v == 0:
            out[idx] = ""
            continue
        label = fmt.format(v)
        out[idx] = "" if float(label) == 0 else label
    return out


def zone_heatmap_figure(matrix, title: str, signed: bool, fmt: str = "{:.2f}", value_name: str = "값") -> go.Figure:
    """8x12 zone matrix (rows = y bands, cols = x bands toward the attacked goal) drawn on the pitch."""
    m = np.asarray(matrix, dtype=float)
    if m.shape != (8, 12):
        raise ValueError("Expected an 8 x 12 matrix")
    xc = (np.arange(12) + 0.5) * 100 / 12
    yc = (np.arange(8) + 0.5) * 100 / 8
    if signed:
        bound = float(np.abs(m).max()) or 1.0
        colour = dict(colorscale=DIVERGING, zmid=0.0, zmin=-bound, zmax=bound)
    else:
        colour = dict(colorscale=SEQUENTIAL, zmin=0.0, zmax=float(m.max()) or 1.0)
    third = np.array(["우리 진영"] * 4 + ["중앙"] * 4 + ["상대 진영"] * 4)
    lane = np.array(["측면"] * 2 + ["중앙 통로"] * 4 + ["측면"] * 2)
    where = np.array([[f"{third[c]} · {lane[r]}" for c in range(12)] for r in range(8)])
    fig = go.Figure(go.Heatmap(
        x=xc, y=yc, z=m, text=zone_labels(m, fmt), texttemplate="%{text}", textfont=dict(size=11),
        customdata=where, xgap=2, ygap=2, opacity=0.92,
        hovertemplate=f"%{{customdata}}<br>{value_name}: %{{z:.3f}}<extra></extra>",
        colorbar=dict(thickness=12, outlinewidth=0, len=0.8), **colour))
    return _pitch_layout(fig, title, height=560)


def direction_bar_figure(dist: pd.DataFrame) -> go.Figure:
    """Horizontal bars of attempted passes per direction (rows already in display order)."""
    fig = go.Figure(go.Bar(
        x=dist["attempted"], y=dist["label"], orientation="h", marker=dict(color=SUCCESS, cornerradius=4),
        text=[f"{a:,}번 · 성공률 {r:.0%}" for a, r in zip(dist["attempted"], dist["completion_rate"])],
        textposition="auto", hovertemplate="%{y}: %{x:,}번<extra></extra>"))
    fig.update_layout(font=FONT, height=230, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", bargap=0.35)
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(showgrid=True, gridcolor="#e6e4df", zeroline=False, title=None)
    return fig


def compare_bar_figure(found: pd.DataFrame, a: str, b: str, labels: dict[str, str]) -> go.Figure:
    """Grouped bars for count metrics only (same unit); xT and rates stay in the table."""
    metrics = ["attempted", "successful", "progressive"]
    fig = go.Figure()
    for name, colour in ((a, SUCCESS), (b, FAIL)):
        vals = [int(found.loc[name, m]) for m in metrics]
        fig.add_trace(go.Bar(name=name, y=[labels[m] for m in metrics], x=vals, orientation="h",
                             marker=dict(color=colour, cornerradius=4), text=[f"{v:,}" for v in vals],
                             textposition="outside", hovertemplate=f"{name}<br>%{{y}}: %{{x:,}}<extra></extra>"))
    fig.update_layout(barmode="group", font=FONT, height=260, margin=dict(l=10, r=40, t=10, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", bargap=0.3, bargroupgap=0.1,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(showgrid=True, gridcolor="#e6e4df", zeroline=False)
    return fig
