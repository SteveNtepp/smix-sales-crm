import re

with open('database_handler.py', 'r') as f:
    code = f.read()

# 1. Imports and Connection
code = code.replace(
    'import sqlite3\nimport hashlib',
    'import psycopg2\nfrom psycopg2.extras import RealDictCursor\nimport streamlit as st\nimport os\nfrom sqlalchemy import create_engine\nimport hashlib'
)
code = code.replace('DB_PATH = "smix_sales.db"\n', '')

conn_old = """def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn"""
conn_new = """def get_engine():
    db_url = os.getenv("DB_URL") or st.secrets["DB_URL"]
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return create_engine(db_url)

def get_connection():
    db_url = os.getenv("DB_URL") or st.secrets["DB_URL"]
    conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    conn.autocommit = False
    return conn"""
code = code.replace(conn_old, conn_new)

# 2. Table creation replacements 
code = code.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
code = code.replace("INTEGER DEFAULT 1", "BOOLEAN DEFAULT true")
code = code.replace("INTEGER DEFAULT 0", "BOOLEAN DEFAULT false")
code = code.replace("TEXT DEFAULT (datetime('now'))", "TIMESTAMP DEFAULT NOW()")
code = code.replace("TEXT DEFAULT (datetime('now', '-7 days'))", "TIMESTAMP DEFAULT (NOW() - INTERVAL '7 days')")
# Replace any PRAGMA migrations inside init_db as they are sqlite specific
pragma_re = re.compile(r'# migrations for users\n.*?lead_cols = \[r\[1\].*?c\.execute\(f"ALTER TABLE leads ADD COLUMN \{col\} \{defn\}"\)', re.DOTALL)
code = pragma_re.sub('', code)
# Also need to scrub remaining users Pragma separately if the regex missed part
pragma_u_re = re.compile(r'# migrations for users\n\s*user_cols = \[.*?ALTER TABLE users ADD COLUMN active BOOLEAN DEFAULT true"\)\n\n', re.DOTALL)
code = pragma_u_re.sub('', code)
code = code.replace('lead_cols = [r[1] for r in c.execute("PRAGMA table_info(leads)").fetchall()]\n    for col, defn in [("follow_up_date", "TEXT"), ("follow_up_day", "BOOLEAN DEFAULT false")]:\n        if col not in lead_cols:\n            c.execute(f"ALTER TABLE leads ADD COLUMN {col} {defn}")', '')


# 3. ON CONFLICT mapping
code = code.replace('INSERT OR IGNORE INTO users (username,password,role,full_name) VALUES (?,?,?,?)', 'INSERT INTO users (username,password,role,full_name) VALUES (%s,%s,%s,%s) ON CONFLICT (username) DO NOTHING')
code = code.replace('INSERT OR IGNORE INTO config(key,value) VALUES(?,?)', 'INSERT INTO config(key,value) VALUES(%s,%s) ON CONFLICT (key) DO NOTHING')
code = code.replace('INSERT OR REPLACE INTO scripts(day,title,content) VALUES(?,?,?)', 'INSERT INTO scripts(day,title,content) VALUES(%s,%s,%s) ON CONFLICT (day) DO UPDATE SET title=EXCLUDED.title, content=EXCLUDED.content')
code = code.replace('INSERT OR IGNORE INTO kit_sections (section_key, title, icon, content, order_idx)\n            VALUES (?, ?, ?, ?, ?)', 'INSERT INTO kit_sections (section_key, title, icon, content, order_idx)\n            VALUES (%s, %s, %s, %s, %s) ON CONFLICT (section_key) DO NOTHING')
# Videos insert or ignore where not exists...
vid_old = """INSERT OR IGNORE INTO videos (title, description, youtube_url, order_idx)
            SELECT ?, ?, ?, ?
            WHERE NOT EXISTS (SELECT 1 FROM videos WHERE youtube_url=?)"""
vid_new = """INSERT INTO videos (title, description, youtube_url, order_idx)
            VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING"""
# Wait, Videos has no UNIQUE constraint on youtube_url. Let's add it dynamically
code = code.replace("youtube_url TEXT NOT NULL,", "youtube_url TEXT UNIQUE NOT NULL,")
# For postgres, %s is used
code = code.replace(vid_old, vid_new)
code = code.replace('(title, desc, url, order, url)', '(title, desc, url, order)')


# 4. Replace parameter placeholders
code = code.replace("WHERE username=? AND password=? AND active=1", 'WHERE username=%s AND password=%s AND active=true')
code = code.replace("WHERE active=1", 'WHERE active=true')
code = code.replace("SET password=? WHERE id=?", 'SET password=%s WHERE id=%s')
code = code.replace("SET active=? WHERE id=?", 'SET active=%s WHERE id=%s')
code = code.replace("VALUES(?,?,?,?)", 'VALUES(%s,%s,%s,%s)')
code = code.replace("VALUES(?,?,?,?,?)", 'VALUES(%s,%s,%s,%s,%s)')
code = code.replace("WHERE id=?", 'WHERE id=%s')
code = code.replace("WHERE assigned_to=?", 'WHERE assigned_to=%s')
code = code.replace("WHERE youtube_url=?", 'WHERE youtube_url=%s')

code = code.replace('INSERT OR REPLACE INTO config(key,value) VALUES(?,?)', 'INSERT INTO config(key,value) VALUES(%s,%s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value')
code = code.replace('INSERT OR REPLACE INTO kit_sections (section_key, title, icon, content, order_idx)\n        VALUES (?, ?, ?, ?,\n            COALESCE((SELECT order_idx FROM kit_sections WHERE section_key=?), 99))', 'INSERT INTO kit_sections (section_key, title, icon, content, order_idx)\n        VALUES (%s, %s, %s, %s,\n            COALESCE((SELECT order_idx FROM kit_sections WHERE section_key=%s), 99)) ON CONFLICT (section_key) DO UPDATE SET title=EXCLUDED.title, icon=EXCLUDED.icon, content=EXCLUDED.content')


# 5. Read SQL Query replacements (Pandas requires SQLAlchemy engine)
# Replace pd.read_sql_query(..., conn) with pd.read_sql_query(..., get_engine())
code = code.replace(', conn)', ', get_engine())')
code = code.replace('conn, params=(assigned_to,))', 'get_engine(), params=(assigned_to,))')
code = code.replace(', conn, params=(assigned_to,))', ', get_engine(), params=(assigned_to,))')
code = code.replace(', conn, params=(limit,))', ', get_engine(), params=(limit,))')

# SQLite datetime('now') to PG NOW() inside query strings
code = code.replace("datetime('now', '-7 days')", "NOW() - INTERVAL '7 days'")

# 6. Deal with returning / lastrowid
code = code.replace('c.execute("INSERT INTO script_templates(name,category,content,created_by) VALUES(%s,%s,%s,%s)",\n              (name, category, content, created_by))\n    tid = c.lastrowid', 'c.execute("INSERT INTO script_templates(name,category,content,created_by) VALUES(%s,%s,%s,%s) RETURNING id",\n              (name, category, content, created_by))\n    tid = c.fetchone()["id"]')
code = code.replace('c.execute("INSERT INTO videos(title,description,youtube_url,order_idx,created_by) VALUES(%s,%s,%s,%s,%s)",\n              (title, description, youtube_url, order_idx, created_by))\n    vid = c.lastrowid', 'c.execute("INSERT INTO videos(title,description,youtube_url,order_idx,created_by) VALUES(%s,%s,%s,%s,%s) RETURNING id",\n              (title, description, youtube_url, order_idx, created_by))\n    vid = c.fetchone()["id"]')

# 7. Add lead parameter placeholders update (Named parameters: :name -> %(name)s)
lead_ins_old = """INSERT INTO leads
        (name,phone,email,assigned_to,status,goal,profile_type,urgency,
         budget_confirmed,available,fast_response,score,temperature,
         campaign,adset,creative,notes,last_contact,follow_up_date,follow_up_day)
        VALUES
        (:name,:phone,:email,:assigned_to,:status,:goal,:profile_type,:urgency,
         :budget_confirmed,:available,:fast_response,:score,:temperature,
         :campaign,:adset,:creative,:notes,:last_contact,:follow_up_date,:follow_up_day)"""
lead_ins_new = """INSERT INTO leads
        (name,phone,email,assigned_to,status,goal,profile_type,urgency,
         budget_confirmed,available,fast_response,score,temperature,
         campaign,adset,creative,notes,last_contact,follow_up_date,follow_up_day)
        VALUES
        (%(name)s,%(phone)s,%(email)s,%(assigned_to)s,%(status)s,%(goal)s,%(profile_type)s,%(urgency)s,
         %(budget_confirmed)s,%(available)s,%(fast_response)s,%(score)s,%(temperature)s,
         %(campaign)s,%(adset)s,%(creative)s,%(notes)s,%(last_contact)s,%(follow_up_date)s,%(follow_up_day)s) RETURNING id"""

code = code.replace(lead_ins_old, lead_ins_new)
code = code.replace('lead_id = c.lastrowid', 'lead_id = c.fetchone()["id"]')

lead_upd_old = """UPDATE leads SET
            name=:name, phone=:phone, email=:email, assigned_to=:assigned_to,
            status=:status, goal=:goal, profile_type=:profile_type, urgency=:urgency,
            budget_confirmed=:budget_confirmed, available=:available,
            fast_response=:fast_response, score=:score, temperature=:temperature,
            campaign=:campaign, adset=:adset, creative=:creative,
            amount_paid=:amount_paid, notes=:notes, last_contact=:last_contact,
            follow_up_date=:follow_up_date, updated_at=:updated_at
        WHERE id=:id"""
lead_upd_new = """UPDATE leads SET
            name=%(name)s, phone=%(phone)s, email=%(email)s, assigned_to=%(assigned_to)s,
            status=%(status)s, goal=%(goal)s, profile_type=%(profile_type)s, urgency=%(urgency)s,
            budget_confirmed=%(budget_confirmed)s, available=%(available)s,
            fast_response=%(fast_response)s, score=%(score)s, temperature=%(temperature)s,
            campaign=%(campaign)s, adset=%(adset)s, creative=%(creative)s,
            amount_paid=%(amount_paid)s, notes=%(notes)s, last_contact=%(last_contact)s,
            follow_up_date=%(follow_up_date)s, updated_at=%(updated_at)s
        WHERE id=%(id)s"""
code = code.replace(lead_upd_old, lead_upd_new)

# bools conversion in calculate_score -> 1 to True, 0 to False
code = code.replace('data.get("budget_confirmed", 0)', 'data.get("budget_confirmed", False)')
code = code.replace('data.get("available", 0)', 'data.get("available", False)')
code = code.replace('data.get("fast_response", 0)', 'data.get("fast_response", False)')


with open("database_handler.py", "w") as f:
    f.write(code)
print("Migration script completed.")
