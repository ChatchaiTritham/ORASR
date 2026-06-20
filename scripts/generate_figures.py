"""Generate manuscript-ready ORASR figures.

The figures are intentionally derived from the current ORASR pathway and gate
structure so the thesis can use repository-native visual evidence.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"
RESULTS = ROOT / "results"


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


def add_box(ax, xy, width, height, label, facecolor="#f8fafc", edgecolor="#334155"):
    patch = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.035,rounding_size=0.03",
        linewidth=1.4,
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
        fontsize=10,
        wrap=True,
    )


def arrow(ax, start, end, color="#334155"):
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops={"arrowstyle": "->", "lw": 1.5, "color": color},
    )


def save_current(name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        plt.savefig(FIGURES / f"{name}.{ext}", dpi=300, bbox_inches="tight")
    plt.close()


def generate_pathway_architecture() -> None:
    fig, ax = plt.subplots(figsize=(11, 6.2))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.5,
        0.95,
        "ORASR Operational Reasoning-Action Safety Routing",
        ha="center",
        va="center",
        fontsize=16,
        fontweight="bold",
    )

    bands = {b["name"]: b for b in load_threshold_bands()}
    lo_n = bands["NORMAL"]["lo"]
    hi_n = bands["NORMAL"]["hi"]

    add_box(ax, (0.04, 0.48), 0.16, 0.16, "Input action\nclinical context\nrisk score", "#e0f2fe")
    add_box(
        ax,
        (0.28, 0.68),
        0.18,
        0.13,
        f"FAST\nrisk < {lo_n:.2f}\nG1 precondition",
        "#dcfce7",
    )
    add_box(
        ax,
        (0.28, 0.44),
        0.18,
        0.16,
        f"NORMAL\n{lo_n:.2f} <= risk < {hi_n:.2f}\nG1 + G2 + G3",
        "#fef9c3",
    )
    add_box(
        ax,
        (0.28, 0.18),
        0.18,
        0.17,
        f"SAFE\nrisk >= {hi_n:.2f}\nG1 + G2 + G3 + G4\nhuman approval",
        "#fee2e2",
    )
    add_box(ax, (0.58, 0.55), 0.18, 0.16, "Safety gates\nconstraints\nreasoning trace", "#f1f5f9")
    add_box(ax, (0.58, 0.25), 0.18, 0.16, "Blocked or deferred\nviolations logged\nsafe = false", "#ffe4e6")
    add_box(ax, (0.82, 0.48), 0.14, 0.16, "Routed action\nsafe result\naudit history", "#ede9fe")

    arrow(ax, (0.20, 0.56), (0.28, 0.74))
    arrow(ax, (0.20, 0.56), (0.28, 0.52))
    arrow(ax, (0.20, 0.56), (0.28, 0.27))
    arrow(ax, (0.46, 0.745), (0.58, 0.64))
    arrow(ax, (0.46, 0.52), (0.58, 0.64))
    arrow(ax, (0.46, 0.27), (0.58, 0.64))
    arrow(ax, (0.76, 0.63), (0.82, 0.56))
    arrow(ax, (0.67, 0.55), (0.67, 0.41), "#b91c1c")
    arrow(ax, (0.76, 0.33), (0.82, 0.50), "#b91c1c")

    ax.text(
        0.5,
        0.07,
        "Pathway selection follows ORASRRouter._select_pathway thresholds and PathwayConfig gate lists.",
        ha="center",
        va="center",
        fontsize=9,
        color="#475569",
    )

    save_current("orasr_pathway_architecture")


def generate_risk_pathway_map() -> None:
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Risk score")
    ax.set_yticks([])
    ax.set_title("ORASR Risk-Score Pathway Selection", fontsize=15, fontweight="bold")

    notes = {
        "FAST": "Precondition gate",
        "NORMAL": "Precondition, risk, constraints",
        "SAFE": "Full gates and human approval",
    }
    colors = {"FAST": "#dcfce7", "NORMAL": "#fef9c3", "SAFE": "#fee2e2"}
    loaded = load_threshold_bands()
    for band in loaded:
        x0, x1, name = band["lo"], band["hi"], band["name"]
        ax.axvspan(x0, x1, color=colors[name])
        ax.text((x0 + x1) / 2, 0.62, name, ha="center", va="center", fontsize=14, fontweight="bold")
        ax.text((x0 + x1) / 2, 0.42, notes[name], ha="center", va="center", fontsize=10)

    lo_n = {b["name"]: b for b in loaded}["NORMAL"]["lo"]
    hi_n = {b["name"]: b for b in loaded}["NORMAL"]["hi"]
    ax.axvline(lo_n, color="#334155", linestyle="--", linewidth=1.4)
    ax.axvline(hi_n, color="#334155", linestyle="--", linewidth=1.4)
    ax.text(lo_n, 0.86, f"{lo_n:.2f}", ha="center", fontsize=10)
    ax.text(hi_n, 0.86, f"{hi_n:.2f}", ha="center", fontsize=10)
    ax.text(
        0.5,
        0.16,
        "Thresholds match ORASRRouter.FAST_PATH_THRESHOLD and SAFE_PATH_THRESHOLD.",
        ha="center",
        fontsize=9,
        color="#475569",
    )
    ax.spines[["left", "right", "top"]].set_visible(False)

    save_current("orasr_risk_pathway_map")


def main() -> None:
    generate_pathway_architecture()
    generate_risk_pathway_map()
    print(f"Generated ORASR figures in {FIGURES}")


if __name__ == "__main__":
    main()
