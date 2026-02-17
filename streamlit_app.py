import pandas as pd
import numpy as np

np.random.seed(42)

SOURCES = [
    'Barrington', 'Channel Edge', 'Google', 'Lucent', 'O2C',
    'Other', 'Policy Chat', 'Ring 2', 'Roku', 'VOXR', 'Youtube', 'Regal'
]

# Base lead volume and PSL by source (gives realistic variation)
SOURCE_CONFIG = {
    'Barrington':    {'leads_base': 120, 'psl_base': 280, 'sales_rate': 0.18},
    'Channel Edge':  {'leads_base': 80,  'psl_base': 220, 'sales_rate': 0.14},
    'Google':        {'leads_base': 300, 'psl_base': 195, 'sales_rate': 0.22},
    'Lucent':        {'leads_base': 60,  'psl_base': 310, 'sales_rate': 0.16},
    'O2C':           {'leads_base': 200, 'psl_base': 260, 'sales_rate': 0.20},
    'Other':         {'leads_base': 50,  'psl_base': 150, 'sales_rate': 0.10},
    'Policy Chat':   {'leads_base': 90,  'psl_base': 175, 'sales_rate': 0.12},
    'Ring 2':        {'leads_base': 75,  'psl_base': 240, 'sales_rate': 0.17},
    'Roku':          {'leads_base': 110, 'psl_base': 205, 'sales_rate': 0.15},
    'VOXR':          {'leads_base': 65,  'psl_base': 290, 'sales_rate': 0.19},
    'Youtube':       {'leads_base': 180, 'psl_base': 185, 'sales_rate': 0.13},
    'Regal':         {'leads_base': 95,  'psl_base': 255, 'sales_rate': 0.21},
}

dates = pd.date_range("2023-01-01", "2024-12-31", freq="D")

leads_rows = []
sales_rows = []

for date in dates:
    # Seasonal multiplier (slight summer peak)
    month = date.month
    season = 1.0 + 0.15 * np.sin((month - 3) * np.pi / 6)

    for src, cfg in SOURCE_CONFIG.items():
        # Leads
        lead_count = max(1, int(np.random.poisson(cfg['leads_base'] / 30 * season)))
        leads_rows.append({'PERIOD': date, 'LEAD_SOURCE': src, 'LEAD_COUNT': lead_count})

        # Sales
        sales = max(0, int(np.random.binomial(lead_count, cfg['sales_rate'])))
        psl_noise = np.random.normal(1.0, 0.12)
        premium = round(sales * cfg['psl_base'] * psl_noise, 2) if sales > 0 else 0.0
        sales_rows.append({'PERIOD': date, 'LEAD_SOURCE': src, 'SOURCE_SALES': sales, 'SOURCE_PREMIUM': premium})

leads_df = pd.DataFrame(leads_rows)
sales_df = pd.DataFrame(sales_rows)

leads_df.to_csv("leads_data.csv", index=False)
sales_df.to_csv("sales_data.csv", index=False)

print(f"✅ leads_data.csv  → {len(leads_df):,} rows")
print(f"✅ sales_data.csv  → {len(sales_df):,} rows")
print("\nSample leads_data:")
print(leads_df.head())
print("\nSample sales_data:")
print(sales_df.head())
