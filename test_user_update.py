from backend.auth import auth_manager

# 1. Update Existing User (Admin)
print("Before update:")
with auth_manager.get_db_connection() as conn:
    print(conn.execute("SELECT phone_number FROM users WHERE username='admin'").fetchone()[0])

auth_manager.update_user(username="admin", password="newAdminPassword123", role="admin", phone="888-9999", email="admin@test.org")

print("After update:")
with auth_manager.get_db_connection() as conn:
    print(conn.execute("SELECT phone_number FROM users WHERE username='admin'").fetchone()[0])

# 2. Update Biometrics status
print("Before biometric update:")
with auth_manager.get_db_connection() as conn:
    print(conn.execute("SELECT has_biometric FROM users WHERE username='admin'").fetchone()[0])

auth_manager.update_user_biometric_status("admin", True)

print("After biometric update:")
with auth_manager.get_db_connection() as conn:
    print(conn.execute("SELECT has_biometric FROM users WHERE username='admin'").fetchone()[0])
