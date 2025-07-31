"""
Script to list all users in the proctoring.db database, showing username, role, and whether a face embedding is present.
Usage: python list_users.py
"""
import sqlite3
import sys

DB_PATH = 'proctoring.db'

def list_users():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT id, username, role, face_embedding FROM users')
        users = c.fetchall()
        if not users:
            print("No users found in the database.")
            return
        print(f"{'ID':<5} {'Username':<20} {'Role':<10} {'Has Face Embedding'}")
        print('-' * 50)
        for user in users:
            user_id, username, role, embedding = user
            has_embedding = 'Yes' if embedding else 'No'
            print(f"{user_id:<5} {username:<20} {role or '':<10} {has_embedding}")
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
    list_users()
