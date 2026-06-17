
import requests
import base64
import time
import uuid
import datetime as dt
from datetime import datetime
import os
import pandas as pd
import zipfile
import io
import shutil


# Function to generate a random UUID
def generate_uuid():
    return str(uuid.uuid4())


webhook_url = 'https://api-btg-2.onrender.com/webhook'

# Definindo as variáveis de autenticação
client_id = '1b8fd123f373c20299dc60e51d904658'
client_secret = 'E4ABC1DC05E003E4645989EE6012CAB8AD5E89B7E06829BC3FE7B8478BF1D181'


auth_url = 'https://api.btgpactual.com/iaas-auth/api/v1/authorization/oauth2/accesstoken'

# Função para gerar o header Authorization
def get_basic_auth_header(client_id, client_secret):
    client_credentials = f"{client_id}:{client_secret}"
    client_credentials_base64 = base64.b64encode(client_credentials.encode()).decode()

    # print(f"Basic {client_credentials_base64}")

    return f"Basic {client_credentials_base64}"

# Função para obter o access token
def get_access_token():
    headers = {
        'Authorization': get_basic_auth_header(client_id, client_secret),
        'Content-Type': 'application/x-www-form-urlencoded',
        'x-id-partner-request': generate_uuid()
    }
    data = {
        'grant_type': 'client_credentials'
    }
    response = requests.post(auth_url, headers=headers, data=data)

    print(response)
    print(response.text)

    if response.status_code == 200:
        response_data = response.headers
        date_object = datetime.strptime(response_data.get('Expires'), "%a, %d %b %Y %H:%M:%S %Z")

        return response_data.get('access_token'), (date_object)
    else:
        print(f"Erro ao obter token: {response.status_code} - {response.text}")
        return None, None


def write_token():
    token, expiration = get_access_token()
    print(token)

    writer = f"""token,expiration
{token},{expiration}
"""
    with open('token_consultoria.csv', 'w') as f:
        f.write(writer)
    time.sleep(0.25)



def manage_token():
    # print("Gerenciando token...")
    if not os.path.isfile('token_consultoria.csv'):
        write_token()
        

    df = pd.read_csv('token_consultoria.csv', parse_dates=["expiration"])


    now = datetime.now()
    exp = (df['expiration'].iloc[0])

    diff = (exp - now).total_seconds()

    print(diff)

    if diff <= 9_000:
        write_token()

    df = pd.read_csv('token_consultoria.csv', parse_dates=["expiration"])

    return df['token'].iloc[0]

def take_file_from_server(name):
    
    webhook_url = 'https://api-btg-2.onrender.com/webhook'

    api_key = 'a5d4accd-6cc5-4734-bab4-c52b0711cf8a785f0ddb-a67d-4858-bade-da0c24cd7ad4a5ffdef5-0d31-434a-b71b-0865f047d2e2be705127-bd5c-441d-a8af-1a48d916084664aa522e-0bfb-443e-a90e-80cf299a51386456b7f3-7091-498a-8bcf-c345f3b13a71cc9fc6d9-1bc5-4628-95b1-58dab40500277a38d141-2207-42a2-9bf6-17555c290ba376d47b88-9b12-4dce-8083-3486d46ca9af30909bf4-a95c-44a6-8561-dcd8e2acc6010f88f5ac-a41b-4baf-bd76-da5fc3aee9f6e2cd0625-fe6c-456a-8325-2b76c133a10ef2e771c8-10c7-43d9-aa31-4231c6b35f8dee16307d-dd43-429d-ac3e-3cbb311334cf22d6c199-07f1-48ff-86c8-f9fba45ffb0aeb5db59d-caca-4dea-bbbc-989cb3c0e1113b28d6cf-0e9f-4723-bb47-d873113a19584312cca8-6faf-4e66-9db5-f61b63defe049fda4d2e-55cd-45cc-85b3-b89fba18831f20445dd8-4e66-4dbf-9c4d-29b886f86a0a'


    url_antiga = ''
    path_url_file = 'last_url_consultoria.txt'

    # Lê a última URL salva, se existir
    if os.path.exists(path_url_file):
        with open(path_url_file, 'r') as f:
            url_antiga = f.read().strip()

    contador = 0
    while contador < 5:
        response = requests.get(
            webhook_url,
            headers={
                'Content-Type': 'application/json',
                'x-api-key': api_key
            }
        )

        try:
            json_load = response.json()
            url = json_load['response']['url']

            # Verifica se a URL nova é igual à antiga
            if url == url_antiga:
                print(f"URL repetida. Tentando novamente em 120 segundos... ({contador + 1}/5)")
                time.sleep(120)
                contador += 1
                continue
            else:
                # Salva nova URL
                with open(path_url_file, 'w') as f:
                    f.write(url)
                break  # Sai do loop se URL mudou

        except Exception as e:
            date = str(datetime.now())
            with open("error_log/error_log_consultoria.csv", 'a') as f:
                f.write(f"{date}; ERRO AO OBTER URL: {str(e)}\n")
            return None

    if contador == 5:
        print("URL não mudou após 5 tentativas. Encerrando.")
        return None

    try:
        response_file = requests.get(url, stream=True)

        if response_file.status_code == 200:
            path_extract = 'extracted_files'

            if response_file.headers['Content-Type'] == 'application/zip':
                if os.path.isdir(path_extract):
                    shutil.rmtree(path_extract)

                zip_file = io.BytesIO(response_file.content)
                with zipfile.ZipFile(zip_file) as zip_ref:
                    zip_ref.extractall(path_extract)

                for i in os.listdir(path_extract):
                    os.rename(f"{path_extract}/{i}", f'{name}.csv')

                return 'application/zip'

            else:
                with open(f'{name}.csv', "wb") as file:
                    for chunk in response_file.iter_content(chunk_size=8192):
                        file.write(chunk)
                return 'other'

    except Exception as e:
        date = str(datetime.now())
        with open("error_log/error_log.csv", 'a') as f:
            f.write(f"{date}; ERRO AO BAIXAR ARQUIVO: {str(e)}\n")
        return None

# Exemplo de uso da função get_access_token
if __name__ == "__main__":
    # manage_token()


    
    # take_file_from_server('a')

    token = manage_token()
    
    print(token)


