import os
import io
import time
import uuid
import shutil
import zipfile
import requests
import datetime as dt
import pandas as pd
from dotenv import load_dotenv

# Assumes tokens.py is in the same directory
import tokens as tk

load_dotenv()

# =========================
# CONSTANTS
# =========================
WEBHOOK_URL = "https://api-btg-2.onrender.com/webhook"
BTG_API_PARTNER_ONBOARDING_URL = "https://api.btgpactual.com/api-partner-report-hub/api/v1/report/onboarding-by-date"
API_KEY = os.getenv("BTG_WEBHOOK_API_KEY")

OUTPUT_DIR = "diretorio_arq"
EXTRACT_DIR = "extracted_files"
REQUEST_TIMEOUT = 30

# =========================
# UTILITIES
# =========================

def trigger_btg_report(url: str, token_manager, method: str = "GET", json_data: dict = None) -> None:
    print(f"Triggering report: {url}")
    headers = {
        "x-id-partner-request": str(uuid.uuid4()),
        "access_token": token_manager(),
        "accept": "*/*",
    }
    
    if method.upper() == "POST":
        if json_data is None:
            json_data = {}
        res = requests.post(url, headers=headers, json=json_data, timeout=REQUEST_TIMEOUT)
    else:
        res = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    
    if not res.ok:
        raise RuntimeError(f"BTG API error: {res.status_code} - {res.text}")
    print("Report triggered successfully.")

def fetch_new_file_url(previous_url: str = None) -> str | None:
    """
    Fetches the file URL from the middleware.
    """
    # Using a simpler retry logic for this standalone script
    for attempt in range(15):
        try:
            res = requests.get(
                WEBHOOK_URL,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": API_KEY,
                },
                timeout=REQUEST_TIMEOUT,
            )
            res.raise_for_status()
            
            new_url = res.json()["response"]["url"]
            
            if previous_url and new_url == previous_url:
                print(f"Waiting for new file... (Attempt {attempt+1}/15)")
                time.sleep(20)
                continue

            return new_url

        except Exception as e:
            print(f"Error fetching URL: {e}")
            time.sleep(10)
            
    return None

def download_and_save_file(url: str, output_name_base: str) -> str | None:
    try:
        print(f"Downloading from {url}...")
        res = requests.get(url, stream=True, timeout=REQUEST_TIMEOUT)
        res.raise_for_status()

        os.makedirs(os.path.dirname(output_name_base), exist_ok=True)

        if res.headers.get("Content-Type") == "application/zip" or url.endswith(".zip"):
            if os.path.isdir(EXTRACT_DIR):
                shutil.rmtree(EXTRACT_DIR)
            os.makedirs(EXTRACT_DIR, exist_ok=True)

            with zipfile.ZipFile(io.BytesIO(res.content)) as zip_ref:
                zip_ref.extractall(EXTRACT_DIR)

            for file in os.listdir(EXTRACT_DIR):
                if file.endswith(".csv"):
                    shutil.move(
                        os.path.join(EXTRACT_DIR, file),
                        f"{output_name_base}.csv",
                    )
            return "zip"
        else:
            with open(f"{output_name_base}.csv", "wb") as f:
                for chunk in res.iter_content(8192):
                    f.write(chunk)
            return "csv"

    except Exception as e:
        print(f"Error downloading file: {e}")
        return None

# =========================
# MAIN LOGIC
# =========================

def run_partner_onboarding():
    if not API_KEY:
        print("Error: BTG_WEBHOOK_API_KEY not set in .env")
        return

    runs = [
        {"prefix": "consultoria", "token_manager": tk.manage_token_consultoria},
        {"prefix": "gen", "token_manager": tk.manage_token_gen}
    ]

    for run in runs:
        prefix = run["prefix"]
        t_manager = run["token_manager"]

        print(f"\n>>> RUNNING PARTNER ONBOARDING FOR: {prefix.upper()} <<<")

        # 1. Trigger
        # Testando com 15 dias para diagnosticar o limite da API
        end_date = dt.date.today() - dt.timedelta(days=0)
        start_date = dt.date.today() - dt.timedelta(days=29)
        
        json_data = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d")
        }
        print(f"Enviando datas: {json_data['startDate']} ate {json_data['endDate']}")
        
        try:
            trigger_btg_report(BTG_API_PARTNER_ONBOARDING_URL, t_manager, method="POST", json_data=json_data)
        except Exception as e:
            print(f"Failed to trigger for {prefix}: {e}")
            continue

        # 2. Wait and Fetch URL
        print("Waiting for file generation...")
        time.sleep(30)
        file_url = fetch_new_file_url() # No previous URL check for simplicity in standalone
        
        if not file_url:
            print(f"Could not retrieve URL for {prefix}")
            continue

        # 3. Download
        res = download_and_save_file(file_url, f"{OUTPUT_DIR}/{prefix}_Dados_Onboarding_Partner_Manual")
        if res:
            print(f"Success! File saved to {OUTPUT_DIR}/{prefix}_Dados_Onboarding_Partner_Manual.csv")
        else:
            print(f"Failed to download for {prefix}")

if __name__ == "__main__":
    run_partner_onboarding()
