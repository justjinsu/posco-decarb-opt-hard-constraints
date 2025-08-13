
import pandas as pd

REQUIRED_SHEETS = [
    "tech_routes","process_intensity","ef_scope1","fuel_prices",
    "carbon_price","free_allocation_linked","demand_path"
]

def load_parameters(xlsx_path: str, carbon_scenario: str):
    xls = pd.ExcelFile(xlsx_path)
    for s in REQUIRED_SHEETS:
        if s not in xls.sheet_names:
            raise ValueError(f"Required sheet missing: {s}")

    df_tr = pd.read_excel(xls, "tech_routes").set_index("route")
    df_pi = pd.read_excel(xls, "process_intensity").set_index("route")
    df_ef = pd.read_excel(xls, "ef_scope1").set_index("route")
    df_fp = pd.read_excel(xls, "fuel_prices").set_index("commodity")
    df_cp_all = pd.read_excel(xls, "carbon_price")
    df_fa = pd.read_excel(xls, "free_allocation_linked").set_index("year")
    df_dem = pd.read_excel(xls, "demand_path").set_index("year")

    # Carbon price scenario selection
    if carbon_scenario not in set(df_cp_all["scenario"]):
        raise ValueError(f"Scenario {carbon_scenario} not found in carbon_price sheet.")
    df_cp = df_cp_all[df_cp_all["scenario"]==carbon_scenario].set_index("year")

    years = sorted(df_cp.index.astype(int).tolist())
    t0 = min(years)

    # Helper to read commodity price in year y
    def price_fn(commodity: str, y: int) -> float:
        row = df_fp.loc[commodity]
        return float(row[str(y)])

    params = {
        "years": years,
        "t0": t0,
        "routes": df_tr.index.tolist(),
        "tech": df_tr.to_dict(orient="index"),
        "intensity": df_pi.to_dict(orient="index"),
        "ef_scope1": df_ef["tCO2_per_t"].to_dict(),
        "demand": df_dem["posco_crude_steel_Mt"].to_dict(),
        "carbon_price": df_cp["price_USD_per_tCO2"].to_dict(),
        "free_alloc": df_fa["free_alloc_MtCO2"].to_dict(),
        "price_fn": price_fn
    }
    return params
