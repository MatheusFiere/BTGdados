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
    FILE_POSICAO = sys.argv[1]
else:
    FILE_POSICAO = "posicao.csv"


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

def upload_in_chunks(table_name: str, data: List[Dict[str, Any]], batch_size=1000):
    if not data: return
    print(f"[{table_name}] Uploading {len(data)} rows...")
    for i in range(0, len(data), batch_size):
        chunk = data[i:i + batch_size]
        try:
            # Insert simples pois posição não tem PK única
            supabase.table(table_name).insert(chunk).execute()
            print(f"[{table_name}] Lote {i} OK")
        except Exception as e:
            print(f"ERROR LOTE {i}: {e}")
            if len(chunk) > 0: print(f"DADO: {chunk[0]}")

# --- PIPELINE DE POSIÇÃO COM SEGURANÇA DE CHAVE ESTRANGEIRA ---

def get_valid_accounts():
    """Busca todas as contas cadastradas no Supabase para validar FK"""
    print("Buscando contas válidas no banco...")
    try:
        # Pega apenas a coluna nr_conta para ser leve
        # Nota: Se tiver mais de 1000 contas, precisaria paginar. 
        # Aqui assumo que o .select('*') pega o limite padrão ou ajustado.
        response = supabase.table('tb_conta').select('nr_conta').execute()
        valid_ids = {item['nr_conta'] for item in response.data}
        print(f"Encontradas {len(valid_ids)} contas válidas.")
        return valid_ids
    except Exception as e:
        print(f"Erro ao buscar contas: {e}")
        return set()

def run_posicao_pipeline():
    print("--- PROCESSANDO POSIÇÃO FINANCEIRA ---")
    
    try:
        df = pd.read_csv(FILE_POSICAO, sep=';', dtype=str, on_bad_lines='skip')
    except Exception as e:
        print(f"Erro ao ler CSV: {e}")
        return

    df.columns = df.columns.str.strip()

    # Mapeamento
    map_posicao = {
        'nr_conta': 'nr_conta', 'dt_interface': 'dt_interface', 'dt_movimentacao': 'dt_movimentacao', 'mercado': 'mercado', 'sub_mercado': 'sub_mercado', 'produto': 'produto', 'ativo': 'ativo', 'emissor': 'emissor', 'indexador': 'indexador', 'cnpj_fundo': 'cnpj_fundo', 'cge_fundo': 'cge_fundo', 'tipo': 'tipo', 'tipo_opcao': 'tipo_opcao', 'quantidade': 'quantidade', 'vl_custo': 'vl_custo', 'vl_bruto': 'vl_bruto', 'vl_ir': 'vl_ir', 'vl_iof': 'vl_iof', 'vl_taxa': 'vl_taxa', 'vl_taxa_compra': 'vl_taxa_compra', 'taxa_indexador': 'taxa_indexador', 'vl_preco_mercado': 'vl_preco_mercado', 'vl_preco_compra': 'vl_preco_compra', 'vl_premio': 'vl_premio', 'vl_exercicio': 'vl_exercicio', 'vl_liquido': 'vl_liquido', 'quantidade_contrato': 'quantidade_contrato', 'vl_contrato': 'vl_contrato', 'dt_aquisicao': 'dt_aquisicao', 'dt_exercicio': 'dt_exercicio', 'dt_vencimento': 'dt_vencimento', 'vl_futuro_nao_compoem_pl': 'vl_futuro_nao_compoem_pl', 'vl_aluguel_nao_compoem_pl': 'vl_aluguel_nao_compoem_pl', 'visualizacao_cliente': 'visualizacao_cliente', 'vl_bruto_curva_cliente': 'vl_bruto_curva_cliente', 'ir_curva_cliente': 'ir_curva_cliente', 'iof_curva_cliente': 'iof_curva_cliente', 'vl_liquido_curva_cliente': 'vl_liquido_curva_cliente', 'vl_bruto_curva_mercado': 'vl_bruto_curva_mercado', 'ir_curva_mercado': 'ir_curva_mercado', 'iof_curva_mercado': 'iof_curva_mercado', 'vl_liquido_curva_mercado': 'vl_liquido_curva_mercado', 'cod_certificado': 'cod_certificado', 'tipo_previdencia': 'tipo_previdencia'
    }
    
    existing_cols = [c for c in map_posicao.keys() if c in df.columns]
    df_pos = df[existing_cols].rename(columns={c: map_posicao[c] for c in existing_cols}).copy()
    
    # 1. Limpeza de Inteiros e NR_CONTA
    if 'nr_conta' in df_pos.columns:
        df_pos['nr_conta'] = df_pos['nr_conta'].apply(clean_int)
        df_pos = df_pos.dropna(subset=['nr_conta'])
    
    # -----------------------------------------------------------
    # 2. VALIDAÇÃO DE CHAVE ESTRANGEIRA (IMPORTANTE!)
    # -----------------------------------------------------------
    valid_contas = get_valid_accounts()
    
    if valid_contas:
        initial_len = len(df_pos)
        # Filtra: Mantém apenas linhas onde nr_conta está no set de contas válidas
        df_pos = df_pos[df_pos['nr_conta'].isin(valid_contas)]
        final_len = len(df_pos)
        
        diff = initial_len - final_len
        if diff > 0:
            print(f"AVISO: {diff} linhas removidas pois as contas não existem no banco.")
    else:
        print("AVISO: Nenhuma conta encontrada no banco. O upload provavelmente falhará.")

    # 3. Resto das Limpezas
    cols_data = [c for c in df_pos.columns if c.startswith('dt_')]
    for c in cols_data:
        df_pos[c] = df_pos[c].apply(clean_date)
        
    cols_float = [c for c in df_pos.columns if c.startswith('vl_') or c.startswith('quantidade') or 'taxa' in c or 'ir_' in c or 'iof_' in c]
    for c in cols_float:
        df_pos[c] = df_pos[c].apply(clean_currency)

    # 4. Upload
    records = to_json_safe(df_pos)
    records = sanitize_records(records, ['nr_conta'])
    
    upload_in_chunks('tb_posicao', records)

    print("--- FIM POSIÇÃO ---")

if __name__ == "__main__":
    run_posicao_pipeline()