import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'send'))

from supa_base_client import get_supabase_client
supabase = get_supabase_client()

res = supabase.table('tb_cliente').select('documento_cpf_cnpj, nome_completo').limit(10).execute()
print("tb_cliente rows:")
for row in res.data:
    # Ensure CPF is treated as text with leading zeros (11 digits)
    cpf = str(row['documento_cpf_cnpj']).zfill(11)
    print(f"CPF: {cpf} | Nome: {row['nome_completo']}")
