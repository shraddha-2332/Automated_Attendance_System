import sqlite3
from pathlib import Path

DB_PATH = Path("attendance.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    # Students table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        roll_no TEXT,
        added_on TEXT DEFAULT (datetime('now'))
    )
    ''')
    # Subjects table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
    ''')
    # Timetable (simple sessions)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER,
        teacher TEXT,
        date TEXT,
        start_time TEXT,
        end_time TEXT,
        active INTEGER DEFAULT 0,
        FOREIGN KEY(subject_id) REFERENCES subjects(id)
    )
    ''')
    # Attendance records
    cur.execute('''
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER,
        student_id INTEGER,
        entry_time TEXT,
        exit_time TEXT,
        duration_sec INTEGER,
        status TEXT,
        marked_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(session_id) REFERENCES sessions(id),
        FOREIGN KEY(student_id) REFERENCES students(id)
    )
    ''')
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print('DB initialized')