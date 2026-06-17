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
    FILE_BANKING = sys.argv[1]
else:
    FILE_BANKING = "banking.csv"

try:
    from supa_base_client import get_supabase_client
    supabase = get_supabase_client()
except ImportError:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

warnings.filterwarnings("ignore")

# --- FUNÇÕES DE LIMPEZA (IGUAIS) ---
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

def normalize_for_comparison(val):
    if pd.isna(val) or val is None or str(val).strip() == '' or str(val).strip().lower() in ['nan', 'nat', 'none', 'null']:
        return None
    s = str(val).strip()
    if len(s) >= 10 and s[4] == '-' and s[7] == '-':
        s = s.replace('T', ' ').split('+')[0].split('Z')[0].strip()
        if s.endswith(" 00:00:00"):
            s = s.replace(" 00:00:00", "")
    try:
        f = float(s)
        if f.is_integer():
            return str(int(f))
        return str(f)
    except ValueError:
        pass
    return s

def get_record_changes(new_rec: Dict, old_rec: Dict) -> List[Dict]:
    changes = []
    for key, raw_new_val in new_rec.items():
        if key in ['created_at', 'updated_at']: continue
        raw_old_val = old_rec.get(key)
        new_val = normalize_for_comparison(raw_new_val)
        old_val = normalize_for_comparison(raw_old_val)
        if new_val != old_val:
            changes.append({
                "column_name": key,
                "old_value": old_val,
                "new_value": new_val
            })
    return changes

def smart_sync_table(table_name: str, new_data: List[Dict], pk_field: str, batch_size=500):
    if not new_data: return
    print(f"\n[{table_name}] Processando {len(new_data)} registros do CSV...")

    all_incoming_ids = set(normalize_for_comparison(r[pk_field]) for r in new_data if r.get(pk_field) is not None)
    
    try:
        db_response = supabase.table(table_name).select(pk_field).execute()
        all_db_ids = set(normalize_for_comparison(row[pk_field]) for row in db_response.data if row.get(pk_field) is not None)
        missing_ids = all_db_ids - all_incoming_ids
        if missing_ids:
            print(f"   -> Atenção: {len(missing_ids)} registros não vieram no CSV (Sumiu).")
            missing_logs = []
            for m_id in missing_ids:
                missing_logs.append({
                    "table_name": table_name,
                    "record_id": m_id,
                    "action": "AUSENTE_NO_CSV",
                    "column_name": None,
                    "old_value": "Estava no banco",
                    "new_value": "Não veio no arquivo atual"
                })
            supabase.table("tb_audit_log").insert(missing_logs).execute()
    except Exception as e:
        print(f"   -> Erro ao verificar ausentes: {e}")

    total_upserts = 0
    total_logs = 0

    for i in range(0, len(new_data), batch_size):
        chunk_new = new_data[i:i + batch_size]
        ids_to_check = [str(r[pk_field]) for r in chunk_new if r.get(pk_field) is not None]
        if not ids_to_check: continue

        try:
            response = supabase.table(table_name).select("*").in_(pk_field, ids_to_check).execute()
            existing_map = {str(item[pk_field]): item for item in response.data}
            
            audit_logs = []       
            records_to_upsert = [] 
            
            for new_row in chunk_new:
                pk_val = str(new_row[pk_field])
                if pk_val in existing_map:
                    old_row = existing_map[pk_val]
                    changes = get_record_changes(new_row, old_row)
                    if changes:
                        for change in changes:
                            audit_logs.append({
                                "table_name": table_name,
                                "record_id": pk_val,
                                "action": "UPDATE",
                                "column_name": change["column_name"],
                                "old_value": change["old_value"],
                                "new_value": change["new_value"]
                            })
                        records_to_upsert.append(new_row)
                else:
                    audit_logs.append({
                        "table_name": table_name,
                        "record_id": pk_val,
                        "action": "INSERT",
                        "column_name": None,
                        "old_value": None,
                        "new_value": "Novo registro inserido"
                    })
                    records_to_upsert.append(new_row)

            if audit_logs:
                supabase.table("tb_audit_log").insert(audit_logs).execute()
                total_logs += len(audit_logs)

            if records_to_upsert:
                supabase.table(table_name).upsert(records_to_upsert).execute()
                total_upserts += len(records_to_upsert)

        except Exception as e:
            print(f"ERRO CRÍTICO NO LOTE {i}: {e}")
            raise e

    print(f"   -> Resumo: {total_upserts} registros modificados/inseridos. {total_logs} eventos de log gerados.")

# --- PIPELINE DE BANKING COM SEGURANÇA DE CHAVE ESTRANGEIRA ---

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

def run_banking_pipeline():
    print("--- PROCESSANDO BANKING ---")
    
    try:
        df = pd.read_csv(FILE_BANKING, sep=';', dtype=str, on_bad_lines='skip')
    except Exception as e:
        print(f"Erro ao ler CSV: {e}")
        return

    df.columns = df.columns.str.strip()

    # Mapeamento
    map_banking = {
        'nr_conta': 'nr_conta', 'nome_cliente': 'nome_cliente', 'termo_consentimento': 'termo_consentimento',
        'fopa': 'fopa', 'tipo_conta': 'tipo_conta', 'primeira_ativacao_conta': 'primeira_ativacao_conta',
        'conta_ativa_30dd': 'conta_ativa_30dd', 'cartao': 'cartao', 'pap_clean_cartao': 'pap_clean_cartao',
        'pap_lastreado_cartao': 'pap_lastreado_cartao', 'c_clean_cartao': 'c_clean_cartao',
        'c_lastreado_cartao': 'c_lastreado_cartao', 'primeira_ativacao_cartao': 'primeira_ativacao_cartao',
        'cartao_ativa_30dd': 'cartao_ativa_30dd', 'cheque_aprovado': 'cheque_aprovado',
        'cheque_contratado': 'cheque_contratado', 'cp_aprovado': 'cp_aprovado', 'cp_contratado': 'cp_contratado',
        'prioridade_contato_cp': 'prioridade_contato_cp', 'cobranca': 'cobranca', 'saldo_banking': 'saldo_banking',
        'prog_relacionamento': 'prog_relacionamento', 'modulo_viagem': 'modulo_viagem', 'modulo_seguranca': 'modulo_seguranca',
        'modulo_transacional': 'modulo_transacional', 'modulo_investimento': 'modulo_investimento',
        'seguro_vida': 'seguro_vida', 'seguro_conta_cartao': 'seguro_conta_cartao', 'seguro_prestamista': 'seguro_prestamista',
        'assessor': 'assessor', 'cd_cge_partner': 'cd_cge_partner', 'acco_opening_date': 'acco_opening_date',
        'carrinho_abandonado_card': 'carrinho_abandonado_card', 'heavy_user': 'heavy_user',
        'dt_aquisicao_cartao': 'dt_aquisicao_cartao', 'alto_propenso_cp': 'alto_propenso_cp',
        'debito_automatico': 'debito_automatico', 'portabilidade': 'portabilidade', 'chave_pix': 'chave_pix',
        'auc_total': 'auc_total', 'venda_portal': 'venda_portal', 'upgrade': 'upgrade',
        'carrinho_consorcio': 'carrinho_consorcio', 'seguro_auto': 'seguro_auto', 'seguro_viagem': 'seguro_viagem',
        'status_consentimento': 'status_consentimento'
    }
    
    existing_cols = [c for c in map_banking.keys() if c in df.columns]
    df_bank = df[existing_cols].rename(columns={c: map_banking[c] for c in existing_cols}).copy()
    
    # 1. Limpeza de Inteiros e NR_CONTA
    if 'nr_conta' in df_bank.columns:
        df_bank['nr_conta'] = df_bank['nr_conta'].apply(clean_int)
        df_bank = df_bank.dropna(subset=['nr_conta'])
    
    # -----------------------------------------------------------
    # 2. VALIDAÇÃO DE CHAVE ESTRANGEIRA
    # -----------------------------------------------------------
    if 'nr_conta' not in df_bank.columns:
        print("AVISO: A coluna 'nr_conta' não foi encontrada no CSV!")
        return

    valid_contas = get_valid_accounts()
    
    if valid_contas:
        initial_len = len(df_bank)
        df_bank = df_bank[df_bank['nr_conta'].isin(valid_contas)]
        final_len = len(df_bank)
        
        diff = initial_len - final_len
        if diff > 0:
            print(f"AVISO: {diff} linhas removidas pois as contas não existem no banco.")
    else:
        print("AVISO: Nenhuma conta encontrada no banco. O upload provavelmente falhará.")

    # 3. Resto das Limpezas
    cols_data = [c for c in df_bank.columns if 'dt_' in c or 'date' in c]
    for c in cols_data:
        df_bank[c] = df_bank[c].apply(clean_date)
        
    cols_float = [c for c in df_bank.columns if 'saldo' in c or 'auc_' in c or 'aprovado' in c or 'contratado' in c or 'pap_clean' in c or 'pap_lastreado' in c or 'c_clean' in c or 'c_lastreado' in c]
    for c in cols_float:
        df_bank[c] = df_bank[c].apply(clean_currency)

    # Convertir '-' para NaN antes de enviar para evitar erros de tipo
    df_bank = df_bank.replace(r'^\s*-\s*$', np.nan, regex=True)

    # Remover contas duplicadas no mesmo arquivo para evitar erro no upsert
    df_bank = df_bank.drop_duplicates(subset=['nr_conta'], keep='last')

    # 4. Upload
    records = to_json_safe(df_bank)
    records = sanitize_records(records, ['nr_conta', 'cd_cge_partner'])
    
    smart_sync_table('tb_banking', records, 'nr_conta', batch_size=500)

    print("--- FIM BANKING ---")

if __name__ == "__main__":
    run_banking_pipeline()
