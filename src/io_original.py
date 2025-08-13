import pandas as pd

def load_params(xlsx_path):
    """Load all sheets from Excel parameter file"""
    return pd.read_excel(xlsx_path, sheet_name=None)

def select_scenario(sheets, scenario_name):
    """Select scenario row from scenario matrix"""
    scenario_matrix = sheets["scenario_matrix"]
    row = scenario_matrix[scenario_matrix["scenario_name"] == scenario_name]
    if row.empty:
        raise ValueError(f"Scenario '{scenario_name}' not found")
    return row.iloc[0]