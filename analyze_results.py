import pandas as pd

df = pd.read_csv('outputs/series_HardConstraints.csv')
print('Total rows:', len(df))
print('\nNon-zero values:')
non_zero = df[df['value'] != 0]
if len(non_zero) > 0:
    print(non_zero)
else:
    print('All values are zero!')

print('\nSummary by variable type:')
print(df.groupby('variable')['value'].sum())

print('\nUnique variables:')
print(df['variable'].unique())

# Check demand data
print('\n=== Checking data inputs ===')
try:
    import pandas as pd
    from src.io import load_params, select_scenario
    
    sheets = load_params('data/posco_params_v0_1.xlsx')
    print('Available sheets:', list(sheets.keys()))
    
    # Check demand
    if 'demand_path' in sheets:
        demand = sheets['demand_path']
        print('\nDemand data:')
        print(demand)
    
    if 'product_shares' in sheets:
        shares = sheets['product_shares']  
        print('\nProduct shares:')
        print(shares)
        
except Exception as e:
    print(f'Error loading data: {e}')