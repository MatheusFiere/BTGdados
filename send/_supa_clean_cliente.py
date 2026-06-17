import os
import sys
import warnings
import re
from supa_base_client import get_supabase_client

# Initialize Supabase client (service role for full access)
supabase = get_supabase_client()

warnings.filterwarnings('ignore')

TABLE_NAME = 'tb_cliente'
DOC_COLUMN = 'documento_cpf_cnpj'

def fetch_all_records():
    # Fetch all records with the document column
    response = supabase.table(TABLE_NAME).select(f'{DOC_COLUMN}').execute()
    if not response.data:
        print('Error fetching records:', response)
        sys.exit(1)
    return response.data

def delete_record_by_doc(doc):
    # Delete a single record identified by its documento_cpf_cnpj value
    resp = supabase.table(TABLE_NAME).delete().eq(DOC_COLUMN, doc).execute()
    if resp.data is None:
        print(f'Error deleting {doc}:', resp)
    else:
        print(f'Deleted record with {DOC_COLUMN} = {doc}')

def main():
    records = fetch_all_records()
    to_delete = []
    for rec in records:
        doc = rec.get(DOC_COLUMN)
        if doc is None:
            continue
        # Clean only digits
        digits = re.sub(r'\D', '', str(doc))
        if len(digits) < 11:
            to_delete.append(digits)
    if not to_delete:
        print('No records to delete.')
        return
    print(f'Found {len(to_delete)} records to delete.')
    for doc in to_delete:
        delete_record_by_doc(doc)

if __name__ == '__main__':
    main()
