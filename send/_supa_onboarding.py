import pandas as pd
import numpy as np
from supabase import create_client, Client
import warnings
import math
import sys
import os

# --- CONFIGURAÇÃO ---
SUPABASE_URL = "SUA_URL"
SUPABASE_KEY = "SUA_KEY"

if len(sys.argv) > 1:
    FILE_ONBOARDING = sys.argv[1]
else:
    FILE_ONBOARDING = "update/diretorio_arq/consultoria_Dados_Onboarding_Partner.csv"

try:
    from supa_base_client import get_supabase_client
    supabase = get_supabase_client()
except ImportError:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

warnings.filterwarnings("ignore")

# --- FUNÇÕES DE LIMPEZA ---
def clean_int(val):
    if pd.isna(val) or val == '': return None
    s = str(val).split('.')[0].replace(',', '').strip()
    try:
        return int(s)
    except:
        return None

def clean_str(val):
    if pd.isna(val): return None
    s = str(val).strip()
    if s.lower() in ('nan', 'null', 'none', '<na>', ''): return None
    return s

def run_onboarding_pipeline():
    print(f"\n--- PROCESSANDO ONBOARDING: {FILE_ONBOARDING} ---")

    if not os.path.exists(FILE_ONBOARDING):
        print(f"ERRO: Arquivo não encontrado: {FILE_ONBOARDING}")
        return

    try:
        # Tenta ler com separador ';' e depois ',' se falhar
        df = pd.read_csv(FILE_ONBOARDING, sep=';', dtype=str, on_bad_lines='skip', encoding='utf-8')
        if len(df.columns) < 2:
            df = pd.read_csv(FILE_ONBOARDING, sep=',', dtype=str, on_bad_lines='skip', encoding='utf-8')
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(FILE_ONBOARDING, sep=';', dtype=str, on_bad_lines='skip', encoding='latin-1')
            if len(df.columns) < 2:
                df = pd.read_csv(FILE_ONBOARDING, sep=',', dtype=str, on_bad_lines='skip', encoding='latin-1')
        except Exception as e:
            print(f"Erro ao ler CSV (Encoding Latin-1): {e}")
            return
    except Exception as e:
        print(f"Erro ao ler CSV: {e}")
        return

    df.columns = df.columns.str.strip()
    print(f"Total de linhas lidas do CSV: {len(df)}")

    # Colunas esperadas na tabela do Supabase: id, nome, cge_assessor, cge_parceiro, status, motivo_status, created_at
    cols_required = ['nome', 'status']
    for col in cols_required:
        if col not in df.columns:
            print(f"ERRO: Coluna essencial '{col}' não encontrada no arquivo CSV!")
            return

    # Limpeza e Deduplicação no DataFrame local (mantendo o último registro para cada nome)
    df['nome'] = df['nome'].apply(clean_str)
    df = df.dropna(subset=['nome'])
    
    # Se houver duplicados de nome no mesmo lote, pegamos o último (mais recente)
    df = df.drop_duplicates(subset=['nome'], keep='last')
    
    print(f"Total de candidatos únicos para processar: {len(df)}")

    # 1. Buscar registros existentes no banco para comparação
    try:
        print("Buscando registros existentes no Supabase (tb_status_onboarding)...")
        db_response = supabase.table("tb_status_onboarding").select("*").execute()
        # Mapeia nome (em minúsculas) para a linha do banco
        db_map = {row['nome'].strip().lower(): row for row in db_response.data if row.get('nome')}
        print(f"Encontrados {len(db_map)} registros no banco.")
    except Exception as e:
        print(f"Erro ao consultar tb_status_onboarding: {e}")
        return

    # 2. Iterar sobre os registros do CSV e decidir entre INSERT ou UPDATE
    inserts = []
    updates_count = 0

    for _, row in df.iterrows():
        nome_csv = row['nome']
        nome_key = nome_csv.lower()

        cge_assessor = clean_int(row.get('cge_assessor'))
        cge_parceiro = clean_int(row.get('cge_parceiro'))
        status = clean_str(row.get('status'))
        motivo_status = clean_str(row.get('motivo_status'))
        numero_conta = clean_str(row.get('numero_conta'))

        record = {
            'nome': nome_csv,
            'cge_assessor': cge_assessor,
            'cge_parceiro': cge_parceiro,
            'status': status,
            'motivo_status': motivo_status,
            'numero_conta': numero_conta
        }

        if nome_key in db_map:
            db_row = db_map[nome_key]
            db_id = db_row['id']

            # Verifica se há diferenças entre o banco e o CSV
            has_changed = False
            changes = {}

            # Comparação normalizando tipos (Ex: None vs None, int vs int)
            for field in ['cge_assessor', 'cge_parceiro', 'status', 'motivo_status', 'numero_conta']:
                csv_val = record[field]
                db_val = db_row.get(field)
                
                # Trata int de forma correta (no banco pode vir como int)
                if field in ('cge_assessor', 'cge_parceiro') and db_val is not None:
                    db_val = int(db_val)
                
                if csv_val != db_val:
                    has_changed = True
                    changes[field] = f"'{db_val}' -> '{csv_val}'"

            if has_changed:
                try:
                    # Faz o update no banco para esse ID
                    supabase.table("tb_status_onboarding").update(record).eq("id", db_id).execute()
                    print(f"  [UPDATE] Candidate: '{nome_csv}' | Changes: {changes}")
                    updates_count += 1
                except Exception as ex:
                    print(f"  [ERRO UPDATE] Candidate '{nome_csv}': {ex}")
        else:
            # Novo registro
            inserts.append(record)

    # Executa os inserts em lotes se houver
    if inserts:
        batch_size = 100
        for i in range(0, len(inserts), batch_size):
            chunk = inserts[i:i + batch_size]
            try:
                supabase.table("tb_status_onboarding").insert(chunk).execute()
                for record_ins in chunk:
                    print(f"  [INSERT] Candidate: '{record_ins['nome']}' | Status: '{record_ins['status']}'")
            except Exception as ex:
                print(f"  [ERRO INSERT] Erro ao inserir lote: {ex}")

    print(f"Sincronização concluída: {len(inserts)} inseridos, {updates_count} atualizados.")

if __name__ == "__main__":
    run_onboarding_pipeline()
