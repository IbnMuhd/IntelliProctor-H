"""
Script to remove duplicate users from the 'users' table in proctoring.db.
Keeps only the most recent (highest id) entry for each username.
Usage: python remove_duplicate_users.py
"""
import sqlite3
import sys

DB_PATH = 'proctoring.db'

def remove_duplicates():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # Find duplicate usernames (keep max id)
        c.execute('''
            SELECT username, MAX(id) as max_id
            FROM users
            GROUP BY username
            HAVING COUNT(*) > 1
        ''')
        duplicates = c.fetchall()
        if not duplicates:
            print("No duplicate users found.")
            return
        print(f"Found {len(duplicates)} duplicate usernames. Removing older entries...")
        for username, max_id in duplicates:
            # Delete all but the max_id for this username
            c.execute('DELETE FROM users WHERE username = ? AND id != ?', (username, max_id))
        conn.commit()
        print("Duplicate users removed. Only the most recent entry for each username remains.")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    remove_duplicates()
