"""
init_db.py — Database initialisation for the E-Waste Management app.

Reads database.sql, creates the database if it doesn't exist, then
executes every DDL/DML statement found in the file.  Called once at
application startup from app.py.
"""

import os
import re
import sys

import mysql.connector
from mysql.connector import Error


def init_db() -> None:
    """Create the database (if absent) and apply the schema from database.sql."""

    host     = os.getenv("MYSQLHOST") or os.getenv("MYSQL_HOST", "localhost")
    user     = os.getenv("MYSQLUSER") or os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQLPASSWORD") or os.getenv("MYSQL_PASSWORD", "")
    port     = int(os.getenv("MYSQLPORT") or os.getenv("MYSQL_PORT") or 3306)
    database = os.getenv("MYSQLDATABASE") or os.getenv("MYSQL_DATABASE", "ewaste_college_db")

    # ── Locate database.sql relative to this file ──────────────────────
    sql_path = os.path.join(os.path.dirname(__file__), "database.sql")
    if not os.path.exists(sql_path):
        print(f"[init_db] WARNING: {sql_path} not found — skipping schema init.",
              file=sys.stderr)
        return

    with open(sql_path, "r", encoding="utf-8") as fh:
        raw_sql = fh.read()

    # ── Split into individual statements ───────────────────────────────
    # Strip comments, then split on semicolons.
    # Remove single-line (-- …) and multi-line (/* … */) comments.
    no_comments = re.sub(r"--[^\n]*", "", raw_sql)
    no_comments = re.sub(r"/\*.*?\*/", "", no_comments, flags=re.DOTALL)

    statements = [s.strip() for s in no_comments.split(";") if s.strip()]

    # ── Connect without specifying a database first ─────────────────────
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            port=port,
        )
    except Error as exc:
        print(f"[init_db] ERROR: Could not connect to MySQL — {exc}", file=sys.stderr)
        return

    cursor = conn.cursor()

    try:
        # Ensure the target database exists before switching to it.
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{database}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cursor.execute(f"USE `{database}`")

        for stmt in statements:
            # Skip bare SELECT statements (e.g. the stray "select * from …"
            # at the bottom of database.sql) — they serve no init purpose.
            if re.match(r"^\s*SELECT\b", stmt, re.IGNORECASE):
                continue
            # Skip USE statements — we already selected the database above.
            if re.match(r"^\s*USE\b", stmt, re.IGNORECASE):
                continue
            # Skip CREATE DATABASE — already handled above.
            if re.match(r"^\s*CREATE\s+DATABASE\b", stmt, re.IGNORECASE):
                continue

            try:
                cursor.execute(stmt)
                conn.commit()
            except Error as exc:
                # Non-fatal: log and continue so one bad statement doesn't
                # abort the whole initialisation.
                print(f"[init_db] WARNING: Statement skipped ({exc}):\n  {stmt[:120]}",
                      file=sys.stderr)

        print(f"[init_db] Schema initialised successfully (database: {database}).")

    except Error as exc:
        print(f"[init_db] ERROR during schema init — {exc}", file=sys.stderr)
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    init_db()
