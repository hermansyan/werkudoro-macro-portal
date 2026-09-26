import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger("macro.database")

PG_HOST = os.environ.get("TRADING_DB_HOST", "192.168.68.136")
PG_USER = os.environ.get("TRADING_DB_USER", "trading_bot")
PG_PASSWORD = os.environ.get("TRADING_DB_PASSWORD", "021d48f30fe04dfee0d9de16529bf269")
PG_PORT = int(os.environ.get("TRADING_DB_PORT", 5432))
PG_DBNAME = os.environ.get("TRADING_DB_NAME", "trading_db")

_pg_pool = None

def get_pool():
    global _pg_pool
    if _pg_pool is None:
        try:
            _pg_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=20,
                host=PG_HOST,
                user=PG_USER,
                password=PG_PASSWORD,
                port=PG_PORT,
                dbname=PG_DBNAME
            )
            logger.info("Connected to PostgreSQL LXC 106 pool successfully.")
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL connection pool: {e}")
            raise
    return _pg_pool

class DBContext:
    def __init__(self, commit=False):
        self.commit = commit
        self.pool = get_pool()
        self.conn = None
        self.cur = None

    def __enter__(self):
        self.conn = self.pool.getconn()
        self.cur = self.conn.cursor(cursor_factory=RealDictCursor)
        return self.cur

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            try:
                if exc_type is not None:
                    self.conn.rollback()
                elif self.commit:
                    self.conn.commit()
            finally:
                if self.cur:
                    self.cur.close()
                self.pool.putconn(self.conn)

def get_connection():
    """Return a raw connection that must be closed manually."""
    return get_pool().getconn()

def release_connection(conn):
    if _pg_pool and conn:
        _pg_pool.putconn(conn)

def init_db():
    with DBContext(commit=True) as cur:
        # Schema
        cur.execute("CREATE SCHEMA IF NOT EXISTS macro;")
        
        # 1. Indicators table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS macro.indicators (
            key TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            region TEXT NOT NULL,
            value DOUBLE PRECISION NOT NULL,
            prev_value DOUBLE PRECISION,
            unit TEXT NOT NULL,
            change_pct DOUBLE PRECISION,
            trend TEXT,
            last_updated TEXT NOT NULL,
            source TEXT,
            description TEXT
        );
        """)

        # 2. News table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS macro.news (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            link TEXT UNIQUE NOT NULL,
            summary TEXT,
            source TEXT NOT NULL,
            category TEXT NOT NULL,
            region TEXT NOT NULL,
            published_at TEXT NOT NULL,
            sentiment TEXT,
            tags TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_macro_news_pub ON macro.news(published_at DESC);
        CREATE INDEX IF NOT EXISTS idx_macro_news_reg ON macro.news(region);
        """)

        # 3. Economic Calendar table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS macro.economic_calendar (
            id SERIAL PRIMARY KEY,
            event_name TEXT NOT NULL,
            region TEXT NOT NULL,
            impact TEXT NOT NULL,
            event_date TEXT NOT NULL,
            time_wib TEXT,
            forecast TEXT,
            previous TEXT,
            actual TEXT,
            notes TEXT
        );
        """)

        # 4. Macro Briefing table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS macro.macro_briefing (
            id INT PRIMARY KEY,
            headline TEXT NOT NULL,
            summary_indo TEXT NOT NULL,
            summary_global TEXT NOT NULL,
            key_risks TEXT NOT NULL,
            market_sentiment TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)

        # 5. Users table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS macro.users (
            username TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at DOUBLE PRECISION NOT NULL
        );
        """)

        # 6. Sessions table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS macro.sessions (
            token TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            created_at DOUBLE PRECISION NOT NULL,
            expires_at DOUBLE PRECISION NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_macro_sessions_tok ON macro.sessions(token);
        """)
    logger.info("PostgreSQL database tables initialized in schema 'macro'.")

if __name__ == "__main__":
    init_db()
    print("PostgreSQL Database initialized successfully on LXC 106!")
