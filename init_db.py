# -*- coding: utf-8 -*-
"""初始化数据库（创建表结构）。首次运行 app.py 时会自动调用，也可单独运行。"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chenggu.db')

def init():
    db = sqlite3.connect(DB)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT DEFAULT '',
            birth_year INTEGER,
            birth_month INTEGER,
            birth_day INTEGER,
            birth_hour INTEGER,
            gender TEXT,
            standard_total REAL,
            palace_total REAL,
            song TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    db.commit()
    db.close()
    print(f"数据库已初始化：{DB}")

if __name__ == '__main__':
    init()
