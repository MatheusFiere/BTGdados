"""
Script para criar as tabelas tb_nnm e tb_ordens_bolsa no Supabase via REST API.
Executa o SQL diretamente usando a Service Role Key.
"""
import os
import requests
import sys

# Carrega .env — tenta na pasta send/ relativa ao script, depois no diretório atual
import pathlib
_BASE = pathlib.Path(__file__).parent
_ENV_PATHS = [_BASE / "send" / ".env", _BASE / ".env", pathlib.Path(".env")]

try:
    from dotenv import load_dotenv
    for _env in _ENV_PATHS:
        if _env.exists():
            load_dotenv(dotenv_path=_env)
            print(f"[.env] Carregado de: {_env}")
            break
    else:
        print("[AVISO] Arquivo .env não encontrado em nenhum local esperado.")
except ImportError:
    pass

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERRO: SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY não encontrados no .env")
    sys.exit(1)

SQL_CREATE_NNM = """
CREATE TABLE IF NOT EXISTS public.tb_nnm (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nr_conta BIGINT NOT NULL,
    data_captacao DATE,
    ativo TEXT,
    mercado TEXT,
    cge_officer TEXT,
    tipo_lancamento TEXT,
    descricao TEXT,
    quantidade FLOAT,
    captacao FLOAT,
    is_officer_nnm BOOLEAN,
    is_partner_nnm BOOLEAN,
    is_channel_nnm BOOLEAN,
    is_bu_nnm BOOLEAN,
    submercado TEXT,
    submercado_detalhado TEXT
);
"""

SQL_CREATE_ORDENS = """
CREATE TABLE IF NOT EXISTS public.tb_ordens_bolsa (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account BIGINT NOT NULL,
    "avgPx" FLOAT,
    "clOrdId" TEXT,
    "creationDate" DATE,
    "cumQty" FLOAT,
    "expireTime" TEXT,
    "leavesQty" FLOAT,
    "ordStatus" TEXT,
    "ordStatusDescription" TEXT,
    "orderId" TEXT,
    "orderQty" FLOAT,
    "orderStrategy" TEXT,
    "orderType" TEXT,
    origin TEXT,
    price FLOAT,
    "sendingTime" TIMESTAMPTZ,
    side TEXT,
    "sideDescription" TEXT,
    "startPrice" FLOAT,
    "startTrigger" FLOAT,
    "stopTrigger" FLOAT,
    symbol TEXT,
    "text" TEXT,
    "traderType" TEXT,
    "transactTime" TIMESTAMPTZ
);
"""

def run_sql(sql: str, description: str):
    """Executa SQL via endpoint REST do Supabase."""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }

    # Tenta endpoint /rest/v1/sql (Supabase >= 2.x)
    url = f"{SUPABASE_URL}/rest/v1/sql"
    resp = requests.post(url, headers=headers, json={"query": sql})

    if resp.status_code in (200, 201, 204):
        print(f"  [OK] {description}")
        return True
    else:
        print(f"  [ERRO {resp.status_code}] {description}")
        print(f"  Resposta: {resp.text[:300]}")
        return False


def check_table_exists(table_name: str) -> bool:
    """Verifica se a tabela já existe tentando fazer um SELECT vazio."""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Range": "0-0"
    }
    url = f"{SUPABASE_URL}/rest/v1/{table_name}?select=id&limit=1"
    resp = requests.get(url, headers=headers)
    return resp.status_code in (200, 206)


if __name__ == "__main__":
    print("=" * 50)
    print("  CRIAÇÃO DE TABELAS NO SUPABASE")
    print("=" * 50)
    print(f"Projeto: {SUPABASE_URL}\n")

    # Verificar se já existem
    print("Verificando tabelas existentes...")
    nnm_exists = check_table_exists("tb_nnm")
    ordens_exists = check_table_exists("tb_ordens_bolsa")

    print(f"  tb_nnm         -> {'JÁ EXISTE' if nnm_exists else 'NÃO EXISTE'}")
    print(f"  tb_ordens_bolsa -> {'JÁ EXISTE' if ordens_exists else 'NÃO EXISTE'}")
    print()

    if nnm_exists and ordens_exists:
        print("Ambas as tabelas já existem. Nada a fazer.")
        sys.exit(0)

    print("Criando tabelas via REST API...")

    success = True

    if not nnm_exists:
        ok = run_sql(SQL_CREATE_NNM, "Criando tb_nnm")
        success = success and ok
    else:
        print("  [SKIP] tb_nnm já existe, pulando.")

    if not ordens_exists:
        ok = run_sql(SQL_CREATE_ORDENS, "Criando tb_ordens_bolsa")
        success = success and ok
    else:
        print("  [SKIP] tb_ordens_bolsa já existe, pulando.")

    print()
    if success:
        print("Tabelas criadas com sucesso!")
        print("\nPróximo passo: execute os scripts de envio:")
        print("  python send/_supa_nnm.py update/diretorio_arq/consultoria_NNM.csv")
        print("  python send/_supa_ordens.py update/diretorio_arq/consultoria_Ordens_Bolsa.csv")
    else:
        print("=" * 50)
        print("ATENÇÃO: A criação via REST não foi possível.")
        print("Copie e cole o conteúdo de 'create_tables.sql' no")
        print("SQL Editor do seu painel Supabase e execute manualmente.")
        print("Caminho do arquivo: create_tables.sql")
        print("=" * 50)
        sys.exit(1)
