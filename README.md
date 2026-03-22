# ORASR

## Overview

ORASR implements Operational Reasoning-Action Safety Routing for pathway-aware,
safety-constrained action execution.

## Installation

```bash
pip install -e .
```

## Repository Structure

- `src/orasr/`: importable package
- `tests/`: automated tests
- `scripts/`: runnable demos
- `notebooks/`: interactive walkthroughs

## Tutorials And Demos

- Script demos:
  - `scripts/demo.py`: end-to-end routing walkthrough
  - `scripts/gate_demo.py`: individual gate behavior walkthrough
- Notebooks:
  - `notebooks/01_orasr_quickstart.ipynb`: starter interactive quickstart
  - `notebooks/02_orasr_advanced_workflows.ipynb`: risk sweeps, approvals, latency, and pathway visualization

Run a demo from the repository root:

```bash
python scripts/demo.py
python scripts/gate_demo.py
```

## Cross-Repository Tutorial Charts

- `../tutorial_surface_comparison.png`: scripts vs examples vs notebooks across all repositories
- `../tutorial_asset_density.png`: interactive/tutorial asset density normalized by repository size

## Package Scope

Core modules include routing, pathways, reasoning traces, constraints, and gate
validation helpers.

## Source Layout

This repository uses the recommended `src/<package_name>` layout.
Importable code lives in `src/orasr/`.

## Testing

```bash
pytest tests -v
```

## Contact

### Contact Author

**Chatchai Tritham** (PhD Candidate)

- Email: [chatchait66@nu.ac.th](mailto:chatchait66@nu.ac.th)
- Department of Computer Science and Information Technology
- Faculty of Science, Naresuan University
- Phitsanulok 65000, Thailand

### Supervisor

**Chakkrit Snae Namahoot**

- Email: [chakkrits@nu.ac.th](mailto:chakkrits@nu.ac.th)
- Department of Computer Science
- Faculty of Science, Naresuan University
- Phitsanulok 65000, Thailand
