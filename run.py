# run.py
import threading
import time
import webbrowser

from app import create_app

app = create_app()


def open_browser():
    # 少しだけ待ってからトップページを開く
    time.sleep(0.8)
    webbrowser.open("http://127.0.0.1:5000/")


if __name__ == "__main__":
    # ブラウザ自動起動（EXE / 開発どちらでも動く）
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
