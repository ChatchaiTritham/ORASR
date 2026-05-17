"""Generate manuscript-ready ORASR figures.

The figures are intentionally derived from the current ORASR pathway and gate
structure so the thesis can cite repository-native visual evidence.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"


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

    add_box(ax, (0.04, 0.48), 0.16, 0.16, "Input action\nclinical context\nrisk score", "#e0f2fe")
    add_box(ax, (0.28, 0.68), 0.18, 0.13, "FAST\nrisk < 0.30\nG1 precondition", "#dcfce7")
    add_box(
        ax,
        (0.28, 0.44),
        0.18,
        0.16,
        "NORMAL\n0.30 <= risk < 0.70\nG1 + G2 + G3",
        "#fef9c3",
    )
    add_box(
        ax,
        (0.28, 0.18),
        0.18,
        0.17,
        "SAFE\nrisk >= 0.70\nG1 + G2 + G3 + G4\nhuman approval",
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

    bands = [
        (0.00, 0.30, "FAST", "#dcfce7", "Precondition gate"),
        (0.30, 0.70, "NORMAL", "#fef9c3", "Precondition, risk, constraints"),
        (0.70, 1.00, "SAFE", "#fee2e2", "Full gates and human approval"),
    ]
    for x0, x1, name, color, note in bands:
        ax.axvspan(x0, x1, color=color)
        ax.text((x0 + x1) / 2, 0.62, name, ha="center", va="center", fontsize=14, fontweight="bold")
        ax.text((x0 + x1) / 2, 0.42, note, ha="center", va="center", fontsize=10)

    ax.axvline(0.30, color="#334155", linestyle="--", linewidth=1.4)
    ax.axvline(0.70, color="#334155", linestyle="--", linewidth=1.4)
    ax.text(0.30, 0.86, "0.30", ha="center", fontsize=10)
    ax.text(0.70, 0.86, "0.70", ha="center", fontsize=10)
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
