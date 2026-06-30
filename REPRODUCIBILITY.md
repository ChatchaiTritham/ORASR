# Reproducibility

This document states honestly what the committed code reproduces and what it
does not. Run the deterministic driver:

```bash
python scripts/run_all.py            # structural + cohort + flat-baseline + ablation
python scripts/flat_baseline.py      # gate-work: ORASR vs flat monitor (host-independent)
python scripts/ablation.py           # progressive gate removal -> results/ablation.csv
python scripts/extract_mimic.py --mimic-path /path/to/mimic-iv   # credentialed data only
python -m pytest -q                  # structural + cohort tests (10 tests)
python scripts/generate_figures.py   # figures read thresholds from results/
```

`run_all.py` now also invokes the flat-monitor baseline and the gate-removal
ablation, writing `results/flat_baseline.json`, `results/ablation.json`, and
`results/ablation.csv`.

The driver uses a fixed seed (`DEFAULT_RANDOM_SEED = 42`, from
`src/orasr/constants.py`) for the synthetic cohort. Structural results are
host-independent; the cohort distribution is seed-stable; latencies are
measured per host and labelled as such.

## What reproduces vs. what does not

| Manuscript claim (location) | Status | Source of truth |
|---|---|---|
| Thresholds 0.30 / 0.70 partition Fast/Normal/Safe (Abstract L104; Eq. L204–206) | **Reproduces** | `verify_structure()` reads `ORASRRouter.FAST_PATH_THRESHOLD`/`SAFE_PATH_THRESHOLD` and probes the partition. |
| Monotonic gate inclusion: Fast=1, Normal=3, Safe=4 gates (Abstract L104; Contributions L125) | **Reproduces** | Gate lists read from `router.pathways`; verified as a strict superset chain. |
| Non-bypass: a failed gate blocks execution (P2/P3, L106) | **Reproduces** | Driver routes a malformed input and asserts the action never runs. |
| Synthetic cohort 3,500 / 4,500 / 2,000 across the three strata (L524) | **Reproduces** | `run_cohort()` builds and routes the stratified cohort; distribution is exact. |
| Pathway latencies 2.3 / 45.2 / 287.5 ms (Abstract L106; Tab. L582–584; L906) | **Environment-specific — NOT reproduced** | No timing harness or hardware is committed; the manuscript ran on an i7-12700 / Ubuntu 22.04 (L522). The driver measures latency on the current host and writes it under an `environment` block. It does **not** copy the literals. |
| Gate pass rate 98.7%, 130 blocked (Tab. L608; breakdown L628–644) | **NOT reproducible as published** | The committed validators pass for well-formed inputs, so a clean cohort yields 100%. The 1.3% block rate needs a malformed-input / failure-injection mix that is not committed. The driver reports the honest 100% and records the gap (no tuning). |
| 100% formal compliance / 0 violations (Tab. L549–555) | **Partially reproduces** | Zero violations on the clean cohort follows from the non-bypass property (no action executes after a gate fail). The published confidence intervals over a 10,000-trace audit are a presentation of the same property, not a separate recomputation. |
| Gate-work reduction vs. flat monitor: ~1.94 vs 4.0 evals/call → ~51% (analytic) | **Reproduces (gate-work invariant)** | `scripts/flat_baseline.py` instruments the committed `SafetyGate.check` to count evals/call for ORASR (adaptive) vs a flat monitor (all gates always). On the seed-42 **synthetic** cohort: ORASR=2.5 vs flat=4.0 → **37.5%** reduction, **1.60×** work-normalised throughput. Applying the same arithmetic to the MIMIC mix (58.1/31.5/10.4%) gives **1.942** evals/call → reproduces the manuscript's 1.94 vs 4.0 (51%). These are host-independent integers. |
| 86% latency reduction / 7.3× speedup in **milliseconds** (Abstract L106; L807) | **Environment-specific — NOT reproduced as literals** | Absolute-ms reductions depend on per-gate cost, hardware and load. The portable **gate-work** reduction is reproduced instead (above); the ms figures and any MIMIC-weighted latency are not copied. |
| Ablation / gate-removal coverage tables (L716–839) | **Reproduces (coverage, synthetic)** | `scripts/ablation.py` runs progressive gate removal + a deterministic per-gate failure-injection suite (1,000 scenarios/gate, seed 42) on the **synthetic** cohort → `results/ablation.csv`. Each removed gate leaks exactly its own fault type (coverage_loss 1.00); full G1–G4 stack leaks 0. The MIMIC-weighted ablation **latency** column still needs credentialed data + a specific host. |
| MIMIC-IV: 8,412 actions, 58.1 / 31.5 / 10.4% (L106; L747; Tab. L764–769) | **Requires credentialed data — runnable extraction provided** | `scripts/extract_mimic.py` reads a user-supplied MIMIC-IV copy, maps actions→risk via a transparent rule table, and emits the routing distribution from the committed engine. No MIMIC data is committed and the 58.1/31.5/10.4% / 8,412 numbers are **not** hardcoded; they must be regenerated on a credentialed copy. Absent data the script exits without fabricating. |

Machine-readable versions: `results/structural_verification.json`,
`results/synthetic_cohort.json`, `results/gaps.json`,
`results/flat_baseline.json`, `results/ablation.json`, `results/ablation.csv`,
`results/pathway_distribution.csv`, `results/threshold_bands.csv`.

## What still requires credentialed data / a specific host

These cannot be verified from this repository alone; they need a credentialed
MIMIC-IV copy and/or the original hardware:

- The MIMIC-IV **8,412-action routing distribution** (58.1 / 31.5 / 10.4%) —
  regenerate with `scripts/extract_mimic.py` on your own credentialed data.
- Any **MIMIC-weighted latency** and the **absolute-ms** latency reduction
  (~84–86%, 7.3× in ms) — host-specific; only the gate-work reduction is portable.
- The **MIMIC-based ablation latency column** — coverage is reproduced on the
  synthetic cohort, but the per-configuration latency on the MIMIC corpus is not.

## Root cause (historical) and what changed

The repository originally shipped the **routing engine** and unit tests but not
the **evaluation harness**. It now ships: a flat-monitor gate-work baseline
(`scripts/flat_baseline.py`), a deterministic gate-removal ablation with
failure injection (`scripts/ablation.py`), and a runnable, data-free MIMIC-IV
extraction (`scripts/extract_mimic.py`). The seed-42 synthetic results are
host-independent and byte-stable across runs; only wall-clock latency and the
credentialed-data items above remain non-portable.

## Recommended manuscript tempering

- Efficiency claim: report the **gate-work reduction** (evals/call) as the
  reproducible, host-independent quantity; present the ms / 7.3× speedup as
  measured on the stated hardware (i7-12700 / Ubuntu 22.04) and note the
  artifact does not pin the absolute-ms values.
- MIMIC distribution (58.1/31.5/10.4%): present as regenerable via the released
  `extract_mimic.py` on credentialed data, not bundled with the repo.
- 98.7% gate pass rate / 130-block breakdown: only meaningful with the
  failure-injection methodology; the released ablation demonstrates the
  detection mechanism on the synthetic cohort.
