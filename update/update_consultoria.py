import os
import io
import time
import uuid
import shutil
import zipfile
import requests
import datetime as dt
import pandas as pd
from typing import List, Union

import tokens as tk
import pygsheets
from dotenv import load_dotenv

load_dotenv()

# =========================
# CONFIG
# =========================
WEBHOOK_URL = "https://api-btg-2.onrender.com/webhook"

BTG_API_BASE_URL = "https://api.btgpactual.com/api-rm-reports/api/v1/rm-reports/account-base"
BTG_API_REGISTRATION_URL = "https://api.btgpactual.com/api-rm-reports/api/v1/rm-reports/registration-data"
BTG_API_POSITION_URL = "https://api.btgpactual.com/api-rm-reports/api/v1/rm-reports/position"
BTG_API_BANKING_URL = "https://api.btgpactual.com/api-rm-reports/api/v1/rm-reports/banking"
BTG_API_PERFORMANCE_ACCOUNT_URL = "https://api.btgpactual.com/iaas-profitability/api/v1/performance-report/account"
BTG_API_MOVEMENTS_URL = "https://api.btgpactual.com/api-rm-reports/api/v1/operation-history/monthly"

LAST_URL_FILE = "last_url.txt"
ERROR_LOG_FILE = "error_log/error_log.csv"

REQUEST_TIMEOUT = 30
OUTPUT_DIR = "diretorio_arq"
EXTRACT_DIR = "extract"

GOOGLE_SHEET_ID = "1z63uqeENfqZhtiwKsQ1KEphS9HUg4bMYzMQmwpp83KQ"
CREDENTIALS_PATH = os.path.join("artifac", "cliente.json")

API_KEY = os.getenv("BTG_WEBHOOK_API_KEY")

# =========================
# UTILS
# =========================
def log_error(msg):
    os.makedirs(os.path.dirname(ERROR_LOG_FILE), exist_ok=True)
    with open(ERROR_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now()};{msg}\n")

def read_last_url():
    if not os.path.exists(LAST_URL_FILE):
        return ""
    return open(LAST_URL_FILE).read().strip()

def save_last_url(url):
    with open(LAST_URL_FILE, "w") as f:
        f.write(url)

def fetch_new_file_url(previous_url=None):
    for _ in range(10):
        try:
            r = requests.get(WEBHOOK_URL, headers={"x-api-key": API_KEY}, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            url = r.json()["response"]["url"]

            if previous_url and url == previous_url:
                time.sleep(10)
                continue

            save_last_url(url)
            return url
        except Exception as e:
            log_error(f"WEBHOOK ERROR: {e}")
            time.sleep(5)
    return None

def download_and_save_file(url, output_base):
    try:
        r = requests.get(url, stream=True, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()

        os.makedirs(os.path.dirname(output_base), exist_ok=True)

        if "zip" in r.headers.get("Content-Type", "") or url.endswith(".zip"):
            if os.path.exists(EXTRACT_DIR):
                shutil.rmtree(EXTRACT_DIR)

            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                z.extractall(EXTRACT_DIR)

            for f in os.listdir(EXTRACT_DIR):
                shutil.move(os.path.join(EXTRACT_DIR, f), f"{output_base}_{f}")
        else:
            with open(f"{output_base}.csv", "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)

    except Exception as e:
        log_error(f"DOWNLOAD ERROR: {e}")

def trigger(url, token_fn, method="GET", payload=None):
    headers = {
        "x-id-partner-request": str(uuid.uuid4()),
        "access_token": token_fn(),
        "accept": "*/*",
    }

    if method == "POST":
        r = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
    else:
        r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)

    if not r.ok:
        raise RuntimeError(f"{r.status_code} - {r.text}")

# =========================
# REPORTS
# =========================
def process_simple(url, prev, token_fn, name):
    trigger(url, token_fn)
    time.sleep(60)

    file_url = fetch_new_file_url(prev)
    if not file_url:
        return prev

    download_and_save_file(file_url, name)
    return file_url

def process_performance(prev, token_fn, prefix, accounts, start_date, end_date):
    last = prev

    for acc in accounts:
        payload = {
            "accountId": acc,
            "startDate": start_date,
            "endDate": end_date
        }

        try:
            trigger(BTG_API_PERFORMANCE_ACCOUNT_URL, token_fn, "POST", payload)
        except Exception as e:
            log_error(f"PERF ERROR {acc}: {e}")
            continue

        time.sleep(60)

        file_url = fetch_new_file_url(last)
        if not file_url:
            continue

        download_and_save_file(file_url, f"{OUTPUT_DIR}/{prefix}_performance_{acc}")
        last = file_url

    return last

# =========================
# MAIN
# =========================
def run():
    if not API_KEY:
        raise Exception("API KEY missing")

    runs = [
        ("consultoria", tk.manage_token_consultoria),
        ("gen", tk.manage_token_gen),
    ]

    accounts = ["123456", "7891011"]

    end = dt.date.today()
    start = end - dt.timedelta(days=30)

    start = start.strftime("%Y-%m-%d")
    end = end.strftime("%Y-%m-%d")

    for prefix, token_fn in runs:
        print(f"\nRUN {prefix}")

        last = read_last_url()

        last = process_simple(BTG_API_BASE_URL, last, token_fn, f"{OUTPUT_DIR}/{prefix}_base")
        last = process_simple(BTG_API_REGISTRATION_URL, last, token_fn, f"{OUTPUT_DIR}/{prefix}_cad")
        last = process_simple(BTG_API_POSITION_URL, last, token_fn, f"{OUTPUT_DIR}/{prefix}_pos")
        last = process_simple(BTG_API_BANKING_URL, last, token_fn, f"{OUTPUT_DIR}/{prefix}_bank")

        last = process_performance(last, token_fn, prefix, accounts, start, end)

        last = process_simple(BTG_API_MOVEMENTS_URL, last, token_fn, f"{OUTPUT_DIR}/{prefix}_mov")

if __name__ == "__main__":
    run()