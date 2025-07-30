import sqlite3

# This script adds option1, option2, option3, option4 columns to the questions table if they do not exist.
# Run this once, then you can delete the script.

def add_option_columns():
    conn = sqlite3.connect("proctoring.db")
    c = conn.cursor()
    for col in ["option1", "option2", "option3", "option4"]:
        try:
            c.execute(f"ALTER TABLE questions ADD COLUMN {col} TEXT")
            print(f"Added column: {col}")
        except sqlite3.OperationalError as e:
            print(f"Column {col} may already exist or another error: {e}")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_option_columns()
