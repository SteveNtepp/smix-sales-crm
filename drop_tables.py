import database_handler

conn = database_handler.get_connection()
c = conn.cursor()
tables = ["users", "leads", "config", "scripts", "script_templates", "kit_sections", "videos", "activity_log"]
for t in tables:
    try:
        c.execute(f"DROP TABLE IF EXISTS {t} CASCADE;")
    except Exception as e:
        print(e)
conn.commit()
print("Dropped successfully.")
