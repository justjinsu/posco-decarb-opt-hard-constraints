"""
Simplified POSCO decarbonization model for testing and validation.
Focuses on core functionality while ensuring feasibility.
"""

from pyomo.environ import *
from typing import Dict, List, Optional
import logging
from .io import *

logger = logging.getLogger(__name__)


def build_simple_model(sheets: Dict[str, pd.DataFrame], 
                      years: Optional[List[int]] = None, 
                      discount_rate: float = 0.05) -> ConcreteModel:
    """
    Build simplified POSCO decarbonization model.
    
    Args:
        sheets: Excel worksheets dictionary
        years: Model years (default: 2025-2050)
        discount_rate: NPV discount rate
    
    Returns:
        Pyomo ConcreteModel instance
    """
    
    # Validate input data
    validate_required_sheets(sheets)
    
    if years is None:
        years = get_years(sheets)
    
    logger.info(f"Building simple model for years {min(years)}-{max(years)}")
    
    m = ConcreteModel(name="POSCO_Simple")
    
    # =============================================================================
    # SETS AND INDICES
    # =============================================================================
    
    m.T = RangeSet(min(years), max(years), doc="Model years")
    m.R = Set(initialize=["BF-BOF", "Scrap EAF", "NG-DRI-EAF", "H2-DRI/HyREX"], 
              doc="Technology routes")
    m.K = Set(initialize=["flat_auto_exposed", "flat_other", "long"], 
              doc="Product classes")
    
    # =============================================================================
    # PARAMETERS
    # =============================================================================
    
    # Load parameter data
    D_dict = get_demand_series(sheets, years)
    routes_meta = get_routes_meta(sheets)
    emission_factors = get_emission_factors(sheets)
    carbon_prices, free_alloc = get_carbon_price_and_free_alloc(sheets, years)
    discount_factors_dict = discount_factors(years, rate=discount_rate)
    
    # Convert to Pyomo parameters
    m.D = Param(m.T, m.K, initialize=lambda m, t, k: D_dict[(t, k)], 
                within=NonNegativeReals, doc="Steel demand by product class [Mt]")
    
    # Technology parameters - use safe defaults for missing data
    safe_emission_factors = {}
    for r in m.R:
        if r in emission_factors:
            safe_emission_factors[r] = emission_factors[r]
        else:
            # Use reasonable defaults based on technology type
            if "BF" in r:
                safe_emission_factors[r] = 2.0  # tCO2/t steel
            elif "EAF" in r:
                safe_emission_factors[r] = 0.5  # tCO2/t steel
            else:
                safe_emission_factors[r] = 1.0  # tCO2/t steel
    
    m.EmissionFactor = Param(m.R, initialize=safe_emission_factors, within=NonNegativeReals,
                           doc="Scope 1 emission factor [tCO2/t steel]")
    
    # Cost parameters - simplified
    cost_per_tonne = {"BF-BOF": 500, "Scrap EAF": 400, "NG-DRI-EAF": 600, "H2-DRI/HyREX": 800}
    m.CostPerTonne = Param(m.R, initialize=cost_per_tonne, within=NonNegativeReals,
                          doc="Production cost [USD/t steel]")
    
    # Time series parameters
    safe_carbon_prices = {}
    for t in m.T:
        if t in carbon_prices and carbon_prices[t] > 0:
            safe_carbon_prices[t] = carbon_prices[t]
        else:
            # Use reasonable default carbon price trajectory
            safe_carbon_prices[t] = max(50.0 * (t - 2024), 0.0)  # $50/tCO2 starting 2025
    
    m.CarbonPrice = Param(m.T, initialize=safe_carbon_prices, within=NonNegativeReals,
                         doc="Carbon price [USD/tCO2]")
    m.DiscountFactor = Param(m.T, initialize=discount_factors_dict, within=PositiveReals,
                           doc="NPV discount factors")
    
    # =============================================================================
    # DECISION VARIABLES
    # =============================================================================
    
    # Production variables
    m.Q = Var(m.R, m.K, m.T, domain=NonNegativeReals, 
             doc="Production by route, product, year [Mt steel]")
    
    # Emissions variables
    m.TotalEmissions = Var(m.T, domain=NonNegativeReals, doc="Total emissions [MtCO2]")
    
    # Cost variables
    m.ProductionCost = Var(m.T, domain=NonNegativeReals, doc="Production cost [USD]")
    m.CarbonCost = Var(m.T, domain=NonNegativeReals, doc="Carbon cost [USD]")
    
    # =============================================================================
    # CONSTRAINTS
    # =============================================================================
    
    def demand_balance_rule(m, k, t):
        """Meet steel demand by product class."""
        total_production = sum(m.Q[r, k, t] for r in m.R)
        return total_production >= m.D[t, k]
    
    m.DemandBalance = Constraint(m.K, m.T, rule=demand_balance_rule,
                               doc="Meet demand by product class")
    
    def emissions_calculation_rule(m, t):
        """Calculate total emissions."""
        total_emissions = sum(m.EmissionFactor[r] * sum(m.Q[r, k, t] for k in m.K) 
                             for r in m.R)
        return m.TotalEmissions[t] == total_emissions
    
    m.EmissionsCalculation = Constraint(m.T, rule=emissions_calculation_rule,
                                      doc="Calculate total emissions")
    
    def production_cost_rule(m, t):
        """Calculate production costs."""
        cost = sum(m.CostPerTonne[r] * sum(m.Q[r, k, t] for k in m.K) for r in m.R)
        return m.ProductionCost[t] == cost
    
    m.ProductionCostCalculation = Constraint(m.T, rule=production_cost_rule,
                                           doc="Calculate production costs")
    
    def carbon_cost_rule(m, t):
        """Calculate carbon costs."""
        return m.CarbonCost[t] == m.CarbonPrice[t] * m.TotalEmissions[t]
    
    m.CarbonCostCalculation = Constraint(m.T, rule=carbon_cost_rule,
                                       doc="Calculate carbon costs")
    
    # =============================================================================
    # OBJECTIVE FUNCTION
    # =============================================================================
    
    def objective_rule(m):
        """Minimize discounted NPV of total costs."""
        total_cost = sum(m.DiscountFactor[t] * (m.ProductionCost[t] + m.CarbonCost[t])
                        for t in m.T)
        return total_cost
    
    m.TotalCost = Objective(rule=objective_rule, sense=minimize, 
                           doc="Minimize discounted total cost")
    
    logger.info("Simple model building completed successfully")
    
    return m


def print_simple_model_summary(model: ConcreteModel) -> None:
    """Print a summary of simple model size and key parameters."""
    print("\\n" + "="*60)
    print("POSCO SIMPLE MODEL SUMMARY")
    print("="*60)
    
    # Count variables and constraints
    n_vars = sum(len(var.index_set()) if var.is_indexed() else 1 
                for var in model.component_objects(Var))
    n_cons = sum(len(con.index_set()) if con.is_indexed() else 1 
                for con in model.component_objects(Constraint))
    
    print(f"Variables: {n_vars:,}")
    print(f"Constraints: {n_cons:,}")
    print(f"Years: {model.T.first()}-{model.T.last()}")
    print(f"Routes: {len(model.R)}")
    print(f"Product classes: {len(model.K)}")
    
    # Key parameters
    print(f"\\nKey Parameters:")
    print(f"  Total steel demand (2025): {sum(value(model.D[2025, k]) for k in model.K):.1f} Mt")
    print(f"  Carbon price (2030): ${value(model.CarbonPrice[2030]):.0f}/tCO2")
    print("="*60)