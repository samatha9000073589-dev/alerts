import os
import sqlite3

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
DB_NAME = f"{DATA_DIR}/trading_alerts_20260810.db"
DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = bool(DATABASE_URL)

# SQL placeholder: %s for PostgreSQL, ? for SQLite
PH = "%s" if USE_POSTGRES else "?"

if USE_POSTGRES:
    import psycopg2


def get_connection():
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL)
    os.makedirs(DATA_DIR, exist_ok=True)
    return sqlite3.connect(DB_NAME)


# ==========================
# CREATE DATABASE
# ==========================

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    if USE_POSTGRES:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                symbol TEXT,
                target_price REAL,
                direction TEXT DEFAULT 'ABOVE',
                status TEXT DEFAULT 'ACTIVE'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_favorites (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                symbol TEXT,
                UNIQUE(user_id, symbol)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id BIGINT PRIMARY KEY,
                pushover_user_key TEXT,
                pushover_enabled INTEGER DEFAULT 0
            )
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                symbol TEXT,
                target_price REAL,
                direction TEXT DEFAULT 'ABOVE',
                status TEXT DEFAULT 'ACTIVE'
            )
        """)

        cursor.execute("PRAGMA table_info(alerts)")
        columns = [row[1] for row in cursor.fetchall()]
        if "direction" not in columns:
            cursor.execute("ALTER TABLE alerts ADD COLUMN direction TEXT DEFAULT 'ABOVE'")
        if "status" not in columns:
            cursor.execute("ALTER TABLE alerts ADD COLUMN status TEXT DEFAULT 'ACTIVE'")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                symbol TEXT,
                UNIQUE(user_id, symbol)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                pushover_user_key TEXT,
                pushover_enabled INTEGER DEFAULT 0
            )
        """)

    conn.commit()
    conn.close()


def init_users():
    # kept for backward compatibility — init_db() now creates the users table
    conn = get_connection()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id BIGINT PRIMARY KEY,
                pushover_user_key TEXT,
                pushover_enabled INTEGER DEFAULT 0
            )
        """)
    else:
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                pushover_user_key TEXT,
                pushover_enabled INTEGER DEFAULT 0
            )
        """)
    conn.commit()
    conn.close()


# ==========================
# ADD ALERT
# ==========================

def add_alert(user_id, symbol, price, direction):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"INSERT INTO alerts (user_id, symbol, target_price, direction) VALUES ({PH}, {PH}, {PH}, {PH})",
        (user_id, symbol, price, direction),
    )
    conn.commit()
    conn.close()


# ==========================
# GET USER ACTIVE ALERTS
# ==========================

def get_user_alerts(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT * FROM alerts WHERE user_id = {PH} AND status = 'ACTIVE' ORDER BY id DESC",
        (user_id,),
    )
    alerts = cursor.fetchall()
    conn.close()
    return alerts


# ==========================
# GET ALL ACTIVE ALERTS
# ==========================

def get_active_alerts():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alerts WHERE status = 'ACTIVE'")
    alerts = cursor.fetchall()
    conn.close()
    return alerts


# ==========================
# REMOVE SINGLE ALERT
# ==========================

def remove_alert(alert_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE alerts SET status = 'DONE' WHERE id = {PH}",
        (alert_id,),
    )
    conn.commit()
    conn.close()


# ==========================
# REMOVE MULTIPLE ALERTS
# ==========================

def remove_multiple_alerts(alert_ids):
    conn = get_connection()
    cursor = conn.cursor()
    for alert_id in alert_ids:
        cursor.execute(
            f"UPDATE alerts SET status = 'DONE' WHERE id = {PH}",
            (alert_id,),
        )
    conn.commit()
    conn.close()


# ==========================
# DISABLE ALERT AFTER HIT
# ==========================

def disable_alert(alert_id):
    remove_alert(alert_id)


# ==========================
# PUSHOVER SETTINGS
# ==========================

def save_pushover_key(telegram_id, user_key):
    conn = get_connection()
    cursor = conn.cursor()
    if USE_POSTGRES:
        cursor.execute(
            f"""
            INSERT INTO users (telegram_id, pushover_user_key, pushover_enabled)
            VALUES ({PH}, {PH}, 1)
            ON CONFLICT (telegram_id) DO UPDATE SET
                pushover_user_key = EXCLUDED.pushover_user_key,
                pushover_enabled = 1
            """,
            (telegram_id, user_key),
        )
    else:
        cursor.execute(
            f"INSERT OR REPLACE INTO users (telegram_id, pushover_user_key, pushover_enabled) VALUES ({PH}, {PH}, 1)",
            (telegram_id, user_key),
        )
    conn.commit()
    conn.close()


def get_pushover_key(telegram_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT pushover_user_key FROM users WHERE telegram_id = {PH} AND pushover_enabled = 1",
        (telegram_id,),
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


# ==========================
# CHECK PUSHOVER STATUS
# ==========================

def get_pushover_status(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT pushover_enabled FROM users WHERE telegram_id = {PH}",
        (user_id,),
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0


# ==========================
# DISABLE PUSHOVER
# ==========================

def disable_pushover(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE users SET pushover_enabled = 0 WHERE telegram_id = {PH}",
        (user_id,),
    )
    conn.commit()
    conn.close()


# ==========================
# ENABLE PUSHOVER
# ==========================

def enable_pushover(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE users SET pushover_enabled = 1 WHERE telegram_id = {PH}",
        (user_id,),
    )
    conn.commit()
    conn.close()


# ==========================
# GET PUSHOVER SETTINGS
# ==========================

def get_pushover_settings(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT pushover_enabled, pushover_user_key FROM users WHERE telegram_id = {PH}",
        (user_id,),
    )
    result = cursor.fetchone()
    conn.close()
    return (result[0], result[1]) if result else (0, None)


# ==========================
# FAVORITES
# ==========================

def add_favorite(user_id, symbol):
    conn = get_connection()
    cursor = conn.cursor()
    if USE_POSTGRES:
        cursor.execute(
            f"INSERT INTO user_favorites (user_id, symbol) VALUES ({PH}, {PH}) ON CONFLICT (user_id, symbol) DO NOTHING",
            (user_id, symbol.upper()),
        )
    else:
        cursor.execute(
            f"INSERT OR IGNORE INTO user_favorites (user_id, symbol) VALUES ({PH}, {PH})",
            (user_id, symbol.upper()),
        )
    conn.commit()
    conn.close()


def remove_favorite(user_id, symbol):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"DELETE FROM user_favorites WHERE user_id = {PH} AND symbol = {PH}",
        (user_id, symbol.upper()),
    )
    conn.commit()
    conn.close()


def get_user_favorites(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT symbol FROM user_favorites WHERE user_id = {PH} ORDER BY id ASC",
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


def is_favorite(user_id, symbol):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT 1 FROM user_favorites WHERE user_id = {PH} AND symbol = {PH}",
        (user_id, symbol.upper()),
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None
