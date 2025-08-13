import pandas as pd
from src.io import load_params, select_scenario

sheets = load_params('data/posco_params_v0_1.xlsx')

# Check demand data in detail
demand = sheets['demand_path']
print('Demand data columns:', demand.columns.tolist())
print('\nDemand data:')
print(demand[['year', 'posco_crude_steel_Mt']])

# Check if there are any actual values
print('\nActual steel demand values:')
print(demand['posco_crude_steel_Mt'].describe())

# Check product shares
shares = sheets['product_shares']
print('\nProduct shares columns:', shares.columns.tolist())  
print('\nProduct shares data:')
print(shares)

# Check scenario selection
print('\n=== Scenario Matrix ===')
scenario_matrix = sheets['scenario_matrix']
print(scenario_matrix)