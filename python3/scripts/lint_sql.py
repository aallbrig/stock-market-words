"""
Syntax-check all .sql files in python3/sql/ against a live schema.

Creates an in-memory SQLite DB with the full schema, then runs EXPLAIN
on each non-empty statement. Uses json_each() stubs where needed so
parameterized queries validate correctly.

Exit code 0 = all clean, 1 = any error.
"""
import sqlite3
import sys
from pathlib import Path

SQL_DIR = Path(__file__).parent.parent / "sql"
SCHEMA_PATH = Path(__file__).parent.parent / "schema.sql"

JSON_ARRAY_STUB = "[1]"


def _split_statements(sql: str) -> list[str]:
    return [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]


def _stub_params(stmt: str) -> tuple:
    return tuple(JSON_ARRAY_STUB for _ in range(stmt.count("?")))


def check_file(conn: sqlite3.Connection, path: Path) -> list[str]:
    errors = []
    sql = path.read_text()
    for stmt in _split_statements(sql):
        try:
            conn.execute(f"EXPLAIN {stmt}", _stub_params(stmt))
        except sqlite3.Error as e:
            errors.append(f"  {stmt[:60]!r}... → {e}")
    return errors


def main() -> int:
    sql_files = sorted(SQL_DIR.glob("*.sql"))
    if not sql_files:
        print("No .sql files found in", SQL_DIR)
        return 0

    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    schema = SCHEMA_PATH.read_text()
    conn.executescript(schema)

    overall_ok = True
    for path in sql_files:
        errors = check_file(conn, path)
        if errors:
            print(f"✗ {path.name}")
            for e in errors:
                print(e)
            overall_ok = False
        else:
            print(f"✓ {path.name}")

    conn.close()
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
