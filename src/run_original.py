import argparse, os, json
import pandas as pd
from pyomo.opt import SolverFactory
from .io_original import load_params, select_scenario
from .model_original import build_model
from pyomo.environ import value

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", required=True)
    ap.add_argument("--scenario", default="HardConstraints")
    ap.add_argument("--solve", action="store_true")
    ap.add_argument("--solver", default="glpk")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    sheets = load_params(args.params)
    row = select_scenario(sheets, args.scenario)
    m = build_model(sheets, row)

    if args.dry_run and not args.solve:
        print("Model built successfully (dry run).")
        return

    if args.solve:
        opt = SolverFactory(args.solver)
        if (opt is None) or (not opt.available()):
            print(f"Solver '{args.solver}' not available. Run with --dry-run or install a MILP solver.")
            return
        res = opt.solve(m, tee=True)
        print(res.solver.status, res.solver.termination_condition)

    # Export results
    os.makedirs("outputs", exist_ok=True)
    
    # Summary (works in dry-run too)
    summary = {
        "routes": list(m.R.data()),
        "years": [int(t) for t in m.T.data()],
        "objective": float(value(m.Obj)) if hasattr(m, "Obj") else None
    }
    with open("outputs/summary_{}.json".format(args.scenario), "w") as f:
        json.dump(summary, f, indent=2)
    print("Wrote outputs/summary_{}.json".format(args.scenario))
    
    # Detailed time series (only if solved)
    if args.solve and hasattr(m, "Obj"):
        results = []
        
        # Build decisions
        for r in m.R:
            for t in m.T:
                results.append({
                    'year': int(t),
                    'route': r,
                    'variable': 'build_decision',
                    'value': float(value(m.x[r,t]))
                })
        
        # Capacity levels
        for r in m.R:
            for t in m.T:
                results.append({
                    'year': int(t),
                    'route': r,
                    'variable': 'capacity_Mt',
                    'value': float(value(m.Kcap[r,t]))
                })
        
        # Production by route and product
        for r in m.R:
            for k in m.K:
                for t in m.T:
                    results.append({
                        'year': int(t),
                        'route': r,
                        'variable': f'production_{k}_Mt',
                        'value': float(value(m.Q[r,k,t]))
                    })
        
        # Total production by route
        for r in m.R:
            for t in m.T:
                total_prod = sum(float(value(m.Q[r,k,t])) for k in m.K)
                results.append({
                    'year': int(t),
                    'route': r,
                    'variable': 'total_production_Mt',
                    'value': total_prod
                })
        
        df_results = pd.DataFrame(results)
        df_results.to_csv("outputs/series_{}.csv".format(args.scenario), index=False)
        print("Wrote outputs/series_{}.csv".format(args.scenario))

if __name__ == "__main__":
    main()