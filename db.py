import pymysql
import pymysql.cursors
from flask import g, current_app


def get_db():
    """Return a request-scoped MySQL connection with dict cursors."""
    if "db" not in g:
        g.db = pymysql.connect(
            host=current_app.config["MYSQL_HOST"],
            port=current_app.config["MYSQL_PORT"],
            user=current_app.config["MYSQL_USER"],
            password=current_app.config["MYSQL_PASSWORD"],
            database=current_app.config["MYSQL_DB"],
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
        )
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql, params=None, fetchone=False):
    """SELECT helper."""
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchone() if fetchone else cur.fetchall()


def execute(sql, params=None):
    """INSERT/UPDATE/DELETE helper. Returns lastrowid and commits."""
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        conn.commit()
        return cur.lastrowid


def init_app(app):
    app.teardown_appcontext(close_db)
