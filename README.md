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
  - `scripts/generate_figures.py`: manuscript figure generation
  - `scripts/generate_manuscript_manifest.py`: curated manuscript figure manifest and visual QA sheet
- Notebooks:
  - `notebooks/01_orasr_quickstart.ipynb`: starter interactive quickstart
  - `notebooks/02_orasr_advanced_workflows.ipynb`: risk sweeps, approvals, latency, and pathway visualization

Run a demo from the repository root:

```bash
python scripts/demo.py
python scripts/gate_demo.py
```

## Curated Manuscript Figures

Curated manuscript figures listed in `FIGURE_MANIFEST.csv` are maintained for a
manuscript that is still in preparation. This status does not imply publication,
acceptance, or final journal readiness.

Regenerate figure exports:

```bash
python scripts/generate_figures.py
```

Regenerate the manifest and visual QA sheet:

```bash
python scripts/generate_manuscript_manifest.py
```

Outputs:

- `figures/`: PDF and PNG figure exports
- `FIGURE_MANIFEST.csv`: curated figure role, source script, source artifact,
  caption, and intended article section
- `figures/visual_qa_contact_sheet.png`: visual QA sheet

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

## Manuscript Alignment

The ORASR manuscript is still in preparation and owns the routing/action-
selection contribution in the research program. This repository supports the
manuscript's formulas, pseudocode, data/results, and figures for:

- operational pathway routing
- risk-proportionate action selection
- safety-gate validation
- transparent reasoning traces
- pathway architecture and risk-pathway map figures

The current manuscript uses local figure names, while the repository records the
curated routing figure artifacts in `FIGURE_MANIFEST.csv`. Future manuscript
cleanup should map each manuscript figure to the corresponding manifest row.

## Methodological References

ORASR is positioned as an operational routing layer. It should be cited or
described separately from TRI-X:

- TRI-X is the integrated framework.
- ORASR owns pathway routing and safety action selection.
- DRAS-5 owns stateful risk-action behavior.
- SURgul/SRGL owns governance logic.

## Citation

The associated manuscript is still in preparation. Until its publication status
changes, cite this software repository using `CITATION.cff`.

## Contact

### Contact Author

**Chatchai Tritham** (Author)

- Email: [chatchait66@nu.ac.th](mailto:chatchait66@nu.ac.th)
- ORCID: [0000-0001-7899-228X](https://orcid.org/0000-0001-7899-228X)
- Department of Computer Science and Information Technology
- Faculty of Science, Naresuan University
- Phitsanulok 65000, Thailand

### Supervisor

**Chakkrit Snae Namahoot**

- E-mail: [chakkrits@nu.ac.th](mailto:chakkrits@nu.ac.th)
- ORCID: [0000-0003-4660-4590](https://orcid.org/0000-0003-4660-4590)
- Department of Computer Science and Information Technology
- Faculty of Science, Naresuan University
- Phitsanulok 65000, Thailand
