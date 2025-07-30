import sqlite3

# Path to your SQLite database file
DB_PATH = 'proctoring.db'

def ensure_exams_columns():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Check if course_code column exists
    c.execute("PRAGMA table_info(exams)")
    columns = [row[1] for row in c.fetchall()]
    if 'course_code' not in columns:
        print('Adding course_code column to exams table...')
        c.execute('ALTER TABLE exams ADD COLUMN course_code TEXT')
    if 'exam_title' not in columns:
        print('Adding exam_title column to exams table...')
        c.execute('ALTER TABLE exams ADD COLUMN exam_title TEXT')
    conn.commit()
    conn.close()
    print('Done. Exams table columns ensured.')

if __name__ == '__main__':
    ensure_exams_columns()
