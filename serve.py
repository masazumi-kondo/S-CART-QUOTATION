# serve.py - 社内共有サーバー用の本番起動（waitress）
# 必須環境変数: SECRET_KEY / 任意: SCART_DB_PATH, SCART_HOST(既定0.0.0.0), SCART_PORT(既定5000)
import os

os.environ.setdefault("FLASK_DEBUG", "0")

from waitress import serve

from app import create_app

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("SCART_HOST", "0.0.0.0")
    port = int(os.environ.get("SCART_PORT", "5000"))
    serve(app, host=host, port=port, threads=8)
