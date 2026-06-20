# Operational Reasoning-Action Safety Routing (ORASR)

> Run the routing engine yourself and confirm that every safety property the paper proves about it holds at runtime, on a fixed-seed synthetic cohort.

![License](https://img.shields.io/badge/license-MIT-blue) ![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![Reproducible](https://img.shields.io/badge/reproducible-seed--42-success)

## Overview

Clinical decision support has to make a hard trade-off on every recommendation: spend more time checking an action and the system stays safe but slow; skip the checks and it becomes fast but unaccountable. A single fixed verification pipeline forces the same cost on a routine vitals lookup and a high-risk medication change alike. ORASR treats that trade-off as a routing problem instead of a fixed cost.

The engine reads a risk score for each requested action and sends it down one of three lanes. Low-risk actions take a short path with a single precondition check; mid-risk actions add risk and constraint gates; high-risk actions run the full gate sequence and require human approval before anything executes. The gate sets are nested by design, so a higher-risk action always passes through a strict superset of the checks applied to a lower-risk one, and a failed gate stops the action rather than letting it slip through.

This repository holds the routing engine, its gates and constraints, and a deterministic driver that exercises the published structural guarantees against the actual code. It is the reproducibility companion to the manuscript, not a re-implementation of the clinical study: the parts that depend on private data or on an external baseline are documented as gaps rather than silently regenerated.

## Key results

All numbers below come from `scripts/run_all.py` at seed 42 and match the committed files in `results/`.

- The three-lane partition is exact at the published cut points: risk below 0.30 routes to FAST, the 0.30–0.70 band routes to NORMAL, and 0.70 and above routes to SAFE (`structural_verification.json`, `partition_correct = true`).
- Gate counts are 1 / 3 / 4 for FAST / NORMAL / SAFE and form a strict inclusion chain, so risk-proportionate coverage holds by construction rather than by tuning.
- A failed precondition gate marks the route unsafe and the wrapped action never runs (`non_bypass_holds = true`) — the non-bypass property the paper states as a theorem.
- Routing a stratified 10,000-scenario cohort (3,500 / 4,500 / 2,000) reproduces the 35 / 45 / 20 percent pathway distribution exactly every time.
- On a clean, well-formed cohort the gate pass rate is 100 percent. The manuscript's 98.7 percent figure and the 130-block breakdown come from an injected-failure mix that is not committed here; we report the honest clean-cohort number rather than tuning the code to match the paper (see `results/gaps.json`).

Two manuscript results are deliberately **not** reproduced by this code: the MIMIC-IV retrospective corpus (8,412 actions; 58.1 / 31.5 / 10.4 percent distribution) and the flat-monitor latency baseline (the 84–86 percent reduction and 7.3x throughput claims). Neither the clinical extraction nor the baseline implementation is committed. Latencies are measured on the host that runs the driver and are environment-specific; the paper's literal values (2.3 / 45.2 / 287.5 ms) are not copied into the repository.

## Repository structure

```text
src/orasr/        routing engine — router, pathways, gates, constraints, reasoning trace, constants
scripts/          run_all.py (reproducibility driver), generate_figures.py, demo.py, gate_demo.py
results/          machine-readable artifacts written by run_all.py (JSON + CSV), including gaps.json
figures/          pathway architecture and risk-band figures (PNG + PDF) plus the QA contact sheet
tests/            router behaviour and reproducibility checks
notebooks/        quickstart and advanced-workflow walkthroughs
FIGURE_MANIFEST.csv   curated figure inventory used as manuscript evidence
```

## Installation

```bash
git clone https://github.com/ChatchaiTritham/ORASR.git
cd ORASR
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
pip install -r requirements.txt
```

## Reproducing the results

```bash
python scripts/run_all.py        # fixed seed 42; finishes in well under a minute on a laptop
```

The driver writes `structural_verification.json`, `synthetic_cohort.json`, `gaps.json`, `pathway_distribution.csv`, and `threshold_bands.csv` to `results/`. Everything scientific — the threshold partition, the gate-inclusion chain, the non-bypass check, the 35 / 45 / 20 distribution, and the clean-cohort pass rate — is deterministic and comes out identical on every run with the same seed. The only values that change between machines are the wall-clock latencies, which the driver records inside an explicit `environment` block and labels as host-specific. Re-running on a different computer will therefore reproduce all reported metrics except those latencies.

To regenerate the figures from the same artifacts:

```bash
python scripts/generate_figures.py
```

## Results and figures

The figure scripts read the threshold bands straight from the engine (or from `results/threshold_bands.csv`); no threshold literal is hard-coded, so the figures stay consistent with whatever the engine actually does.

- `figures/orasr_pathway_architecture.png` — the full routing flow from an incoming action and its risk score through the FAST / NORMAL / SAFE lanes, the gate stages, and the audit output. Use it to see how the three lanes diverge and where a blocked action is logged instead of executed.
- `figures/orasr_risk_pathway_map.png` — the risk axis from 0 to 1 split into the three coloured bands with the 0.30 and 0.70 cut points marked. It is the quickest way to read which lane a given risk score selects and how many gates that lane runs.
- `figures/visual_qa_contact_sheet.png` — a contact sheet collecting the figure renders for a fast visual check that the exported images match the current engine configuration.

## Data

No clinical or human-subject data is used or distributed here. The evaluation cohort is fully synthetic: 10,000 routing scenarios with risk scores drawn from uniform distributions over the three risk bands at a fixed seed. Because nothing in this repository touches patient records, no ethics approval or IRB review applies. The MIMIC-IV figures cited in the paper rely on credentialed access and are not part of this package.

## Citation

```bibtex
@article{tritham_orasr,
  author  = {Tritham, Chatchai and Snae Namahoot, Chakkrit},
  title    = {Operational Reasoning-Action Safety Routing for Clinical Decision Support},
  journal  = {Cognitive Computation},
  note     = {to appear},
  year     = {2026}
}
```

## License

Released under the MIT License (see `LICENSE`).

## Contact

**Chatchai Tritham** — Department of Computer Science and Information Technology, Faculty of Science, Naresuan University, Phitsanulok 65000, Thailand. Email: chatchait66@nu.ac.th · ORCID: 0000-0001-7899-228X
**Chakkrit Snae Namahoot** — same affiliation. Email: chakkrits@nu.ac.th · ORCID: 0000-0003-4660-4590

## Portfolio relationship

| Repository | Role |
|---|---|
| BASICS-CDSS | Beyond-accuracy evaluation methodology |
| TRI-X | Framework-level package |
| ORASR | Routing and safety-action component |
| DRAS-5 | Dynamic risk-state component |
| SAFE-Gate | Safety-gated ensemble framework |
| SynDX | Synthetic validation and explainability evidence |
| SURgul | SRGL/governance reproducibility component |
| TRI-X-CDSS | Integration and implementation package |
| Selective-CDSS | Risk-controlled selective-prediction (abstention) component |
| Causal-CDSS | Causal-inference evaluation component |
| Beyond-Accuracy | Simulation-based safety/calibration evaluation framework |
