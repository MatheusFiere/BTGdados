import pandas as pd
import numpy as np
from supabase import create_client, Client
import warnings
import math
import re
from typing import List, Dict, Any

# --- CONFIGURATION ---
SUPABASE_URL = "SUA_URL"
SUPABASE_KEY = "SUA_KEY"

import sys
from pathlib import Path

if len(sys.argv) > 1:
    FILE_ORDENS = Path(sys.argv[1])
else:
    # Resolve default CSV relative to project root (all3)
    base_dir = Path(__file__).resolve().parents[2]  # .../all3/send -> .../all3
    FILE_ORDENS = base_dir / "update" / "diretorio_arq" / "consultoria_Ordens_Bolsa.csv"
FILE_ORDENS = str(FILE_ORDENS)


# Load Supabase client (tries to use .env via supa_base_client)
try:
    from supa_base_client import get_supabase_client
    supabase = get_supabase_client()
except ImportError:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

warnings.filterwarnings("ignore")

# --- CLEANING HELPERS ---
def clean_currency(val):
    if pd.isna(val) or val == '':
        return None
    s = str(val).replace('R$', '').replace(' ', '')
    try:
        if ',' in s and '.' in s:
            s = s.replace('.', '').replace(',', '.')
        elif ',' in s:
            s = s.replace(',', '.')
        f = float(s)
        return f if not (math.isinf(f) or math.isnan(f)) else None
    except Exception:
        return None

def clean_int(val):
    if pd.isna(val) or val == '':
        return None
    s = str(val).split('.')[0].replace(',', '')
    try:
        return int(s)
    except Exception:
        return None

def clean_date(val):
    if pd.isna(val) or val == '':
        return None
    try:
        dt = pd.to_datetime(val, dayfirst=True, errors='coerce')
        if pd.isna(dt):
            return None
        return dt.strftime('%Y-%m-%d')
    except Exception:
        return None

def clean_bool(val):
    if pd.isna(val) or val == '':
        return None
    s = str(val).strip().lower()
    if s in ('t', 'true', '1', 'yes', 's', 'sim'):
        return True
    if s in ('f', 'false', '0', 'no', 'nao', 'não'):
        return False
    return None

def to_json_safe(df: pd.DataFrame) -> List[Dict]:
    df_obj = df.astype(object)
    df_clean = df_obj.where(pd.notnull(df_obj), None)
    return df_clean.to_dict(orient='records')

def sanitize_records(records: List[Dict], int_columns: List[str]) -> List[Dict]:
    for row in records:
        for col in int_columns:
            val = row.get(col)
            if val is not None:
                try:
                    row[col] = int(float(val))
                except Exception:
                    row[col] = None
    return records

def upload_in_chunks(table_name: str, data: List[Dict[str, Any]], batch_size: int = 500):
    if not data:
        return
    print(f"[{table_name}] Uploading {len(data)} rows (upsert)...")
    # Choose conflict column based on table name
    conflict_col = None
    if table_name == 'tb_nnm':
        conflict_col = 'nr_conta'
    elif table_name == 'tb_ordens_bolsa':
        conflict_col = 'account'
    for i in range(0, len(data), batch_size):
        chunk = data[i:i + batch_size]
        try:
            if conflict_col:
                supabase.table(table_name).upsert(chunk, on_conflict=conflict_col).execute()
            else:
                supabase.table(table_name).insert(chunk).execute()
            print(f"[{table_name}] Batch {i // batch_size + 1} OK ({len(chunk)} rows)")
        except Exception as e:
            print(f"ERROR batch {i // batch_size + 1}: {e}")
            if chunk:
                print(f"Sample data: {chunk[0]}")

# FK validation – ensure account exists
def get_valid_accounts():
    print("Fetching valid accounts from tb_conta...")
    try:
        resp = supabase.table('tb_conta').select('nr_conta').execute()
        return {row['nr_conta'] for row in resp.data}
    except Exception as e:
        print(f"Error fetching accounts: {e}")
        return set()

def run_ordens_pipeline():
    print("--- Processing Ordens Bolsa ---")
    try:
        df = pd.read_csv(FILE_ORDENS, sep=',', dtype=str, on_bad_lines='skip', encoding='utf-8')
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(FILE_ORDENS, sep=',', dtype=str, on_bad_lines='skip', encoding='latin-1')
        except Exception as e:
            print(f"Failed to read CSV: {e}")
            return
    except Exception as e:
        print(f"Failed to read CSV: {e}")
        return

    df.columns = df.columns.str.strip()
    print(f"Columns found: {list(df.columns)}")
    print(f"Rows read: {len(df)}")

    # Mapping CSV columns to Supabase table tb_ordens_bolsa
    map_ordens = {
        'account': 'account',
        'avgPx': 'avgPx',
        'clOrdId': 'clOrdId',
        'creationDate': 'creationDate',
        'cumQty': 'cumQty',
        'expireTime': 'expireTime',
        'leavesQty': 'leavesQty',
        'ordStatus': 'ordStatus',
        'ordStatusDescription': 'ordStatusDescription',
        'orderId': 'orderId',
        'orderQty': 'orderQty',
        'orderStrategy': 'orderStrategy',
        'orderType': 'orderType',
        'origin': 'origin',
        'price': 'price',
        'sendingTime': 'sendingTime',
        'side': 'side',
        'sideDescription': 'sideDescription',
        'startPrice': 'startPrice',
        'startTrigger': 'startTrigger',
        'stopTrigger': 'stopTrigger',
        'symbol': 'symbol',
        'text': 'text',
        'traderType': 'traderType',
        'transactTime': 'transactTime',
    }

    existing_cols = [c for c in map_ordens.keys() if c in df.columns]
    df_ord = df[existing_cols].rename(columns={c: map_ordens[c] for c in existing_cols}).copy()

    # Clean primary key (account)
    if 'account' not in df_ord.columns:
        print("ERROR: 'account' column missing.")
        return
    df_ord['account'] = df_ord['account'].apply(clean_int)
    df_ord = df_ord.dropna(subset=['account'])

    # FK validation – ensure account exists in tb_conta
    valid_accounts = get_valid_accounts()
    if valid_accounts:
        before = len(df_ord)
        df_ord = df_ord[df_ord['account'].isin(valid_accounts)]
        removed = before - len(df_ord)
        if removed > 0:
            print(f"Removed {removed} rows with unknown accounts.")
    else:
        print("WARNING: No accounts found, upload may fail.")

    # Clean other fields
    if 'data_ordem' in df_ord.columns:
        df_ord['data_ordem'] = df_ord['data_ordem'].apply(clean_date)
    if 'qtde' in df_ord.columns:
        df_ord['qtde'] = df_ord['qtde'].apply(clean_int)
    if 'preco' in df_ord.columns:
        df_ord['preco'] = df_ord['preco'].apply(clean_currency)
    if 'valor_total' in df_ord.columns:
        df_ord['valor_total'] = df_ord['valor_total'].apply(clean_currency)
    # Convert possible boolean columns
    for bool_col in ['situacao']:
        if bool_col in df_ord.columns:
            df_ord[bool_col] = df_ord[bool_col].apply(clean_bool)

    # Replace isolated dashes with NaN
    df_ord = df_ord.replace(r'^\s*-\s*$', np.nan, regex=True)

    records = to_json_safe(df_ord)
    records = sanitize_records(records, ['account'])
    print(f"Ready to upload {len(records)} records to tb_ordens_bolsa.")
    upload_in_chunks('tb_ordens_bolsa', records)
    print("--- Finished Ordens Bolsa ---")

if __name__ == "__main__":
    run_ordens_pipeline()
