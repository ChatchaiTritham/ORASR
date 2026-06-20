# Reproducibility

This document states honestly what the committed code reproduces and what it
does not. Run the deterministic driver:

```bash
python scripts/run_all.py      # writes results/*.json and results/*.csv
python -m pytest -q            # structural + cohort tests (10 tests)
python scripts/generate_figures.py   # figures read thresholds from results/
```

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
| MIMIC-IV: 8,412 actions, 58.1 / 31.5 / 10.4% (L106; L747; Tab. L764–769) | **NOT reproducible** | No MIMIC-IV data, extraction code, or ICD→risk mapping is committed. The corpus and its distribution cannot be regenerated. |
| 86% latency reduction / 7.3× vs. flat monitor (Abstract L106; L807) | **NOT reproducible** | No flat runtime-monitor baseline is implemented in the repository. |
| Ablation / sensitivity tables (L716–839) | **NOT reproducible** | Depend on the MIMIC corpus and failure-injection suites that are not committed. |

Machine-readable versions: `results/structural_verification.json`,
`results/synthetic_cohort.json`, `results/gaps.json`,
`results/pathway_distribution.csv`, `results/threshold_bands.csv`.

## Root cause

The repository ships the **routing engine** (thresholds, gate configuration,
gate execution, reasoning trace, audit history) and unit tests, but it does
**not** ship the **evaluation harness**: there is no benchmark/timing script,
no synthetic-failure generator, no flat-monitor baseline, and no MIMIC-IV data
or extraction pipeline. The declared seed was unused and `results/` was empty.
Consequently the *structural* claims — which are properties of the committed
engine — reproduce exactly, while every *empirical* number that depends on a
specific machine, an injected-failure mix, a baseline implementation, or
external clinical data cannot be regenerated from this repository alone.

`scripts/run_all.py` closes the gap for everything the committed code can
honestly support and documents the rest in `results/gaps.json`.

## Recommended manuscript tempering

- Latency literals (2.3 / 45.2 / 287.5 ms): present as measured on the stated
  hardware and note that the published artifact does not pin these values.
- 98.7% gate pass rate / 130-block breakdown: only meaningful with the
  failure-injection methodology described; either commit that generator or mark
  the figures as illustrative of the injected-failure mix.
- MIMIC-IV section and flat-monitor comparison: clearly flag as not included in
  the released code/data, or release the extraction and baseline scripts.
