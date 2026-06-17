import pandas as pd

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

    # remove espaços escondidos (tipo "accept_comunication ")
    # df.columns = df.columns.str.strip()

    # aplica tradução sem quebrar se faltar chave
    df = df.rename(columns=lambda col: traducao.get(col, col))

    return df


# ===== EXEMPLO DE USO =====
df = pd.read_csv("consultoria_Dados_Onboarding_Partner_Manual.csv", sep=',')
df = traduzir_colunas(df)
print(df)

df.to_csv('onboarding.csv', sep=';')