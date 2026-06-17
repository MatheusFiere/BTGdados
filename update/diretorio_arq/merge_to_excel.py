import os
import pandas as pd
from collections import defaultdict

def main():
    diretorio = os.path.dirname(os.path.abspath(__file__))
    
    tipos_de_dado = defaultdict(list)
    
    # Mapear os arquivos .csv pelo tipo de dado
    for arquivo in os.listdir(diretorio):
        if not arquivo.endswith('.csv'):
            continue
        # Ignorar arquivos gerados anteriormente (que comecem com merged_)
        if arquivo.startswith('merged_'):
            continue
            
        if '_' in arquivo:
            prefixo, tipo_com_ext = arquivo.split('_', 1)
            tipo = tipo_com_ext.replace('.csv', '')
            tipos_de_dado[tipo].append(arquivo)

    caminho_excel = os.path.join(diretorio, 'Dados_Mesclados.xlsx')
    
    # Criar um arquivo excel contendo todos os merges
    try:
        writer = pd.ExcelWriter(caminho_excel, engine='openpyxl')
    except ImportError:
        # Tenta usar xlsxwriter se openpyxl não estiver instalado
        writer = pd.ExcelWriter(caminho_excel, engine='xlsxwriter')
    
    with writer:
        for tipo, arquivos in tipos_de_dado.items():
            if len(arquivos) == 0:
                continue
                
            print(f"Processando tipo: {tipo} (Arquivos: {arquivos})")
            
            df_list = []
            for arquivo in arquivos:
                caminho_arquivo = os.path.join(diretorio, arquivo)
                prefixo = arquivo.split('_', 1)[0]
                
                # Tentar ler com utf-8, se der erro usar latin1
                try:
                    df = pd.read_csv(caminho_arquivo, sep=';', encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(caminho_arquivo, sep=';', encoding='latin1')
                
                # Adicionar a coluna indicando o prefixo (Origem)
                df.insert(0, 'Prefixo', prefixo)
                df_list.append(df)
            
            # Merge por linhas (Concatenação)
            df_concatenado = pd.concat(df_list, ignore_index=True)
            
            # 1) Colocar eles no mesmo CSV
            nome_csv_saida = f"merged_tipo_{tipo}.csv"
            caminho_csv_saida = os.path.join(diretorio, nome_csv_saida)
            df_concatenado.to_csv(caminho_csv_saida, sep=';', index=False, encoding='utf-8')
            
            # 2) Juntar todos os CSVs em apenas um Excel
            nome_aba = tipo[:31] # O nome da aba no Excel é limitado a 31 caracteres
            df_concatenado.to_excel(writer, sheet_name=nome_aba, index=False)

    print(f"\nProcesso finalizado com sucesso!")
    print(f"Arquivo Excel gerado em: {caminho_excel}")

if __name__ == '__main__':
    main()
