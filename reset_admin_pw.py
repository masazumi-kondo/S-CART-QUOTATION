import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect('estimates.db')
cursor = conn.cursor()

# Reset admin password to "admin123"
new_password = "admin123"
password_hash = generate_password_hash(new_password)

cursor.execute('UPDATE users SET password_hash = ? WHERE login_id = ?', 
               (password_hash, 'admin'))
conn.commit()
conn.close()

print(f"Admin password reset to: {new_password}")
