from app import app, db

def add_estimator_name_column():
    with app.app_context():
        try:
            engine = db.engine
            conn = engine.raw_connection()
            cursor = conn.cursor()

            # quotations テーブルのカラム一覧を取得
            cursor.execute("PRAGMA table_info(quotations);")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]

            if "estimator_name" in column_names:
                print("estimator_name カラムは既に存在します。")
            else:
                cursor.execute("ALTER TABLE quotations ADD COLUMN estimator_name VARCHAR(100);")
                conn.commit()
                print("estimator_name カラムを追加しました。")

            cursor.close()
            conn.close()
        except Exception as e:
            print(f"エラー: {e}")

if __name__ == "__main__":
    add_estimator_name_column()

"""
【実行手順】
1. 必要なら仮想環境を有効化してください。
2. プロジェクトルートで以下を実行してください:
   python scripts/add_estimator_name_column.py
3. 「estimator_name カラムを追加しました」または
   「estimator_name カラムは既に存在します」と表示されればOKです。
"""
