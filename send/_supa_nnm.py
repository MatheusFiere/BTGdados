import pandas as pd
import numpy as np
from supabase import create_client, Client
import warnings
import math
import re
from typing import List, Dict, Any

# --- CONFIGURAÇÃO ---
SUPABASE_URL = "SUA_URL"
SUPABASE_KEY = "SUA_KEY"

import sys
if len(sys.argv) > 1:
    FILE_NNM = sys.argv[1]
else:
    FILE_NNM = "nnm.csv"

try:
    from supa_base_client import get_supabase_client
    supabase = get_supabase_client()
except ImportError:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

warnings.filterwarnings("ignore")

# --- FUNÇÕES DE LIMPEZA ---
def clean_currency(val):
    if pd.isna(val) or val == '': return None
    s = str(val).replace('R$', '').replace(' ', '')
    try:
        if ',' in s and '.' in s: s = s.replace('.', '').replace(',', '.')
        elif ',' in s: s = s.replace(',', '.')
        f = float(s)
        return f if not (math.isinf(f) or math.isnan(f)) else None
    except: return None

def clean_int(val):
    if pd.isna(val) or val == '': return None
    s = str(val).split('.')[0].replace(',', '')
    try: return int(s)
    except: return None

def clean_date(val):
    if pd.isna(val) or val == '': return None
    try:
        dt = pd.to_datetime(val, dayfirst=True, errors='coerce')
        if pd.isna(dt): return None
        return dt.strftime('%Y-%m-%d')
    except: return None

def clean_bool(val):
    if pd.isna(val) or val == '': return None
    s = str(val).strip().lower()
    if s in ('t', 'true', '1', 'yes', 's', 'sim'): return True
    if s in ('f', 'false', '0', 'no', 'nao', 'não'): return False
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
                try: row[col] = int(float(val))
                except: row[col] = None
    return records

def upload_in_chunks(table_name: str, data: List[Dict[str, Any]], batch_size: int = 500):
    if not data:
        return
    print(f"[{table_name}] Uploading {len(data)} rows (upsert)...")
    # Determine conflict column based on table
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

# --- VALIDAÇÃO FK ---
def get_valid_accounts():
    print("Buscando contas válidas no banco...")
    try:
        response = supabase.table('tb_conta').select('nr_conta').execute()
        valid_ids = {item['nr_conta'] for item in response.data}
        print(f"Encontradas {len(valid_ids)} contas válidas.")
        return valid_ids
    except Exception as e:
        print(f"Erro ao buscar contas: {e}")
        return set()

# --- PIPELINE NNM ---
def run_nnm_pipeline():
    print("--- PROCESSANDO NNM (NET NEW MONEY) ---")

    try:
        df = pd.read_csv(FILE_NNM, sep=';', dtype=str, on_bad_lines='skip', encoding='utf-8')
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(FILE_NNM, sep=';', dtype=str, on_bad_lines='skip', encoding='latin-1')
        except Exception as e:
            print(f"Erro ao ler CSV: {e}")
            return
    except Exception as e:
        print(f"Erro ao ler CSV: {e}")
        return

    df.columns = df.columns.str.strip()
    print(f"Colunas encontradas: {list(df.columns)}")
    print(f"Total de linhas lidas: {len(df)}")

    # Mapeamento de colunas CSV -> tabela do banco
    map_nnm = {
        'nr_conta': 'nr_conta',
        'data_captacao': 'data_captacao',
        'ativo': 'ativo',
        'mercado': 'mercado',
        'cge_officer': 'cge_officer',
        'tipo_lancamento': 'tipo_lancamento',
        'descricao': 'descricao',
        'quantidade': 'quantidade',
        'captacao': 'captacao',
        'is_officer_nnm': 'is_officer_nnm',
        'is_partner_nnm': 'is_partner_nnm',
        'is_channel_nnm': 'is_channel_nnm',
        'is_bu_nnm': 'is_bu_nnm',
        'submercado': 'submercado',
        'submercado_detalhado': 'submercado_detalhado',
    }

    existing_cols = [c for c in map_nnm.keys() if c in df.columns]
    df_nnm = df[existing_cols].rename(columns={c: map_nnm[c] for c in existing_cols}).copy()

    # 1. Limpar e validar nr_conta
    if 'nr_conta' not in df_nnm.columns:
        print("ERRO: Coluna 'nr_conta' não encontrada no CSV!")
        return

    df_nnm['nr_conta'] = df_nnm['nr_conta'].apply(clean_int)
    df_nnm = df_nnm.dropna(subset=['nr_conta'])

    # 2. Validação de FK (só insere contas que existem no banco)
    valid_contas = get_valid_accounts()
    if valid_contas:
        initial_len = len(df_nnm)
        df_nnm = df_nnm[df_nnm['nr_conta'].isin(valid_contas)]
        diff = initial_len - len(df_nnm)
        if diff > 0:
            print(f"AVISO: {diff} linhas removidas pois as contas não existem no banco.")
    else:
        print("AVISO: Nenhuma conta encontrada no banco. O upload pode falhar.")

    # 3. Limpeza de tipos
    if 'data_captacao' in df_nnm.columns:
        df_nnm['data_captacao'] = df_nnm['data_captacao'].apply(clean_date)

    cols_float = ['quantidade', 'captacao']
    for c in cols_float:
        if c in df_nnm.columns:
            df_nnm[c] = df_nnm[c].apply(clean_currency)

    cols_bool = ['is_officer_nnm', 'is_partner_nnm', 'is_channel_nnm', 'is_bu_nnm']
    for c in cols_bool:
        if c in df_nnm.columns:
            df_nnm[c] = df_nnm[c].apply(clean_bool)

    # Substituir traços soltos por NaN
    df_nnm = df_nnm.replace(r'^\s*-\s*$', np.nan, regex=True)

    # 4. Upload
    records = to_json_safe(df_nnm)
    records = sanitize_records(records, ['nr_conta'])

    print(f"Total de registros prontos para envio: {len(records)}")
    upload_in_chunks('tb_nnm', records)

    print("--- FIM NNM ---")

if __name__ == "__main__":
    run_nnm_pipeline()
