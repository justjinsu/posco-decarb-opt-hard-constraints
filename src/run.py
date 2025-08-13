
import argparse, os, json
from pyomo.opt import SolverFactory, TerminationCondition
from pyomo.environ import value

from . import io as local_io
from .model import build_model
from .export import export_timeseries

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", required=True, help="Path to consolidated Excel")
    ap.add_argument("--carbon_scenario", default="NGFS_NetZero2050",
                    help="NGFS_NetZero2050 | NGFS_Below2C | NGFS_NDCs | NGFS_CurrentPolicies")
    ap.add_argument("--discount", type=float, default=0.05)
    ap.add_argument("--util", type=float, default=0.90)
    ap.add_argument("--hydrogen_case", choices=["baseline","optimistic"], default="baseline")
    ap.add_argument("--solver", default="glpk")
    ap.add_argument("--solve", action="store_true")
    ap.add_argument("--outdir", default="outputs")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    p = local_io.load_parameters(args.params, args.carbon_scenario)
    m = build_model(p, discount_rate=args.discount, utilization=args.util,
                    hydrogen_case=args.hydrogen_case)

    if args.solve:
        opt = SolverFactory(args.solver)
        res = opt.solve(m, tee=True)
        tc = res.solver.termination_condition
        if tc not in (TerminationCondition.optimal, TerminationCondition.feasible):
            print("WARNING: solver termination =", tc)

    # Export
    csv_path = os.path.join(args.outdir, f"series_{args.carbon_scenario}.csv")
    export_timeseries(m, p, csv_path)

    # Summary JSON (objective, cumulative emissions/production)
    import pandas as pd
    df = pd.read_csv(csv_path)
    total_emis = df["scope1_MtCO2"].sum()
    prod_cols = [c for c in df.columns if c.startswith("Q_")]
    total_prod = df[prod_cols].sum().sum()
    summary = {
        "scenario": args.carbon_scenario,
        "discount_rate": args.discount,
        "objective_USD": float(value(m.Obj)),
        "cumulative_scope1_MtCO2": float(total_emis),
        "total_production_Mt": float(total_prod)
    }
    with open(os.path.join(args.outdir, f"summary_{args.carbon_scenario}.json"), "w") as f:
        json.dump(summary, f, indent=2)

    print("Wrote:", csv_path)

if __name__ == "__main__":
    main()
