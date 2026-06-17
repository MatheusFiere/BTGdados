import os
import io
import time
import uuid
import shutil
import zipfile
import requests
import datetime as dt
import pandas as pd
from dotenv import load_dotenv

import tokens as tk


load_dotenv()

# =========================
# CONFIGURAÇÕES
# =========================
WEBHOOK_URL = "https://api-btg-2.onrender.com/webhook"
BTG_API_POSITION_URL = "https://api.btgpactual.com/api-rm-reports/api/v1/rm-reports/position"
API_KEY = os.getenv("BTG_WEBHOOK_API_KEY")

LAST_URL_FILE = "last_url_test.txt"
EXTRACT_DIR = "extracted_files"
SLEEP_MULTIPLIERS = [1, 1.5, 2, 2.5, 3, 5, 5, 5, 10, 10]
SLEEP_MULTIPLIERS = [i * 30 for i in SLEEP_MULTIPLIERS]  # increased back‑off
REQUEST_TIMEOUT = 120  # extended network timeout



# =========================
# FUNÇÕES CORE
# =========================
def log_error(message: str) -> None:
    print(f"[{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: {message}")

def read_last_url() -> str:
    if not os.path.exists(LAST_URL_FILE):
        return ""
    with open(LAST_URL_FILE, "r") as f:
        return f.read().strip()

def save_last_url(url: str) -> None:
    with open(LAST_URL_FILE, "w") as f:
        f.write(url)

def fetch_new_file_url(previous_url: str = None) -> str:
    """
    Busca a URL do arquivo no webhook.
    Tenta repetidamente até a URL ser DIFERENTE de previous_url.
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
            new_url = None
            try:
                if "response" in payload and "url" in payload["response"]:
                    new_url = payload["response"]["url"]
                elif "result" in payload and "url" in payload["result"]:
                    new_url = payload["result"]["url"]
                elif "url" in payload:
                    new_url = payload["url"]
                else:
                    print(f"ERRO: Payload recebido sem URL. Retorno: {payload}")
                    time.sleep(5)
                    continue
            except Exception as ex:
                print(f"ERRO AO PROCESSAR PAYLOAD: {ex}")
                time.sleep(5)
                continue
            
            if previous_url and new_url == previous_url:
                print(f"Aguardando arquivo novo... (Tentativa {attempt+1}/{len(SLEEP_MULTIPLIERS)})")
                time.sleep(10 * SLEEP_MULTIPLIERS[attempt])
                continue

            save_last_url(new_url)
            return new_url

        except Exception as e:
            print(f"ERRO AO OBTER URL do webhook: {e}")
            time.sleep(5)
            
    return None

def download_and_save_file(url: str, output_name_base: str) -> str:
    try:
        print(f"Baixando de {url}...")
        res = requests.get(url, stream=True, timeout=REQUEST_TIMEOUT)
        res.raise_for_status()

        os.makedirs(os.path.dirname(output_name_base), exist_ok=True)

        if res.headers.get("Content-Type") == "application/zip" or url.endswith(".zip"):
            if os.path.isdir(EXTRACT_DIR):
                shutil.rmtree(EXTRACT_DIR)

            with zipfile.ZipFile(io.BytesIO(res.content)) as zip_ref:
                zip_ref.extractall(EXTRACT_DIR)

            for file in os.listdir(EXTRACT_DIR):
                if file.endswith(".csv"):
                    shutil.move(
                        os.path.join(EXTRACT_DIR, file),
                        f"{output_name_base}.csv",
                    )
            return "zip"
        else:
            with open(f"{output_name_base}.csv", "wb") as f:
                for chunk in res.iter_content(8192):
                    f.write(chunk)
            return "csv"

    except Exception as e:
        log_error(f"ERRO AO BAIXAR ARQUIVO: {e}")
        return None

def trigger_btg_report(url: str, token_manager) -> str:
    print(f"Disparando relatório: {url}")
    request_uuid = str(uuid.uuid4())
    headers = {
        "x-id-partner-request": request_uuid,
        "access_token": token_manager(),
        "accept": "*/*",
    }
    
    res = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    if not res.ok:
        raise RuntimeError(f"BTG API error: {res.status_code} - {res.text}")
    print(f"Relatório disparado com sucesso. UUID da requisição: {request_uuid}")
    return request_uuid

def process_position_report(previous_url: str, token_manager, prefix: str) -> str:
    print(f"\n--- Processando POSITION REPORT ({prefix}) ---")
    
    try:
        request_uuid = trigger_btg_report(BTG_API_POSITION_URL, token_manager)
    except Exception as e:
        log_error(f"Erro ao disparar Position Report: {e}")
        return previous_url

    print("Aguardando arquivo de Posição ser gerado...")
    time.sleep(10) # Tempo inicial ajustável para testes
    
    file_url = fetch_new_file_url(previous_url=previous_url)
    if not file_url:
        print("Aviso: Não foi possível obter URL do relatório de Posição.")
        return previous_url

    download_and_save_file(file_url, f"{OUTPUT_DIR}/{prefix}_Posicao")
    print(f"Position Data ({prefix}) saved successfully.")
    return file_url

if __name__ == "__main__":
    if not API_KEY:
        print("AVISO: BTG_WEBHOOK_API_KEY não configurada no .env!")

    prefix = "gen"
    print(f"Iniciando processamento para conta {prefix.upper()}...")

    # Lê a última URL conhecida (se houver)
    last_known_url = read_last_url()

    # Dispara o relatório de posição e obtém a URL
    try:
        request_uuid = trigger_btg_report(BTG_API_POSITION_URL, tk.manage_token_gen)
    except Exception as e:
        log_error(f"Erro ao disparar Position Report: {e}")
        request_uuid = None

    # Aguarda um tempo razoável para o relatório ser gerado
    time.sleep(60)

    # Processa o relatório de posição, salvando como gen_Posicao.csv
    new_url = process_position_report(last_known_url, tk.manage_token_gen, prefix)
    if new_url:
        print(f"Relatório de posição atualizado: {new_url}")
    else:
        print("Falha ao atualizar relatório de posição.")

    print("\nProcessamento concluído.")
