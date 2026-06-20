"""Generate manuscript-ready ORASR figures.

The figures are intentionally derived from the current ORASR pathway and gate
structure, plus the deterministic seed-42 evaluation written to ``results/`` by
``scripts/run_all.py`` so the thesis can use repository-native visual evidence.
Styling follows the canonical shared publication utility (``pubviz.py``, vendored
byte-identical next to this script): Okabe-Ito colour-blind-safe palette, Times
serif fonts, vector PDF + 300 dpi PNG. All quantitative figures load numbers from
``results/`` at run time -- nothing is hard-coded.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

from pubviz import (
    apply_pub_style,
    save_fig,
    PALETTE,
    add_box,
    arrow,
    load_results,
    results_dir,
)

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"
RESULTS = ROOT / "results"


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
ACCENT_EDGE = PALETTE[0]       # primary blue for normal flow
BLOCK_EDGE = PALETTE[1]        # vermillion for blocked / deferred flow
INPUT_FILL = "#d6e7f2"         # tint of Okabe-Ito blue (#0072B2)
RESULT_FILL = "#e6dcef"        # tint of Okabe-Ito purple (#CC79A7)


def load_threshold_bands():
    """Load pathway risk bands and gate counts from run_all.py output.

    Falls back to the engine defaults if results/ has not been generated yet,
    so the figure script never hard-codes the threshold literals.
    """
    try:
        rows = load_results("threshold_bands.csv", start=ROOT)
        return [
            {
                "name": r["pathway"],
                "lo": float(r["rho_low"]),
                "hi": float(r["rho_high"]),
                "n_gates": int(r["n_gates"]),
            }
            for r in rows
        ]
    except FileNotFoundError:
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


def load_pathway_distribution():
    """Load measured pathway counts + latency, or None if not generated yet."""
    try:
        rows = load_results("pathway_distribution.csv", start=ROOT)
    except FileNotFoundError:
        return None
    out = {}
    for r in rows:
        out[r["pathway"]] = {
            "count": int(r["count"]),
            "pct": float(r["pct"]),
            "mean_ms": float(r["mean_latency_ms"]) if r["mean_latency_ms"] else None,
            "p95_ms": float(r["p95_latency_ms"]) if r["p95_latency_ms"] else None,
        }
    return out


# --------------------------------------------------------------------------
# Schematic 1: pathway architecture (now drawn through pubviz add_box / arrow)
# --------------------------------------------------------------------------
def generate_pathway_architecture() -> None:
    # constrained_layout is for axes; turn it off on this pure-canvas schematic
    # to use the full figure area without reflow.
    fig, ax = plt.subplots(figsize=(11, 6.4), layout="none")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.5, 0.965,
        "ORASR Operational Reasoning-Action Safety Routing",
        ha="center", va="center", fontsize=15, fontweight="bold",
    )

    bands = {b["name"]: b for b in load_threshold_bands()}
    lo_n = bands["NORMAL"]["lo"]
    hi_n = bands["NORMAL"]["hi"]
    dist = load_pathway_distribution()

    def lane_label(name: str, base: str) -> str:
        """Overlay the empirical routing share + mean latency when available."""
        if dist and name in dist:
            d = dist[name]
            extra = f"\n{d['pct']:.0f}% of cohort"
            if d["mean_ms"] is not None:
                extra += f" · {d['mean_ms']:.3f} ms"
            return base + extra
        return base

    # --- Input ----------------------------------------------------------
    add_box(ax, (0.03, 0.46), 0.17, 0.18,
            "Input\naction + clinical context\n+ risk score",
            facecolor=INPUT_FILL, edgecolor=ACCENT_EDGE)

    # --- Three pathways (well separated vertically, no overlap) ---------
    add_box(ax, (0.275, 0.70), 0.21, 0.165,
            lane_label("FAST", f"FAST\nrisk < {lo_n:.2f} · G1"),
            facecolor=PATHWAY_FILL["FAST"], edgecolor=PATHWAY_EDGE["FAST"])
    add_box(ax, (0.275, 0.435), 0.21, 0.17,
            lane_label("NORMAL", f"NORMAL\n{lo_n:.2f} <= risk < {hi_n:.2f} · G1+G2+G3"),
            facecolor=PATHWAY_FILL["NORMAL"], edgecolor=PATHWAY_EDGE["NORMAL"])
    add_box(ax, (0.275, 0.145), 0.21, 0.19,
            lane_label("SAFE", f"SAFE\nrisk >= {hi_n:.2f} · G1+G2+G3+G4\nhuman approval"),
            facecolor=PATHWAY_FILL["SAFE"], edgecolor=PATHWAY_EDGE["SAFE"])

    # --- Gate evaluation + blocked branch -------------------------------
    add_box(ax, (0.575, 0.555), 0.195, 0.175,
            "Safety gates\nconstraints +\nreasoning trace",
            facecolor=NEUTRAL_FILL, edgecolor=NEUTRAL_EDGE)
    add_box(ax, (0.575, 0.205), 0.195, 0.175,
            "Blocked or deferred\nviolations logged\nsafe = false",
            facecolor=PATHWAY_FILL["SAFE"], edgecolor=BLOCK_EDGE)

    # --- Routed result --------------------------------------------------
    add_box(ax, (0.83, 0.455), 0.155, 0.18,
            "Routed action\nsafe result +\naudit history",
            facecolor=RESULT_FILL, edgecolor=PALETTE[3])

    # Input -> three pathways
    arrow(ax, (0.20, 0.55), (0.275, 0.78), color=ACCENT_EDGE)
    arrow(ax, (0.20, 0.55), (0.275, 0.52), color=ACCENT_EDGE)
    arrow(ax, (0.20, 0.55), (0.275, 0.24), color=ACCENT_EDGE)
    # Pathways -> gate evaluation
    arrow(ax, (0.485, 0.78), (0.575, 0.66), color=ACCENT_EDGE)
    arrow(ax, (0.485, 0.52), (0.575, 0.64), color=ACCENT_EDGE)
    arrow(ax, (0.485, 0.24), (0.575, 0.61), color=ACCENT_EDGE)
    # Gate -> routed result (pass) and gate -> blocked (fail)
    arrow(ax, (0.77, 0.64), (0.83, 0.56), color=ACCENT_EDGE)
    arrow(ax, (0.6725, 0.555), (0.6725, 0.38), color=BLOCK_EDGE)
    # Blocked -> routed result (deferred is still an audited outcome)
    arrow(ax, (0.77, 0.30), (0.83, 0.50), color=BLOCK_EDGE)

    ax.text(
        0.5, 0.045,
        "Pathway selection follows ORASRRouter._select_pathway thresholds and "
        "PathwayConfig gate lists; shares/latency from results/ (seed 42).",
        ha="center", va="center", fontsize=8.5, color="#333333", style="italic",
    )

    save_fig(fig, "orasr_pathway_architecture", out_dir=str(FIGURES))
    plt.close(fig)


# --------------------------------------------------------------------------
# Schematic 2: risk-score pathway map (axvspans + thresholds)
# --------------------------------------------------------------------------
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
        ax.text((x0 + x1) / 2, 0.64, name, ha="center", va="center",
                fontsize=13, fontweight="bold", color=PATHWAY_EDGE[name], zorder=3)
        ax.text((x0 + x1) / 2, 0.45, notes[name], ha="center", va="center",
                fontsize=9.5, color="#222222", zorder=3)
        ax.text((x0 + x1) / 2, 0.31, f"{band['n_gates']} gate(s)", ha="center",
                va="center", fontsize=8.5, color="#444444", style="italic", zorder=3)

    by_name = {b["name"]: b for b in loaded}
    lo_n = by_name["NORMAL"]["lo"]
    hi_n = by_name["NORMAL"]["hi"]
    for thr in (lo_n, hi_n):
        # Stop the dashed line above the footnote band so the two never cross.
        ax.axvline(thr, ymin=0.18, ymax=1.0, color=PALETTE[6], linestyle="--",
                   linewidth=1.3, zorder=2)
        ax.text(thr, 0.88, f"{thr:.2f}", ha="center", va="center", fontsize=9.5,
                color=PALETTE[6],
                bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.2}, zorder=4)

    ax.text(
        0.5, 0.07,
        "Thresholds match ORASRRouter.FAST_PATH_THRESHOLD and SAFE_PATH_THRESHOLD.",
        ha="center", va="center", fontsize=8.5, color="#333333", style="italic", zorder=3,
    )
    ax.spines[["left", "right", "top"]].set_visible(False)

    save_fig(fig, "orasr_risk_pathway_map", out_dir=str(FIGURES))
    plt.close(fig)


# --------------------------------------------------------------------------
# Quantitative 1: risk-coverage curve for the reject-option routing
# --------------------------------------------------------------------------
def generate_risk_coverage() -> bool:
    """Real risk-coverage curve from results/risk_coverage.csv (seed 42).

    Returns False (and emits nothing) if the artifact is absent, so the caller
    can report honestly rather than fabricate a curve.
    """
    try:
        rows = load_results("risk_coverage.csv", start=ROOT)
        meta = load_results("reject_option.json", start=ROOT)
    except FileNotFoundError:
        return False

    cov = [float(r["coverage"]) for r in rows]
    risk = [float(r["risk"]) for r in rows]
    # Drop the degenerate tail point (coverage 0 -> risk 0) for a clean line.
    pts = [(c, k) for c, k in zip(cov, risk) if c > 0]
    pts.sort()
    cov_s = [p[0] for p in pts]
    risk_s = [p[1] for p in pts]

    op = meta["operating_point"]
    base = meta["robustness_cohort"]["base_violation_rate"]

    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    ax.plot(cov_s, risk_s, color=PALETTE[0], lw=1.8, label="ORASR reject-option")
    # Full-coverage baseline (no abstention) -- the risk you accept covering all.
    ax.axhline(base, color=PALETTE[6], ls=":", lw=1.2,
               label=f"No abstention (risk={base:.3f})")
    # Operating point: tau = SAFE threshold.
    ax.scatter([op["coverage"]], [op["risk"]], color=PALETTE[1], zorder=5, s=55,
               label=f"Operating point $\\tau$={op['tau']:.2f}")
    ax.annotate(
        f"coverage={op['coverage']:.2f}\nrisk={op['risk']:.3f}",
        xy=(op["coverage"], op["risk"]),
        xytext=(op["coverage"] - 0.34, op["risk"] + 0.05),
        fontsize=8.5, color="#333333",
        arrowprops={"arrowstyle": "->", "color": "#555555", "lw": 1.0},
    )

    ax.set_xlabel("Coverage (fraction auto-executed)")
    ax.set_ylabel("Risk (gate-violation rate among covered)")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, max(risk_s) * 1.35)
    ax.set_title("Reject-Option Risk-Coverage Curve", fontsize=12, fontweight="bold")
    ax.legend(loc="upper left", fontsize=8)
    ax.text(
        0.5, -0.20,
        "Risk = ORASRRouter safe==false rate among auto-executed actions; abstain on "
        "$\\rho\\geq\\tau$. Violations stem from a seed-42 malformed-input mix that is "
        "risk-independent, so abstention by risk alone leaves residual risk roughly flat.",
        transform=ax.transAxes, ha="center", va="top", fontsize=7.3,
        color="#444444", style="italic", wrap=True,
    )

    save_fig(fig, "orasr_risk_coverage", out_dir=str(FIGURES))
    plt.close(fig)
    return True


# --------------------------------------------------------------------------
# Quantitative 2: per-lane routing distribution + gate-pass reliability
# --------------------------------------------------------------------------
def generate_lane_reliability() -> bool:
    """Per-lane routing share + gate-pass reliability from results/ (seed 42).

    Calibration in the probabilistic sense is NOT available (gates are boolean,
    no per-item confidence is emitted), so -- per the brief -- we honestly fall
    back to a routing-distribution + gate-pass reliability chart. Returns False
    if the artifact is absent.
    """
    try:
        rel = load_results("lane_reliability.csv", start=ROOT)
    except FileNotFoundError:
        return False

    lanes = [r["lane"] for r in rel]
    ns = [int(r["n"]) for r in rel]
    pass_rate = [float(r["pass_rate_pct"]) for r in rel]
    total = sum(ns)
    share = [100.0 * n / total for n in ns]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.2, 4.2))
    lane_colors = {"FAST": PALETTE[2], "NORMAL": PALETTE[4], "SAFE": PALETTE[1]}
    colors = [lane_colors.get(name, PALETTE[0]) for name in lanes]

    # Left: routing distribution (robustness cohort share per lane).
    b1 = ax1.bar(lanes, share, color=colors, width=0.62, edgecolor="white")
    ax1.set_ylabel("Routing share (%)")
    ax1.set_title("Routing distribution", fontsize=11, fontweight="bold")
    ax1.set_ylim(0, max(share) * 1.25)
    for rect, n in zip(b1, ns):
        ax1.text(rect.get_x() + rect.get_width() / 2, rect.get_height() + 1,
                 f"n={n}", ha="center", va="bottom", fontsize=8.5)

    # Right: gate-pass reliability per lane.
    b2 = ax2.bar(lanes, pass_rate, color=colors, width=0.62, edgecolor="white")
    ax2.set_ylabel("Gate-pass rate (%)")
    ax2.set_title("Per-lane gate reliability", fontsize=11, fontweight="bold")
    ax2.set_ylim(0, 105)
    for rect, p in zip(b2, pass_rate):
        ax2.text(rect.get_x() + rect.get_width() / 2, rect.get_height() + 1.5,
                 f"{p:.1f}%", ha="center", va="bottom", fontsize=8.5)

    fig.suptitle("ORASR Routing Distribution and Gate Reliability (seed 42)",
                 fontsize=12, fontweight="bold")
    fig.text(
        0.5, -0.02,
        "Robustness cohort with a deterministic malformed-input mix; pass rate = "
        "fraction with engine safe==true per lane. Boolean gates carry no per-item "
        "confidence, so a probabilistic calibration diagram is not backed by results "
        "and is intentionally not shown.",
        ha="center", va="top", fontsize=7.4, color="#444444", style="italic", wrap=True,
    )

    save_fig(fig, "orasr_lane_reliability", out_dir=str(FIGURES))
    plt.close(fig)
    return True


def main() -> None:
    apply_pub_style()
    generate_pathway_architecture()
    generate_risk_pathway_map()
    rc = generate_risk_coverage()
    lr = generate_lane_reliability()
    if not rc:
        print("SKIPPED orasr_risk_coverage: results/risk_coverage.csv absent "
              "(run scripts/run_all.py, seed 42).")
    if not lr:
        print("SKIPPED orasr_lane_reliability: results/lane_reliability.csv absent "
              "(run scripts/run_all.py, seed 42).")
    print(f"Generated ORASR figures in {FIGURES}")


if __name__ == "__main__":
    main()
