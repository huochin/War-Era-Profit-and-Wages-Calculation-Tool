# War-Era-Profit-and-Wages-Calculation-Tool-V3

A fully automated desktop application for the game **WarEra**. This tool pulls live market and region data via the WarEra API, runs complex economic formulas (factoring in Strategic Resources, Deposits, and Party Ethics), and generates a visual dashboard of the most profitable regions.

## ✨ Features

* **Easy to Use:** A standalone `.exe` desktop interface (No Python installation required!).
* **API Key Manager:** Automatically saves and loads your WarEra API key locally so you don't have to paste it every time.
* **Live Market Integration:** Fetches real-time trading prices for all goods and raw materials.
* **Complex Math Engine:** Calculates total production bonuses, Price of Production, Profit per PP, and Worker Wages (Pre and Post-Tax).
* **CSV Export:** Compiles all merged country, party, and region data into a detailed `extracted_countries.csv` spreadsheet.
* **Visual Charting:** Automatically generates a polished `wages_summary_chart.png` highlighting the highest-profit regions.

## 🚀 Installation & Usage

1. Go to the **Releases** tab on the right side of this GitHub page.
2. Download the latest `WarEra_Analyser.zip` file.
3. Extract the `.zip` folder somewhere on your computer.
4. Double-click **`WarEraApp.exe`** to run the program.
5. When the window opens, paste your **WarEra API Key** (must start with `wae_`) into the input box and click **Save & Run**.
6. Once finished, check the folder for your newly generated CSV and PNG dashboard!

## 📁 Output Files

When you run the app, it will generate three files in the same folder:
* `warera_api_key.txt`: Created locally to remember your API key for next time. 
* `extracted_countries.csv`: The raw, calculated data for every region.
* `wages_summary_chart.png`: A colour-coded table showing the most profitable region for each major product.

## 🔒 Security & Privacy Transparency
This application communicates directly with the official WarEra API. Your API key is **never** sent to any third-party servers. It is only saved locally on your own computer in the `warera_api_key.txt` file, so you don't have to type it in every time. Treat that text file like a password!

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
