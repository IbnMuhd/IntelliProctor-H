import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from src.auth.face_auth import FaceAuthenticator

DB_PATH = 'proctoring.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            face_embedding BLOB,
            role TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_user(username, password):
    password_hash = generate_password_hash(password)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, password_hash))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verify_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT password_hash FROM users WHERE username = ?', (username,))
    row = c.fetchone()
    conn.close()
    if row and check_password_hash(row[0], password):
        return True
    return False

def add_user_with_embedding(username, password, embedding, role):
    """
    Add a user with username, password, face embedding (as BLOB), and role.
    """
    password_hash = generate_password_hash(password)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (username, password_hash, face_embedding, role) VALUES (?, ?, ?, ?)',
                  (username, password_hash, embedding, role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_face_embedding(username):
    """
    Retrieve the face embedding BLOB for a user.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT face_embedding FROM users WHERE username = ?', (username,))
    row = c.fetchone()
    conn.close()
    if row and row[0] is not None:
        return row[0]
    return None