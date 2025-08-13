
from pyomo.environ import (ConcreteModel, Var, Objective, Constraint, Set, Param, RangeSet,
                           NonNegativeReals, NonNegativeIntegers, minimize, value)

def build_model(p: dict, discount_rate: float = 0.05, utilization: float = 0.90,
                hydrogen_case: str = "baseline", ccus_capture_max: float = 0.80):
    """
    NPV objective = CAPEX + Fixed OM + variable OPEX (fuel, power, H2, materials) + ETS.
    Demand must be met each year. Lumpy capacity using integer build units.
    """
    m = ConcreteModel(name="POSCO Decarb — Updated")

    # Sets & Params
    m.T = RangeSet(p["years"][0], p["years"][-1])
    m.R = Set(initialize=p["routes"])
    m.t0 = Param(initialize=p["t0"])
    m.D = Param(m.T, initialize=lambda m,t: float(p["demand"][t]))

    unit_cap = {r: float(p["tech"][r]["unit_capacity_Mtpy"]) for r in p["routes"]}
    capex = {r: float(p["tech"][r]["capex_USD_per_tpy"]) for r in p["routes"]}
    fixom = {r: float(p["tech"][r]["fixed_opex_USD_per_tpy"]) for r in p["routes"]}
    m.unit_cap = Param(m.R, initialize=unit_cap)
    m.capex = Param(m.R, initialize=capex)
    m.fixom = Param(m.R, initialize=fixom)

    # Per-ton intensities
    keys = ["iron_ore_t_per_t","coking_coal_t_per_t","scrap_t_per_t","ng_GJ_per_t",
            "electricity_MWh_per_t","h2_kg_per_t","fluxes_t_per_t","alloys_USD_per_t"]
    intens = {r: {k: float(p["intensity"][r].get(k,0.0)) for k in keys} for r in p["routes"]}

    # Effective Scope1 EF (apply CCUS to CCUS routes)
    ef = {}
    for r in p["routes"]:
        v = float(p["ef_scope1"][r])
        if "CCUS" in r:
            v *= (1.0 - ccus_capture_max)
        ef[r] = v

    # Variables
    m.Q = Var(m.R, m.T, domain=NonNegativeReals)         # Production (Mt)
    m.K = Var(m.R, m.T, domain=NonNegativeReals)         # Capacity (Mtpy)
    m.Build = Var(m.R, m.T, domain=NonNegativeIntegers)  # Units built
    m.ETSpos = Var(m.T, domain=NonNegativeReals)         # (Scope1 - free_alloc)+

    # Initial capacity: all demand in first year is covered by BF-BOF
    y0 = p["years"][0]
    def init_cap(m, r):
        return p["demand"][y0] if r == "BF-BOF" else 0.0

    # Capacity balance
    def cap_balance(m, r, t):
        if t == y0:
            return m.K[r,t] == init_cap(m,r) + m.unit_cap[r]*m.Build[r,t]
        return m.K[r,t] == m.K[r,t-1] + m.unit_cap[r]*m.Build[r,t]
    m.CapacityBalance = Constraint(m.R, m.T, rule=cap_balance)

    # Utilization
    def prod_limit(m, r, t):
        return m.Q[r,t] <= utilization * m.K[r,t]
    m.ProdLimit = Constraint(m.R, m.T, rule=prod_limit)

    # Demand balance
    def demand(m, t):
        return sum(m.Q[r,t] for r in m.R) == m.D[t]
    m.Demand = Constraint(m.T, rule=demand)

    # ETS slack: ETSpos >= S1 - free_alloc
    def ets_balance(m, t):
        s1 = sum(ef[r] * m.Q[r,t] for r in m.R)      # MtCO2
        free = float(p["free_alloc"].get(t, 0.0))    # MtCO2
        return m.ETSpos[t] >= s1 - free
    m.ETSBalance = Constraint(m.T, rule=ets_balance)

    # Helper to get price
    def price(commodity, year):
        return p["price_fn"](commodity, year)

    # Objective
    def obj_rule(m):
        total = 0.0
        for t in m.T:
            disc = 1.0 / ((1.0 + discount_rate) ** (t - value(m.t0)))
            # CAPEX
            capex_t = sum(m.Build[r,t] * m.unit_cap[r] * m.capex[r] * 1e6 for r in m.R)
            # Fixed O&M
            fix_t = sum(m.K[r,t] * m.fixom[r] * 1e6 for r in m.R)
            # Variable OPEX
            var_t = 0.0
            for r in m.R:
                ore  = intens[r]["iron_ore_t_per_t"]      * price("iron_ore_USD_per_t", t)
                coal = intens[r]["coking_coal_t_per_t"]   * price("coking_coal_USD_per_t", t)
                scrap= intens[r]["scrap_t_per_t"]         * price("scrap_USD_per_t", t)
                ng   = intens[r]["ng_GJ_per_t"]           * price("ng_USD_per_GJ", t)
                elec = intens[r]["electricity_MWh_per_t"] * price("electricity_USD_per_MWh", t)
                if hydrogen_case == "optimistic":
                    h2 = intens[r]["h2_kg_per_t"] * price("hydrogen_USD_per_kg_optimistic", t)
                else:
                    h2 = intens[r]["h2_kg_per_t"] * price("hydrogen_USD_per_kg_baseline", t)
                flux = intens[r]["fluxes_t_per_t"]        * price("fluxes_USD_per_t", t)
                alloys = intens[r]["alloys_USD_per_t"]
                usd_per_t = ore+coal+scrap+ng+elec+h2+flux+alloys
                var_t += m.Q[r,t] * usd_per_t * 1e6
            # ETS cost
            ets_t = float(p["carbon_price"][t]) * m.ETSpos[t] * 1e6
            total += disc * (capex_t + fix_t + var_t + ets_t)
        return total
    m.Obj = Objective(rule=obj_rule, sense=minimize)

    return m
