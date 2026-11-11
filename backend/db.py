import pymysql
import pymysql.cursors
from flask import g
from backend.config import Config

def get_db():
    """
    Returns a per-request database connection, stored in Flask application context `g`.
    """
    if "db" not in g:
        g.db = pymysql.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASS,
            database=Config.DB_NAME,
            charset="utf8mb4",
            autocommit=False,
            cursorclass=pymysql.cursors.DictCursor
        )
    return g.db

def close_db(e=None):
    """
    Closes the database connection at the end of the request.
    """
    db = g.pop("db", None)
    if db is not None:
        try:
            db.close()
        except Exception:
            pass

def query_all(sql, params=None):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()

def query_one(sql, params=None):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchone()

def execute_write(sql, params=None):
    conn = get_db()
    with conn.cursor() as cur:
        affected = cur.execute(sql, params or ())
        last_id = cur.lastrowid
        conn.commit()
        return {"affected_rows": affected, "last_id": last_id}

def call_proc(proc_name, params=None):
    """
    Calls a stored procedure and commits changes.
    """
    conn = get_db()
    with conn.cursor() as cur:
        cur.callproc(proc_name, params or ())
        conn.commit()
