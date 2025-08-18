
import pandas as pd
from pyomo.environ import value

def export_detailed_timeseries(m, p, path_csv: str, discount_rate: float = 0.05, utilization: float = 0.90, hydrogen_case: str = "baseline"):
    """
    Export detailed annual results to CSV with comprehensive cost breakdown.
    
    Args:
        m: Solved Pyomo model
        p: Parameters dictionary
        path_csv: Output CSV file path
        discount_rate: Discount rate used in model
        utilization: Utilization rate used in model
        hydrogen_case: Hydrogen case used in model
    """
    years = p["years"]
    routes = p["routes"]
    t0 = p["t0"]
    
    # Calculate effective emission factors (with CCUS reduction)
    ef = {}
    for r in routes:
        v = float(p["ef_scope1"][r])
        if "CCUS" in r:
            v *= (1.0 - 0.80)  # keep consistent with model
        ef[r] = v
    
    # Helper to get price
    def price(commodity, year):
        return p["price_fn"](commodity, year)
    
    # Per-ton intensities for cost calculation
    keys = ["iron_ore_t_per_t","coking_coal_t_per_t","scrap_t_per_t","ng_GJ_per_t",
            "electricity_MWh_per_t","h2_kg_per_t","fluxes_t_per_t","alloys_USD_per_t"]
    intens = {r: {k: float(p["intensity"][r].get(k,0.0)) for k in keys} for r in routes}
    
    rows = []
    for t in years:
        row = {"year": t}
        discount_factor = 1.0 / ((1.0 + discount_rate) ** (t - t0))
        
        # === EMISSIONS AND ETS ===
        scope1_emissions = sum(ef[r] * float(value(m.Q[r,t])) for r in routes)  # MtCO2
        row["scope1_emissions_MtCO2"] = scope1_emissions
        row["scope2_emissions_MtCO2"] = 0.0  # Not modeled in this version
        row["free_allocation_MtCO2"] = float(p["free_alloc"].get(t, 0.0))
        row["carbon_price_USD_per_tCO2"] = float(p["carbon_price"][t])
        
        # ETS cost calculation
        ets_positive_mt = float(value(m.ETSpos[t]))  # MtCO2
        ets_cost = ets_positive_mt * row["carbon_price_USD_per_tCO2"] * 1e6  # USD
        row["ets_cost_USD"] = ets_cost
        row["ets_positive_MtCO2"] = ets_positive_mt
        row["ets_cost_discounted_USD"] = ets_cost * discount_factor
        
        # Independent ETS calculation for validation
        net_emissions = max(0, scope1_emissions - row["free_allocation_MtCO2"])
        ets_cost_calc = net_emissions * 1e6 * row["carbon_price_USD_per_tCO2"]
        row["ets_cost_calculated_USD"] = ets_cost_calc
        row["ets_validation_match"] = abs(ets_cost - ets_cost_calc) < 1e3
        
        # === COST BREAKDOWN ===
        # CAPEX (undiscounted and discounted)
        capex_year = sum(float(value(m.Build[r,t])) * float(p["tech"][r]["unit_capacity_Mtpy"]) * 
                        float(p["tech"][r]["capex_USD_per_tpy"]) * 1e6 for r in routes)
        row["capex_USD"] = capex_year
        row["capex_discounted_USD"] = capex_year * discount_factor
        
        # Fixed O&M
        fixed_om_year = sum(float(value(m.K[r,t])) * float(p["tech"][r]["fixed_opex_USD_per_tpy"]) * 1e6 for r in routes)
        row["fixed_om_USD"] = fixed_om_year
        row["fixed_om_discounted_USD"] = fixed_om_year * discount_factor
        
        # Variable OPEX
        var_opex_year = 0.0
        for r in routes:
            production_mt = float(value(m.Q[r,t])) * 1e6  # Convert Mt to t
            ore_cost = intens[r]["iron_ore_t_per_t"] * price("iron_ore_USD_per_t", t)
            coal_cost = intens[r]["coking_coal_t_per_t"] * price("coking_coal_USD_per_t", t)
            scrap_cost = intens[r]["scrap_t_per_t"] * price("scrap_USD_per_t", t)
            ng_cost = intens[r]["ng_GJ_per_t"] * price("ng_USD_per_GJ", t)
            elec_cost = intens[r]["electricity_MWh_per_t"] * price("electricity_USD_per_MWh", t)
            if hydrogen_case == "optimistic":
                h2_cost = intens[r]["h2_kg_per_t"] * price("hydrogen_USD_per_kg_optimistic", t)
            else:
                h2_cost = intens[r]["h2_kg_per_t"] * price("hydrogen_USD_per_kg_baseline", t)
            flux_cost = intens[r]["fluxes_t_per_t"] * price("fluxes_USD_per_t", t)
            alloys_cost = intens[r]["alloys_USD_per_t"]
            
            usd_per_t = ore_cost + coal_cost + scrap_cost + ng_cost + elec_cost + h2_cost + flux_cost + alloys_cost
            var_opex_year += production_mt * usd_per_t
        
        row["opex_USD"] = var_opex_year
        row["opex_discounted_USD"] = var_opex_year * discount_factor
        
        # Total system cost (undiscounted and discounted)
        row["total_cost_USD"] = capex_year + fixed_om_year + var_opex_year + ets_cost
        row["total_cost_discounted_USD"] = row["total_cost_USD"] * discount_factor
        
        # === PRODUCTION BY TECHNOLOGY ROUTE ===
        for r in routes:
            row[f"Q_{r}_Mt"] = float(value(m.Q[r,t]))
        
        # Total production (match naming from working example)
        row["total_steel_Mt"] = sum(float(value(m.Q[r,t])) for r in routes)
        row["total_production_Mt"] = row["total_steel_Mt"]  # Also keep this for compatibility
        
        # === CAPACITY ===
        for r in routes:
            row[f"K_{r}_Mtpy"] = float(value(m.K[r,t]))
            row[f"Build_{r}_units"] = float(value(m.Build[r,t]))
        
        # === DEMAND SATISFACTION ===
        row["demand_Mt"] = float(p["demand"][t])
        row["demand_satisfied"] = abs(row["total_production_Mt"] - row["demand_Mt"]) < 1e-6
        
        rows.append(row)
    
    # Calculate cumulative values
    cumulative_emissions = sum(row["scope1_emissions_MtCO2"] for row in rows)
    cumulative_production = sum(row["total_production_Mt"] for row in rows)
    
    # Add cumulative columns to each row (for compatibility with validation scripts)
    for i, row in enumerate(rows):
        row["cumulative_emissions_MtCO2"] = sum(rows[j]["scope1_emissions_MtCO2"] for j in range(i+1))
        row["cumulative_production_Mt"] = sum(rows[j]["total_production_Mt"] for j in range(i+1))
    
    pd.DataFrame(rows).to_csv(path_csv, index=False)

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
