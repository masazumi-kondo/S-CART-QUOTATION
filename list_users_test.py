import sqlite3
conn = sqlite3.connect('estimates.db')
cursor = conn.cursor()
cursor.execute('SELECT id, login_id, role, is_active FROM users LIMIT 20')
users = cursor.fetchall()
for user in users:
    print(f'ID: {user[0]}, User: {user[1]}, Role: {user[2]}, Active: {user[3]}')
conn.close()
