"""Matplotlib pitch charts. Colours follow a validated reference palette:
categorical slot 1 (blue) / slot 2 (orange), sequential blue, diverging red-gray-blue.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
LINE = "#c3c2b7"
SUCCESS = "#2a78d6"      # categorical slot 1
FAIL = "#eb6834"         # categorical slot 2
SEQUENTIAL = LinearSegmentedColormap.from_list("seq_blue", ["#f0efec", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
DIVERGING = LinearSegmentedColormap.from_list("div_red_blue", ["#a83232", "#e34948", "#f0efec", "#2a78d6", "#104281"])
# OpenPlay units -> metres on a nominal 105 x 68 pitch, so the drawing keeps true proportions.
ASPECT = 0.68 / 1.05


def _pitch(ax):
    ax.set_facecolor(SURFACE)
    kw = dict(color=LINE, linewidth=1, zorder=0)
    ax.plot([0, 100, 100, 0, 0], [0, 0, 100, 100, 0], **kw)
    ax.plot([50, 50], [0, 100], **kw)
    for x0, x1 in ((0, 17), (100, 83)):  # penalty areas (16.5 m deep, 40.3 m wide)
        ax.plot([x0, x1, x1, x0], [21.1, 21.1, 78.9, 78.9], **kw)
    ax.add_patch(matplotlib.patches.Ellipse((50, 50), 2 * 9.15 / 1.05, 2 * 9.15 / 0.68, fill=False, color=LINE, linewidth=1))
    ax.set_xlim(-1, 101)
    ax.set_ylim(-1, 101)
    ax.set_aspect(ASPECT)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_yticks([0, 50, 100])
    ax.tick_params(colors=INK_2, labelsize=8, length=0)
    for side in ax.spines.values():
        side.set_visible(False)
    ax.set_xlabel("x  (attacking direction →, opponent goal = 100)", color=INK_2, fontsize=9)
    ax.set_ylabel("y (OpenPlay coordinate)", color=INK_2, fontsize=9)


def _figure():
    fig, ax = plt.subplots(figsize=(10, 10 * ASPECT * 0.98))
    fig.patch.set_facecolor(SURFACE)
    return fig, ax


def pass_map_figure(passes, title: str):
    """Every row is drawn (no sampling). Colour = successful (blue) / unsuccessful (orange)."""
    fig, ax = _figure()
    _pitch(ax)
    n = len(passes)
    # Fewer, stronger lines for one match; faint thin lines when a season is overplotted.
    alpha = float(np.clip(12 / max(n, 1) ** 0.5, 0.03, 0.8))
    width = 0.8 if n <= 2000 else 0.4
    for ok, colour, label in ((True, SUCCESS, "Successful"), (False, FAIL, "Unsuccessful")):
        part = passes.loc[passes["is_successful"] == ok]
        if part.empty:
            continue
        segs = np.stack([part[["x", "y"]].to_numpy(float), part[["end_x", "end_y"]].to_numpy(float)], axis=1)
        ax.add_collection(LineCollection(segs, colors=colour, linewidths=width, alpha=alpha, label=f"{label} ({len(part):,})", zorder=2))
        if n <= 2000:  # end-point dots only while they stay legible
            ax.scatter(part["end_x"], part["end_y"], s=4, color=colour, alpha=min(1.0, alpha * 1.5), linewidths=0, zorder=3)
    if n:
        leg = ax.legend(loc="upper left", bbox_to_anchor=(0, -0.08), ncol=2, frameon=False, fontsize=9)
        for h in leg.legend_handles:
            h.set_alpha(1)
    ax.set_title(title, color=INK, fontsize=11, loc="left")
    fig.tight_layout()
    return fig


def zone_heatmap_figure(matrix, title: str, signed: bool, fmt: str = "{:.2f}"):
    """8x12 zone matrix (rows=y, cols=x). signed -> diverging around 0, else sequential."""
    m = np.asarray(matrix, dtype=float)
    if m.shape != (8, 12):
        raise ValueError("Expected an 8 x 12 matrix")
    fig, ax = _figure()
    if signed:
        bound = float(np.abs(m).max()) or 1.0
        norm = TwoSlopeNorm(vmin=-bound, vcenter=0.0, vmax=bound)
        cmap = DIVERGING
    else:
        norm = matplotlib.colors.Normalize(vmin=0, vmax=float(m.max()) or 1.0)
        cmap = SEQUENTIAL
    img = ax.imshow(m, origin="lower", extent=(0, 100, 0, 100), cmap=cmap, norm=norm, aspect=ASPECT, zorder=1)
    _pitch(ax)
    for r in range(8):
        for c in range(12):
            v = m[r, c]
            if v == 0:
                continue
            light_bg = abs(norm(v) - 0.5) < 0.3 if signed else norm(v) < 0.55
            label = fmt.format(v)
            if float(label) == 0:  # avoid "-0.00" for tiny negatives; exact values are in the table
                label = fmt.format(0.0)
            ax.text((c + 0.5) * 100 / 12, (r + 0.5) * 100 / 8, label, ha="center", va="center",
                    fontsize=7, color=INK if light_bg else "#ffffff", zorder=4)
    cb = fig.colorbar(img, ax=ax, fraction=0.025, pad=0.02)
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=8, colors=INK_2, length=0)
    ax.set_title(title, color=INK, fontsize=11, loc="left")
    fig.tight_layout()
    return fig
