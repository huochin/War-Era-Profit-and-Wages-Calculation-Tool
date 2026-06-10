# War-Era-Profit-and-Wages-Calculation-Tool-V4

A fully automated desktop application for the game **WarEra**. This tool pulls live market and region data via the WarEra API, runs complex economic formulas (factoring in Strategic Resources, Deposits, and Party Ethics), and generates visual dashboards of the most profitable regions.

## ✨ Features

* **Easy to Use:** A standalone `.exe` desktop interface (No Python installation required!).
* **Secure API Key Manager:** Automatically saves and loads your WarEra API key locally. The input field is masked to protect your token if you are streaming or screen-sharing.
* **Live Market Integration:** Fetches real-time trading prices for all goods and raw materials, including newly added industries like Wood and Paper.
* **Complex Math Engine:** Calculates total production bonuses, Price of Production, Profit per PP, and Worker Wages (Pre and Post-Tax).
* **CSV Export:** Compiles all merged country, party, and region data into a detailed `extracted_countries.csv` spreadsheet.
* **Dual Visual Dashboards:** * Automatically generates a `wages_summary_chart.png` highlighting the single highest-profit region per product.
  * Generates a ranked `ranked_wages_chart.png` showcasing all highly profitable regions (Top Net Wages > 0.12) sorted for quick investment decisions.

## 🚀 Installation & Usage

1. Go to the **Releases** tab on the right side of this GitHub page.
2. Download the latest `ProfitnWagesCalc_V4.zip` file.
3. Extract the `.zip` folder somewhere on your computer.
4. Double-click **`AllBonusV4.exe`** to run the program.
5. When the window opens, paste your **WarEra API Key** (must start with `wae_`) into the secure input box and click **Save & Run**.
6. Once finished, check the folder for your newly generated CSV and PNG dashboards!

## 📁 Output Files

When you run the app, it will generate four files in the same folder:
* `warera_api_key.txt`: Created locally to remember your API key for next time. 
* `extracted_countries.csv`: The raw, calculated data for every region.
* `wages_summary_chart.png`: A colour-coded table showing the most profitable region for each major product.
* `ranked_wages_chart.png`: A comprehensive ranked list of the most lucrative regions globally based on post-tax wages.

## 🔒 Security & Privacy Transparency
This application communicates directly with the official WarEra API. Your API key is **never** sent to any third-party servers. It is only saved locally on your own computer in the `warera_api_key.txt` file, so you don't have to type it in every time. Treat that text file like a password!

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
