import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "backend", "users.db")
if not os.path.exists(db_path):
    print("Database does not exist yet. Run the app to initialize it.")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT username, totp_secret, role FROM users WHERE role = 'admin'")
    admins = cursor.fetchall()
    
    if admins:
        for admin in admins:
            print(f"Username: {admin[0]}")
            print(f"TOTP/Authenticator Secret: {admin[1]}")
            print(f"Role: {admin[2]}")
            print("-" * 30)
            print("Action: Enter the TOTP/Authenticator Secret into Google Authenticator or Authy to generate your OTPs.")
    else:
        print("No admin users found in the database.")
