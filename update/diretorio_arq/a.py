import pandas as pd


df = pd.read_csv('consultoria_Dados_Cadastrais.csv', sep=';', dtype={'documento_cpf_cnpj' : str})

a = "02155154470"

df = df[df['documento_cpf_cnpj'] == a]

print(df)