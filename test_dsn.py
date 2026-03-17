import urllib.parse
password = "++%6ttplD--"
encoded = urllib.parse.quote(password, safe='')
dsn = f"postgresql://postgres.oebqgbfazfdmeakqqpko:{encoded}@aws-1-eu-central-2.pooler.supabase.com:5432/postgres"

import psycopg2
try:
    conn = psycopg2.connect(dsn)
    print("OK psycopg2")
except Exception as e:
    print("psycopg2 error:", e)

from sqlalchemy import create_engine
try:
    engine = create_engine(dsn)
    with engine.connect() as c:
        pass
    print("OK sqlalchemy")
except Exception as e:
    print("sqlalchemy error:", type(e).__name__)
