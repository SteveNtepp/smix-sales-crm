import re

with open('database_handler.py', 'r') as f:
    lines = f.readlines()

new_lines = []
skip = 0

for i, line in enumerate(lines):
    if skip > 0:
        skip -= 1
        continue
    
    # Match assignment: rows = conn.execute("...").fetchall()
    match_rows = re.search(r'(\s+)rows\s+=\s+conn\.execute\((.*?)\)\.fetchall\(\)', line)
    if match_rows:
        indent = match_rows.group(1)
        query = match_rows.group(2)
        new_lines.append(f"{indent}with conn.cursor() as cur:\n")
        new_lines.append(f"{indent}    cur.execute({query})\n")
        new_lines.append(f"{indent}    rows = cur.fetchall()\n")
        continue

    # Match row = conn.execute("...").fetchone()
    match_row = re.search(r'(\s+)row\s+=\s+conn\.execute\((.*?)\)\.fetchone\(\)', line)
    if match_row:
        indent = match_row.group(1)
        query = match_row.group(2)
        new_lines.append(f"{indent}with conn.cursor() as cur:\n")
        new_lines.append(f"{indent}    cur.execute({query})\n")
        new_lines.append(f"{indent}    row = cur.fetchone()\n")
        continue

    # Match multiline conn.execute select
    if 'rows = conn.execute(' in line and ').fetchall()' in lines[i+1]:
        match = re.search(r'(\s+)rows\s+=\s+conn\.execute\(', line)
        indent = match.group(1)
        query = line.strip().replace('rows = conn.execute(', '')
        new_lines.append(f"{indent}with conn.cursor() as cur:\n")
        new_lines.append(f"{indent}    cur.execute({query}\n")
        new_lines.append(f"{indent}    rows = cur.fetchall()\n")
        skip = 1
        continue

    # Match conn.execute update/insert
    match_exec = re.search(r'(\s+)conn\.execute\((.*?)\)', line)
    if match_exec and 'rows =' not in line and 'row =' not in line:
        indent = match_exec.group(1)
        query = match_exec.group(2)
        new_lines.append(f"{indent}with conn.cursor() as cur:\n")
        new_lines.append(f"{indent}    cur.execute({query})\n")
        continue
    
    new_lines.append(line)

with open('database_handler.py', 'w') as f:
    f.writelines(new_lines)
