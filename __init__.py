# app/__init__.py
import os
import sys
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from .config import Config  # 相対インポートに統一

db = SQLAlchemy()


def resource_path(relative_path: str) -> str:
    """
    リソース（templates/static）用のベースパスを返す
    - PyInstaller 実行時: sys._MEIPASS
    - 通常実行時: app/__init__.py のあるディレクトリ
    """
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)


def create_app() -> Flask:
    """Flask アプリ本体を生成するファクトリ"""

    # --- DB 用ベースディレクトリ（EXE の場所 or プロジェクトルート） ---
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    db_path = os.path.join(base_dir, "estimates.db")

    # --- テンプレート / static フォルダ ---
    template_dir = resource_path("templates")
    static_dir = resource_path("static")

    app = Flask(
        __name__,
        template_folder=template_dir,
        static_folder=static_dir,
    )

    # --- ログ設定 ---
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    )
    app.logger.info("=== Flask app started ===")
    app.logger.info("app.static_folder = %s", app.static_folder)

    # --- 設定 ---
    app.config.from_object(Config)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # テンプレート自動リロード OFF（EXE 起動高速化）
    app.config["TEMPLATES_AUTO_RELOAD"] = False
    app.jinja_env.auto_reload = False

    # --- DB 初期化 ---
    db.init_app(app)

    # 初回だけテーブル作成
    if not os.path.exists(db_path):
        with app.app_context():
            from app.models.quotation import Quotation
            from app.models.quotation_detail import QuotationDetail
            from app.models.product import Product
            from app.models.logic_config import LogicConfig

            db.create_all()
            app.logger.info("DB created at %s", db_path)

    # --- customer_approval_log テーブルの作成 ---
    with app.app_context():
        conn = db.engine.connect()
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customer_approval_log'")
        if not cur.fetchone():
            conn.execute('''CREATE TABLE customer_approval_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                approved_by INTEGER NOT NULL,
                approved_at DATETIME NOT NULL
            )''')
            conn.commit()

    # --- Blueprint 登録（ここで import して循環参照を回避） ---
    from app.routes.main import main_bp
    from app.routes.quotation import quotation_bp
    from app.routes.product import product_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(quotation_bp)
    app.register_blueprint(product_bp)

    return app
