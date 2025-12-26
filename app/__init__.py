import os
import sys
import logging
import sqlite3
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from .config import Config
from werkzeug.security import generate_password_hash

db = SQLAlchemy()

def resource_path(relative_path: str) -> str:
    """
    リソース（templates/static）用ベースパス
    - EXE: sys._MEIPASS 配下の templates, static
    - 開発: app ディレクトリ配下の templates, static
    """
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)

def create_app():
    from flask import g, session, render_template
    from app.models.user import User
    from flask.signals import template_rendered

    def load_current_user():
        user_id = session.get("user_id")
        if not user_id:
            g.current_user = None
            return

        user = db.session.get(User, user_id)  # SQLAlchemy 2系互換
        if not user or not getattr(user, "is_active", True):
            session.clear()
            g.current_user = None
        else:
            g.current_user = user

    def inject_current_user():
        return {"current_user": g.get("current_user")}

    def ensure_table_exists_users(conn):
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        exists = cur.fetchone() is not None

        def _create_users_table():
            conn.execute('''CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                login_id TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )''')
            conn.commit()

        if not exists:
            _create_users_table()

        cur = conn.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cur.fetchall()]
        required = ["login_id", "display_name", "password_hash"]
        missing = [c for c in required if c not in columns]
        if not missing:
            return

        logging.warning("[MIG] users table schema mismatch detected. columns=%s", columns)
        backup = "users_legacy"
        i = 1
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (backup,))
        while cur.fetchone():
            i += 1
            backup = f"users_legacy_{i}"
            cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (backup,))

        logging.warning("[MIG] renaming users -> %s", backup)
        conn.execute(f"ALTER TABLE users RENAME TO {backup}")
        conn.commit()

        _create_users_table()

        try:
            conn.execute(f"""
                INSERT INTO users (login_id, display_name, password_hash, role, is_active, created_at)
                SELECT
                    COALESCE(CAST(user_id AS TEXT), name, 'legacy') AS login_id,
                    COALESCE(name, CAST(user_id AS TEXT), 'legacy') AS display_name,
                    password_hash,
                    COALESCE(role, 'user') AS role,
                    COALESCE(is_active, 1) AS is_active,
                    COALESCE(created_at, CURRENT_TIMESTAMP) AS created_at
                FROM {backup}
            """)
            conn.commit()
        except Exception as e:
            logging.exception("[MIG] users data copy failed: %s", e)
            raise RuntimeError(f"usersテーブル移行に失敗: {e}")

        cur = conn.execute("PRAGMA table_info(users)")
        columns2 = [row[1] for row in cur.fetchall()]
        missing2 = [c for c in required if c not in columns2]
        if missing2:
            raise RuntimeError(f"usersテーブルの移行後も必須列がありません: {missing2}")

        logging.warning("[MIG] users table migrated successfully. legacy table kept as %s", backup)

    def ensure_table_exists_quotations(conn):
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='quotations'")
        if cur.fetchone():
            logging.info("[MIG] quotations already exists")
            return
        logging.info("[MIG] creating quotations table (model準拠)...")
        conn.execute('''CREATE TABLE quotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            contact_name TEXT,
            project_name TEXT NOT NULL,
            delivery_date TEXT,
            delivery_terms TEXT,
            payment_terms TEXT,
            valid_until TEXT,
            remarks TEXT,
            estimator_name TEXT,
            discount_rate REAL DEFAULT 0,
            original_id INTEGER,
            revision_no INTEGER DEFAULT 0,
            customer_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.commit()
        logging.info("[MIG] quotations table created (model準拠)")

    def seed_admin_user(conn):
        cur = conn.execute("SELECT id FROM users WHERE login_id = ?", ("admin",))
        if not cur.fetchone():
            password_hash = generate_password_hash("admin1234")
            conn.execute("INSERT INTO users (login_id, display_name, password_hash, role, is_active) VALUES (?, ?, ?, ?, ?)",
                         ("admin", "管理者", password_hash, "admin", 1))
            conn.commit()

    # DB path
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    env_db = os.environ.get("SCART_DB_PATH")
    db_path = env_db if env_db else os.path.join(base_dir, "estimates.db")

    # templates/static
    template_dir = resource_path("templates")
    static_dir = resource_path("static")

    # logging
    debug_mode = os.environ.get("FLASK_DEBUG", "1") == "1"
    logging.basicConfig(
        level=logging.DEBUG if debug_mode else logging.INFO,
        format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    )

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.logger.setLevel(logging.INFO)
    app.logger.info("[DB] Using database path: %s", db_path)

    # ...existing code...
    logging.info("[TEMPLATE] template_folder=%s", app.template_folder)
    logging.info("[TEMPLATE] jinja searchpath=%s", getattr(app.jinja_loader, "searchpath", None))

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template("500.html"), 500

    app.before_request(load_current_user)
    app.context_processor(inject_current_user)

    app.config.from_object(Config)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev_secret_key")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if debug_mode:
        app.config["TEMPLATES_AUTO_RELOAD"] = True
        app.jinja_env.auto_reload = True
        app.jinja_env.cache = {}
        app.config["PROPAGATE_EXCEPTIONS"] = True
    else:
        app.config["TEMPLATES_AUTO_RELOAD"] = False

    db.init_app(app)

    # --- migration helpers (move above usage) ---
    def ensure_table_exists(conn, table_name):
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        return cur.fetchone() is not None

    def safe_set_pragma(conn, sql):
        try:
            conn.execute(sql)
            conn.commit()
        except Exception as e:
            logging.warning("PRAGMA failed: %s (%s)", sql, e)

    def get_user_version(conn):
        return conn.execute("PRAGMA user_version").fetchone()[0]

    def set_user_version(conn, version):
        conn.execute(f"PRAGMA user_version = {version}")
        conn.commit()

    def ensure_column_exists(conn, table, column, coldef):
        if not ensure_table_exists(conn, table):
            logging.error(f"[MIG] Table '{table}' does not exist; cannot add column '{column}'")
            return
        cur = conn.execute(f"PRAGMA table_info({table})")
        cols = [row[1] for row in cur.fetchall()]
        if column not in cols:
            try:
                logging.info(f"[MIG] Adding column '{column}' to '{table}' ({coldef})")
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coldef}")
                conn.commit()
                logging.info(f"[MIG] Added column '{column}' to '{table}'")
            except Exception as e:
                logging.exception(f"[MIG] Failed to add column '{column}' to '{table}': {e}")
                raise
        else:
            logging.info(f"[MIG] Column '{column}' already exists in '{table}'")

    def ensure_table_exists_customers(conn):
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customers'")
        if not cur.fetchone():
            conn.execute('''CREATE TABLE customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_code TEXT,
    name TEXT NOT NULL UNIQUE,
    name_kana TEXT,
    postal_code TEXT,
    address TEXT,
    contact_name TEXT,
    phone TEXT,
    email TEXT,
    transaction_type TEXT,
    payment_terms TEXT,
    transaction_type_id INTEGER,
    payment_term_id INTEGER,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
)''')
            conn.commit()

    def ensure_table_exists_quotation_details(conn):
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='quotation_details'")
        if cur.fetchone():
            logging.info("[MIG] quotation_details already exists")
            return
        logging.info("[MIG] creating quotation_details table...")
        conn.execute('''CREATE TABLE quotation_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quotation_id INTEGER NOT NULL,
            item_name TEXT,
            quantity REAL DEFAULT 0,
            unit_price REAL DEFAULT 0,
            subtotal REAL DEFAULT 0,
            label TEXT,
            profit_rate REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.commit()
        logging.info("[MIG] quotation_details table created")

    def apply_migrations(conn):
        logging.info("[MIG] start apply_migrations")
        try:
            uv = conn.execute("PRAGMA user_version").fetchone()[0]
        except Exception:
            uv = "N/A"
        try:
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        except Exception:
            tables = "N/A"
        logging.info("[MIG] precheck user_version=%s tables=%s", uv, tables)

        logging.info("[MIG] ensure auth_login_log")
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='auth_login_log'")
        if not cur.fetchone():
            conn.execute('''CREATE TABLE auth_login_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login_id TEXT,
    user_id INTEGER,
    result TEXT,
    ip TEXT,
    user_agent TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)''')
            conn.commit()


        logging.info("[MIG] ensure customer_approval_log (minimal approval log schema)")

        def _table_exists(name: str) -> bool:
            cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
            return cur.fetchone() is not None

        def _columns(name: str) -> set[str]:
            cur = conn.execute(f"PRAGMA table_info({name})")
            return {r[1] for r in cur.fetchall()}

        # 目標：最小承認ログ型
        required_cols = {"id", "customer_id", "user_id", "approved_by", "approved_at"}

        # 監査ログ型にありがちな列（現DBに合わせて広めに拾う）
        audit_like_cols = {
            "action", "from_status", "to_status",
            "actor_user_id", "acted_by_user_id",
            "acted_at", "created_at",
            "comment",
        }

        if not _table_exists("customer_approval_log"):
            conn.execute("""
                CREATE TABLE customer_approval_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    approved_by INTEGER NOT NULL,
                    approved_at DATETIME NOT NULL
                )
            """)
            conn.commit()
        else:
            cols = _columns("customer_approval_log")

            is_minimal_ok = required_cols.issubset(cols)
            looks_audit = len(cols.intersection(audit_like_cols)) > 0

            # 最小型じゃない、または監査ログっぽい列があるなら退避→作り直し
            if (not is_minimal_ok) or looks_audit:
                legacy = f"customer_approval_log_legacy_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                logging.warning("[MIG] customer_approval_log schema mismatch. rename to %s and recreate", legacy)
                conn.execute(f"ALTER TABLE customer_approval_log RENAME TO {legacy}")
                conn.commit()

                conn.execute("""
                    CREATE TABLE customer_approval_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        customer_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        approved_by INTEGER NOT NULL,
                        approved_at DATETIME NOT NULL
                    )
                """)
                conn.commit()
                logging.warning("[MIG] legacy approval log kept as %s (no data migration)", legacy)

        try:
            logging.info("[MIG] ensure customers/users/admin")
            ensure_table_exists_customers(conn)
            ensure_table_exists_users(conn)
            seed_admin_user(conn)
            ensure_table_exists_quotations(conn)
            q = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='quotations'").fetchone()
            logging.info("[MIG] quotations exists after ensure? %s", bool(q))
            ensure_table_exists_quotation_details(conn)
            qd = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='quotation_details'").fetchone()
            logging.info("[MIG] quotation_details exists after ensure? %s", bool(qd))
            try:
                logging.info("[MIG] ensure idx_quotation_details_quotation_id")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_quotation_details_quotation_id ON quotation_details(quotation_id)")
                conn.commit()
            except Exception as e:
                logging.exception("[MIG] Failed to create idx_quotation_details_quotation_id: %s", e)
                raise
            logging.info("[MIG] ensure customers master columns (model準拠)")
            ensure_column_exists(conn, "customers", "customer_code", "TEXT")
            ensure_column_exists(conn, "customers", "name", "TEXT NOT NULL UNIQUE")
            ensure_column_exists(conn, "customers", "name_kana", "TEXT")
            ensure_column_exists(conn, "customers", "postal_code", "TEXT")
            ensure_column_exists(conn, "customers", "address", "TEXT")
            ensure_column_exists(conn, "customers", "contact_name", "TEXT")
            ensure_column_exists(conn, "customers", "phone", "TEXT")
            ensure_column_exists(conn, "customers", "email", "TEXT")
            ensure_column_exists(conn, "customers", "transaction_type", "TEXT")
            ensure_column_exists(conn, "customers", "payment_terms", "TEXT")
            ensure_column_exists(conn, "customers", "transaction_type_id", "INTEGER")
            ensure_column_exists(conn, "customers", "payment_term_id", "INTEGER")
            ensure_column_exists(conn, "customers", "note", "TEXT")
            ensure_column_exists(conn, "customers", "created_at", "DATETIME")
            ensure_column_exists(conn, "customers", "updated_at", "DATETIME")
            logging.info("[MIG] ensure customers approval columns")
            ensure_column_exists(conn, "customers", "status", "TEXT NOT NULL DEFAULT 'approved'")
            ensure_column_exists(conn, "customers", "requested_by_user_id", "INTEGER")
            ensure_column_exists(conn, "customers", "approved_by_user_id", "INTEGER")
            ensure_column_exists(conn, "customers", "approved_at", "DATETIME")
            ensure_column_exists(conn, "customers", "rejected_at", "DATETIME")
            ensure_column_exists(conn, "customers", "approval_comment", "TEXT")
            logging.info("[MIG] ensure customer_credit")
            cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customer_credit'")
            if not cur.fetchone():
                conn.execute('''CREATE TABLE customer_credit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    fiscal_year INTEGER NOT NULL,
    sales_amount REAL,
    net_income REAL,
    equity REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(customer_id, fiscal_year)
)''')
                conn.commit()
            logging.info("[MIG] quotations migration start")
            ensure_column_exists(conn, "quotations", "customer_id", "INTEGER")
            ensure_column_exists(conn, "quotations", "original_id", "INTEGER")
            ensure_column_exists(conn, "quotations", "revision_no", "INTEGER DEFAULT 0")
            ensure_column_exists(conn, "quotations", "contact_name", "TEXT")
            ensure_column_exists(conn, "quotations", "estimator_name", "TEXT")
            cur = conn.execute("PRAGMA table_info(quotations)")
            columns = [row[1] for row in cur.fetchall()]
            if "contact_person" in columns and "contact_name" in columns:
                conn.execute("UPDATE quotations SET contact_name = contact_person WHERE contact_name IS NULL AND contact_person IS NOT NULL")
                conn.commit()
                logging.info("[MIG] migrated contact_person → contact_name")
            conn.execute("UPDATE quotations SET original_id = id WHERE original_id IS NULL")
            conn.execute("UPDATE quotations SET revision_no = 0 WHERE revision_no IS NULL")
            conn.commit()
            ensure_column_exists(conn, "quotation_details", "profit_rate", "REAL")
            if get_user_version(conn) < 1:
                set_user_version(conn, 1)
            logging.info("[MIG] done user_version=%s", get_user_version(conn))
        except Exception as e:
            logging.exception("DB migration failed: %s", e)
            raise RuntimeError(f"DB migration failed: {e}")

    # --- end migration helpers ---

    # Apply migrations
    if not os.path.exists(db_path):
        with app.app_context():
            from app.models.quotation import Quotation
            from app.models.quotation_detail import QuotationDetail
            from app.models.product import Product
            from app.models.logic_config import LogicConfig
            from app.models.customer import Customer
            db.create_all()
        conn = sqlite3.connect(db_path, timeout=30)
        safe_set_pragma(conn, "PRAGMA foreign_keys=ON")
        safe_set_pragma(conn, "PRAGMA journal_mode=WAL")
        try:
            apply_migrations(conn)
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(db_path, timeout=30)
        safe_set_pragma(conn, "PRAGMA foreign_keys=ON")
        safe_set_pragma(conn, "PRAGMA journal_mode=WAL")
        try:
            apply_migrations(conn)
        finally:
            conn.close()

    # Blueprints
    from app.routes.main import main_bp
    from app.routes.quotation import quotation_bp
    from app.routes.product import product_bp
    from app.routes.customer import customer_bp
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(quotation_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_view_functions():
        return {"view_functions": app.view_functions}

    def log_routes():
        logging.info("[Flask routes] URL map:")
        for rule in app.url_map.iter_rules():
            logging.info("%s %s -> %s", ",".join(rule.methods), rule.rule, rule.endpoint)

    with app.app_context():
        log_routes()


    @template_rendered.connect_via(app)
    def when_template_rendered(sender, template, context, **extra):
        sender.logger.info(
            "[TEMPLATE-RENDERED] name=%s file=%s context_keys=%s",
            template.name,
            getattr(template, "filename", "N/A"),
            list(context.keys())[:10],
        )


    # CI用ヘルスチェックルート（認証・DB依存なし）
    @app.route("/health")
    def health():
        return "OK", 200

    # ★ create_appの末尾は必ずこれで終わる
    current_app_logger = app.logger
    current_app_logger.info("[BOOT] create_app completed")
    return app

