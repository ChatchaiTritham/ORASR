"""Generate manuscript-ready ORASR figures.

The figures are intentionally derived from the current ORASR pathway and gate
structure so the thesis can use repository-native visual evidence. Styling
follows the canonical shared publication style (_management/FIGURE_STYLE.md):
Okabe-Ito color-blind-safe palette, Times serif fonts, vector PDF + 300 dpi PNG.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"
RESULTS = ROOT / "results"


# Color-blind-safe (Okabe-Ito) — canonical shared order.
PALETTE = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#000000"]


def apply_pub_style() -> None:
    """Apply the canonical Top-Tier matplotlib style (once, before plotting)."""
    mpl.rcParams.update(
        {
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.02,
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "mathtext.fontset": "stix",
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.8,
            "axes.grid": True,
            "grid.alpha": 0.3,
            "grid.linewidth": 0.6,
            "lines.linewidth": 1.6,
            "lines.markersize": 5,
            "legend.frameon": False,
            "figure.constrained_layout.use": True,
            "axes.prop_cycle": mpl.cycler(color=PALETTE),
        }
    )


# Muted palette-derived tints for schematic fills (keep text readable on top).
# Each pathway maps to a palette hue; neutral boxes use a light slate.
PATHWAY_FILL = {
    "FAST": "#cfeae0",     # tint of Okabe-Ito green  (#009E73)
    "NORMAL": "#f7e3c9",   # tint of Okabe-Ito orange (#E69F00)
    "SAFE": "#f4d6c6",     # tint of Okabe-Ito vermillion (#D55E00)
}
PATHWAY_EDGE = {
    "FAST": "#009E73",
    "NORMAL": "#E69F00",
    "SAFE": "#D55E00",
}
NEUTRAL_FILL = "#eef2f6"
NEUTRAL_EDGE = "#000000"
ACCENT_EDGE = "#0072B2"       # primary blue for normal flow
BLOCK_EDGE = "#D55E00"        # vermillion for blocked / deferred flow
INPUT_FILL = "#d6e7f2"        # tint of Okabe-Ito blue (#0072B2)
RESULT_FILL = "#e6dcef"       # tint of Okabe-Ito purple (#CC79A7)


def load_threshold_bands():
    """Load pathway risk bands and gate counts from run_all.py output.

    Falls back to the engine defaults if results/ has not been generated yet,
    so the figure script never hard-codes the threshold literals.
    """
    path = RESULTS / "threshold_bands.csv"
    if path.exists():
        bands = []
        with path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                bands.append(
                    {
                        "name": row["pathway"],
                        "lo": float(row["rho_low"]),
                        "hi": float(row["rho_high"]),
                        "n_gates": int(row["n_gates"]),
                    }
                )
        return bands
    # Fallback: read live from the engine rather than embedding literals.
    import sys

    sys.path.insert(0, str(ROOT / "src"))
    from orasr.router import ORASRRouter

    r = ORASRRouter()
    lo_n, hi_n = r.FAST_PATH_THRESHOLD, r.SAFE_PATH_THRESHOLD
    return [
        {"name": "FAST", "lo": 0.0, "hi": lo_n, "n_gates": 1},
        {"name": "NORMAL", "lo": lo_n, "hi": hi_n, "n_gates": 3},
        {"name": "SAFE", "lo": hi_n, "hi": 1.0, "n_gates": 4},
    ]


def add_box(ax, xy, width, height, label, facecolor=NEUTRAL_FILL, edgecolor=NEUTRAL_EDGE):
    patch = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.035,rounding_size=0.03",
        linewidth=1.3,
        edgecolor=edgecolor,
        facecolor=facecolor,
    )
    ax.add_patch(patch)
    ax.text(
        xy[0] + width / 2,
        xy[1] + height / 2,
        label,
        ha="center",
        va="center",
        fontsize=9.5,
        linespacing=1.35,
        zorder=5,
    )


def arrow(ax, start, end, color=ACCENT_EDGE):
    # FancyArrowPatch with a small shrink keeps the head off the box border so
    # arrows never overlap the text inside a box.
    patch = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=12,
        lw=1.4,
        color=color,
        shrinkA=3,
        shrinkB=3,
        zorder=1,
    )
    ax.add_patch(patch)


def save_current(name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        plt.savefig(FIGURES / f"{name}.{ext}")
    plt.close()


def generate_pathway_architecture() -> None:
    # constrained_layout is for axes; turn it off on this pure-canvas schematic
    # to use the full figure area without reflow.
    fig, ax = plt.subplots(figsize=(11, 6.4), layout="none")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.5,
        0.955,
        "ORASR Operational Reasoning-Action Safety Routing",
        ha="center",
        va="center",
        fontsize=15,
        fontweight="bold",
    )

    bands = {b["name"]: b for b in load_threshold_bands()}
    lo_n = bands["NORMAL"]["lo"]
    hi_n = bands["NORMAL"]["hi"]

    # --- Input -----------------------------------------------------------
    add_box(
        ax,
        (0.03, 0.46),
        0.17,
        0.18,
        "Input\naction + clinical context\n+ risk score",
        INPUT_FILL,
        ACCENT_EDGE,
    )

    # --- Three pathways (well separated vertically, no overlap) ----------
    add_box(
        ax,
        (0.275, 0.70),
        0.20,
        0.155,
        f"FAST\nrisk < {lo_n:.2f}\nG1 precondition",
        PATHWAY_FILL["FAST"],
        PATHWAY_EDGE["FAST"],
    )
    add_box(
        ax,
        (0.275, 0.435),
        0.20,
        0.165,
        f"NORMAL\n{lo_n:.2f} ≤ risk < {hi_n:.2f}\nG1 + G2 + G3",
        PATHWAY_FILL["NORMAL"],
        PATHWAY_EDGE["NORMAL"],
    )
    add_box(
        ax,
        (0.275, 0.145),
        0.20,
        0.185,
        f"SAFE\nrisk ≥ {hi_n:.2f}\nG1 + G2 + G3 + G4\nhuman approval",
        PATHWAY_FILL["SAFE"],
        PATHWAY_EDGE["SAFE"],
    )

    # --- Gate evaluation + blocked branch --------------------------------
    add_box(
        ax,
        (0.565, 0.555),
        0.195,
        0.175,
        "Safety gates\nconstraints +\nreasoning trace",
        NEUTRAL_FILL,
        NEUTRAL_EDGE,
    )
    add_box(
        ax,
        (0.565, 0.205),
        0.195,
        0.175,
        "Blocked or deferred\nviolations logged\nsafe = false",
        PATHWAY_FILL["SAFE"],
        BLOCK_EDGE,
    )

    # --- Routed result ---------------------------------------------------
    add_box(
        ax,
        (0.825, 0.455),
        0.155,
        0.18,
        "Routed action\nsafe result +\naudit history",
        RESULT_FILL,
        "#CC79A7",
    )

    # Input -> three pathways
    arrow(ax, (0.20, 0.55), (0.275, 0.775))
    arrow(ax, (0.20, 0.55), (0.275, 0.515))
    arrow(ax, (0.20, 0.55), (0.275, 0.235))
    # Pathways -> gate evaluation
    arrow(ax, (0.475, 0.775), (0.565, 0.66))
    arrow(ax, (0.475, 0.515), (0.565, 0.64))
    arrow(ax, (0.475, 0.235), (0.565, 0.61))
    # Gate -> routed result (pass) and gate -> blocked (fail)
    arrow(ax, (0.76, 0.64), (0.825, 0.56))
    arrow(ax, (0.6625, 0.555), (0.6625, 0.38), BLOCK_EDGE)
    # Blocked -> routed result (deferred is still an audited outcome)
    arrow(ax, (0.76, 0.30), (0.825, 0.50), BLOCK_EDGE)

    ax.text(
        0.5,
        0.055,
        "Pathway selection follows ORASRRouter._select_pathway thresholds and "
        "PathwayConfig gate lists.",
        ha="center",
        va="center",
        fontsize=8.5,
        color="#333333",
        style="italic",
    )

    save_current("orasr_pathway_architecture")


def generate_risk_pathway_map() -> None:
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Risk score $\\rho$")
    ax.set_yticks([])
    ax.grid(False)
    ax.set_title("ORASR Risk-Score Pathway Selection", fontsize=13, fontweight="bold")

    notes = {
        "FAST": "Precondition gate",
        "NORMAL": "Precondition, risk, constraints",
        "SAFE": "Full gates and human approval",
    }
    loaded = load_threshold_bands()
    for band in loaded:
        x0, x1, name = band["lo"], band["hi"], band["name"]
        ax.axvspan(x0, x1, color=PATHWAY_FILL[name], zorder=0)
        ax.text(
            (x0 + x1) / 2,
            0.64,
            name,
            ha="center",
            va="center",
            fontsize=13,
            fontweight="bold",
            color=PATHWAY_EDGE[name],
            zorder=3,
        )
        ax.text(
            (x0 + x1) / 2,
            0.45,
            notes[name],
            ha="center",
            va="center",
            fontsize=9.5,
            color="#222222",
            zorder=3,
        )
        ax.text(
            (x0 + x1) / 2,
            0.31,
            f"{band['n_gates']} gate(s)",
            ha="center",
            va="center",
            fontsize=8.5,
            color="#444444",
            style="italic",
            zorder=3,
        )

    by_name = {b["name"]: b for b in loaded}
    lo_n = by_name["NORMAL"]["lo"]
    hi_n = by_name["NORMAL"]["hi"]
    for thr in (lo_n, hi_n):
        # Stop the dashed line above the footnote band so the two never cross.
        ax.axvline(thr, ymin=0.18, ymax=1.0, color=PALETTE[6], linestyle="--", linewidth=1.3, zorder=2)
        ax.text(
            thr,
            0.88,
            f"{thr:.2f}",
            ha="center",
            va="center",
            fontsize=9.5,
            color=PALETTE[6],
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.2},
            zorder=4,
        )

    ax.text(
        0.5,
        0.07,
        "Thresholds match ORASRRouter.FAST_PATH_THRESHOLD and "
        "SAFE_PATH_THRESHOLD.",
        ha="center",
        va="center",
        fontsize=8.5,
        color="#333333",
        style="italic",
        zorder=3,
    )
    ax.spines[["left", "right", "top"]].set_visible(False)

    save_current("orasr_risk_pathway_map")


def main() -> None:
    apply_pub_style()
    generate_pathway_architecture()
    generate_risk_pathway_map()
    print(f"Generated ORASR figures in {FIGURES}")


if __name__ == "__main__":
    main()
