import sqlite3
from pathlib import Path
from contextlib import contextmanager

class SQLManager:
    def __init__(self, db_path=None):
        self.base_dir = Path(__file__).resolve().parent
        self.db_path = Path(db_path) if db_path else self.base_dir / "instance" / "nexadb.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self):
        connection = sqlite3.connect(str(self.db_path), timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @contextmanager
    def transaction(self):
        connection = self.connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def execute(self, query, parameters=()):
        with self.transaction() as connection:
            cursor = connection.execute(query, parameters)
            return {
                "rows_affected": cursor.rowcount,
                "last_insert_id": cursor.lastrowid
            }

    def execute_many(self, query, parameters):
        with self.transaction() as connection:
            previous_changes = connection.total_changes
            connection.executemany(query, parameters)
            return connection.total_changes - previous_changes

    def fetch_all(self, query, parameters=()):
        connection = self.connect()
        try:
            rows = connection.execute(query, parameters).fetchall()
            return [dict(row) for row in rows]
        finally:
            connection.close()

    def fetch_one(self, query, parameters=()):
        connection = self.connect()
        try:
            row = connection.execute(query, parameters).fetchone()
            return dict(row) if row else None
        finally:
            connection.close()

    def init(self, schema_path=None):
        schema_file = Path(schema_path) if schema_path else self.base_dir / "database" / "nexadb.sql"
        if not schema_file.is_file():
            raise FileNotFoundError(f"Arquivo SQL não encontrado: {schema_file}")

        schema = schema_file.read_text(encoding="utf-8")
        connection = self.connect()
        try:
            connection.executescript(schema)
            # Migração não destrutiva para bancos criados antes do campo de resposta.
            fields = {row["name"] for row in connection.execute("PRAGMA table_info(desafios)")}
            if "resposta_correta" not in fields:
                connection.execute("ALTER TABLE desafios ADD COLUMN resposta_correta TEXT")
                connection.commit()
        finally:
            connection.close()

    def check_connection(self):
        try:
            result = self.fetch_one("SELECT 1 AS connected")
            return result is not None and result["connected"] == 1
        except sqlite3.Error:
            return False

    def get_tables(self):
        rows = self.fetch_all(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        )
        return [row["name"] for row in rows]