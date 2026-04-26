import os
import sys
import mysql.connector
from mysql.connector import Error as MySQLError


def init_db():
    """
    Initialise the database schema and seed data.
    All output goes to stderr so it appears in Railway deployment logs.
    Returns True on success, False on failure — never raises.
    """
    # ── Connection details (no password) ──────────────────────────────
    host     = os.getenv("MYSQLHOST")     or os.getenv("MYSQL_HOST")
    user     = os.getenv("MYSQLUSER")     or os.getenv("MYSQL_USER")
    database = os.getenv("MYSQLDATABASE") or os.getenv("MYSQL_DATABASE")
    port_raw = os.getenv("MYSQLPORT")     or os.getenv("MYSQL_PORT") or "3306"
    password = os.getenv("MYSQLPASSWORD") or os.getenv("MYSQL_PASSWORD")

    print("[init_db] Starting database initialisation…", file=sys.stderr)
    print(f"[init_db] Host:     {host}", file=sys.stderr)
    print(f"[init_db] Port:     {port_raw}", file=sys.stderr)
    print(f"[init_db] User:     {user}", file=sys.stderr)
    print(f"[init_db] Database: {database}", file=sys.stderr)
    print(f"[init_db] Password: {'<set>' if password else '<NOT SET>'}", file=sys.stderr)

    # ── Validate required env vars ─────────────────────────────────────
    missing = [name for name, val in [
        ("MYSQLHOST / MYSQL_HOST",         host),
        ("MYSQLUSER / MYSQL_USER",         user),
        ("MYSQLPASSWORD / MYSQL_PASSWORD", password),
        ("MYSQLDATABASE / MYSQL_DATABASE", database),
    ] if not val]

    if missing:
        print(f"[init_db] ERROR: Missing required environment variables: {missing}",
              file=sys.stderr)
        return False

    try:
        port = int(port_raw)
    except (TypeError, ValueError):
        print(f"[init_db] ERROR: Invalid port value: {port_raw!r}", file=sys.stderr)
        return False

    # ── Connect ────────────────────────────────────────────────────────
    print("[init_db] Connecting to MySQL…", file=sys.stderr)
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port,
            connection_timeout=10,
        )
    except MySQLError as exc:
        print(f"[init_db] ERROR: Could not connect to MySQL: {exc}", file=sys.stderr)
        return False

    print("[init_db] Connected successfully.", file=sys.stderr)

    # ── Run DDL statements ─────────────────────────────────────────────
    statements = [
        # users
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id          INT           PRIMARY KEY AUTO_INCREMENT,
            name             VARCHAR(100)  NOT NULL,
            email            VARCHAR(100)  NOT NULL UNIQUE,
            phone            VARCHAR(15)   NOT NULL,
            department       VARCHAR(100),
            class_year       VARCHAR(50),
            roll_no          VARCHAR(50),
            college_location TEXT,
            password         VARCHAR(255)  NOT NULL,
            created_at       DATETIME      DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # admin
        """
        CREATE TABLE IF NOT EXISTS admin (
            admin_id   INT          PRIMARY KEY AUTO_INCREMENT,
            username   VARCHAR(50)  NOT NULL UNIQUE,
            password   VARCHAR(255) NOT NULL
        )
        """,
        # ewaste_items
        """
        CREATE TABLE IF NOT EXISTS ewaste_items (
            waste_id        INT             PRIMARY KEY AUTO_INCREMENT,
            user_id         INT             NOT NULL,
            item_name       VARCHAR(100)    NOT NULL,
            category        VARCHAR(100)    NOT NULL,
            quantity        INT             NOT NULL DEFAULT 1,
            waste_condition VARCHAR(100),
            approx_weight   DECIMAL(8,2),
            description     TEXT,
            created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        """,
        # pickup_requests
        """
        CREATE TABLE IF NOT EXISTS pickup_requests (
            request_id       INT          PRIMARY KEY AUTO_INCREMENT,
            user_id          INT          NOT NULL,
            waste_id         INT          NOT NULL,
            pickup_location  TEXT         NOT NULL,
            pickup_date      DATE         NOT NULL,
            time_slot        VARCHAR(50),
            note             TEXT,
            status           VARCHAR(50)  NOT NULL DEFAULT 'Pending',
            collector_name   VARCHAR(100),
            collector_phone  VARCHAR(15),
            assigned_at      DATETIME     NULL,
            completed_at     DATETIME     NULL,
            cancelled_at     DATETIME     NULL,
            created_at       DATETIME     DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id)  REFERENCES users(user_id)  ON DELETE CASCADE,
            FOREIGN KEY (waste_id) REFERENCES ewaste_items(waste_id) ON DELETE CASCADE
        )
        """,
        # recycling_records
        """
        CREATE TABLE IF NOT EXISTS recycling_records (
            recycle_id        INT          PRIMARY KEY AUTO_INCREMENT,
            request_id        INT          NOT NULL,
            recycling_center  VARCHAR(150),
            sent_date         DATE,
            recycled_date     DATE,
            recycle_status    VARCHAR(100),
            remarks           TEXT,
            FOREIGN KEY (request_id) REFERENCES pickup_requests(request_id) ON DELETE CASCADE
        )
        """,
    ]

    # Seed: default admin account (password: admin123)
    seed_admin = """
        INSERT INTO admin (username, password)
        VALUES ('admin',
                'scrypt:32768:8:1$FBn0Wp70GTgjamWr$ac09a6b1e70ddc84c6d5b8fefc8125bdbcce398741d85ce39264ef7612a4803fce2bb64cbc87ecb9d7e5e7dbf6bc071110362c89ee6e69b28adc303a1b0b460f')
        ON DUPLICATE KEY UPDATE username = username
    """

    table_names = [
        "users", "admin", "ewaste_items", "pickup_requests", "recycling_records"
    ]

    try:
        cursor = conn.cursor()

        for name, stmt in zip(table_names, statements):
            print(f"[init_db] Creating table '{name}' if not exists…", file=sys.stderr)
            try:
                cursor.execute(stmt)
                print(f"[init_db] Table '{name}' OK.", file=sys.stderr)
            except MySQLError as exc:
                print(f"[init_db] ERROR creating table '{name}': {exc}", file=sys.stderr)
                conn.rollback()
                return False

        print("[init_db] Seeding default admin account…", file=sys.stderr)
        try:
            cursor.execute(seed_admin)
            conn.commit()
            print("[init_db] Seed OK.", file=sys.stderr)
        except MySQLError as exc:
            print(f"[init_db] ERROR seeding admin: {exc}", file=sys.stderr)
            conn.rollback()
            return False

        cursor.close()

    except MySQLError as exc:
        print(f"[init_db] ERROR during schema setup: {exc}", file=sys.stderr)
        return False
    finally:
        try:
            conn.close()
            print("[init_db] Connection closed.", file=sys.stderr)
        except Exception:
            pass

    print("[init_db] Database initialisation complete.", file=sys.stderr)
    return True


if __name__ == "__main__":
    success = init_db()
    sys.exit(0 if success else 1)
