import requests
import base64
import time
import uuid
import os
import pandas as pd
from datetime import datetime

# ==========================================
# CREDENCIAIS
# ==========================================
CONSULTORIA_CLIENT_ID = '1b8fd123f373c20299dc60e51d904658'
CONSULTORIA_CLIENT_SECRET = 'E4ABC1DC05E003E4645989EE6012CAB8AD5E89B7E06829BC3FE7B8478BF1D181'
CONSULTORIA_TOKEN_FILE = 'token_consultoria.csv'

GEN_CLIENT_ID = 'e1ac9da1700e6a00396d234a24a682f9'
GEN_CLIENT_SECRET = 'E4472FD67B09B522945010E6D8385FE78B7D762199889203F70F8F27A2BA056A'
GEN_TOKEN_FILE = 'token.csv'

AUTH_URL = 'https://api.btgpactual.com/iaas-auth/api/v1/authorization/oauth2/accesstoken'


def generate_uuid():
    return str(uuid.uuid4())

def get_basic_auth_header(client_id, client_secret):
    client_credentials = f"{client_id}:{client_secret}"
    client_credentials_base64 = base64.b64encode(client_credentials.encode()).decode()
    return f"Basic {client_credentials_base64}"

def get_access_token(client_id, client_secret):
    headers = {
        'Authorization': get_basic_auth_header(client_id, client_secret),
        'Content-Type': 'application/x-www-form-urlencoded',
        'x-id-partner-request': generate_uuid()
    }
    data = {
        'grant_type': 'client_credentials'
    }
    response = requests.post(AUTH_URL, headers=headers, data=data)

    if response.status_code == 200:
        response_data = response.headers
        date_object = datetime.strptime(response_data.get('Expires'), "%a, %d %b %Y %H:%M:%S %Z")
        return response_data.get('access_token'), date_object
    else:
        print(f"Erro ao obter token: {response.status_code} - {response.text}")
        return None, None

def write_token(client_id, client_secret, token_file):
    token, expiration = get_access_token(client_id, client_secret)
    writer = f"token,expiration\n{token},{expiration}\n"
    with open(token_file, 'w') as f:
        f.write(writer)
    time.sleep(0.25)

def manage_token(token_type="consultoria"):
    if token_type == "consultoria":
        client_id = CONSULTORIA_CLIENT_ID
        client_secret = CONSULTORIA_CLIENT_SECRET
        token_file = CONSULTORIA_TOKEN_FILE
    elif token_type == "gen":
        client_id = GEN_CLIENT_ID
        client_secret = GEN_CLIENT_SECRET
        token_file = GEN_TOKEN_FILE
    else:
        raise ValueError("token_type must be either 'consultoria' or 'gen'")

    if not os.path.isfile(token_file):
        write_token(client_id, client_secret, token_file)
        
    df = pd.read_csv(token_file, parse_dates=["expiration"])
    now = datetime.now()
    exp = df['expiration'].iloc[0]
    
    diff = (exp - now).total_seconds()

    if diff <= 9000:
        write_token(client_id, client_secret, token_file)
        df = pd.read_csv(token_file, parse_dates=["expiration"])

    return df['token'].iloc[0]

def manage_token_consultoria():
    return manage_token("consultoria")

def manage_token_gen():
    return manage_token("gen")

if __name__ == "__main__":
    print("Testando token consultoria:", manage_token_consultoria())
    print("Testando token gen:", manage_token_gen())
