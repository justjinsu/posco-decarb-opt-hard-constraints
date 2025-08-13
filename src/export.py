
import pandas as pd
from pyomo.environ import value

def export_timeseries(m, p, path_csv: str):
    years = p["years"]
    routes = p["routes"]

    ef = {}
    for r in routes:
        v = float(p["ef_scope1"][r])
        if "CCUS" in r:
            v *= (1.0 - 0.80)  # keep consistent with model
        ef[r] = v

    rows = []
    for t in years:
        row = {"year": t}
        # production (Mt)
        for r in routes:
            row[f"Q_{r}_Mt"] = float(value(m.Q[r,t]))
        # scope1 emissions (MtCO2)
        row["scope1_MtCO2"] = sum(ef[r]*float(value(m.Q[r,t])) for r in routes)
        row["free_alloc_MtCO2"] = float(p["free_alloc"].get(t, 0.0))
        row["carbon_price_USDpt"] = float(p["carbon_price"][t])
        rows.append(row)

    pd.DataFrame(rows).to_csv(path_csv, index=False)
