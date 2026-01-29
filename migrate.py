"""Database migration script.

Creates the `users` table if it does not exist. Uses `SUPABASE_URL` from
environment to connect directly to Postgres. If you prefer not to provide
`SUPABASE_URL`, you can create the table from Supabase SQL editor manually.

Run:
  python migrate.py
"""
import os
import sys
import time

import psycopg2
from psycopg2 import sql


CREATE_USERS_SQL = """
CREATE TABLE IF NOT EXISTS users (
  id bigint PRIMARY KEY,
  username text
);
"""


CREATE_ATTENDANCES_SQL = """
CREATE TABLE IF NOT EXISTS attendances (
  id serial PRIMARY KEY,
  user_id bigint NOT NULL,
  ts timestamptz NOT NULL DEFAULT now()
);
"""
CREATE_ATT_IDX_SQL = """
CREATE INDEX IF NOT EXISTS idx_attendances_user_ts ON attendances (user_id, ts DESC);
"""


# Ensure users table has xp & level cols and index on xp for leaderboard
ALTER_USERS_SQL = """
ALTER TABLE users ADD COLUMN IF NOT EXISTS xp integer DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS level integer DEFAULT 1;
CREATE INDEX IF NOT EXISTS idx_users_xp ON users (xp DESC);
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_xp_at timestamptz;
"""


def main() -> int:
    # Prefer DATABASE_URL for local postgres, but allow SUPABASE_URL for backwards compatibility
    db_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_URL")
    if not db_url:
        print("DATABASE_URL or SUPABASE_URL not set. Set it in your .env or environment.")
        return 2

    # Wait for DB to be available (useful when Postgres takes a moment to start)
    start = time.time()
    timeout = 30
    while True:
        try:
            conn = psycopg2.connect(db_url)
            break
        except Exception as e:
            if time.time() - start > timeout:
                print(f"DB connection timed out after {timeout}s: {e}")
                return 1
            print("Waiting for DB to be available...", end="\r")
            time.sleep(1)

    try:
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(CREATE_USERS_SQL)
        cur.execute(CREATE_ATTENDANCES_SQL)
        cur.execute(CREATE_ATT_IDX_SQL)
        cur.execute(ALTER_USERS_SQL)
        print("마이그레이션 완료: users 및 attendances 테이블이 생성되었거나 이미 존재합니다.")
        cur.close()
        conn.close()
        return 0
    except Exception as e:
        print(f"마이그레이션 실패: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
