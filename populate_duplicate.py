import sys
import os
import re

# Add send to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'send'))

from supa_base_client import get_supabase_client

def format_cpf_cnpj(val):
    if val is None or val == '':
        return None
    # Strip any non-digit character
    s = re.sub(r'\D', '', str(val))
    if not s:
        return None
    # Pad to 11 digits if <= 11 (CPF), or 14 digits if > 11 (CNPJ)
    if len(s) <= 11:
        return s.zfill(11)
    else:
        return s.zfill(14)

def main():
    try:
        supabase = get_supabase_client()
        print("Connected to Supabase.")
    except Exception as e:
        print(f"Error connecting to Supabase: {e}")
        return

    # Fetch all records from tb_cliente
    print("Fetching records from tb_cliente...")
    try:
        res = supabase.table('tb_cliente').select('*').execute()
        records = res.data
        print(f"Retrieved {len(records)} records from tb_cliente.")
    except Exception as e:
        print(f"Error fetching from tb_cliente: {e}")
        return

    if not records:
        print("No records found in tb_cliente.")
        return

    # Format the document columns as string (keeping leading zeros)
    formatted_records = []
    for r in records:
        # Create a copy of the record
        new_record = dict(r)
        
        # Format documento_cpf_cnpj
        old_cpf_cnpj = r.get('documento_cpf_cnpj')
        new_cpf_cnpj = format_cpf_cnpj(old_cpf_cnpj)
        new_record['documento_cpf_cnpj'] = new_cpf_cnpj
        
        # Format cpf_conjuge if present
        if 'cpf_conjuge' in new_record:
            new_record['cpf_conjuge'] = format_cpf_cnpj(new_record['cpf_conjuge'])
            
        formatted_records.append(new_record)

    # Let's clean or print a couple of examples of formatted records
    print("\nSample transformations:")
    sample_count = min(5, len(records))
    for i in range(sample_count):
        orig = records[i].get('documento_cpf_cnpj')
        trans = formatted_records[i].get('documento_cpf_cnpj')
        name = records[i].get('nome_completo')
        print(f"Original: {orig} -> Formatted: {trans} | Name: {name}")

    # Insert/Upsert the formatted records into tb_cliente (main table)
    print("\nInserting records into tb_cliente ...")
    # We can process in batches of 100 to be safe
    batch_size = 100
    success_count = 0
    
    for i in range(0, len(formatted_records), batch_size):
        chunk = formatted_records[i:i + batch_size]
        try:
            # Upsert into the main tb_cliente table
            supabase.table('tb_cliente').upsert(chunk).execute()
            success_count += len(chunk)
            print(f"  [OK] Batch {i//batch_size + 1}: Upserted {len(chunk)} records.")
        except Exception as e:
            print(f"  [ERROR] Batch {i//batch_size + 1} failed: {e}")
            # Try to print first item in batch for debugging
            if chunk:
                print("First record of failed chunk:", chunk[0])
            break

    print(f"\nDone! Successfully populated {success_count} records into tb_cliente_duplicate.")

if __name__ == "__main__":
    main()
