import mysql.connector
from mysql.connector import pooling
from config import Config

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="tazaura_pool",
            pool_size=5,
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            autocommit=False,
        )
    return _pool


def get_db():
    """Return a pooled connection. Remember to call conn.close() after use."""
    return _get_pool().get_connection()


def query(sql: str, params: tuple = (), *, fetchone: bool = False,
          commit: bool = False):
    """
    Convenience helper for read / write queries.
    Returns:
        fetchone=True  → single dict or None
        fetchone=False → list of dicts
        commit=True    → lastrowid (int)
    """
    conn = get_db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params)
        if commit:
            conn.commit()
            return cursor.lastrowid
        if fetchone:
            return cursor.fetchone()
        return cursor.fetchall()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
