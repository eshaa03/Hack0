import sqlite3
import os

try:
    path = os.path.join("backend", "users.db")
    print(f"Path: {path}, Size: {os.path.getsize(path)}")
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("SELECT id, username, role, has_biometric FROM users")
    users = cur.fetchall()
    print("Users in DB:")
    for u in users:
        print(u)
except Exception as e:
    print("Error:", e)
