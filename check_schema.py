import sqlite3

DB_PATH = 'proctoring.db'

def check_schema():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    print('--- USERS ---')
    c.execute("PRAGMA table_info(users)")
    for col in c.fetchall():
        print(col)
    print('\n--- EXAMS ---')
    c.execute("PRAGMA table_info(exams)")
    for col in c.fetchall():
        print(col)
    print('\n--- QUESTIONS ---')
    c.execute("PRAGMA table_info(questions)")
    for col in c.fetchall():
        print(col)
    print('\n--- ALERTS ---')
    c.execute("PRAGMA table_info(alerts)")
    for col in c.fetchall():
        print(col)
    print('\n--- EXAM_SETTINGS ---')
    c.execute("PRAGMA table_info(exam_settings)")
    for col in c.fetchall():
        print(col)
    print('\n--- RESULTS ---')
    c.execute("PRAGMA table_info(results)")
    for col in c.fetchall():
        print(col)
    print('\n--- INTEGRITY_THRESHOLDS ---')
    c.execute("PRAGMA table_info(integrity_thresholds)")
    for col in c.fetchall():
        print(col)
    conn.close()

if __name__ == '__main__':
    check_schema()
