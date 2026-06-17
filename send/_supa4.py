import pandas as pd
import numpy as np
from supabase import create_client, Client
import warnings
import math
import re
from typing import List, Dict, Any

# --- CONFIGURAÇÃO ---
SUPABASE_URL = "SUA_URL"
# ATENÇÃO: Use a chave 'service_role' (secret) aqui para ignorar o bloqueio de RLS!
SUPABASE_KEY = "SUA_KEY_SERVICE_ROLE"

import sys
if len(sys.argv) > 1:
    CSV_PATH = sys.argv[1]
else:
    CSV_PATH = "merged_consultoria.csv"


try:
    from supa_base_client import get_supabase_client
    supabase = get_supabase_client()
except ImportError:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

warnings.filterwarnings("ignore")

# --- FUNÇÕES DE LIMPEZA ORIGINAIS ---

def clean_cpf_cnpj(val):
    if pd.isna(val) or val == '':
        return None
    s = re.sub(r'\D', '', str(val))
    if not s:
        return None
    # Pad to 11 digits for CPF (<=11) or 14 for CNPJ (>11)
    if len(s) <= 11:
        return s.zfill(11)
    else:
        return s.zfill(14)

def clean_currency(val):
    if pd.isna(val) or val == '': return None
    s = str(val).replace('R$', '').replace(' ', '')
    try:
        if ',' in s and '.' in s: s = s.replace('.', '').replace(',', '.')
        elif ',' in s: s = s.replace(',', '.')
        f = float(s)
        return f if not (math.isinf(f) or math.isnan(f)) else None
    except:
        return None

def clean_date(val):
    if pd.isna(val) or val == '': return None
    try:
        dt = pd.to_datetime(val, dayfirst=True, errors='coerce')
        if pd.isna(dt): return None
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return None

def clean_int_pandas(val):
    if pd.isna(val) or val == '': return None
    s = str(val).replace('.', '').replace(',', '')
    try: return int(float(s))
    except: return None

def clean_phone(val):
    if pd.isna(val) or val == '': return None
    s = str(val).strip()
    if s.endswith(',0'):
        s = s[:-2]
    elif s.endswith('.0'):
        s = s[:-2]
    return s if s else None

def sanitize_records(records: List[Dict], int_columns: List[str]) -> List[Dict]:
    """Garante Inteiros Puros no JSON final"""
    for row in records:
        for col in int_columns:
            val = row.get(col)
            if val is not None:
                try:
                    row[col] = int(float(val))
                except:
                    row[col] = None
    return records

def safe_prepare_dataframe(df_source: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
    existing = [c for c in mapping.keys() if c in df_source.columns]
    df_new = df_source[existing].rename(columns={c: mapping[c] for c in existing}).copy()
    for target in mapping.values():
        if target not in df_new.columns:
            df_new[target] = None
    return df_new

def to_json_safe(df: pd.DataFrame) -> List[Dict]:
    df_obj = df.astype(object)
    df_clean = df_obj.where(pd.notnull(df_obj), None)
    return df_clean.to_dict(orient='records')


# --- NOVA LÓGICA: NORMALIZAÇÃO E LOG DE AUDITORIA ---

def normalize_for_comparison(val):
    """
    Padroniza os valores para evitar que o script ache que houve mudança 
    só por causa de formatação de data, zeros à direita ou tipos nulos.
    """
    if pd.isna(val) or val is None or str(val).strip() == '' or str(val).strip().lower() in ['nan', 'nat', 'none', 'null']:
        return None
    
    s = str(val).strip()
    
    # Normaliza Datas (remove o 'T' e fuso horário do Supabase)
    if len(s) >= 10 and s[4] == '-' and s[7] == '-':
        s = s.replace('T', ' ').split('+')[0].split('Z')[0].strip()
        if s.endswith(" 00:00:00"):
            s = s.replace(" 00:00:00", "")
            
    # Normaliza Números (100.0 == 100)
    try:
        f = float(s)
        if f.is_integer():
            return str(int(f))
        return str(f)
    except ValueError:
        pass
        
    return s

def get_record_changes(new_rec: Dict, old_rec: Dict) -> List[Dict]:
    """
    Compara as versões normalizadas. Só aciona o log se a informação REAL for diferente.
    """
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

    # 1. VERIFICAÇÃO DE AUSENTES (Estão no Banco, mas não no CSV)
    # Usando normalize_for_comparison nos IDs para não dar falso positivo
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
                    "action": "AUSENTE_NO_CSV", # Trocado de 'DELETE' para evitar sustos
                    "column_name": None,
                    "old_value": "Estava no banco",
                    "new_value": "Não veio no arquivo atual"
                })
            # Apenas registra no log, NUNCA deleta a linha principal
            supabase.table("tb_audit_log").insert(missing_logs).execute()
            
    except Exception as e:
        print(f"   -> Erro ao verificar ausentes: {e}")

    # 2. PROCESSAMENTO EM LOTES (Updates e Inserts)
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
                        # Para cada coluna que mudou DE FATO, cria uma linha de log
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
                    # É um registro novo (Insert)
                    audit_logs.append({
                        "table_name": table_name,
                        "record_id": pk_val,
                        "action": "INSERT",
                        "column_name": None,
                        "old_value": None,
                        "new_value": "Novo registro inserido"
                    })
                    records_to_upsert.append(new_row)

            # 3. Envia os logs para a tabela de Auditoria
            if audit_logs:
                supabase.table("tb_audit_log").insert(audit_logs).execute()
                total_logs += len(audit_logs)

            # 4. Faz o Upsert dos dados novos/modificados na tabela principal
            if records_to_upsert:
                supabase.table(table_name).upsert(records_to_upsert).execute()
                total_upserts += len(records_to_upsert)

        except Exception as e:
            print(f"ERRO CRÍTICO NO LOTE {i}: {e}")
            raise e

    print(f"   -> Resumo: {total_upserts} registros modificados/inseridos. {total_logs} eventos de log gerados.")


# --- PIPELINE PRINCIPAL ---

def run_pipeline():
    print("--- INICIANDO SMART SYNC ---")
    
    try:
        df = pd.read_csv(CSV_PATH, sep=';', dtype=str, on_bad_lines='skip')
        if len(df.columns) < 2:
            df = pd.read_csv(CSV_PATH, sep=',', dtype=str, on_bad_lines='skip')
    except Exception as e:
        print(f"Erro CSV: {e}")
        return

    df.columns = df.columns.str.strip()

    # 1. ASSESSORES
    map_assessor = {'cge_officer': 'cge_officer', 'nm_officer': 'nm_officer', 'email_assessor': 'email_assessor', 'cge_partner': 'cge_partner', 'nm_partner': 'nm_partner', 'tipo_parceiro': 'tipo_parceiro'}
    df_assessor = safe_prepare_dataframe(df, map_assessor)
    
    if 'cge_officer' in df_assessor.columns:
        df_assessor['cge_officer'] = df_assessor['cge_officer'].apply(clean_int_pandas)
        df_assessor['cge_partner'] = df_assessor['cge_partner'].apply(clean_int_pandas)
        df_assessor = df_assessor.dropna(subset=['cge_officer']).drop_duplicates(subset=['cge_officer'])
        
        records = to_json_safe(df_assessor)
        records = sanitize_records(records, ['cge_officer', 'cge_partner'])
        
        smart_sync_table('tb_assessor', records, 'cge_officer')

    # 2. CLIENTES
    col_prox_rev = 'dt_prox_revisao_cadastral' if 'dt_prox_revisao_cadastral' in df.columns else 'dt_prox_revisao_castral'
    map_cliente = {
        'documento_cpf_cnpj': 'documento_cpf_cnpj',
        'id_cliente': 'id_cliente_original',
        'nome_completo': 'nome_completo', 'dt_nascimento': 'dt_nascimento', 'genero': 'genero', 'profissao': 'profissao', 'estado_civil': 'estado_civil', 'nacionalidade': 'nacionalidade', 'celular': 'celular', 'telefone': 'telefone', 'email': 'email_principal', 'email_acesso': 'email_acesso', 'email_comunicacao': 'email_comunicacao', 'documento_tipo': 'documento_tipo', 'documento': 'documento_numero', 'documento_dt_emissao': 'documento_dt_emissao', 'endereco_completo': 'endereco_completo', 'endereco_cidade': 'endereco_cidade', 'endereco_estado': 'endereco_estado', 'endereco_cep': 'endereco_cep', 'suitability': 'suitability', 'dt_vencimento_suitability': 'dt_vencimento_suitability', 'tipo_cliente': 'tipo_cliente', 'tipo_investidor': 'tipo_investidor', 'faixa_cliente': 'faixa_cliente', 'perfil_acesso': 'perfil_acesso', 'residente': 'residente', 'idade': 'idade', 'cpf_conjuge': 'cpf_conjuge', 'dt_ult_revisao_cadastral': 'dt_ult_revisao_cadastral', col_prox_rev: 'dt_prox_revisao_cadastral', 'pendencia_cadastral': 'pendencia_cadastral', 'vencimento_cadastro': 'vencimento_cadastro'
    }
    df_cliente = safe_prepare_dataframe(df, map_cliente)
    
    if 'documento_cpf_cnpj' in df_cliente.columns:
        df_cliente['documento_cpf_cnpj'] = df_cliente['documento_cpf_cnpj'].apply(clean_cpf_cnpj)
        
    for c in df_cliente.columns:
        if c.startswith('dt_') or c in ['dt_nascimento', 'vencimento_cadastro']:
            df_cliente[c] = df_cliente[c].apply(clean_date)
            
    if 'telefone' in df_cliente.columns:
        df_cliente['telefone'] = df_cliente['telefone'].apply(clean_phone)
    if 'celular' in df_cliente.columns:
        df_cliente['celular'] = df_cliente['celular'].apply(clean_phone)
            
    if 'documento_cpf_cnpj' in df_cliente.columns:
        df_cliente = df_cliente.dropna(subset=['documento_cpf_cnpj']).drop_duplicates(subset=['documento_cpf_cnpj'])
        records = to_json_safe(df_cliente)
        records = sanitize_records(records, ['idade'])
        
        smart_sync_table('tb_cliente', records, 'documento_cpf_cnpj')

    # 3. CONTAS
    map_conta = {
        'nr_conta': 'nr_conta', 'documento_cpf_cnpj': 'documento_cpf_cnpj', 'cge_officer': 'cge_officer', 'status': 'status', 'carteira_administrada': 'carteira_administrada', 'termo_curva_rf': 'termo_curva_rf', 'dt_abertura': 'dt_abertura', 'dt_encerramento': 'dt_encerramento', 'dt_primeiro_investimento': 'dt_primeiro_investimento', 'dt_ultimo_aporte': 'dt_ultimo_aporte', 'dt_vinculo': 'dt_vinculo', 'dt_vinculo_escritorio': 'dt_vinculo_escritorio', 'vl_pl_declarado': 'vl_pl_declarado', 'pl_total': 'pl_total', 'vl_rendimento_total': 'vl_rendimento_total', 'vl_rendimento_anual': 'vl_rendimento_anual', 'pl_conta_corrente': 'pl_conta_corrente', 'pl_fundos': 'pl_fundos', 'pl_renda_fixa': 'pl_renda_fixa', 'pl_renda_variavel': 'pl_renda_variavel', 'pl_previdencia': 'pl_previdencia', 'pl_derivativos': 'pl_derivativos', 'pl_valores_transito': 'pl_valores_transito', 'qtd_aportes': 'qtd_aportes', 'vl_aportes': 'vl_aportes', 'vl_retiradas': 'vl_retiradas', 'qtd_ativos': 'qtd_ativos', 'qtd_fundos': 'qtd_fundos', 'qtd_renda_fixa': 'qtd_renda_fixa', 'qtd_renda_variavel': 'qtd_renda_variavel', 'qtd_previdencia': 'qtd_previdencia', 'qtd_derivativos': 'qtd_derivativos', 'qtd_valores_transito': 'qtd_valores_transito'
    }
    df_conta = safe_prepare_dataframe(df, map_conta)

    if 'documento_cpf_cnpj' in df_conta.columns:
        df_conta['documento_cpf_cnpj'] = df_conta['documento_cpf_cnpj'].apply(clean_cpf_cnpj)

    cols_inteiro = [
        'nr_conta', 'cge_officer', 'qtd_aportes', 'qtd_ativos', 'qtd_fundos', 
        'qtd_renda_fixa', 'qtd_renda_variavel', 'qtd_previdencia', 
        'qtd_derivativos', 'qtd_valores_transito'
    ]
    
    for col in df_conta.columns:
        if col.startswith('vl_') or col.startswith('pl_'):
            df_conta[col] = df_conta[col].apply(clean_currency)
        elif col.startswith('dt_'):
            df_conta[col] = df_conta[col].apply(clean_date)

    if 'nr_conta' in df_conta.columns and 'documento_cpf_cnpj' in df_conta.columns:
        df_conta = df_conta.dropna(subset=['nr_conta', 'documento_cpf_cnpj'])
        records = to_json_safe(df_conta)
        records = sanitize_records(records, cols_inteiro)
        
        smart_sync_table('tb_conta', records, 'nr_conta')

    print("\n--- SUCESSO COMPLETO ---")

if __name__ == "__main__":
    run_pipeline()