import os
import time
import json
import urllib.parse
import csv
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
from datetime import datetime
import pandas as pd

# CRITICAL: When generating charts in a background thread, we must tell 
# matplotlib to use the 'Agg' backend (Anti-Grain Geometry) so it doesn't crash the GUI.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

KEY_FILE = "warera_api_key.txt"
BASE_URL = "https://api2.warera.io/trpc"

# ==========================================
# 1. CORE SCRIPT LOGIC (Runs in Background)
# ==========================================
def run_warera_analysis(api_key, log_callback, done_callback):
    try:
        headers = {
            'accept': '*/*',
            'Content-Type': 'application/json',
            'x-api-key': api_key.strip(),
            'User-Agent': 'Mozilla/5.0'
        }

        def calculate_sr(amount):
            if amount == 0: return 0
            elif amount == 1: return 5
            else: return 5 + (0.25 * amount)

        # NEW: Upgraded API caller with Auto-Retry for 429 Rate Limits
        def api_call(endpoint: str, params: dict = None, retries=3) -> dict:
            if params is None: params = {}
            encoded_input = urllib.parse.quote(json.dumps(params))
            url = f"{BASE_URL}/{endpoint}?input={encoded_input}"
            
            for attempt in range(retries):
                try:
                    response = requests.get(url, headers=headers)
                    
                    # If we get a 429 Too Many Requests, pause and retry!
                    if response.status_code == 429:
                        log_callback(f"⚠️ Server cooling down... Pausing for 2s (Retry {attempt+1}/{retries})")
                        time.sleep(2)
                        continue # Try the loop again
                        
                    data = response.json()
                    if response.status_code == 200 and 'result' in data:
                        return data['result']['data']
                    else:
                        log_callback(f"⚠️ API Warning ({endpoint}): Code {response.status_code}")
                        return None
                        
                except Exception as e:
                    log_callback(f"⚠️ API Error ({endpoint}): {e}")
                    return None
                    
            # If it fails all retries, return None to trigger the hard exit
            return None

        # --- Avoid crashing if user hasn't installed requests ---
        import requests 

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

        log_callback("🌍 Fetching Countries...")
        countries_data = api_call('country.getAllCountries') or []

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
        log_callback(f"🏛️ Fetching {len(unique_ruling_parties)} parties... (This will take a moment)")

        # Fetch parties with progress updates
        for idx, party_id in enumerate(unique_ruling_parties, 1):
            party_data = api_call('party.getById', {'partyId': party_id})
            if party_data:
                party_lookup[party_id] = {
                    'Party Name': party_data.get('name', 'Unknown Party'),
                    'Party Industrialism': party_data.get('ethics', {}).get('industrialism', 0)
                }
            else:
                # UPDATE: Force application to return back and request API typing again
                log_callback("❌ Error fetching party data. Connection interrupted or Invalid API Key. Please try again.")
                done_callback()
                return
            
            if idx % 20 == 0:
                log_callback(f"   ...fetched {idx}/{len(unique_ruling_parties)} parties...")
            
            # UPDATE: Shortened sleep clock to 0.1 seconds
            time.sleep(0.1) 

        for c_id, c_data in country_lookup.items():
            p_id = c_data['Ruling Party ID']
            if p_id in party_lookup:
                c_data['Ruling Party Name'] = party_lookup[p_id]['Party Name']
                c_data['Ruling Party Industrialism'] = party_lookup[p_id]['Party Industrialism']
            else:
                c_data['Ruling Party Name'] = 'None'
                c_data['Ruling Party Industrialism'] = 0

        log_callback("📈 Fetching live market prices...")
        live_prices = api_call('itemTrading.getPrices') or {}

        # --- NEW: MANUAL OVERRIDE FOR WOOD & PAPER ---
        # Replace the numbers below with the actual market prices when API endpoints is malfunctioning.
        # live_prices['wood'] = 0.078   # Example: Price of Wood
        # live_prices['paper'] = 0.164  # Example: Price of Paper
        # ---------------------------------------------

        log_callback("⚙️ Calculating economic data...")
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
                if spec in ind_specs:
                    total_bonus = ethics_bonus + sr_bonus + (deposit_bonus if dep == spec else 0)
                elif spec not in ind_specs:
                    total_bonus = sr_bonus
                bonus_source = original_spec
            elif party_ind in [-1, -2]:
                agri_deps = ["fish", "coca", "grain", "livestock"]
                total_bonus = ethics_bonus + (deposit_bonus if dep in agri_deps else 0)
                bonus_source = deposit
            else: 
                total_bonus = sr_bonus + deposit_bonus if dep == 'none' else max(sr_bonus, deposit_bonus)
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

        with open('extracted_countries.csv', 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = list(combined_extracted_data[0].keys())
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(combined_extracted_data)

        log_callback("💾 Data successfully extracted and saved to 'extracted_countries.csv'!")

        # ----------------------------------------------------
        # CHART GENERATION #1 (Wages Summary)
        # ----------------------------------------------------
        log_callback("📊 Generating visual chart...")
        df = pd.read_csv('extracted_countries.csv')

        df = df[df['Bonus Source'].str.lower() != 'none']
        idx = df.groupby('Bonus Source')['Profit per PP'].idxmax()
        best_df = df.loc[idx].copy()
        best_df = best_df.sort_values(by='Profit per PP', ascending=False)
        best_df['Bonus Source'] = best_df['Bonus Source'].str.title()

        custom_names = {
            "Heavyammo": "Heavy Ammo", "Lightammo": "Light Ammo",
            "Cookedfish": "Cooked Fish", "Coca": "Mysterious Plant", "Cocain": "Pill"
        }
        best_df['Bonus Source'] = best_df['Bonus Source'].replace(custom_names)

        display_df = best_df[['Bonus Source', 'Profit per PP', 'Old workers top wages', 'Top wages after tax']].copy()
        display_df.rename(columns={'Bonus Source': 'Product', 'Old workers top wages': 'Top Gross Wages', 
                                   'Top wages after tax': 'Top Net Wages'}, inplace=True)

        for col in ['Profit per PP', 'Top Gross Wages', 'Top Net Wages']:
            display_df[col] = display_df[col].apply(lambda x: f"{float(x):.3f}")

        current_time = datetime.utcnow().strftime("%d/%m/%y, %H:%M UTC")
        table_data = display_df.values.tolist()
        footer_row = [""] * (len(display_df.columns) - 2) + ["Analysed at", current_time]
        table_data.append(footer_row)
        col_labels = display_df.columns.tolist()

        fig, ax = plt.subplots(figsize=(5, len(table_data) * 0.35))
        ax.axis('off')

        table = ax.table(cellText=table_data, colLabels=col_labels, loc='center', cellLoc='left')
        table.auto_set_column_width(col=list(range(len(col_labels))))
        table.auto_set_font_size(False)
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
                if row % 2 == 0: cell.set_facecolor('#E8F5E9') 
                else: cell.set_facecolor('white') 

        plt.savefig('product_profitability_ranking_chart.png', bbox_inches='tight', pad_inches=0.02, dpi=600)
        log_callback("✅ Chart successfully generated as 'wages_summary_chart.png'!")

        # ----------------------------------------------------
        # UPDATE: CHART GENERATION #2 (Ranked Performance Data)
        # ----------------------------------------------------
        log_callback("📊 Generating ranked metrics dashboard chart...")
        df_ranked = pd.read_csv('extracted_countries.csv')
        df_ranked = df_ranked[df_ranked['Bonus Source'].str.lower() != 'none']
        
        # Steps 1 & 2: Find highest wage per Country and Product combo
        idx_ranked = df_ranked.groupby(['Country Name', 'Bonus Source'])['Top wages after tax'].idxmax()
        best_ranked_df = df_ranked.loc[idx_ranked].copy()
        
        # Step 5: Filter values strictly higher than 0.12 and sort descending
        best_ranked_df = best_ranked_df[best_ranked_df['Top wages after tax'] > 0.12]
        best_ranked_df = best_ranked_df.sort_values(by='Top wages after tax', ascending=False)
        
        # Apply standard translation corrections
        best_ranked_df['Bonus Source'] = best_ranked_df['Bonus Source'].str.title()
        best_ranked_df['Bonus Source'] = best_ranked_df['Bonus Source'].replace(custom_names)
        
        # Select exact column headers to match reference dashboard image format
        display_ranked = best_ranked_df[[
            'Region Name', 'Country Name', 'Bonus Source', 
            'Price of Goods', 'Price of Raw Material', 'Total Bonus', 'Profit per PP', 
            'Old workers top wages', 'Income Tax Rate', 'Top wages after tax'
        ]].copy()
        
        # Step 4: Rename headers as specified
        display_ranked.rename(columns={
            'Income Tax Rate': 'Tax %',
            'Total Bonus': 'Prod Bonus',
            'Top wages after tax': 'Top Net Wages',
            'Price of Goods' : 'Price',
            'Bonus Source': 'Product',
            'Price of Raw Material' : 'Matl',
            'Old workers top wages' : 'Top Gross Wages'
        }, inplace=True)
        
        # Step 4: Configure precision scaling format constraints
        display_ranked['Prod Bonus'] = display_ranked['Prod Bonus'].apply(lambda x: f"{float(x):.2f}")
        display_ranked['Tax %'] = display_ranked['Tax %'].apply(lambda x: f"{float(x):.1f}")
        
        numeric_3_dec = ['Price', 'Matl', 'Profit per PP', 'Top Gross Wages', 'Top Net Wages']
        for col in numeric_3_dec:
            display_ranked[col] = display_ranked[col].apply(lambda x: f"{float(x):.3f}")
            
        # Draw the table layout structure
        table_data_ranked = display_ranked.values.tolist()
        footer_row_ranked = [""] * (len(display_ranked.columns) - 3) + ["Analysed at", "", current_time]
        table_data_ranked.append(footer_row_ranked)
        col_labels_ranked = display_ranked.columns.tolist()
        
        fig2, ax2 = plt.subplots(figsize=(11, len(table_data_ranked) * 0.35))
        ax2.axis('off')
        
        table2 = ax2.table(cellText=table_data_ranked, colLabels=col_labels_ranked, loc='center', cellLoc='left')
        table2.auto_set_column_width(col=list(range(len(col_labels_ranked))))
        table2.auto_set_font_size(False)
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
                cell.visible_edges = 'open'  # Removes borders entirely from the footer row
                if col >= len(col_labels_ranked) - 3:
                    cell.set_text_props(ha='right')
            else:
                if row % 2 == 0: cell.set_facecolor('#EAF2F8')
                else: cell.set_facecolor('white')
                
                # Step 4: Explicit right alignment parsing logic for numeric column rows
                if col in [3, 4, 5, 6, 7, 8, 9]:
                    cell.set_text_props(ha='right')
                    
        plt.savefig('regional_wages_ranking_chart.png', bbox_inches='tight', pad_inches=0.02, dpi=600)
        log_callback("✅ Ranked chart successfully generated as 'ranked_wages_chart.png'!")
        log_callback("\n🎉 All processes complete. You can close this window.")
        
    except Exception as e:
        log_callback(f"❌ A critical error occurred: {str(e)}")
    
    finally:
        # Re-enable the run button when finished
        done_callback()

# ==========================================
# 2. GUI APPLICATION SETUP
# ==========================================
class WarEraGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("WarEra Economic Analyser")
        self.root.geometry("600x450")
        self.root.configure(padx=20, pady=20)
        
        # 1. API Key Input Section
        self.api_frame = tk.Frame(self.root)
        self.api_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(self.api_frame, text="API Key:").pack(side=tk.LEFT)
        
        # UPDATE: Configured entry character hiding using asterisks
        self.api_entry = tk.Entry(self.api_frame, width=50, show="*")
        self.api_entry.pack(side=tk.LEFT, padx=10)
        
        self.run_btn = tk.Button(self.api_frame, text="Save & Run", command=self.start_script, bg="#5CB85C", fg="white", font=("Arial", 10, "bold"))
        self.run_btn.pack(side=tk.LEFT)
        
        # 2. Scrolling Console Output
        self.console = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, height=18, font=("Consolas", 10))
        self.console.pack(fill=tk.BOTH, expand=True)
        self.console.insert(tk.END, "Welcome to the WarEra Analyser!\n----------------------------------\n")
        
        # Disable editing in the console
        self.console.configure(state='disabled')

        # 3. Startup Logic: Check for existing API key
        self.check_saved_key()

    def check_saved_key(self):
        if os.path.exists(KEY_FILE):
            try:
                with open(KEY_FILE, 'r') as f:
                    saved_key = f.read().strip()
                
                if saved_key.startswith("wae"):
                    self.api_entry.insert(0, saved_key)
                    self.log_to_console(f"✔️ Found saved API key in {KEY_FILE}!")
                    self.start_script()
                else:
                    self.log_to_console("⚠️ Saved API key is invalid (must start with 'wae'). Please enter a new one.")
            except Exception as e:
                self.log_to_console(f"⚠️ Could not read {KEY_FILE}: {e}")
        else:
            self.log_to_console("ℹ️ No saved API key found. Please paste your key above to begin.")

    def log_to_console(self, message):
        def append():
            self.console.configure(state='normal')
            self.console.insert(tk.END, message + "\n")
            self.console.see(tk.END)
            self.console.configure(state='disabled')
        self.root.after(0, append)

    def start_script(self):
        api_key = self.api_entry.get().strip()
        
        # Validate API Key
        if not api_key.startswith("wae"):
            messagebox.showerror("Invalid Key", "API key must start with 'wae'.")
            return
            
        # Save valid key
        with open(KEY_FILE, 'w') as f:
            f.write(api_key)
            
        # UI Updates
        self.run_btn.config(state=tk.DISABLED, text="Running...")
        self.api_entry.config(state=tk.DISABLED)
        self.log_to_console("\n🚀 Starting extraction process...")
        
        # Run the heavy script in a background thread so the window doesn't freeze!
        thread = threading.Thread(
            target=run_warera_analysis, 
            args=(api_key, self.log_to_console, self.script_finished)
        )
        thread.daemon = True
        thread.start()

    def script_finished(self):
        def reset_ui():
            self.run_btn.config(state=tk.NORMAL, text="Run Again")
            self.api_entry.config(state=tk.NORMAL)
        self.root.after(0, reset_ui)

# ==========================================
# 3. RUN APPLICATION
# ==========================================
if __name__ == "__main__":
    root = tk.Tk()
    app = WarEraGUI(root)
    root.mainloop()
