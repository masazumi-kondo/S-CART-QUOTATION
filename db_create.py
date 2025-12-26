print("db_create.py start")
import os
import traceback
from app import create_app, db

# DBファイルの親ディレクトリを作成（なければ）
db_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "app", "db")
os.makedirs(db_dir, exist_ok=True)

try:
    app = create_app()
    with app.app_context():
        db.create_all()
        print("Database and tables created successfully.")
except Exception as e:
    print("=== Exception occurred ===")
    traceback.print_exc()
