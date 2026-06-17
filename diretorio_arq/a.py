import pandas as pd

df = pd.read_csv('onboarding.csv', sep=';')

df = df.sort_values('timestamp_escrita')

df = df.groupby('cpf').last()

df.to_csv('onboarding_dedup.csv', sep=';')
# print(df)