from supa_base_client import get_supabase_client
from _supa_banking import normalize_for_comparison, get_record_changes
import json

supabase = get_supabase_client()
res = supabase.table("tb_banking").select("*").limit(3).execute()
for item in res.data:
    print(json.dumps(item, indent=2))
    break
