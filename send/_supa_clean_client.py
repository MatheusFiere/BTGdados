import os
import sys
from supa_base_client import get_supabase_client

# Initialize Supabase client
supabase = get_supabase_client()

# Name of the table and primary key column (adjust if different)
TABLE_NAME = "tb_client"
PRIMARY_KEY = "id"  # Adjust to actual primary key column if needed
DOC_COLUMN = "documento_cnpj_cpf"

def fetch_all_clients():
    """Fetch all client rows with their primary key and document column."""
    response = supabase.table(TABLE_NAME).select(f"{PRIMARY_KEY},{DOC_COLUMN}").execute()
    if response.error:
        print(f"Error fetching data: {response.error}")
        return []
    return response.data

def filter_invalid_ids(clients):
    """Return a list of primary keys where the document length is less than 11."""
    invalid_ids = []
    for row in clients:
        doc = row.get(DOC_COLUMN, "")
        if doc is None:
            continue
        # Ensure it's a string for length check
        doc_str = str(doc).strip()
        if len(doc_str) < 11:
            invalid_ids.append(row[PRIMARY_KEY])
    return invalid_ids

def delete_rows(ids):
    if not ids:
        print("No invalid rows to delete.")
        return
    # Supabase supports bulk delete via .in_ filter
    print(f"Deleting {len(ids)} invalid rows from {TABLE_NAME}...")
    response = supabase.table(TABLE_NAME).delete().in_(PRIMARY_KEY, ids).execute()
    if response.error:
        print(f"Error deleting rows: {response.error}")
    else:
        print("Deletion completed.")

if __name__ == "__main__":
    all_clients = fetch_all_clients()
    invalid_ids = filter_invalid_ids(all_clients)
    delete_rows(invalid_ids)
