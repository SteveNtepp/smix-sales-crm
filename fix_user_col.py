with open("database_handler.py", "r") as f:
    c = f.read()

# Replace user column definition in activity_log table
c = c.replace("user       TEXT,", '"user"       TEXT,')

# Replace insert into activity log
c = c.replace(
    'INSERT INTO activity_log(user,lead_id,action,detail) VALUES(%s,%s,%s,%s)',
    'INSERT INTO activity_log("user",lead_id,action,detail) VALUES(%s,%s,%s,%s)'
)

with open("database_handler.py", "w") as f:
    f.write(c)
