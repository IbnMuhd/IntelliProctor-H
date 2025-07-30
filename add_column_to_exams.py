import sqlite3

# This script adds the course_code column to the exams table if it does not exist.
# Run this once, then you can delete the script.

def add_course_code_column():
    conn = sqlite3.connect("proctoring.db")
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE exams ADD COLUMN course_code TEXT")
        print("course_code column added.")
    except sqlite3.OperationalError as e:
        print("course_code column may already exist or another error:", e)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_course_code_column()
