#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Initialize database
python3 << EOF
import sqlite3
import os
from datetime import datetime

DATABASE = '/opt/render/project/src/bjj_coaching.db'

print(f"Initializing database at {DATABASE}")

conn = sqlite3.connect(DATABASE)
conn.row_factory = sqlite3.Row

# Create all tables
conn.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        is_approved INTEGER DEFAULT 0,
        is_admin INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    )
''')

conn.execute('''
    CREATE TABLE IF NOT EXISTS gyms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        location TEXT,
        created_at TEXT NOT NULL
    )
''')

conn.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        belt TEXT NOT NULL,
        since_date TEXT NOT NULL,
        stripes INTEGER DEFAULT 0,
        competition_date TEXT,
        competition_prep_active INTEGER DEFAULT 0,
        current_weight REAL,
        gym_id INTEGER,
        FOREIGN KEY (gym_id) REFERENCES gyms (id)
    )
''')

conn.execute('''
    CREATE TABLE IF NOT EXISTS curriculum (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        gym_id INTEGER NOT NULL,
        technique_name TEXT NOT NULL,
        category TEXT,
        belt_level TEXT,
        description TEXT,
        date_from TEXT,
        date_to TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (gym_id) REFERENCES gyms (id)
    )
''')

conn.execute('''
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        gym_id INTEGER,
        date TEXT NOT NULL,
        techniques TEXT,
        note_goed TEXT,
        note_focus TEXT,
        note_algemeen TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (student_id) REFERENCES students (id),
        FOREIGN KEY (gym_id) REFERENCES gyms (id)
    )
''')

conn.execute('''
    CREATE TABLE IF NOT EXISTS technique_suggestions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        technique TEXT UNIQUE NOT NULL
    )
''')

conn.execute('''
    CREATE TABLE IF NOT EXISTS technique_mastery (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        technique TEXT NOT NULL,
        level TEXT DEFAULT 'introduced',
        mastery_percentage INTEGER DEFAULT 0,
        last_updated TEXT NOT NULL,
        FOREIGN KEY (student_id) REFERENCES students (id),
        UNIQUE(student_id, technique)
    )
''')

conn.execute('''
    CREATE TABLE IF NOT EXISTS sparring_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        opponent_name TEXT NOT NULL,
        date TEXT NOT NULL,
        outcome TEXT,
        notes TEXT,
        what_worked TEXT,
        what_didnt TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (student_id) REFERENCES students (id)
    )
''')

conn.execute('''
    CREATE TABLE IF NOT EXISTS injuries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        injury_type TEXT NOT NULL,
        affected_area TEXT NOT NULL,
        restricted_techniques TEXT,
        start_date TEXT NOT NULL,
        end_date TEXT,
        notes TEXT,
        active INTEGER DEFAULT 1,
        FOREIGN KEY (student_id) REFERENCES students (id)
    )
''')

conn.execute('''
    CREATE TABLE IF NOT EXISTS belt_promotions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        from_belt TEXT NOT NULL,
        to_belt TEXT NOT NULL,
        promotion_date TEXT NOT NULL,
        notes TEXT,
        FOREIGN KEY (student_id) REFERENCES students (id)
    )
''')

conn.commit()
conn.close()

print("Database initialized successfully!")
EOF
