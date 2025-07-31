"""
Migration script to safely add the 'exam_id' column to the 'questions' table in proctoring.db,
copy all existing data, and preserve foreign key constraints.

Usage:
    python migrate_questions_table.py

This script will:
- Create a new table 'questions_new' with the correct schema (including exam_id and FK)
- Copy all data from 'questions' to 'questions_new', setting exam_id to NULL for old rows
- Drop the old 'questions' table
- Rename 'questions_new' to 'questions'
- Recreate indexes and foreign keys if needed
"""
import sqlite3
import os

DB_PATH = 'proctoring.db'

BACKUP_PATH = 'proctoring_backup_before_questions_migration.db'

def backup_db():
    if os.path.exists(DB_PATH):
        import shutil
        shutil.copy(DB_PATH, BACKUP_PATH)
        print(f"Backup created at {BACKUP_PATH}")
    else:
        print(f"Database file {DB_PATH} not found!")
        exit(1)

def migrate_questions_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Check if exam_id already exists
    c.execute("PRAGMA table_info(questions)")
    columns = [col[1] for col in c.fetchall()]
    if 'exam_id' in columns:
        print("'exam_id' column already exists in 'questions'. No migration needed.")
        conn.close()
        return

    print("Migrating 'questions' table...")

    # 1. Create new table with correct schema
    c.execute('''
        CREATE TABLE IF NOT EXISTS questions_new (
            id INTEGER PRIMARY KEY,
            question TEXT,
            option1 TEXT,
            option2 TEXT,
            option3 TEXT,
            option4 TEXT,
            answer TEXT,
            exam_id INTEGER,
            FOREIGN KEY(exam_id) REFERENCES exams(id)
        )
    ''')

    # 2. Copy data from old table to new table (exam_id will be NULL)
    c.execute('''
        INSERT INTO questions_new (id, question, option1, option2, option3, option4, answer)
        SELECT id, question, option1, option2, option3, option4, answer FROM questions
    ''')

    # 3. Drop old table
    c.execute('DROP TABLE questions')

    # 4. Rename new table
    c.execute('ALTER TABLE questions_new RENAME TO questions')

    conn.commit()
    conn.close()
    print("Migration complete! 'questions' table now includes 'exam_id'.")
    print("You can now safely re-run assign_exam_id.py to assign orphan questions.")

if __name__ == '__main__':
    backup_db()
    migrate_questions_table()
