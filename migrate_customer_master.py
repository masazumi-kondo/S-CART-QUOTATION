import os
import sqlite3
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "estimates.db")


def table_exists(conn, table: str) -> bool:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return cur.fetchone() is not None


def column_exists(conn, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def add_column_if_not_exists(conn, table: str, column: str, coldef: str) -> None:
    if not column_exists(conn, table, column):
        print(f"Adding column {column} to {table} ...")
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coldef}")
    else:
        print(f"Column {column} already exists in {table}")


def create_table_if_not_exists(conn, create_sql: str, table: str) -> None:
    if not table_exists(conn, table):
        print(f"Creating table {table} ...")
        conn.execute(create_sql)
    else:
        print(f"Table {table} already exists")


def main() -> None:
    try:
        print("[DIAG] Current working directory:", os.getcwd())
        print("[DIAG] __file__:", os.path.abspath(__file__))
        print("[DIAG] DB_PATH:", DB_PATH)
        print("[DIAG] DB file exists:", os.path.exists(DB_PATH))
        print("[DIAG] sqlite3 version:", sqlite3.sqlite_version)

        conn = sqlite3.connect(DB_PATH)
        try:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
            ).fetchall()
            print("[DIAG] Tables:", [t[0] for t in tables])

            # 1) transaction_types
            create_table_if_not_exists(
                conn,
                """
CREATE TABLE transaction_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    note TEXT,
    is_active BOOLEAN DEFAULT 1
)
""".strip(),
                "transaction_types",
            )

            # 2) payment_terms
            create_table_if_not_exists(
                conn,
                """
CREATE TABLE payment_terms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT 1
)
""".strip(),
                "payment_terms",
            )

            # 3) customers existence
            if not table_exists(conn, "customers"):
                raise RuntimeError("customers table not found")

            # 4) add columns (new)
            add_column_if_not_exists(conn, "customers", "customer_code", "VARCHAR(50)")
            add_column_if_not_exists(conn, "customers", "postal_code", "VARCHAR(20)")
            add_column_if_not_exists(conn, "customers", "transaction_type_id", "INTEGER")
            add_column_if_not_exists(conn, "customers", "payment_term_id", "INTEGER")


            # 5) legacy columns (compat)
            add_column_if_not_exists(conn, "customers", "transaction_type", "VARCHAR(50)")
            add_column_if_not_exists(conn, "customers", "payment_terms", "VARCHAR(100)")

            # 6) customer_approval_log table (minimal, no foreign keys)
            create_table_if_not_exists(
                conn,
                '''
CREATE TABLE IF NOT EXISTS customer_approval_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    approved_by INTEGER NOT NULL,
    approved_at DATETIME NOT NULL
)
'''.strip(),
                "customer_approval_log",
            )

            conn.commit()
            print("\nMigration completed.\n")
        finally:
            conn.close()

    except Exception:
        traceback.print_exc()


if __name__ == "__main__":
    main()
