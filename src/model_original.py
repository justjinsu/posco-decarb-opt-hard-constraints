from pyomo.environ import (ConcreteModel, Set, Var, Param, RangeSet, NonNegativeReals, Binary, Objective, Constraint, minimize, value)
import pandas as pd
import numpy as np

def build_model(sheets, scenario_row, years=range(2025,2051)):
    m = ConcreteModel()
    m.T = RangeSet(min(years), max(years))
    # Routes and simple data (placeholder sizes; detailed params read from sheets)
    m.R = Set(initialize=["BF-BOF","BF-BOF+CCUS","Scrap EAF","NG-DRI-EAF","H2-DRI/HyREX"])
    m.K = Set(initialize=["flat_auto_exposed","flat_other","long"])

    # Demand (placeholder: we use 'demand_path' + 'product_shares')
    dem = sheets["demand_path"].copy()
    
    # Get baseline demand from 2023 if available
    baseline_demand = None
    baseline_row = dem[dem["year"] == 2023]
    if not baseline_row.empty and pd.notna(baseline_row.iloc[0]["posco_crude_steel_Mt"]):
        baseline_demand = float(baseline_row.iloc[0]["posco_crude_steel_Mt"])
    
    dem = dem[dem["year"].between(min(years), max(years))].copy()
    # fill forward crude steel from growth rule later; use 2023 baseline if available
    dem["posco_crude_steel_Mt"] = dem["posco_crude_steel_Mt"].fillna(method="ffill").fillna(baseline_demand if baseline_demand else 0.0)

    shares = sheets["product_shares"].copy()
    shares = shares[shares["year"].between(min(years), max(years))]
    shares = shares.set_index("year")
    D = {}
    for y in years:
        total = float(dem.loc[dem["year"]==y,"posco_crude_steel_Mt"].fillna(0.0).values[0])
        if total==0.0:
            # conservative placeholder: keep 2025 value if zero
            total = float(dem.loc[dem["year"]==min(years),"posco_crude_steel_Mt"].fillna(0.0).values[0])
        s = shares.loc[y]
        D[(y,"flat_auto_exposed")] = total*float(s["flat_automotive_exposed_share"])
        D[(y,"flat_other")] = total*float(s["flat_other_share"])
        D[(y,"long")] = total*float(s["long_share"])
    m.D = Param(m.T, m.K, initialize=lambda m,t,k: D[(t,k)], mutable=True)

    # Capacity increments per build decision (unit sizes)
    tr = sheets["tech_routes"].copy().set_index("route")
    cap_add = tr["unit_capacity_Mtpy"].to_dict()

    # Decision vars
    m.x = Var(m.R, m.T, domain=Binary)   # build (aggregated over plants for now)
    m.Kcap = Var(m.R, m.T, domain=NonNegativeReals)  # capacity Mt/y
    m.Q = Var(m.R, m.K, m.T, domain=NonNegativeReals)  # production by route and product class Mt

    # Simple capacity evolution with aggregated builds (can expand to plant-level later)
    def cap_evo_rule(m,r,t):
        if t==min(m.T):
            return m.Kcap[r,t] >= cap_add.get(r,1.0)*m.x[r,t]
        return m.Kcap[r,t] >= m.Kcap[r,t-1] + cap_add.get(r,1.0)*m.x[r,t]
    m.CapacityEvo = Constraint(m.R, m.T, rule=cap_evo_rule)

    # Utilization (placeholder u=0.9)
    u = {r:0.9 for r in m.R}
    def util_rule(m,t):
        return sum(m.Q[r,k,t] for r in m.R for k in m.K) <= sum(u[r]*m.Kcap[r,t] for r in m.R)
    m.Util = Constraint(m.T, rule=util_rule)

    # Demand balance per product class
    def demand_rule(m,k,t):
        return sum(m.Q[r,k,t] for r in m.R) >= m.D[t,k]
    m.Demand = Constraint(m.K, m.T, rule=demand_rule)

    # Quality constraint (auto exposed): if EAF is used, require DRI/HBI content >= 50% and scrap <= 50%.
    # Here we approximate by limiting EAF contribution to auto exposed by DR-grade availability fraction alpha_t.
    drdf = None
    if "dr_grade_supply_conservative" in sheets:
        drdf = sheets["dr_grade_supply_conservative"].copy()
        drdf.index = drdf["year"]
        drdict = drdf["DR_grade_Mt_DRIeq_conservative"].to_dict()
    else:
        drdf = sheets["dr_grade_supply"].copy()
        drdf.index = drdf["year"]
        drdict = drdf.iloc[:,1].to_dict()  # assumes second column is the series

    # Define an exogenous cap on EAF/hydrogen routes serving auto-exposed = DR-grade supply
    def auto_cap_rule(m,t):
        # Only EAF and H2/NG DRI routes allowed to serve auto exposed up to dr-grade availability
        allowed = ["Scrap EAF","NG-DRI-EAF","H2-DRI/HyREX"]
        return sum(m.Q[r,"flat_auto_exposed",t] for r in allowed) <= drdict.get(t,0.0)
    m.AutoExposedCap = Constraint(m.T, rule=auto_cap_rule)

    # Irreversibility / min lifetime (placeholder via cumulative builds monotonicity)
    def monotone_rule(m,r,t):
        if t==min(m.T): 
            return m.x[r,t] >= 0
        return m.x[r,t] >= m.x[r,t-1]  # proxy to avoid build-then-retire in toy model
    m.Monotone = Constraint(m.R, m.T, rule=monotone_rule)

    # Objective (placeholder cost weights)
    # NOTE: Real objective will read CAPEX/OPEX/Carbon cost; here we put simple penalties to make the model testable.
    capex = {r: tr.loc[r,"capex_USD_per_tpy"] if pd.notna(tr.loc[r,"capex_USD_per_tpy"]) else 100.0e3 for r in m.R}
    opex = {r: tr.loc[r,"variable_opex_USD_per_t"] if pd.notna(tr.loc[r,"variable_opex_USD_per_t"]) else 150.0 for r in m.R}

    def obj_rule(m):
        return sum(capex[r]*m.x[r,t] for r in m.R for t in m.T) + sum(opex[r]*m.Q[r,k,t] for r in m.R for k in m.K for t in m.T)
    m.Obj = Objective(rule=obj_rule, sense=minimize)
    return m