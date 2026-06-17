import os

print("Searching for 'tb_cliente_duplicate' in files...")
found = False
for root, dirs, files in os.walk('.'):
    if '.git' in dirs:
        dirs.remove('.git')
    if '__pycache__' in dirs:
        dirs.remove('__pycache__')
    for file in files:
        if file.endswith('.py') or file.endswith('.sql') or file.endswith('.txt'):
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if 'tb_cliente_duplicate' in content:
                        print(f"Found in {path}")
                        found = True
            except Exception as e:
                print(f"Error reading {path}: {e}")

if not found:
    print("No references to 'tb_cliente_duplicate' found in any files.")
