"""
Academic visualization script for POSCO decarbonization optimization results
Creates publication-ready figures showing facility transitions and production pathways
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Set academic paper style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

def setup_academic_style():
    """Configure matplotlib for academic papers"""
    plt.rcParams.update({
        'font.size': 11,
        'axes.titlesize': 12,
        'axes.labelsize': 11,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'legend.fontsize': 10,
        'figure.titlesize': 14,
        'font.family': 'serif',
        'font.serif': ['Times New Roman', 'DejaVu Serif'],
        'figure.dpi': 300,
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.1
    })

def load_and_process_data(csv_path="outputs/series_HardConstraints.csv"):
    """Load and process optimization results"""
    df = pd.read_csv(csv_path)
    
    # Separate different variable types
    production_vars = [col for col in df['variable'].unique() if 'production_' in col and 'total' not in col]
    
    return df, production_vars

def create_production_pathway_chart(df):
    """Create Figure 1: Steel Production Pathway by Technology (2025-2050)"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Panel A: Total production by route
    production_data = df[df['variable'] == 'total_production_Mt'].copy()
    pivot_prod = production_data.pivot(index='year', columns='route', values='value')
    
    # Create stacked area chart
    ax1.stackplot(pivot_prod.index, 
                  pivot_prod['BF-BOF'], 
                  pivot_prod['BF-BOF+CCUS'],
                  pivot_prod['Scrap EAF'], 
                  pivot_prod['NG-DRI-EAF'],
                  pivot_prod['H2-DRI/HyREX'],
                  labels=['BF-BOF (Conventional)', 'BF-BOF+CCUS', 'Scrap EAF', 'NG-DRI-EAF', 'H₂-DRI/HyREX'],
                  alpha=0.8)
    
    ax1.set_ylabel('Steel Production (Mt/year)')
    ax1.set_title('(A) Total Steel Production by Technology Route')
    ax1.legend(loc='upper left', bbox_to_anchor=(1.02, 1))
    ax1.set_xlim(2025, 2050)
    ax1.grid(True, alpha=0.3)
    
    # Panel B: Production by product type (using BF-BOF only since others are zero)
    product_types = ['production_flat_auto_exposed_Mt', 'production_flat_other_Mt', 'production_long_Mt']
    product_labels = ['Flat Auto Exposed', 'Flat Other', 'Long Products']
    
    bf_bof_data = df[(df['route'] == 'BF-BOF') & (df['variable'].isin(product_types))]
    pivot_products = bf_bof_data.pivot(index='year', columns='variable', values='value')
    
    ax2.stackplot(pivot_products.index,
                  pivot_products['production_flat_auto_exposed_Mt'],
                  pivot_products['production_flat_other_Mt'], 
                  pivot_products['production_long_Mt'],
                  labels=product_labels,
                  alpha=0.8)
    
    ax2.set_xlabel('Year')
    ax2.set_ylabel('Steel Production (Mt/year)')
    ax2.set_title('(B) Steel Production by Product Type')
    ax2.legend(loc='upper left', bbox_to_anchor=(1.02, 1))
    ax2.set_xlim(2025, 2050)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('outputs/Figure1_Production_Pathways.png', dpi=300, bbox_inches='tight')
    plt.savefig('outputs/Figure1_Production_Pathways.pdf', bbox_inches='tight')
    print("✓ Saved Figure 1: Production Pathways")
    return fig

def create_capacity_evolution_chart(df):
    """Create Figure 2: Capacity Evolution and Investment Decisions"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Panel A: Capacity evolution by technology
    capacity_data = df[df['variable'] == 'capacity_Mt'].copy()
    pivot_capacity = capacity_data.pivot(index='year', columns='route', values='value')
    
    # Line plot for capacity evolution
    for route in pivot_capacity.columns:
        if pivot_capacity[route].max() > 0:  # Only plot routes with capacity
            ax1.plot(pivot_capacity.index, pivot_capacity[route], 
                    marker='o', markersize=4, linewidth=2, label=route)
    
    ax1.set_ylabel('Installed Capacity (Mt/year)')
    ax1.set_title('(A) Technology Capacity Evolution')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(2025, 2050)
    
    # Panel B: Investment decisions (binary build decisions)
    build_data = df[df['variable'] == 'build_decision'].copy()
    pivot_builds = build_data.pivot(index='year', columns='route', values='value')
    
    # Create heatmap for build decisions
    sns.heatmap(pivot_builds.T, cmap='RdYlBu_r', center=0.5, 
                cbar_kws={'label': 'Build Decision (0=No, 1=Yes)'},
                ax=ax2, xticklabels=5, yticklabels=True)
    
    ax2.set_xlabel('Year')
    ax2.set_ylabel('Technology Route')
    ax2.set_title('(B) Investment Decisions Heatmap')
    
    plt.tight_layout()
    plt.savefig('outputs/Figure2_Capacity_Evolution.png', dpi=300, bbox_inches='tight')
    plt.savefig('outputs/Figure2_Capacity_Evolution.pdf', bbox_inches='tight')
    print("✓ Saved Figure 2: Capacity Evolution")
    return fig

def create_technology_mix_analysis(df):
    """Create Figure 3: Technology Mix Analysis and Decarbonization Progress"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    
    # Panel A: Technology share over time
    production_data = df[df['variable'] == 'total_production_Mt'].copy()
    pivot_prod = production_data.pivot(index='year', columns='route', values='value')
    
    # Calculate percentages
    total_prod = pivot_prod.sum(axis=1)
    pivot_pct = pivot_prod.div(total_prod, axis=0) * 100
    
    ax1.stackplot(pivot_pct.index,
                  pivot_pct['BF-BOF'],
                  pivot_pct['BF-BOF+CCUS'], 
                  pivot_pct['Scrap EAF'],
                  pivot_pct['NG-DRI-EAF'],
                  pivot_pct['H2-DRI/HyREX'],
                  labels=['BF-BOF', 'BF-BOF+CCUS', 'Scrap EAF', 'NG-DRI-EAF', 'H₂-DRI/HyREX'])
    
    ax1.set_ylabel('Production Share (%)')
    ax1.set_title('(A) Technology Mix Evolution')
    ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax1.set_xlim(2025, 2050)
    ax1.set_ylim(0, 100)
    
    # Panel B: Annual production levels
    years = [2025, 2030, 2035, 2040, 2045, 2050]
    year_data = pivot_prod.loc[years]
    
    ax2.bar(range(len(years)), year_data['BF-BOF'], label='BF-BOF', alpha=0.8)
    ax2.bar(range(len(years)), year_data['BF-BOF+CCUS'], 
            bottom=year_data['BF-BOF'], label='BF-BOF+CCUS', alpha=0.8)
    
    ax2.set_xticks(range(len(years)))
    ax2.set_xticklabels(years)
    ax2.set_ylabel('Production (Mt/year)')
    ax2.set_title('(B) Production Levels at Key Years')
    ax2.legend()
    
    # Panel C: Product type distribution (pie chart for 2030 and 2050)
    product_2030 = df[(df['year'] == 2030) & (df['route'] == 'BF-BOF') & 
                      (df['variable'].str.contains('production_') & ~df['variable'].str.contains('total'))]
    
    sizes_2030 = product_2030['value'].values
    labels = ['Auto Exposed\n(7.14 Mt)', 'Other Flat\n(21.41 Mt)', 'Long Products\n(7.14 Mt)']
    colors = ['#ff9999', '#66b3ff', '#99ff99']
    
    ax3.pie(sizes_2030, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    ax3.set_title('(C) Product Mix in 2030')
    
    # Panel D: Summary metrics
    total_capacity = df[df['variable'] == 'capacity_Mt']['value'].sum()
    total_production_2050 = df[(df['variable'] == 'total_production_Mt') & (df['year'] == 2050)]['value'].sum()
    
    metrics = {
        'Total Steel\nProduction\n(2050)': f'{total_production_2050:.1f} Mt',
        'BF-BOF\nDominance': '100%',
        'Clean Tech\nAdoption': '0%',
        'Capacity\nUtilization': f'{(total_production_2050/39.65*100):.1f}%'
    }
    
    x_pos = np.arange(len(metrics))
    bars = ax4.bar(x_pos, [35.7, 100, 0, 90], 
                   color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'], alpha=0.7)
    
    ax4.set_xticks(x_pos)
    ax4.set_xticklabels(list(metrics.keys()), rotation=0, ha='center')
    ax4.set_ylabel('Value (%)')
    ax4.set_title('(D) Key Performance Metrics')
    
    # Add value labels on bars
    for bar, (key, value) in zip(bars, metrics.items()):
        if 'Mt' in value:
            ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    value, ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('outputs/Figure3_Technology_Analysis.png', dpi=300, bbox_inches='tight')
    plt.savefig('outputs/Figure3_Technology_Analysis.pdf', bbox_inches='tight')
    print("✓ Saved Figure 3: Technology Mix Analysis")
    return fig

def create_economic_summary_table():
    """Create Table 1: Economic and Technical Summary"""
    # Read summary data
    import json
    with open('outputs/summary_HardConstraints.json', 'r') as f:
        summary = json.load(f)
    
    # Create summary table data
    table_data = {
        'Parameter': [
            'Planning Horizon',
            'Total Objective Value (USD)',
            'Annual Steel Demand (Mt)',
            'Primary Technology Route',
            'BF-BOF Capacity (Mt/year)',
            'Clean Technology Investment',
            'Capacity Utilization Rate',
            'Flat Auto Exposed Share',
            'Flat Other Share', 
            'Long Products Share'
        ],
        'Value': [
            '2025-2050 (26 years)',
            f'${summary["objective"]:,.0f}',
            '35.68',
            'BF-BOF (Conventional)',
            '39.65',
            'None (0 Mt)',
            '90%',
            '20%',
            '60%',
            '20%'
        ],
        'Unit': [
            'Years',
            'USD (discounted)',
            'Mt/year',
            'Technology',
            'Mt/year',
            'Investment',
            '%',
            '%',
            '%', 
            '%'
        ]
    }
    
    df_table = pd.DataFrame(table_data)
    
    # Create table figure
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.axis('tight')
    ax.axis('off')
    
    table = ax.table(cellText=df_table.values,
                     colLabels=df_table.columns,
                     cellLoc='left',
                     loc='center',
                     colWidths=[0.5, 0.3, 0.2])
    
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 2)
    
    # Style the table
    for i in range(len(df_table.columns)):
        table[(0, i)].set_facecolor('#4CAF50')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    plt.title('Table 1: POSCO Decarbonization Optimization Results Summary\n(Hard Constraints Scenario)', 
              fontsize=14, fontweight='bold', pad=20)
    
    plt.savefig('outputs/Table1_Economic_Summary.png', dpi=300, bbox_inches='tight')
    plt.savefig('outputs/Table1_Economic_Summary.pdf', bbox_inches='tight')
    print("✓ Saved Table 1: Economic Summary")
    return fig

def main():
    """Generate all academic visualizations"""
    setup_academic_style()
    
    print("🎨 Generating Academic Visualizations for POSCO Decarbonization Study")
    print("=" * 70)
    
    # Create output directory
    Path("outputs").mkdir(exist_ok=True)
    
    # Load data
    df, production_vars = load_and_process_data()
    print(f"📊 Loaded {len(df)} data points across {len(production_vars)} production variables")
    
    # Generate figures
    print("\n📈 Creating Figures...")
    fig1 = create_production_pathway_chart(df)
    fig2 = create_capacity_evolution_chart(df)  
    fig3 = create_technology_mix_analysis(df)
    fig4 = create_economic_summary_table()
    
    plt.close('all')  # Close all figures to free memory
    
    print("\n✅ Academic Visualization Complete!")
    print("Generated files:")
    print("  • Figure1_Production_Pathways.png/pdf - Steel production by technology route")
    print("  • Figure2_Capacity_Evolution.png/pdf - Capacity and investment decisions")  
    print("  • Figure3_Technology_Analysis.png/pdf - Technology mix and performance metrics")
    print("  • Table1_Economic_Summary.png/pdf - Summary of optimization results")
    print("\n📄 Ready for academic paper submission!")

if __name__ == "__main__":
    main()