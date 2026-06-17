import os
import io
import time
import uuid
import shutil
import zipfile
import requests
import datetime as dt
import pandas as pd
import locale
from typing import List, Union

# Assumes tokens.py is in the same directory
import tokens as tk

import pygsheets
from dotenv import load_dotenv

load_dotenv(".env")

# =========================
# CONSTANTS
# =========================
WEBHOOK_URL = "https://api-btg-2.onrender.com/webhook"

# Existing Endpoint (Account Base)
BTG_API_BASE_URL = "https://api.btgpactual.com/api-rm-reports/api/v1/rm-reports/account-base"
# New Endpoint (Registration Data / Dados Cadastrais)
BTG_API_REGISTRATION_URL = "https://api.btgpactual.com/api-rm-reports/api/v1/rm-reports/registration-data"

BTG_API_POSITION_URL = "https://api.btgpactual.com/api-rm-reports/api/v1/rm-reports/position"
BTG_API_BANKING_URL = "https://api.btgpactual.com/api-rm-reports/api/v1/rm-reports/banking"
BTG_API_PERFORMANCE_ACCOUNT_URL = "https://api.btgpactual.com/iaas-profitability/api/v1/performance-report/account"
BTG_API_MOVEMENTS_URL = "https://api.btgpactual.com/api-rm-reports/api/v1/operation-history/monthly"
BTG_API_PROFITABILITY_PRODUCT_URL = "https://api.btgpactual.com/iaas-profitability/api/v1/profitability/daily/product"
BTG_API_ONBOARDING_URL = "https://api.btgpactual.com/api-rm-reports/api/v1/rm-reports/onboarding-data"
BTG_API_PARTNER_ONBOARDING_URL = "https://api.btgpactual.com/api-partner-report-hub/api/v1/report/onboarding-by-date"
BTG_API_FUNDS_INFORMATION_URL = "https://api.btgpactual.com/api-funds-information/api/v1/funds-information/public"
BTG_API_STOCK_ORDER_URL = "https://api.btgpactual.com/iaas-stock-order/api/v1/stock-order/orders"
BTG_API_DEBENTURE_URL = "https://api.btgpactual.com/iaas-debenture/api/v1/debenture"
BTG_API_NNM_URL = "https://api.btgpactual.com/api-rm-reports/api/v1/rm-reports/nnm"


LAST_URL_FILE = "last_url.txt"
import os as _os
BASE_DIR = _os.path.dirname(_os.path.abspath(__file__))
ERROR_LOG_FILE = _os.path.join(BASE_DIR, "error_log", "error_log.txt")

MAX_RETRIES = 10  # Increased retries to account for webhook delays
SLEEP_MULTIPLIERS = [1, 1.5, 2, 2.5, 3, 5, 5, 5, 10, 10]
SLEEP_MULTIPLIERS = [i * 10 for i in SLEEP_MULTIPLIERS]
SLEEP_MULTIPLIERS = [1, 1.5, 2, 2.5, 3]

REQUEST_TIMEOUT = 30

EXTRACT_DIR = "extracted_files"
OUTPUT_DIR = "diretorio_arq"

# Google Sheets Config
GOOGLE_SHEET_ID = "1z63uqeENfqZhtiwKsQ1KEphS9HUg4bMYzMQmwpp83KQ"
CREDENTIALS_PATH = os.path.join("artifac", "cliente.json")

API_KEY = os.getenv("BTG_WEBHOOK_API_KEY")  # MUST be set in env


# =========================
# UTILITIES
# =========================

def traduzir_colunas(df: pd.DataFrame) -> pd.DataFrame:
    traducao = {
        "cod_file": "codigo_arquivo",
        "candidate_id": "id_candidato",
        "name": "nome",
        "email": "email",
        "hash_email": "hash_email",
        "cpf": "cpf",
        "hash_cpf": "hash_cpf",
        "phone": "telefone",
        "cge": "cge",
        "cod_login": "codigo_login",
        "segment": "segmento",
        "co_segment": "co_segmento",
        "cge_officer": "cge_assessor",
        "cge_partner": "cge_parceiro",
        "status": "status",
        "sg_status": "sigla_status",
        "status_reason": "motivo_status",
        "form_name": "nome_formulario",
        "account_number": "numero_conta",
        "dt_created": "data_criacao",
        "dt_updated": "data_atualizacao",
        "dt_opening_account": "data_abertura_conta",
        "scr": "scr",
        "last_screen": "ultima_tela",
        "current_screen": "tela_atual",
        "status_analisys_credit": "status_analise_credito",
        "device_id": "id_dispositivo",
        "user_agent": "user_agent",
        "accept_comunication ": "aceita_comunicacao",
        "latitude": "latitude",
        "longitude": "longitude",
        "appsflyer_id": "id_appsflyer",
        "fire_base_id": "id_firebase",
        "facebook_id": "id_facebook",
        "document_number": "numero_documento",
        "document_issuing_agency": "orgao_emissor",
        "document_type": "tipo_documento",
        "document_dt_capture_self": "data_captura_selfie",
        "document_dt_capture_document": "data_captura_documento",
        "mother_name": "nome_mae",
        "marital_status": "estado_civil",
        "birth_date": "data_nascimento",
        "gender": "genero",
        "spouse_name": "nome_conjuge",
        "address_street": "rua",
        "address_number": "numero",
        "address_complement": "complemento",
        "address_neighborhood": "bairro",
        "address_city": "cidade",
        "address_uf": "uf",
        "address_country": "pais",
        "address_cep": "cep",
        "external_relationship_country_birth": "pais_nascimento",
        "external_relationship_state_birth": "estado_nascimento",
        "external_relationship_city_birth": "cidade_nascimento",
        "external_relationship_citizenship_nationality": "nacionalidade",
        "external_relationship_link_eua": "vinculo_eua",
        "profession": "profissao",
        "position": "cargo",
        "income": "renda",
        "patrimony_real_estate": "patrimonio_imoveis",
        "patrimony_moveables": "patrimonio_bens_moveis",
        "patrimony_investments": "patrimonio_investimentos",
        "patrimony_welfare": "patrimonio_previdencia",
        "patrimony_others": "outros_patrimonios",
        "patrimony_no_want_inform": "nao_informar_patrimonio",
        "financial_responsible_document": "doc_responsavel_financeiro",
        "financial_responsible_profession": "profissao_responsavel",
        "financial_responsible_position": "cargo_responsavel",
        "financial_responsible_income": "renda_responsavel",
        "advisor_name": "nome_assessor",
        "advisor_mail": "email_assessor",
        "advisor_type": "tipo_assessor",
        "advisor_cge": "cge_assessor",
        "advisor_cge_partner": "cge_parceiro_assessor",
        "advisor_name_partner": "nome_parceiro_assessor",
        "mgm_code": "codigo_mgm",
        "mgm_nif": "nif_mgm",
        "advertising_id": "id_publicidade",
        "invite": "convite",
        "platform": "plataforma",
        "user_pseudo_id": "id_usuario_pseudo",
        "joint_account_exists_joint_account": "conta_conjunta_existe",
        "joint_account_name_holder": "nome_titular",
        "joint_account_name_coholder": "nome_cotitular",
        "pix_field_pix_cpf": "pix_cpf",
        "pix_field_pix_email": "pix_email",
        "pix_field_pix_phone": "pix_telefone",
        "pix_flow_button_selected": "botao_pix_selecionado",
        "system_origin": "origem_sistema",
        "stack_screen": "stack_telas",
        "ingestion_timestamp": "timestamp_ingestao",
        "write_timestamp": "timestamp_escrita"
    }
    df = df.rename(columns=lambda col: traducao.get(col, col))
    return df

def log_error(message: str) -> None:
    os.makedirs(os.path.dirname(ERROR_LOG_FILE), exist_ok=True)
    with open(ERROR_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: {message}\n")


def read_last_url() -> str:
    if not os.path.exists(LAST_URL_FILE):
        return ""
    with open(LAST_URL_FILE, "r") as f:
        return f.read().strip()


def save_last_url(url: str) -> None:
    with open(LAST_URL_FILE, "w") as f:
        f.write(url)


def append_to_gsheet(
    credentials_json: str,
    spreadsheet_id: str,
    worksheet_title: str,
    data: Union[List[List], pd.DataFrame],
    brazilian_format: bool = True,
    numeric_columns: List[int] = None,
):
    """
    Append rows to a Google Sheets worksheet using pygsheets with Brazilian numeric format support.
    """
    # Authorize
    gc = pygsheets.authorize(service_file=credentials_json)

    # Open spreadsheet and worksheet
    sh = gc.open_by_key(spreadsheet_id)
    ws = sh.worksheet_by_title(worksheet_title)

    # Normalize input
    if isinstance(data, pd.DataFrame):
        if brazilian_format:
            data_copy = data.copy()
            
            # Identify numeric columns
            if numeric_columns is None:
                numeric_cols = data_copy.select_dtypes(include=['number']).columns
            else:
                numeric_cols = [data_copy.columns[i] for i in numeric_columns if i < len(data_copy.columns)]
            
            # Format numeric columns with Brazilian format
            for col in numeric_cols:
                data_copy[col] = data_copy[col].apply(
                    lambda x: f"{x:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',') 
                    if pd.notna(x) else ''
                )
            values = data_copy.values.tolist()
        else:
            values = data.values.tolist()
    else:  # data is a list of lists
        values = [row[:] for row in data]
        if brazilian_format:
            if numeric_columns is None:
                # Try to identify numeric columns automatically
                if values:
                    numeric_columns = []
                    for i, val in enumerate(values[0]):
                        try:
                            float(str(val).replace('.', '').replace(',', '.'))
                            numeric_columns.append(i)
                        except:
                            pass
            
            if numeric_columns:
                for row in values:
                    for col_idx in numeric_columns:
                        if col_idx < len(row):
                            val = row[col_idx]
                            try:
                                if isinstance(val, (int, float)):
                                    num = float(val)
                                else:
                                    clean_str = str(val).replace('R$', '').replace(' ', '').strip()
                                    if ',' in clean_str and '.' in clean_str:
                                        clean_str = clean_str.replace('.', '')
                                    clean_str = clean_str.replace(',', '.')
                                    num = float(clean_str)
                                
                                formatted = f"{num:,.2f}"
                                formatted = formatted.replace('.', 'X').replace(',', '.').replace('X', ',')
                                row[col_idx] = formatted
                            except (ValueError, TypeError):
                                pass

    if not values:
        raise ValueError("No data to append")

    # Append rows
    ws.append_table(
        values=values,
        dimension="ROWS",
        overwrite=False
    )


# =========================
# CORE FUNCTIONS
# =========================

def fetch_new_file_url(previous_url: str = None) -> str | None:
    """
    Fetches the file URL from the middleware.
    If previous_url is provided, it retries until the fetched URL is DIFFERENT from previous_url.
    """
    for attempt in range(len(SLEEP_MULTIPLIERS)):
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
            
            payload = res.json()
            try:
                if "response" in payload and "url" in payload["response"]:
                    new_url = payload["response"]["url"]
                elif "result" in payload and "url" in payload["result"]:
                    new_url = payload["result"]["url"]
                elif "url" in payload:
                    new_url = payload["url"]
                else:
                    log_error(f"ERRO AO OBTER URL (Formato desconhecido). Payload recebido: {payload}")
                    time.sleep(5 * 2)
                    continue
            except Exception as ex:
                log_error(f"ERRO AO PROCESSAR PAYLOAD: {ex}. Payload: {payload}")
                time.sleep(5 * 2)
                continue
            
            # If we are looking for a *fresh* URL (different from the one we just got), check it
            if previous_url and new_url == previous_url:
                print(f"Waiting for new file... (Attempt {attempt+1}/{len(SLEEP_MULTIPLIERS)})")
                time.sleep(10 * SLEEP_MULTIPLIERS[attempt])
                continue

            # Found a valid (and potentially new) URL
            save_last_url(new_url)
            return new_url

        except Exception as e:
            log_error(f"ERRO AO OBTER URL: {e}")
            time.sleep(5 * 2)
            
    return None


def download_and_save_file(url: str, output_name_base: str) -> str | None:
    """
    Downloads file from url. Handles ZIP extraction or direct CSV save.
    output_name_base: path without extension (e.g. 'folder/myfile')
    """
    try:
        print(f"Downloading from {url}...")
        res = requests.get(url, stream=True, timeout=REQUEST_TIMEOUT)
        res.raise_for_status()

        os.makedirs(os.path.dirname(output_name_base), exist_ok=True)

        if res.headers.get("Content-Type") == "application/zip" or url.endswith(".zip"):
            if os.path.isdir(EXTRACT_DIR):
                shutil.rmtree(EXTRACT_DIR)

            with zipfile.ZipFile(io.BytesIO(res.content)) as zip_ref:
                zip_ref.extractall(EXTRACT_DIR)

            # Move extracted csv to destination
            for file in os.listdir(EXTRACT_DIR):
                if file.endswith(".csv"):
                    shutil.move(
                        os.path.join(EXTRACT_DIR, file),
                        f"{output_name_base}.csv",
                    )
            return "zip"
        else:
            # Direct CSV
            with open(f"{output_name_base}.csv", "wb") as f:
                for chunk in res.iter_content(8192):
                    f.write(chunk)
            return "csv"

    except Exception as e:
        log_error(f"ERRO AO BAIXAR ARQUIVO {output_name_base}: {e}")
        return None


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
        # time.sleep(60*10)
    else:
        res = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    
    if not res.ok:
        # Log specifically if it's a window error or registration error
        raise RuntimeError(f"BTG API error: {res.status_code} - {res.text}")
    print("Report triggered successfully.")


# =========================
# REPORT PROCESSORS
# =========================

def process_base_report(previous_url: str, token_manager, prefix: str) -> str:
    """
    Handles the 'Account Base' report: Trigger -> Download -> Diff -> GSheets.
    Returns the URL of the file downloaded to be used for comparison later.
    """
    print(f"\n--- Processing BASE REPORT ({prefix}) ---")
    
    # 1. Load Old Data
    base_file_path = f"{OUTPUT_DIR}/{prefix}_Cliente_Base_BTG.csv"
    try:
        df_old = pd.read_csv(base_file_path, sep=';')
    except FileNotFoundError:
        df_old = pd.DataFrame(columns=['nr_conta']) # Empty if first run

    # 2. Trigger Report
    trigger_btg_report(BTG_API_BASE_URL, token_manager)
    
    # 3. Wait for Webhook to update
    print("Waiting for Base file generation...")
    time.sleep(60 * 2) # Initial wait
    
    file_url = fetch_new_file_url(previous_url=previous_url)
    if not file_url:
        raise RuntimeError("Failed to retrieve Base Report URL")

    # 4. Download
    download_and_save_file(file_url, f"{OUTPUT_DIR}/{prefix}_Cliente_Base_BTG")

    # 5. Diff Logic
    df_new = pd.read_csv(base_file_path, sep=';')
    
    # Identify new accounts
    if 'nr_conta' in df_new.columns and 'nr_conta' in df_old.columns:
        df_diff = df_new[~df_new['nr_conta'].isin(df_old['nr_conta'])]
        
        diff_updated_columns = [
            'nome_completo', 'email', 'id_cliente', 'nr_conta', 'nm_officer', 'vl_pl_declarado'
        ]
        
        # Check if columns exist before selecting
        valid_cols = [c for c in diff_updated_columns if c in df_diff.columns]
        df_diff_up = df_diff[valid_cols]

        print(f"New rows found: {len(df_diff_up)}")

        if not df_diff_up.empty:
            try:
                append_to_gsheet(
                    credentials_json=CREDENTIALS_PATH,
                    spreadsheet_id=GOOGLE_SHEET_ID,
                    worksheet_title="api",
                    data=df_diff_up,
                )
            except FileNotFoundError:
                print(f"Warning: Credentials file {CREDENTIALS_PATH} not found. Skipping Google Sheets update.")
            except Exception as e:
                print(f"Error updating Google Sheets: {e}")
            
        # Save diff file
        df_diff.to_csv(f"{OUTPUT_DIR}/{prefix}_Cliente_Base_Diferenca.csv", sep=';', index=False)
    else:
        print("Warning: 'nr_conta' column missing. Skipping Diff logic.")

    return file_url


def process_registration_report(previous_url: str, token_manager, prefix: str) -> str:
    """
    Handles the 'Registration Data' report: Trigger -> Download.
    Note: This report has specific windows (07h, 15h, 20h). If triggered outside, it may fail or wait.
    Returns the URL of the file downloaded.
    """
    print(f"\n--- Processing REGISTRATION DATA REPORT ({prefix}) ---")
    
    # 1. Trigger Report
    try:
        trigger_btg_report(BTG_API_REGISTRATION_URL, token_manager)
    except Exception as e:
        log_error(f"Error triggering Registration Report: {e}")
        return previous_url

    # 2. Wait for Webhook to update (Must be a NEW url different from the Base report)
    print("Waiting for Registration file generation...")
    time.sleep(60 * 2)
    
    file_url = fetch_new_file_url(previous_url=previous_url)
    if not file_url:
        print("Warning: Could not retrieve Registration Report URL (might be outside execution window).")
        return previous_url

    # 3. Download
    # Saving as a different filename
    download_and_save_file(file_url, f"{OUTPUT_DIR}/{prefix}_Dados_Cadastrais")
    
    print(f"Registration Data ({prefix}) saved successfully.")
    return file_url


def process_position_report(previous_url: str, token_manager, prefix: str) -> str:
    """
    Handles the 'Position' report: Trigger -> Download.
    Returns the URL of the file downloaded.
    """
    print(f"\n--- Processing POSITION REPORT ({prefix}) ---")
    
    # 1. Trigger Report
    try:
        trigger_btg_report(BTG_API_POSITION_URL, token_manager)
    except Exception as e:
        log_error(f"Error triggering Position Report: {e}")
        return previous_url

    # 2. Wait for Webhook to update
    print("Waiting for Position file generation...")
    time.sleep(60 * 2)
    
    # Fetch the file URL without comparing to previous_url to ensure download
    file_url = fetch_new_file_url(previous_url=None)
    if not file_url:
        print("Warning: Could not retrieve Position Report URL.")
        return previous_url

    # 3. Download
    download_and_save_file(file_url, f"{OUTPUT_DIR}/{prefix}_Posicao")
    
    print(f"Position Data ({prefix}) saved successfully.")
    return file_url


def process_banking_report(previous_url: str, token_manager, prefix: str) -> str:
    """
    Handles the 'Banking' report: Trigger -> Download.
    Returns the URL of the file downloaded.
    """
    print(f"\n--- Processing BANKING REPORT ({prefix}) ---")
    
    # 1. Trigger Report
    try:
        trigger_btg_report(BTG_API_BANKING_URL, token_manager)
    except Exception as e:
        log_error(f"Error triggering Banking Report: {e}")
        return previous_url

    # 2. Wait for Webhook to update
    print("Waiting for Banking file generation...")
    time.sleep(60 * 2)
    
    file_url = fetch_new_file_url(previous_url=previous_url)
    if not file_url:
        print("Warning: Could not retrieve Banking Report URL.")
        return previous_url

    # 3. Download
    download_and_save_file(file_url, f"{OUTPUT_DIR}/{prefix}_Banking")
    
    print(f"Banking Data ({prefix}) saved successfully.")
    return file_url


def process_performance_account_report(previous_url: str, token_manager, prefix: str) -> str:
    """
    Handles the 'Performance Account' report: Trigger -> Download.
    Returns the URL of the file downloaded.
    """
    print(f"\n--- Processing PERFORMANCE ACCOUNT REPORT ({prefix}) ---")
    
    # 1. Trigger Report
    try:
        trigger_btg_report(BTG_API_PERFORMANCE_ACCOUNT_URL, token_manager, method="POST")
    except Exception as e:
        log_error(f"Error triggering Performance Account Report: {e}")
        return previous_url

    # 2. Wait for Webhook to update
    print("Waiting for Performance Account file generation...")
    time.sleep(60 * 2)
    
    file_url = fetch_new_file_url(previous_url=previous_url)
    if not file_url:
        print("Warning: Could not retrieve Performance Account Report URL.")
        return previous_url

    # 3. Download
    download_and_save_file(file_url, f"{OUTPUT_DIR}/{prefix}_Performance_Account")
    
    print(f"Performance Account Data ({prefix}) saved successfully.")
    return file_url


def merge_data_reports(prefix: str) -> None:
    print(f"\n--- Merging Datasets ({prefix}) ---")
    try:
        # Load datasets
        df_cad = pd.read_csv(f"{OUTPUT_DIR}/{prefix}_Dados_Cadastrais.csv", sep=';')
        df_base = pd.read_csv(f"{OUTPUT_DIR}/{prefix}_Cliente_Base_BTG.csv", sep=';')

        # Merge
        df = df_cad.merge(df_base, on="nr_conta", how="left", suffixes=("", "_dup"))

        # Drop duplicate columns
        df = df.loc[:, ~df.columns.str.endswith("_dup")]

        # Save merged file
        df.to_csv(f"{OUTPUT_DIR}/merged_{prefix}.csv", sep=';', decimal=',', index=False)
        print(f"Data merged successfully for {prefix}.")
        
    except Exception as e:
        log_error(f"Error merging datasets for {prefix}: {e}")
        print(f"Error merging datasets for {prefix}: {e}")

def process_profitability_product_report(previous_url: str, token_manager, prefix: str) -> str:
    """
    Handles the 'Daily Profitability by Product' report: Trigger -> Download.
    Returns the URL of the file downloaded.
    """
    print(f"\n--- Processing DAILY PROFITABILITY BY PRODUCT REPORT ({prefix}) ---")
    
    # 1. Trigger Report
    try:
        trigger_btg_report(BTG_API_PROFITABILITY_PRODUCT_URL, token_manager, method="POST")
    except Exception as e:
        log_error(f"Error triggering Profitability by Product Report: {e}")
        return previous_url

    # 2. Wait for Webhook to update
    print("Waiting for Profitability by Product file generation...")
    time.sleep(60 * 2)
    
    file_url = fetch_new_file_url(previous_url=previous_url)
    if not file_url:
        print("Warning: Could not retrieve Profitability by Product Report URL.")
        return previous_url

    # 3. Download
    download_and_save_file(file_url, f"{OUTPUT_DIR}/{prefix}_Rentabilidade_Diaria_Produto")
    
    print(f"Profitability by Product Data ({prefix}) saved successfully.")
    return file_url


def process_movements_report(previous_url: str, token_manager, prefix: str) -> str:
    """
    Handles the 'Monthly Movements' report: Trigger -> Download.
    Covers the previous month + current month days.
    """
    print(f"\n--- Processing MONTHLY MOVEMENTS REPORT ({prefix}) ---")
    
    # 1. Trigger Report
    try:
        # O endpoint é GET conforme a documentação fornecida
        trigger_btg_report(BTG_API_MOVEMENTS_URL, token_manager, method="GET")
    except Exception as e:
        log_error(f"Error triggering Movements Report: {e}")
        return previous_url

    # 2. Wait for Webhook to update
    print("Waiting for Movements file generation (this may take longer due to volume)...")
    time.sleep(60 * 2) # Espera inicial
    
    file_url = fetch_new_file_url(previous_url=previous_url)
    if not file_url:
        print("Warning: Could not retrieve Movements Report URL.")
        return previous_url

    # 3. Download
    download_and_save_file(file_url, f"{OUTPUT_DIR}/{prefix}_Movimentacoes_Mensais")
    
    print(f"Movements Data ({prefix}) saved successfully.")
    return file_url


def process_onboarding_report(previous_url: str, token_manager, prefix: str) -> str:
    """
    Handles the 'Onboarding Data' report: Trigger -> Download.
    Note: This report has specific windows (08h, 15h, 20h). If triggered outside, it may fail or wait.
    Returns the URL of the file downloaded.
    """
    print(f"\n--- Processing ONBOARDING DATA REPORT ({prefix}) ---")
    
    # 1. Trigger Report
    try:
        trigger_btg_report(BTG_API_ONBOARDING_URL, token_manager, method="GET")
    except Exception as e:
        log_error(f"Error triggering Onboarding Report: {e}")
        return previous_url

    # 2. Wait for Webhook to update
    print("Waiting for Onboarding file generation...")
    time.sleep(60 * 2)
    
    file_url = fetch_new_file_url(previous_url=previous_url)
    if not file_url:
        print("Warning: Could not retrieve Onboarding Report URL (might be outside execution window).")
        return previous_url

    # 3. Download
    download_and_save_file(file_url, f"{OUTPUT_DIR}/{prefix}_Dados_Onboarding")
    
    # 4. Clean Data
    try:
        file_path = f"{OUTPUT_DIR}/{prefix}_Dados_Onboarding.csv"
        df = pd.read_csv(file_path, sep=',')
        df = traduzir_colunas(df)
        df.to_csv(file_path, sep=';', index=False)
    except Exception as e:
        log_error(f"Error cleaning Onboarding Data ({prefix}): {e}")
        print(f"Error cleaning Onboarding Data ({prefix}): {e}")
    
    print(f"Onboarding Data ({prefix}) saved successfully.")
    return file_url

def process_partner_onboarding_report(previous_url: str, token_manager, prefix: str) -> str:
    """
    Handles the 'Partner Onboarding Data' report: Trigger -> Download.
    Returns the URL of the file downloaded.
    """
    print(f"\n--- Processing PARTNER ONBOARDING DATA REPORT ({prefix}) ---")
    
    # 1. Trigger Report
    try:
        # Get date range (last 30 days)
        end_date = dt.date.today() - dt.timedelta(days=0)
        start_date = dt.date.today() - dt.timedelta(days=29)
        
        json_data = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d")
        }
        
        trigger_btg_report(BTG_API_PARTNER_ONBOARDING_URL, token_manager, method="POST", json_data=json_data)
    except Exception as e:
        log_error(f"Error triggering Partner Onboarding Report: {e}")
        return previous_url

    # 2. Wait for Webhook to update
    print("Waiting for Partner Onboarding file generation...")
    time.sleep(60 * 2)
    
    file_url = fetch_new_file_url(previous_url=previous_url)
    if not file_url:
        print("Warning: Could not retrieve Partner Onboarding Report URL.")
        return previous_url

    # 3. Download
    download_and_save_file(file_url, f"{OUTPUT_DIR}/{prefix}_Dados_Onboarding_Partner")
    
    # 4. Clean Data
    try:
        file_path = f"{OUTPUT_DIR}/{prefix}_Dados_Onboarding_Partner.csv"
        df = pd.read_csv(file_path, sep=',')
        df = traduzir_colunas(df)
        df = df.sort_values('timestamp_escrita')
        df = df.groupby('cpf').last()
        df.to_csv(file_path, sep=';', index=False)
    except Exception as e:
        log_error(f"Error cleaning Partner Onboarding Data ({prefix}): {e}")
        print(f"Error cleaning Partner Onboarding Data ({prefix}): {e}")
    
    print(f"Partner Onboarding Data ({prefix}) saved successfully.")
    return file_url

def process_funds_information_report(previous_url: str, token_manager, prefix: str) -> str:
    """
    Handles the 'Funds Information' report: Trigger -> Download.
    Returns the URL of the file downloaded.
    """
    print(f"\n--- Processing FUNDS INFORMATION REPORT ({prefix}) ---")
    
    # 1. Trigger Report
    try:
        trigger_btg_report(BTG_API_FUNDS_INFORMATION_URL, token_manager, method="GET")
    except Exception as e:
        log_error(f"Error triggering Funds Information Report: {e}")
        return previous_url

    # 2. Wait for Webhook to update
    print("Waiting for Funds Information file generation...")
    time.sleep(60 * 2)
    
    file_url = fetch_new_file_url(previous_url=previous_url)
    if not file_url:
        print("Warning: Could not retrieve Funds Information Report URL.")
        return previous_url

    # 3. Download
    download_and_save_file(file_url, f"{OUTPUT_DIR}/{prefix}_Informacao_Fundos")
    
    print(f"Funds Information Data ({prefix}) saved successfully.")
    return file_url

def process_stock_order_report(previous_url: str, token_manager, prefix: str) -> str:
    """
    Handles the 'Stock Order' report: Trigger -> Download.
    Returns the URL of the file downloaded.
    """
    print(f"\n--- Processing STOCK ORDER REPORT ({prefix}) ---")
    
    # 1. Trigger Report
    try:
        # Intervalo máximo de 3 dias
        end_date = dt.date.today()
        start_date = end_date - dt.timedelta(days=2)
        
        json_data = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d")
        }
        
        trigger_btg_report(BTG_API_STOCK_ORDER_URL, token_manager, method="POST", json_data=json_data)
    except Exception as e:
        log_error(f"Error triggering Stock Order Report: {e}")
        return previous_url

    # 2. Wait for Webhook to update
    print("Waiting for Stock Order file generation...")
    time.sleep(60 * 2)
    
    file_url = fetch_new_file_url(previous_url=previous_url)
    if not file_url:
        print("Warning: Could not retrieve Stock Order Report URL.")
        return previous_url

    # 3. Download
    download_and_save_file(file_url, f"{OUTPUT_DIR}/{prefix}_Ordens_Bolsa")
    
    print(f"Stock Order Data ({prefix}) saved successfully.")
    return file_url

def process_debenture_report(previous_url: str, token_manager, prefix: str) -> str:
    """
    Handles the 'Debenture' report: Synchronous Trigger -> Download.
    Returns previous_url as this doesn't use the async webhook mechanism.
    """
    print(f"\n--- Processing DEBENTURE REPORT ({prefix}) ---")
    
    # 1. Find the last business day
    ref_date = dt.date.today() - dt.timedelta(days=1)
    while ref_date.weekday() > 4: # 5=Sat, 6=Sun
        ref_date -= dt.timedelta(days=1)
        
    reference_date_str = ref_date.strftime("%Y-%m-%d")
    
    url = f"{BTG_API_DEBENTURE_URL}?referenceDate={reference_date_str}"
    
    headers = {
        "x-id-partner-request": str(uuid.uuid4()),
        "access_token": token_manager(),
        "accept": "application/json",
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        
        if res.status_code == 200:
            data = res.json()
            if data:
                df = pd.DataFrame(data)
                out_file = f"{OUTPUT_DIR}/{prefix}_Debentures.csv"
                df.to_csv(out_file, sep=';', index=False)
                print(f"Debenture Data ({prefix}) saved successfully with {len(data)} records for {reference_date_str}.")
            else:
                print(f"No Debenture records found for {reference_date_str} ({prefix}).")
        elif res.status_code == 404:
            print(f"Debenture API returned 404: No data published for {reference_date_str} ({prefix}).")
        else:
            log_error(f"Debenture API error: {res.status_code} - {res.text}")
    except Exception as e:
        log_error(f"Error fetching Debenture Report: {e}")
        
    return previous_url

def process_nnm_report(previous_url: str, token_manager, prefix: str) -> str:
    """
    Handles the 'NNM Gerencial' report: Trigger -> Download.
    Returns the URL of the file downloaded.
    """
    print(f"\n--- Processing NNM REPORT ({prefix}) ---")
    
    # 1. Trigger Report
    try:
        trigger_btg_report(BTG_API_NNM_URL, token_manager, method="GET")
    except Exception as e:
        log_error(f"Error triggering NNM Report: {e}")
        return previous_url

    # 2. Wait for Webhook to update
    print("Waiting for NNM file generation...")
    time.sleep(60 * 2)
    
    file_url = fetch_new_file_url(previous_url=previous_url)
    if not file_url:
        print("Warning: Could not retrieve NNM Report URL.")
        return previous_url

    # 3. Download
    download_and_save_file(file_url, f"{OUTPUT_DIR}/{prefix}_NNM")
    
    print(f"NNM Data ({prefix}) saved successfully.")
    return file_url

def update_consultoria() -> None:
    # return
    if not API_KEY:
        raise EnvironmentError("BTG_WEBHOOK_API_KEY not set")
    
    # Define our tokens to run
    runs = [
        {"prefix": "consultoria", "token_manager": tk.manage_token_consultoria},
        {"prefix": "gen", "token_manager": tk.manage_token_gen}
    ]

    for run in runs:
        prefix = run["prefix"]
        t_manager = run["token_manager"]

        print(f"\n==============================================")
        print(f"       STARTING RUN FOR: {prefix.upper()}")
        print(f"==============================================")

        # Get the last known URL to avoid re-downloading stale data immediately
        last_url = read_last_url()

        print("BTG_WEBHOOK_API_KEY =", os.getenv("BTG_WEBHOOK_API_KEY"))

        # # # --- Step 1: Base Report ---
        try:
            base_url = process_base_report(previous_url=last_url, token_manager=t_manager, prefix=prefix)
            last_url = base_url # Update last_url to the one we just fetched
        except Exception as e:
            log_error(f"CRITICAL ERROR IN BASE REPORT ({prefix}): {e}")
            print(f"Error in Base Report ({prefix}): {e}")

        # --- Step 2: Registration Data Report ---
        try:
            # Pass the last_url so we wait for the URL to CHANGE
            reg_url = process_registration_report(previous_url=last_url, token_manager=t_manager, prefix=prefix)
            last_url = reg_url
        except Exception as e:
            log_error(f"CRITICAL ERROR IN REGISTRATION REPORT ({prefix}): {e}")
            print(f"Error in Registration Report ({prefix}): {e}")

        # --- Step 3: Position Report ---
        try:
            pos_url = process_position_report(previous_url=last_url, token_manager=t_manager, prefix=prefix)
            last_url = pos_url
        except Exception as e:
            log_error(f"CRITICAL ERROR IN POSITION REPORT ({prefix}): {e}")
            print(f"Error in Position Report ({prefix}): {e}")

        # --- Step 4: Banking Report ---
        try:
            bank_url = process_banking_report(previous_url=last_url, token_manager=t_manager, prefix=prefix)
            last_url = bank_url
        except Exception as e:
            log_error(f"CRITICAL ERROR IN BANKING REPORT ({prefix}): {e}")
            print(f"Error in Banking Report ({prefix}): {e}")

        # --- Step 5: Performance Account Report ---
        try:
            perf_url = process_performance_account_report(previous_url=last_url, token_manager=t_manager, prefix=prefix)
            last_url = perf_url
        except Exception as e:
            log_error(f"CRITICAL ERROR IN PERFORMANCE ACCOUNT REPORT ({prefix}): {e}")
            print(f"Error in Performance Account Report ({prefix}): {e}")

        # --- Step 6: Monthly Movements Report ---
        try:
            mov_url = process_movements_report(previous_url=last_url, token_manager=t_manager, prefix=prefix)
            last_url = mov_url
        except Exception as e:
            log_error(f"CRITICAL ERROR IN MOVEMENTS REPORT ({prefix}): {e}")
            print(f"Error in Movements Report ({prefix}): {e}")

        # --- Step 7: Daily Profitability By Product Report ---
        try:
            prof_url = process_profitability_product_report(previous_url=last_url, token_manager=t_manager, prefix=prefix)
            last_url = prof_url
        except Exception as e:
            log_error(f"CRITICAL ERROR IN PROFITABILITY BY PRODUCT REPORT ({prefix}): {e}")
            print(f"Error in Profitability by Product Report ({prefix}): {e}")

        # --- Step 8: Onboarding Data Report ---
        try:
            onb_url = process_onboarding_report(previous_url=last_url, token_manager=t_manager, prefix=prefix)
            last_url = onb_url
        except Exception as e:
            log_error(f"CRITICAL ERROR IN ONBOARDING REPORT ({prefix}): {e}")
            print(f"Error in Onboarding Report ({prefix}): {e}")

        # --- Step 9: Partner Onboarding Data Report ---
        try:
            onb_p_url = process_partner_onboarding_report(previous_url=last_url, token_manager=t_manager, prefix=prefix)
            last_url = onb_p_url
        except Exception as e:
            log_error(f"CRITICAL ERROR IN PARTNER ONBOARDING REPORT ({prefix}): {e}")
            print(f"Error in Partner Onboarding Report ({prefix}): {e}")

        # --- Step 10: Funds Information Report ---
        try:
            funds_info_url = process_funds_information_report(previous_url=last_url, token_manager=t_manager, prefix=prefix)
            last_url = funds_info_url
        except Exception as e:
            log_error(f"CRITICAL ERROR IN FUNDS INFORMATION REPORT ({prefix}): {e}")
            print(f"Error in Funds Information Report ({prefix}): {e}")

        # --- Step 11: Stock Order Report ---
        try:
            stock_order_url = process_stock_order_report(previous_url=last_url, token_manager=t_manager, prefix=prefix)
            last_url = stock_order_url
        except Exception as e:
            log_error(f"CRITICAL ERROR IN STOCK ORDER REPORT ({prefix}): {e}")
            print(f"Error in Stock Order Report ({prefix}): {e}")

        # --- Step 12: Debenture Report ---
        try:
            debenture_url = process_debenture_report(previous_url=last_url, token_manager=t_manager, prefix=prefix)
            last_url = debenture_url
        except Exception as e:
            log_error(f"CRITICAL ERROR IN DEBENTURE REPORT ({prefix}): {e}")
            print(f"Error in Debenture Report ({prefix}): {e}")

        # --- Step 12.5: NNM Report ---
        try:
            nnm_url = process_nnm_report(previous_url=last_url, token_manager=t_manager, prefix=prefix)
            last_url = nnm_url
        except Exception as e:
            log_error(f"CRITICAL ERROR IN NNM REPORT ({prefix}): {e}")
            print(f"Error in NNM Report ({prefix}): {e}")

        # --- Step 13: Merge Data ---
        try:
            merge_data_reports(prefix=prefix)
        except Exception as e:
            log_error(f"CRITICAL ERROR IN DATA MERGE ({prefix}): {e}")
            print(f"Error merging data ({prefix}): {e}")

        time.sleep(60 * 5)


if __name__ == "__main__":
    update_consultoria()