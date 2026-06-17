import subprocess
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPDATE_DIR = os.path.join(BASE_DIR, "update")
SEND_DIR = os.path.join(BASE_DIR, "send")

def run_update():
    print(">>> Iniciando processo de atualização (update_consultoria3.py) <<<")
    # Executa a partir da pasta update
    result = subprocess.run([sys.executable, "update_consultoria3.py"], cwd=UPDATE_DIR)
    if result.returncode != 0:
        print("Erro durante a atualização dos dados.")
        sys.exit(result.returncode)
    print(">>> Atualização concluída com sucesso <<<")

def run_send(prefix):
    print(f"\n>>> Iniciando envio de dados para o prefixo: {prefix.upper()} <<<")
    
    # Caminhos dos arquivos gerados pelo update_consultoria.py
    merged_csv = os.path.join(UPDATE_DIR, "diretorio_arq", f"merged_{prefix}.csv")
    posicao_csv = os.path.join(UPDATE_DIR, "diretorio_arq", f"{prefix}_Posicao.csv")
    banking_csv = os.path.join(UPDATE_DIR, "diretorio_arq", f"{prefix}_Banking.csv")
    perf_account_csv = os.path.join(UPDATE_DIR, "diretorio_arq", f"{prefix}_Performance_Account.csv")
    nnm_csv = os.path.join(UPDATE_DIR, "diretorio_arq", f"{prefix}_NNM.csv")
    ordens_csv = os.path.join(UPDATE_DIR, "diretorio_arq", f"{prefix}_Ordens_Bolsa.csv")
    onboarding_csv = os.path.join(UPDATE_DIR, "diretorio_arq", f"{prefix}_Dados_Onboarding_Partner.csv")
    
    # Checar se existem
    if not os.path.isfile(merged_csv):
        print(f"AVISO: Arquivo não encontrado: {merged_csv}. O script pode falhar.")
    if not os.path.isfile(posicao_csv):
        print(f"AVISO: Arquivo não encontrado: {posicao_csv}. O script pode falhar.")
    if not os.path.isfile(banking_csv):
        print(f"AVISO: Arquivo não encontrado: {banking_csv}. O script pode falhar.")
    if not os.path.isfile(perf_account_csv):
        print(f"AVISO: Arquivo não encontrado: {perf_account_csv}. O script pode falhar.")
    if not os.path.isfile(onboarding_csv):
        print(f"AVISO: Arquivo não encontrado: {onboarding_csv}. O script de onboarding será pulado.")
    # 1. Enviar Dados Cadastrais e de Contas
    print(f"-> Sincronizando dados cadastrais, contas e assessores ({prefix})...")
    res1 = subprocess.run([sys.executable, "_supa4.py", merged_csv], cwd=SEND_DIR)
    if res1.returncode != 0:
        print(f"Erro no _supa4.py para {prefix}.")
    
    # 2. Enviar Posição
    if os.path.isfile(posicao_csv):
        print(f"-> Sincronizando posição financeira ({prefix})...")
        res2 = subprocess.run([sys.executable, "_supa_pos.py", posicao_csv], cwd=SEND_DIR)
        if res2.returncode != 0:
            print(f"Erro no _supa_pos.py para {prefix}.")
    else:
        print(f"-> Pulando posição financeira ({prefix}), arquivo não encontrado.")

    # 3. Enviar Banking
    if os.path.isfile(banking_csv):
        print(f"-> Sincronizando dados bancários ({prefix})...")
        res3 = subprocess.run([sys.executable, "_supa_banking.py", banking_csv], cwd=SEND_DIR)
        if res3.returncode != 0:
            print(f"Erro no _supa_banking.py para {prefix}.")
    else:
        print(f"-> Pulando dados bancários ({prefix}), arquivo não encontrado.")
        
    # 4. Enviar Performance Account
    if os.path.isfile(perf_account_csv):
        print(f"-> Sincronizando dados de performance_account ({prefix})...")
        res4 = subprocess.run([sys.executable, "_supa_perf_account.py", perf_account_csv], cwd=SEND_DIR)
        if res4.returncode != 0:
            print(f"Erro no _supa_perf_account.py para {prefix}.")
    else:
        print(f"-> Pulando dados de performance ({prefix}), arquivo não encontrado.")

    # 5. Enviar NNM
    if os.path.isfile(nnm_csv):
        print(f"-> Sincronizando dados de NNM ({prefix})...")
        res5 = subprocess.run([sys.executable, "_supa_nnm.py", nnm_csv], cwd=SEND_DIR)
        if res5.returncode != 0:
            print(f"Erro no _supa_nnm.py para {prefix}.")
    else:
        print(f"-> Pulando NNM ({prefix}), arquivo não encontrado.")

    # 6. Enviar Ordens Bolsa
    if os.path.isfile(ordens_csv):
        print(f"-> Sincronizando dados de Ordens Bolsa ({prefix})...")
        res6 = subprocess.run([sys.executable, "_supa_ordens.py", ordens_csv], cwd=SEND_DIR)
        if res6.returncode != 0:
            print(f"Erro no _supa_ordens.py para {prefix}.")
    else:
        print(f"-> Pulando Ordens Bolsa ({prefix}), arquivo não encontrado.")

    # 7. Enviar Onboarding
    if os.path.isfile(onboarding_csv):
        print(f"-> Sincronizando dados de Onboarding ({prefix})...")
        res7 = subprocess.run([sys.executable, "_supa_onboarding.py", onboarding_csv], cwd=SEND_DIR)
        if res7.returncode != 0:
            print(f"Erro no _supa_onboarding.py para {prefix}.")
    else:
        print(f"-> Pulando Onboarding ({prefix}), arquivo não encontrado.")

    print(f">>> Envio para {prefix.upper()} concluído <<<")

if __name__ == "__main__":
    print("========================================")
    print("      INICIANDO ORQUESTRAÇÃO GERAL      ")
    print("========================================")
    
    # Passo 1: Atualizar dados (baixar relatórios do BTG, gerar merges)
    run_update()
    
    # Passo 2: Enviar dados da "consultoria" para o Supabase
    run_send("consultoria")
    
    # Passo 3: Enviar dados "gen" para o Supabase
    run_send("gen")
    
    print("\n========================================")
    print("      ORQUESTRAÇÃO GERAL CONCLUÍDA!     ")
    print("========================================")
