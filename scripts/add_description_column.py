from app import app, db

def add_description_column():
    with app.app_context():
        try:
            engine = db.engine
            conn = engine.raw_connection()
            cursor = conn.cursor()

            # quotation_details テーブルのカラム一覧を取得
            cursor.execute("PRAGMA table_info(quotation_details);")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]

            if "description" in column_names:
                print("description カラムは既に存在します。")
            else:
                cursor.execute("ALTER TABLE quotation_details ADD COLUMN description VARCHAR(255);")
                conn.commit()
                print("description カラムを追加しました。")

            cursor.close()
            conn.close()
        except Exception as e:
            print(f"エラー: {e}")

if __name__ == "__main__":
    add_description_column()

"""
【実行手順】
1. 必要なら仮想環境を有効化してください。
2. プロジェクトルートで以下を実行してください:
   python scripts/add_description_column.py
3. 「description カラムを追加しました」または
   「description カラムは既に存在します」と表示されればOKです。
"""
