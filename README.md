
# POSCO Decarbonization Optimization (Hard Constraints, Deterministic)

This repository contains a **deterministic** mixed-integer optimization (Pyomo) for POSCO's decarbonization under **Hard Constraints** (tight DR-grade metallics + conservative CCUS).

## Quick start

```bash
conda env create -f environment.yml
conda activate posco-steel-opt
python -m src.run --params data/posco_params_v0_1.xlsx --scenario HardConstraints --dry-run
# if you have a MILP solver (e.g., gurobi, cbc, glpk), then:
python -m src.run --params data/posco_params_v0_1.xlsx --scenario HardConstraints --solve --solver glpk
```

> If no solver is installed, `--dry-run` will only build the model and validate dimensions.

## Files
- `data/posco_params_v0_1.xlsx`: parameters (already populated).
- `src/io.py`: Excel loaders and scenario selection.
- `src/model.py`: Pyomo MIP with lumpy units, quality & lifetime constraints, Scope 2 accounting (unpriced).
- `src/run.py`: CLI wrapper.

## Outputs
- `outputs/summary_{scenario}.json`: KPIs (if solve runs).
- `outputs/series_{scenario}.csv`: time series (if solve runs).

## Notes
- Objective = discounted **CAPEX + OPEX + carbon cost (Scope 1, effective K-ETS)**.
- Scope 2 is reported and priced implicitly via electricity tariffs (pass-through), not in carbon term.
- H2 lifecycle emissions excluded in core; an appendix toggle exists to price them if desired.
