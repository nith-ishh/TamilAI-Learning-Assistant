"""
TamilAI - Database initialization
Creates all tables on first run
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'tamilai.db')


def get_db():
    """Return a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
        -- Users (students, teachers, parents)
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            email       TEXT    UNIQUE NOT NULL,
            password    TEXT    NOT NULL,
            role        TEXT    NOT NULL DEFAULT 'student',  -- student | teacher | parent
            class_grade TEXT,
            school      TEXT,
            avatar      TEXT,
            xp          INTEGER DEFAULT 0,
            coins       INTEGER DEFAULT 0,
            streak      INTEGER DEFAULT 0,
            last_active DATE,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- Books uploaded by students
        CREATE TABLE IF NOT EXISTS books (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title       TEXT    NOT NULL,
            subject     TEXT,
            file_path   TEXT    NOT NULL,
            faiss_index TEXT,
            pages       INTEGER DEFAULT 0,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- Chat history (AI Tutor conversations)
        CREATE TABLE IF NOT EXISTS chats (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            book_id     INTEGER REFERENCES books(id),
            session_id  TEXT    NOT NULL,
            role        TEXT    NOT NULL,  -- user | assistant
            content     TEXT    NOT NULL,
            subject     TEXT,
            liked       INTEGER DEFAULT 0,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- Quizzes generated
        CREATE TABLE IF NOT EXISTS quizzes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title       TEXT    NOT NULL,
            subject     TEXT,
            topic       TEXT,
            difficulty  TEXT    DEFAULT 'medium',
            questions   TEXT    NOT NULL,  -- JSON
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- Quiz attempt results
        CREATE TABLE IF NOT EXISTS quiz_results (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            quiz_id     INTEGER NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
            score       INTEGER NOT NULL,
            total       INTEGER NOT NULL,
            answers     TEXT    NOT NULL,  -- JSON
            time_taken  INTEGER,           -- seconds
            completed_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- AI-generated notes
        CREATE TABLE IF NOT EXISTS notes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title       TEXT    NOT NULL,
            subject     TEXT,
            topic       TEXT,
            content     TEXT    NOT NULL,  -- JSON with summary, keypoints, flashcards
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- Daily study progress
        CREATE TABLE IF NOT EXISTS progress (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            date        DATE    NOT NULL,
            subject     TEXT,
            minutes     INTEGER DEFAULT 0,
            topics      TEXT,              -- JSON array
            xp_earned   INTEGER DEFAULT 0,
            UNIQUE(user_id, date, subject)
        );

        -- Achievements & badges
        CREATE TABLE IF NOT EXISTS achievements (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            badge_key   TEXT    NOT NULL,
            badge_name  TEXT    NOT NULL,
            earned_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, badge_key)
        );

        -- AI study recommendations
        CREATE TABLE IF NOT EXISTS recommendations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            type        TEXT    NOT NULL,  -- topic | revision | practice | goal
            content     TEXT    NOT NULL,  -- JSON
            is_done     INTEGER DEFAULT 0,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")
