import pandas as pd
from supabase import create_client
import io
from supa_base_client import get_supabase_client

supabase = get_supabase_client()

def run_pipeline(csv_metrics_path, csv_cadastral_path):
    # 1. Carregar Dados
    df1 = pd.read_csv(csv_metrics_path, sep=';', dtype=str).where(pd.notnull, None)
    df2 = pd.read_csv(csv_cadastral_path, sep=';', dtype=str).where(pd.notnull, None)

    # --- POPULAR PARCEIROS ---
    parceiros = df1[['cge_partner', 'nm_partner', 'tipo_parceiro']].drop_duplicates('cge_partner')
    supabase.table("parceiros").upsert(parceiros.to_dict(orient='records'), on_conflict="cge_partner").execute()

    # --- POPULAR ASSESSORES ---
    assessores = df1[['cge_officer', 'nm_officer', 'email_assessor', 'cge_partner']].drop_duplicates('cge_officer')
    supabase.table("assessores").upsert(assessores.to_dict(orient='records'), on_conflict="cge_officer").execute()

    # --- POPULAR CLIENTES (Dados do Contexto 2) ---
    clientes_cols = [
        'documento_cpf_cnpj', 'nome_completo', 'dt_nascimento', 'profissao', 'estado_civil', 
        'celular', 'telefone', 'email_acesso', 'email_comunicacao', 'documento_tipo', 
        'documento', 'documento_dt_emissao', 'endereco_completo', 'endereco_complemento', 
        'endereco_cidade', 'endereco_estado', 'endereco_cep', 'genero', 'cpf_conjuge', 
        'idade', 'nacionalidade', 'residente'
    ]
    clientes = df2[clientes_cols].drop_duplicates('documento_cpf_cnpj')
    supabase.table("clientes").upsert(clientes.to_dict(orient='records'), on_conflict="documento_cpf_cnpj").execute()

    # --- POPULAR CONTAS (Merge de informações dos dois CSVs) ---
    # Pegamos a estrutura do df2 e complementamos com colunas exclusivas do df1
    contas_df2 = df2[['nr_conta', 'documento_cpf_cnpj', 'dt_abertura', 'status', 'tipo_cliente', 
                      'tipo_investidor', 'suitability', 'dt_vencimento_suitability', 'dt_encerramento', 
                      'dt_vinculo_escritorio', 'dt_ult_revisao_cadastral', 'dt_prox_revisao_castral', 
                      'pendencia_cadastral', 'perfil_acesso', 'vencimento_cadastro']]
    
    # Colunas de conta que só existem no df1
    contas_df1 = df1[['nr_conta', 'cge_officer', 'perfil_investidor', 'faixa_cliente', 
                      'termo_curva_rf', 'carteira_administrada', 'id_cliente']]
    
    contas_final = pd.merge(contas_df2, contas_df1, on='nr_conta', how='outer')
    supabase.table("contas").upsert(contas_final.to_dict(orient='records'), on_conflict="nr_conta").execute()

    # --- POPULAR POSIÇÃO DIÁRIA (Dados financeiros do Contexto 1 e 2) ---
    posicao = df1[[
        'nr_conta', 'dt_vinculo', 'dt_primeiro_investimento', 'dt_ultimo_aporte', 'qtd_aportes', 
        'vl_aportes', 'vl_retiradas', 'qtd_ativos', 'qtd_fundos', 'qtd_renda_fixa', 
        'qtd_renda_variavel', 'qtd_previdencia', 'qtd_derivativos', 'qtd_valores_transito', 
        'pl_total', 'pl_conta_corrente', 'pl_fundos', 'pl_renda_fixa', 'pl_renda_variavel', 
        'pl_previdencia', 'pl_derivativos', 'pl_valores_transito', 'vl_pl_declarado', 
        'vl_rendimento_anual'
    ]]
    # Adicionando vl_rendimento_total que só tem no context 2
    posicao = pd.merge(posicao, df2[['nr_conta', 'vl_rendimento_total']], on='nr_conta', how='left')
    
    supabase.table("posicao_diaria").insert(posicao.to_dict(orient='records')).execute()

    print("Pipeline executado. Todos os campos foram contemplados.")

# Exemplo de uso:
run_pipeline("BTG_Cliente_Base_BTG.csv", "BTG_Dados_Cadastrais.csv")