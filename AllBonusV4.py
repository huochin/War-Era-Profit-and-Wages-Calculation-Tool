import os
import time
import json
import urllib.parse
import pandas as pd
from datetime import datetime
import io
import base64
import requests

from flask import Flask, render_template, request, flash

import matplotlib
matplotlib.use('Agg') # Required for background rendering
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = "super_secret_key" # Required for flashing error messages
BASE_URL = "https://api2.warera.io/trpc"

RECIPES = {
    "cookedfish": {"good": "cookedFish", "rm": "fish", "rm_amt": 1, "pp": 40},
    "heavyammo": {"good": "heavyAmmo", "rm": "lead", "rm_amt": 16, "pp": 16},
    "steel": {"good": "steel", "rm": "iron", "rm_amt": 10, "pp": 10},
    "bread": {"good": "bread", "rm": "grain", "rm_amt": 10, "pp": 10},
    "grain": {"good": "grain", "rm": None, "rm_amt": 0, "pp": 1},
    "limestone": {"good": "limestone", "rm": None, "rm_amt": 0, "pp": 1},
    "coca": {"good": "coca", "rm": None, "rm_amt": 0, "pp": 1},
    "concrete": {"good": "concrete", "rm": "limestone", "rm_amt": 10, "pp": 10},
    "oil": {"good": "oil", "rm": "petroleum", "rm_amt": 1, "pp": 1},
    "paper": {"good": "paper", "rm": "wood", "rm_amt": 1, "pp": 1},
    "lightammo": {"good": "lightAmmo", "rm": "lead", "rm_amt": 1, "pp": 1},
    "steak": {"good": "steak", "rm": "livestock", "rm_amt": 1, "pp": 20},
    "livestock": {"good": "livestock", "rm": None, "rm_amt": 0, "pp": 20},
    "cocain": {"good": "cocain", "rm": "coca", "rm_amt": 200, "pp": 200},
    "lead": {"good": "lead", "rm": None, "rm_amt": 0, "pp": 1},
    "fish": {"good": "fish", "rm": None, "rm_amt": 0, "pp": 40},
    "petroleum": {"good": "petroleum", "rm": None, "rm_amt": 0, "pp": 1},
    "wood": {"good": "wood", "rm": None, "rm_amt": 0, "pp": 1},
    "ammo": {"good": "ammo", "rm": "lead", "rm_amt": 4, "pp": 4},
    "iron": {"good": "iron", "rm": None, "rm_amt": 0, "pp": 1}
}

def calculate_sr(amount):
    if amount == 0: return 0
    elif amount == 1: return 5
    else: return 5 + (0.25 * amount)

def process_warera_data(api_key):
    headers = {
        'accept': '*/*',
        'Content-Type': 'application/json',
        'x-api-key': api_key.strip(),
        'User-Agent': 'Mozilla/5.0'
    }

    # API caller with Auto-Retry for 429 Rate Limits
    def api_call(endpoint: str, params: dict = None, retries=3) -> dict:
        if params is None: params = {}
        encoded_input = urllib.parse.quote(json.dumps(params))
        url = f"{BASE_URL}/{endpoint}?input={encoded_input}"
        
        for attempt in range(retries):
            try:
                response = requests.get(url, headers=headers)
                if response.status_code == 429:
                    print(f"Server cooling down... Pausing for 2s (Retry {attempt+1}/{retries})")
                    time.sleep(2)
                    continue 
                    
                data = response.json()
                if response.status_code == 200 and 'result' in data:
                    return data['result']['data']
                else:
                    return None
            except Exception:
                return None
        return None

    countries_data = api_call('country.getAllCountries') or []
    if not countries_data:
        raise ValueError("Failed to fetch countries. Invalid API Key or server down.")

    country_lookup = {}
    unique_ruling_parties = set()

    for countryDetail in countries_data:
        country_id = countryDetail.get('_id') 
        country_name = countryDetail.get('name', 'Unknown')
        specialisation = countryDetail.get('specializedItem', 'None')
        
        taxes = countryDetail.get('taxes', {})
        income_tax = taxes.get('income', 0)
        
        ruling_party = countryDetail.get('rulingParty', 'None')
        if ruling_party and ruling_party != 'None':
            unique_ruling_parties.add(ruling_party)
            
        resources = countryDetail.get('strategicResources', {}).get('resources', {})
        
        country_lookup[country_id] = {
            'Country Name': country_name,
            'Specialisation': specialisation,
            'Income Tax Rate': income_tax,
            'Ruling Party ID': ruling_party, 
            'Gold': len(resources.get('gold', [])),
            'Rare Earth': len(resources.get('rareEarths', [])), 
            'Coal': len(resources.get('coal', [])),
            'Lithium': len(resources.get('lithium', [])),
            'Diamonds': len(resources.get('diamonds', [])),
            'Uranium': len(resources.get('uranium', []))
        }

    party_lookup = {}
    for party_id in unique_ruling_parties:
        party_data = api_call('party.getById', {'partyId': party_id})
        if party_data:
            party_lookup[party_id] = {
                'Party Name': party_data.get('name', 'Unknown Party'),
                'Party Industrialism': party_data.get('ethics', {}).get('industrialism', 0)
            }
        time.sleep(0.1)

    for c_id, c_data in country_lookup.items():
        p_id = c_data['Ruling Party ID']
        if p_id in party_lookup:
            c_data['Ruling Party Name'] = party_lookup[p_id]['Party Name']
            c_data['Ruling Party Industrialism'] = party_lookup[p_id]['Party Industrialism']
        else:
            c_data['Ruling Party Name'] = 'None'
            c_data['Ruling Party Industrialism'] = 0

    live_prices = api_call('itemTrading.getPrices') or {}

    # MANUAL OVERRIDE FOR WOOD & PAPER
    # Replace the numbers below with the actual market prices when API endpoints is malfunctioning.
    # live_prices['wood'] = 0.078   
    # live_prices['paper'] = 0.164  

    regions_data = api_call('region.getRegionsObject') or {}
    combined_extracted_data = []

    for region_id, details in regions_data.items():
        region_name = details.get('name', 'Unknown')
        country_id = details.get('country', 'Unknown') 
        deposit_dict = details.get('deposit', {})
        deposit = deposit_dict.get('type', 'None') if deposit_dict else 'None'
        
        matching_country = country_lookup.get(country_id, {})
        party_ind = matching_country.get('Ruling Party Industrialism', 0)
        income_tax_rate = matching_country.get('Income Tax Rate', 0)
        original_spec = matching_country.get('Specialisation', 'None')
        spec = original_spec.lower()
        dep = deposit.lower()
        
        sr_bonus = sum([
            calculate_sr(matching_country.get('Gold', 0)),
            calculate_sr(matching_country.get('Rare Earth', 0)),
            calculate_sr(matching_country.get('Coal', 0)),
            calculate_sr(matching_country.get('Lithium', 0)),
            calculate_sr(matching_country.get('Diamonds', 0)),
            calculate_sr(matching_country.get('Uranium', 0))
        ])
        deposit_bonus = 0 if dep == 'none' else 30
        ethics_bonus = {2: 30, 1: 10, -2: 30, -1: 10, 0: 0}.get(party_ind, 0)
        
        total_bonus = 0
        bonus_source = "None"
        
        if party_ind in [1, 2]:
                ind_specs = ["oil", "petroleum", "steel", "iron", "concrete", "limestone", "lead", 
                             "lightammo", "ammo", "heavyammo", "wood", "paper"]
                if spec in ind_specs and party_ind == 1 and dep == spec:
                    total_bonus = ethics_bonus + sr_bonus + deposit_bonus
                elif spec in ind_specs:
                    total_bonus = ethics_bonus + sr_bonus
                elif spec not in ind_specs:
                    total_bonus = sr_bonus
                bonus_source = original_spec
        elif party_ind in [-1, -2]:
            agri_deps = ["fish", "coca", "grain", "livestock"]
            if party_ind == -1 and dep == spec and dep in agri_deps:
                total_bonus = ethics_bonus + deposit_bonus + sr_bonus
            else:
                total_bonus = ethics_bonus + (deposit_bonus if dep in agri_deps else 0)
                bonus_source = deposit
        else: 
            total_bonus = sr_bonus + deposit_bonus if dep == spec else max(sr_bonus, deposit_bonus)
            bonus_source = deposit if deposit_bonus > sr_bonus else original_spec

        recipe = RECIPES.get(bonus_source.lower())
        
        if recipe:
            raw_goods_price = live_prices.get(recipe['good'], 0)
            price_of_goods = round(raw_goods_price, 3)
            raw_rm_price = live_prices.get(recipe['rm'], 0) if recipe['rm'] else 0
            price_of_rm = round(raw_rm_price, 3)
            
            raw_production_price = (raw_goods_price - (recipe['rm_amt'] * raw_rm_price)) / recipe['pp']
            price_of_production = round(raw_production_price, 3)
            
            raw_profit = raw_production_price * (1 + (total_bonus / 100))
            profit_per_pp = round(raw_profit, 3)
            
            raw_old_wages = raw_production_price * (1 + ((total_bonus + 10) / 100))
            old_workers_top_wages = round(raw_old_wages, 3)
            
            raw_top_wages = raw_old_wages * (1 - (income_tax_rate / 100))
            top_wages_after_tax = round(raw_top_wages, 3)
        else:
            price_of_goods = price_of_rm = price_of_production = profit_per_pp = old_workers_top_wages = top_wages_after_tax = 0
        
        combined_row = {
            'Region Name': region_name, 'Region Deposit': deposit,
            'Country Name': matching_country.get('Country Name', 'Unknown'),
            'Specialisation': original_spec, 'Ruling Party Name': matching_country.get('Ruling Party Name', 'None'),
            'Party Industrialism': party_ind, 'Income Tax Rate': income_tax_rate,
            'Gold': matching_country.get('Gold', 0), 'Rare Earth': matching_country.get('Rare Earth', 0),
            'Coal': matching_country.get('Coal', 0), 'Lithium': matching_country.get('Lithium', 0),
            'Diamonds': matching_country.get('Diamonds', 0), 'Uranium': matching_country.get('Uranium', 0),
            'SR Bonus': sr_bonus, 'Deposit Bonus': deposit_bonus, 'Ethics Bonus': ethics_bonus,
            'Total Bonus': total_bonus, 'Bonus Source': bonus_source,
            'Price of Goods': price_of_goods, 'Price of Raw Material': price_of_rm,
            'Price of Production': price_of_production, 'Profit per PP': profit_per_pp,
            'Old workers top wages': old_workers_top_wages, 'Top wages after tax': top_wages_after_tax
        }
        combined_extracted_data.append(combined_row)

    df = pd.DataFrame(combined_extracted_data)
    df = df[df['Bonus Source'].str.lower() != 'none']

    custom_names = {
        "Heavyammo": "Heavy Ammo", "Lightammo": "Light Ammo",
        "Cookedfish": "Cooked Fish", "Coca": "Mysterious Plant", "Cocain": "Pill"
    }

    # Chart 1 Generation
    idx = df.groupby('Bonus Source')['Profit per PP'].idxmax()
    best_df = df.loc[idx].copy().sort_values(by='Profit per PP', ascending=False)
    best_df['Bonus Source'] = best_df['Bonus Source'].str.title().replace(custom_names)

    display_df = best_df[['Bonus Source', 'Profit per PP', 'Old workers top wages', 'Top wages after tax']].copy()
    display_df.rename(columns={'Bonus Source': 'Product', 'Old workers top wages': 'Top Gross Wages', 'Top wages after tax': 'Top Net Wages'}, inplace=True)
    
    for col in ['Profit per PP', 'Top Gross Wages', 'Top Net Wages']:
        display_df[col] = display_df[col].apply(lambda x: f"{float(x):.3f}")

    current_time = datetime.utcnow().strftime("%d/%m/%y, %H:%M UTC")
    table_data = display_df.values.tolist()
    footer_row = [""] * (len(display_df.columns) - 2) + ["Analysed at", current_time]
    table_data.append(footer_row)
    col_labels = display_df.columns.tolist()
    
    fig, ax = plt.subplots(figsize=(10, len(table_data) * 0.35))
    ax.axis('off')
    table = ax.table(cellText=table_data, colLabels=col_labels, loc='center', cellLoc='left')
    table.auto_set_column_width(col=list(range(len(col_labels))))
    table.set_fontsize(12)
    table.scale(1, 1.5) 

    last_row_idx = len(table_data)

    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor('#A5D6A7') 
        if row == 0:
            cell.set_facecolor('#5CB85C') 
            cell.set_text_props(weight='bold', color='black')
        elif row == last_row_idx:
            cell.set_facecolor('white')
            cell.visible_edges = 'open' 
            if col >= len(col_labels) - 2:
                cell.set_text_props(ha='right') 
        else:
            cell.set_facecolor('#E8F5E9' if row % 2 == 0 else 'white')

    img1 = io.BytesIO()
    plt.savefig(img1, format='png', bbox_inches='tight', pad_inches=0.02, dpi=300)
    plt.close(fig)
    img1.seek(0)
    chart1_b64 = base64.b64encode(img1.getvalue()).decode('utf-8')

    # Chart 2 Generation
    idx_ranked = df.groupby(['Country Name', 'Bonus Source'])['Top wages after tax'].idxmax()
    best_ranked_df = df.loc[idx_ranked].copy()
    best_ranked_df = best_ranked_df[best_ranked_df['Top wages after tax'] > 0.12].sort_values(by='Top wages after tax', ascending=False)
    best_ranked_df['Bonus Source'] = best_ranked_df['Bonus Source'].str.title().replace(custom_names)
    
    display_ranked = best_ranked_df[[
        'Region Name', 'Country Name', 'Bonus Source', 
        'Price of Goods', 'Price of Raw Material', 'Total Bonus', 'Profit per PP', 
        'Old workers top wages', 'Income Tax Rate', 'Top wages after tax'
    ]].copy()
    
    display_ranked.rename(columns={
        'Income Tax Rate': 'Tax %',
        'Total Bonus': 'Prod Bonus',
        'Top wages after tax': 'Top Net Wages',
        'Price of Goods' : 'Price',
        'Bonus Source': 'Product',
        'Price of Raw Material' : 'Matl',
        'Old workers top wages' : 'Top Gross Wages'
    }, inplace=True)
    
    display_ranked['Prod Bonus'] = display_ranked['Prod Bonus'].apply(lambda x: f"{float(x):.2f}")
    display_ranked['Tax %'] = display_ranked['Tax %'].apply(lambda x: f"{float(x):.1f}")
    numeric_3_dec = ['Price', 'Matl', 'Profit per PP', 'Top Gross Wages', 'Top Net Wages']
    for col in numeric_3_dec:
        display_ranked[col] = display_ranked[col].apply(lambda x: f"{float(x):.3f}")
        
    table_data_ranked = display_ranked.values.tolist()
    footer_row_ranked = [""] * (len(display_ranked.columns) - 3) + ["Analysed at", "", current_time]
    table_data_ranked.append(footer_row_ranked)
    col_labels_ranked = display_ranked.columns.tolist()
    
    fig2, ax2 = plt.subplots(figsize=(16, len(table_data_ranked) * 0.35))
    ax2.axis('off')
    table2 = ax2.table(cellText=table_data_ranked, colLabels=col_labels_ranked, loc='center', cellLoc='left')
    table2.auto_set_column_width(col=list(range(len(col_labels_ranked))))
    table2.set_fontsize(10)
    table2.scale(1, 1.5)
    
    last_row_idx2 = len(table_data_ranked)
    
    for (row, col), cell in table2.get_celld().items():
        cell.set_edgecolor('#A9CCE3')
        if row == 0:
            cell.set_facecolor('#2980B9')
            cell.set_text_props(weight='bold', color='black')
        elif row == last_row_idx2:
            cell.set_facecolor('white')
            cell.visible_edges = 'open' 
            if col >= len(col_labels_ranked) - 3:
                cell.set_text_props(ha='right')
        else:
            cell.set_facecolor('#EAF2F8' if row % 2 == 0 else 'white')
            if col in [3, 4, 5, 6, 7, 8, 9]:
                cell.set_text_props(ha='right')
                
    img2 = io.BytesIO()
    plt.savefig(img2, format='png', bbox_inches='tight', pad_inches=0.02, dpi=300)
    plt.close(fig2)
    img2.seek(0)
    chart2_b64 = base64.b64encode(img2.getvalue()).decode('utf-8')

    return chart1_b64, chart2_b64

@app.route('/', methods=['GET', 'POST'])
def index():
    chart1 = None
    chart2 = None
    
    if request.method == 'POST':
        api_key = request.form.get('api_key')
        if not api_key or not api_key.startswith("wae"):
            flash("Invalid API Key. It must start with 'wae'.")
        else:
            try:
                chart1, chart2 = process_warera_data(api_key)
            except Exception as e:
                flash(f"An error occurred during analysis: {str(e)}")
                
    return render_template('index.html', chart1=chart1, chart2=chart2)

if __name__ == '__main__':
    app.run(debug=True)
