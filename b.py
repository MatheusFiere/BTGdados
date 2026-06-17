import pandas as pd


df = pd.read_csv(r'update/diretorio_arq/consultoria_Posicao.csv', sep=';')

df = df[df['mercado'] == 'CONTA CORRENTE']
df = df[df['nr_conta'] == 14741839]


print(df[['nr_conta', 'dt_interface', 'vl_bruto']])