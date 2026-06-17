import sys
import os
import json

# Add send to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'send'))

try:
    from supa_base_client import get_supabase_client
    supabase = get_supabase_client()
    print("Supabase connected.")
except Exception as e:
    print(f"Error connecting: {e}")
    sys.exit(1)

# Let's run a query to get columns for tb_cliente and tb_cliente_duplicate if it exists.
# We can use requests to call the postgres REST API if needed, or query postgrest if there's no direct SQL endpoint.
# Wait, let's try querying information_schema.columns via requests (if SQL api is available) or via select on the tables.
# Wait! Since we don't have SQL endpoint in supabase client easily, we can try to select 1 row from both tables.

try:
    print("Checking tb_cliente...")
    res_cliente = supabase.table('tb_cliente').select('*').limit(1).execute()
    print("tb_cliente row columns:", list(res_cliente.data[0].keys()) if res_cliente.data else "No data (table empty?)")
except Exception as e:
    print(f"Error reading tb_cliente: {e}")

try:
    print("Checking tb_cliente_duplicate...")
    res_dup = supabase.table('tb_cliente_duplicate').select('*').limit(1).execute()
    print("tb_cliente_duplicate row columns:", list(res_dup.data[0].keys()) if res_dup.data else "No data (table empty?)")
except Exception as e:
    print(f"Error reading tb_cliente_duplicate: {e}")

# We can also check details from the postgres pg_catalog if we run a query using an RPC or if the client allows it, but let's see.
# Let's inspect the REST API / swagger docs if available by fetching:
import requests
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
headers = {"apikey": key, "Authorization": f"Bearer {key}"}

try:
    r = requests.get(f"{url}/rest/v1/", headers=headers)
    if r.status_code == 200:
        specs = r.json()
        definitions = specs.get('definitions', {})
        print("\nTables found in definitions:")
        for t in sorted(definitions.keys()):
            if 'cliente' in t or 'duplicate' in t:
                print(f"Table: {t}")
                for col, info in definitions[t].get('properties', {}).items():
                    print(f"  - {col}: {info.get('type')} ({info.get('format')})")
except Exception as e:
    print(f"Error getting OpenAPI spec: {e}")
