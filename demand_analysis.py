"""
Additional analysis: Demand patterns and decarbonization implications
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

def analyze_demand_pattern():
    """Analyze the demand pattern and create supplementary figure"""
    
    # Load results
    df = pd.read_csv('outputs/series_HardConstraints.csv')
    
    # Set up the figure
    plt.rcParams.update({
        'font.size': 11,
        'font.family': 'serif',
        'figure.dpi': 300,
        'savefig.dpi': 300,
        'savefig.bbox': 'tight'
    })
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    
    # Panel A: Demand vs Production over time
    production_data = df[df['variable'] == 'total_production_Mt'].copy()
    bf_bof_prod = production_data[production_data['route'] == 'BF-BOF']
    
    years = bf_bof_prod['year'].values
    production = bf_bof_prod['value'].values
    demand = np.full_like(years, 35.682)  # Constant demand from 2023 baseline
    
    ax1.plot(years, demand, 'r--', linewidth=3, label='Steel Demand', marker='o', markersize=4)
    ax1.plot(years, production, 'b-', linewidth=2, label='BF-BOF Production', marker='s', markersize=4)
    ax1.fill_between(years, 0, production, alpha=0.3, color='blue', label='Production Capacity')
    
    ax1.set_xlabel('Year')
    ax1.set_ylabel('Steel (Mt/year)')
    ax1.set_title('(A) Demand vs Production: Constant 35.7 Mt/year (2025-2050)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(2025, 2050)
    
    # Panel B: Capacity utilization over time
    capacity_data = df[df['variable'] == 'capacity_Mt'].copy()
    bf_bof_capacity = capacity_data[capacity_data['route'] == 'BF-BOF']
    
    utilization = (production / bf_bof_capacity['value'].values) * 100
    
    ax2.plot(years, utilization, 'g-', linewidth=3, marker='o', markersize=4)
    ax2.axhline(y=90, color='orange', linestyle='--', alpha=0.7, label='Target Utilization (90%)')
    ax2.fill_between(years, 0, utilization, alpha=0.3, color='green')
    
    ax2.set_xlabel('Year')
    ax2.set_ylabel('Capacity Utilization (%)')
    ax2.set_title('(B) BF-BOF Capacity Utilization Rate')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(2025, 2050)
    ax2.set_ylim(80, 95)
    
    # Panel C: Technology investment comparison (hypothetical vs actual)
    technologies = ['BF-BOF', 'BF-BOF+CCUS', 'Scrap EAF', 'NG-DRI-EAF', 'H₂-DRI/HyREX']
    actual_investment = [39.65, 0, 0, 0, 0]  # Only BF-BOF has capacity
    hypothetical_mix = [20, 5, 5, 5, 5]  # Hypothetical diversified scenario
    
    x_pos = np.arange(len(technologies))
    width = 0.35
    
    bars1 = ax3.bar(x_pos - width/2, actual_investment, width, 
                    label='Actual (Hard Constraints)', color='darkred', alpha=0.7)
    bars2 = ax3.bar(x_pos + width/2, hypothetical_mix, width, 
                    label='Hypothetical Diversified', color='darkgreen', alpha=0.7)
    
    ax3.set_xlabel('Technology Route')
    ax3.set_ylabel('Installed Capacity (Mt/year)')
    ax3.set_title('(C) Technology Portfolio: Actual vs Hypothetical')
    ax3.set_xticks(x_pos)
    ax3.set_xticklabels(technologies, rotation=45, ha='right')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Panel D: Implications for decarbonization
    years_milestone = [2025, 2030, 2035, 2040, 2045, 2050]
    conventional_emissions = [35.7 * 2.0] * len(years_milestone)  # Assume 2.0 tCO2/t steel for BF-BOF
    carbon_neutral_target = [35.7 * 2.0 * (1 - (y-2025)/25 * 0.8) for y in years_milestone]  # 80% reduction by 2050
    
    ax4.plot(years_milestone, conventional_emissions, 'r-', linewidth=3, marker='o', 
             label='Actual Emissions\n(BF-BOF only)', markersize=6)
    ax4.plot(years_milestone, carbon_neutral_target, 'g--', linewidth=3, marker='s', 
             label='Carbon Neutral\nTarget Path', markersize=6)
    ax4.fill_between(years_milestone, conventional_emissions, carbon_neutral_target, 
                     alpha=0.3, color='red', label='Emissions Gap')
    
    ax4.set_xlabel('Year')
    ax4.set_ylabel('CO₂ Emissions (Mt/year)')
    ax4.set_title('(D) Decarbonization Gap Analysis')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    ax4.set_xlim(2025, 2050)
    
    plt.tight_layout()
    plt.savefig('outputs/Figure4_Demand_Analysis.png', dpi=300, bbox_inches='tight')
    plt.savefig('outputs/Figure4_Demand_Analysis.pdf', bbox_inches='tight')
    print("✓ Saved Figure 4: Demand and Decarbonization Analysis")
    
    return fig

def create_policy_implications_summary():
    """Create a summary of key policy implications"""
    
    implications = {
        'Finding': [
            'Demand Pattern',
            'Technology Choice', 
            'Investment Strategy',
            'Capacity Utilization',
            'Decarbonization Progress',
            'Policy Implication'
        ],
        'Result': [
            'Constant 35.7 Mt/year (2025-2050)',
            '100% BF-BOF (Conventional)',
            'No clean technology investment',
            '90% (efficient operation)',
            'Zero progress toward carbon neutrality',
            'Market failures require policy intervention'
        ],
        'Implication': [
            'Stable demand provides investment certainty',
            'Hard constraints make clean tech uneconomical',
            'Cost-optimization favors status quo',
            'Existing capacity sufficient for demand',
            'Emissions remain at 71.4 Mt CO₂/year',
            'Carbon pricing/subsidies needed for transition'
        ]
    }
    
    df_implications = pd.DataFrame(implications)
    
    print("\n" + "="*80)
    print("KEY FINDINGS: POSCO DECARBONIZATION UNDER HARD CONSTRAINTS")
    print("="*80)
    for i, row in df_implications.iterrows():
        print(f"{row['Finding']:.<25} {row['Result']}")
        print(f"{'Implication':.<25} {row['Implication']}")
        print()

if __name__ == "__main__":
    print("📊 Analyzing Demand Patterns and Decarbonization Implications")
    
    Path("outputs").mkdir(exist_ok=True)
    
    analyze_demand_pattern()
    create_policy_implications_summary()
    
    print("✅ Demand analysis complete!")
    print("📄 Additional academic figure generated: Figure4_Demand_Analysis.png/pdf")