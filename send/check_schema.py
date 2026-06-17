import os
from supabase import create_client

SUPABASE_URL = "SUA_URL"
SUPABASE_KEY = "SUA_KEY"
try:
    from supa_base_client import get_supabase_client
    supabase = get_supabase_client()
except:
    pass

res = supabase.table('tb_posicao').select('*').limit(1).execute()
res2 = supabase.table('tb_banking').select('*').limit(1).execute()

with open("out_schema.txt", "w", encoding="utf-8") as f:
    f.write(f"tb_posicao keys: {list(res.data[0].keys()) if res.data else 'No data'}\n")
    f.write(f"tb_banking keys: {list(res2.data[0].keys()) if res2.data else 'No data'}\n")
