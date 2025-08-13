import pandas as pd
from src.io import load_params, select_scenario

sheets = load_params('data/posco_params_v0_1.xlsx')

# Check demand data and how it's processed
demand = sheets['demand_path'].copy()
print('Original demand data:')
print(demand[['year', 'posco_crude_steel_Mt']])

# Apply the same processing as the model
years = range(2025, 2051)
demand_filtered = demand[demand["year"].between(min(years), max(years))].copy()
print('\nFiltered demand (2025-2050):')
print(demand_filtered[['year', 'posco_crude_steel_Mt']])

# Apply forward fill like the model does
demand_filtered["posco_crude_steel_Mt"] = demand_filtered["posco_crude_steel_Mt"].fillna(method="ffill").fillna(0.0)
print('\nAfter forward fill:')
print(demand_filtered[['year', 'posco_crude_steel_Mt']])

# Check product shares
shares = sheets['product_shares']
print('\nProduct shares detailed:')
for col in shares.columns:
    if col != 'note':
        print(f'\n{col}:')
        print(shares[col].head(10))

# Check what 2025 looks like specifically
shares_2025 = shares[shares['year'] == 2025]
print('\n2025 product shares:')
print(shares_2025)