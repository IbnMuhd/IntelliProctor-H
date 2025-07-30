from flask import Flask, render_template, Response, jsonify, request, redirect, url_for, session, flash
from src.utils.db import add_user_with_embedding, get_face_embedding
from src.auth.face_auth import FaceAuthenticator
from src.monitoring.behavior_monitor import BehaviorMonitor
from src.utils.camera import Camera
import cv2
import threading
import queue
import time
import sounddevice as sd
import numpy as np
import sqlite3
import os
from base64 import b64decode
from io import BytesIO
from PIL import Image
from werkzeug.security import check_password_hash
import logging
from datetime import datetime
import uuid
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
# Use environment variable for secret key
app.secret_key = os.environ.get("EXAMGUARD_SECRET_KEY", "unsafe_default_secret_key")
if app.secret_key == "unsafe_default_secret_key":
    logging.warning("SECURITY WARNING: Using default secret key. Set EXAMGUARD_SECRET_KEY in your environment!")

# Secure session cookie settings
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
# Only set secure flag if running in production (HTTPS)
if os.environ.get('FLASK_ENV') == 'production' or os.environ.get('EXAMGUARD_USE_HTTPS') == '1':
    app.config['SESSION_COOKIE_SECURE'] = True

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Initialize rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)


# Database configuration
DATABASE = "proctoring.db"

# Ensure exams table exists
def ensure_exams_table():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_code TEXT,
        exam_title TEXT
    )''')
    conn.commit()
    conn.close()
ensure_exams_table()

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    # Create tables if they do not exist
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        password_hash TEXT,
        role TEXT,
        face_embedding BLOB
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS questions (id INTEGER PRIMARY KEY, question TEXT, option1 TEXT, option2 TEXT, option3 TEXT, option4 TEXT, answer TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS alerts (id INTEGER PRIMARY KEY, user TEXT, alert_type TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    # Add image_path column to alerts if missing
    try:
        c.execute('SELECT image_path FROM alerts LIMIT 1')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE alerts ADD COLUMN image_path TEXT')
    c.execute('''CREATE TABLE IF NOT EXISTS exam_settings (id INTEGER PRIMARY KEY, duration_minutes INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS results (id INTEGER PRIMARY KEY, username TEXT, score INTEGER, total INTEGER, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS integrity_thresholds (
        alert_type TEXT PRIMARY KEY,
        threshold INTEGER
    )''')
    # Add default admin if not exists
    from werkzeug.security import generate_password_hash
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", ("admin", generate_password_hash("adminpass"), "admin"))
    # Add default exam duration if not exists
    c.execute('SELECT * FROM exam_settings WHERE id = 1')
    if not c.fetchone():
        c.execute("INSERT INTO exam_settings (id, duration_minutes) VALUES (1, 30)")
    # Insert default thresholds if not present
    default_thresholds = {
        'face_mismatch': 1,
        'multiple_faces': 2,
        'looking_away': 4,
        'audio': 2,
        'screen_activity': 1,
    }
    for k, v in default_thresholds.items():
        c.execute('INSERT OR IGNORE INTO integrity_thresholds (alert_type, threshold) VALUES (?, ?)', (k, v))
    conn.commit()
    conn.close()

init_db()

# Global objects
camera = None
face_auth = None
behavior_monitor = None
frame_queue = queue.Queue(maxsize=10)
audio_alert = False
registered_face_embedding = None

# In-memory storage for demo
QUESTIONS = []
ALERTS = []

# --- Integrity thresholds per alert type ---
def load_thresholds():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT alert_type, threshold FROM integrity_thresholds')
    rows = c.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

def save_thresholds(thresholds):
    conn = get_db()
    c = conn.cursor()
    for k, v in thresholds.items():
        c.execute('UPDATE integrity_thresholds SET threshold = ? WHERE alert_type = ?', (v, k))
    conn.commit()
    conn.close()

INTEGRITY_THRESHOLDS = load_thresholds()
VIOLATION_COUNTS = {}

def increment_violation(user, alert_type):
    if user is None:
        user = 'unknown'
    if user not in VIOLATION_COUNTS:
        VIOLATION_COUNTS[user] = {}
    if alert_type not in VIOLATION_COUNTS[user]:
        VIOLATION_COUNTS[user][alert_type] = 0
    VIOLATION_COUNTS[user][alert_type] += 1
    threshold = INTEGRITY_THRESHOLDS.get(alert_type, 1)
    return VIOLATION_COUNTS[user][alert_type] >= threshold

def reset_violations(user=None):
    global VIOLATION_COUNTS
    if user:
        VIOLATION_COUNTS.pop(user, None)
    else:
        VIOLATION_COUNTS = {}

def initialize_system(registered_embedding=None):
    global camera, face_auth, behavior_monitor, registered_face_embedding
    try:
        camera = Camera()
        face_auth = FaceAuthenticator()
        frame = None
        # Warm up the camera: try to get a valid frame up to 10 times
        for _ in range(10):
            frame = camera.get_frame()
            if frame is not None:
                break
            time.sleep(0.1)
        if frame is None:
            # Camera could not be accessed or no frames available
            return jsonify({"status": "error", "message": "Camera access denied or not available. Please check your webcam connection and permissions."}), 500
        # Do not verify face here, just store embedding for continuous check
        if registered_embedding is not None:
            registered_face_embedding = registered_embedding
        behavior_monitor = BehaviorMonitor(registered_face_embedding)
    except Exception as e:
        import traceback
        print('Error in initialize_system:', traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500

def process_frame(user=None, role=None):
    global registered_face_embedding
    frame_count = 0
    last_check = 0
    check_interval = 0.5  # seconds between heavy checks
    while True:
        if camera:
            # Only run proctoring for students
            if role == 'admin':
                time.sleep(0.01)
                continue
            frame = camera.get_frame()
            if frame is not None:
                # --- Optimization: Lower resolution for proctoring ---
                frame = cv2.resize(frame, (320, 240))
                frame_count += 1
                now = time.time()
                # --- Optimization: Only run heavy checks every 0.5s ---
                if now - last_check > check_interval:
                    last_check = now
                    # Continuous face verification during exam
                    if registered_face_embedding is not None:
                        result = face_auth.verify_face(frame, registered_face_embedding)
                        if not result['verified']:
                            if increment_violation(user or 'unknown', 'face_mismatch'):
                                add_alert(user or 'unknown', 'face_mismatch', frame=frame)
                    behavior_results = behavior_monitor.analyze_frame(frame)
                    frame = behavior_monitor.draw_results(frame, behavior_results)
                    # Log all BehaviorMonitor alerts (all are relevant)
                    for event, triggered in behavior_results.items():
                        if triggered:
                            if increment_violation(user or 'unknown', event):
                                add_alert(user or 'unknown', event, frame=frame)
                # --- Always update the video feed for smoothness ---
                if not frame_queue.full():
                    frame_queue.put(frame)
                time.sleep(0.01)  # Small sleep for CPU balance
            else:
                time.sleep(0.01)
        else:
            time.sleep(0.01)

def generate_frames():
    while True:
        if not frame_queue.empty():
            frame = frame_queue.get()
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            time.sleep(0.05)

def monitor_audio(user=None, role=None, threshold=0.02, duration=1, samplerate=16000):
    global audio_alert
    import time
    while True:
        # Only run audio proctoring for students
        if role == 'admin':
            sd.sleep(int(duration * 1000))
            continue
        def callback(indata, frames, _time, status):
            volume_norm = np.linalg.norm(indata) / frames
            if volume_norm > threshold:
                ALERTS.append({"type": "audio", "time": time.time()})
                audio_alert = True
                if increment_violation(user or 'unknown', 'audio'):
                    add_alert(user or 'unknown', 'audio')
        with sd.InputStream(callback=callback, channels=1, samplerate=samplerate):
            sd.sleep(int(duration * 1000))

@app.route('/')
def index():
    return render_template('index.html')

# --- Admin Side ---

# --- Admin Dashboard ---
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    conn = get_db()
    exams = conn.execute("SELECT * FROM exams").fetchall()
    selected_exam_id = request.args.get('exam_id') or session.get('selected_exam_id')
    if selected_exam_id:
        session['selected_exam_id'] = selected_exam_id
    else:
        selected_exam_id = exams[0]['id'] if exams else None
        session['selected_exam_id'] = selected_exam_id
    questions = []
    if selected_exam_id:
        questions = conn.execute("SELECT * FROM questions WHERE exam_id = ?", (selected_exam_id,)).fetchall()
    else:
        questions = []
    # Only show alerts for students (not admins) and exclude screen_activity and 'You have left the exam screen!'
    alerts = conn.execute("SELECT * FROM alerts WHERE user IN (SELECT username FROM users WHERE role = 'student') AND alert_type != 'screen_activity' AND alert_type != 'You have left the exam screen!' ORDER BY timestamp DESC LIMIT 20").fetchall()
    duration = conn.execute('SELECT duration_minutes FROM exam_settings WHERE id = 1').fetchone()
    results = conn.execute('SELECT * FROM results ORDER BY timestamp DESC LIMIT 20').fetchall()
    conn.close()
    # Format options for display
    questions_fmt = []
    for q in questions:
        options = ', '.join([q['option1'], q['option2'], q['option3'], q['option4']])
        questions_fmt.append({'question': q['question'], 'options': options})
    thresholds = dict(INTEGRITY_THRESHOLDS)
    return render_template('admin.html', exams=exams, selected_exam_id=selected_exam_id, questions=questions_fmt, alerts=alerts, duration=duration[0] if duration else 30, results=results, thresholds=thresholds)

# --- Create Exam ---
@app.route('/create_exam', methods=['POST'])
def create_exam():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    course_code = request.form.get('course_code')
    exam_title = request.form.get('exam_title')
    if not course_code or not exam_title:
        flash('Course code and exam title are required.', 'danger')
        return redirect(url_for('admin'))
    conn = get_db()
    conn.execute('INSERT INTO exams (course_code, exam_title) VALUES (?, ?)', (course_code, exam_title))
    conn.commit()
    conn.close()
    flash('Exam created successfully!', 'success')
    return redirect(url_for('admin'))

# --- Select Exam ---
@app.route('/select_exam', methods=['POST'])
def select_exam():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    exam_id = request.form.get('exam_id')
    if exam_id:
        session['selected_exam_id'] = exam_id
    return redirect(url_for('admin', exam_id=exam_id))

# --- Add Question ---
@app.route('/add_question', methods=['POST'])
def add_question():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    exam_id = request.form.get('exam_id')
    question = request.form.get('question')
    options = [request.form.get(f'option{i}') for i in range(1, 5)]
    answer = request.form.get('answer')
    if not (exam_id and question and all(options) and answer):
        flash('All question fields are required.', 'danger')
        return redirect(url_for('admin'))
    conn = get_db()
    conn.execute('''INSERT INTO questions (exam_id, question, option1, option2, option3, option4, answer)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''', (exam_id, question, *options, answer))
    conn.commit()
    conn.close()
    flash('Question added successfully!', 'success')
    return redirect(url_for('admin'))

# --- Bulk Upload Questions ---
@app.route('/upload_questions', methods=['POST'])
def upload_questions():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    exam_id = request.form.get('exam_id')
    file = request.files.get('questions_file')
    if not (exam_id and file):
        flash('Exam and file are required.', 'danger')
        return redirect(url_for('admin'))
    import csv
    import io
    stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
    reader = csv.reader(stream)
    conn = get_db()
    count = 0
    for row in reader:
        if len(row) != 6:
            continue
        question, option1, option2, option3, option4, answer = row
        conn.execute('''INSERT INTO questions (exam_id, question, option1, option2, option3, option4, answer)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''', (exam_id, question, option1, option2, option3, option4, answer))
        count += 1
    conn.commit()
    conn.close()
    flash(f'{count} questions uploaded successfully!', 'success')
    return redirect(url_for('admin'))

@app.route('/set_exam_duration', methods=['POST'])
def set_exam_duration():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    duration = int(request.form.get('duration', 30))
    conn = get_db()
    conn.execute('UPDATE exam_settings SET duration_minutes = ? WHERE id = 1', (duration,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/set_thresholds', methods=['POST'])
def set_thresholds():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    changed = False
    for key in INTEGRITY_THRESHOLDS.keys():
        val = request.form.get(key)
        if val is not None and val.isdigit():
            INTEGRITY_THRESHOLDS[key] = int(val)
            changed = True
    if changed:
        save_thresholds(INTEGRITY_THRESHOLDS)
        flash('Integrity thresholds updated!', 'success')
    return redirect(url_for('admin'))

@app.route('/alerts')
def get_alerts():
    return jsonify(ALERTS)

@app.route('/alerts_json')
def alerts_json():
    conn = get_db()
    alerts = conn.execute("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 50").fetchall()
    conn.close()
    formatted_alerts = []
    for alert in alerts:
        # Skip screen_activity for admin
        if alert[2] == "screen_activity":
            continue
        formatted_alerts.append({
            "alert_type": alert[2].replace("_", " ").title(),
            "details": "",  # No details column
            "user": alert[1] if alert[1] else "Unknown",
            "timestamp": datetime.fromtimestamp(alert[3]).strftime("%Y-%m-%d %H:%M:%S")
        })
    return jsonify(formatted_alerts)

# --- Student Side ---
@app.route('/student', methods=['GET', 'POST'])
def student():
    if 'username' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))
    conn = get_db()
    if request.method == 'POST':
        # Save student answers and grade
        answers = {}
        for key, value in request.form.items():
            if key.startswith('q'):  # e.g., q0, q1, ...
                answers[key] = value
        questions = conn.execute("SELECT * FROM questions").fetchall()
        score = 0
        for idx, q in enumerate(questions):
            q_key = f'q{idx}'
            if q_key in answers and answers[q_key] == q['answer']:
                score += 1
        total = len(questions)
        conn.close()
        return render_template('student.html', questions=questions, score=score, total=total, submitted=True)
    questions = conn.execute("SELECT * FROM questions").fetchall()
    conn.close()
    return render_template('student.html', questions=questions)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/register_video_feed')
def register_video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


# --- Start Exam: Connects to exam_questions page ---
@app.route('/start_exam', methods=['POST'])
def start_exam():
    try:
        if session.get('role') != 'student':
            return jsonify({"status": "forbidden"}), 403

        # Get registered embedding for the logged-in student
        username = session.get('username')
        if not username:
            return jsonify({"status": "unauthorized"}), 401

        stored_embedding = get_face_embedding(username)
        if stored_embedding is None:
            return jsonify({"status": "no_embedding"}), 400

        # Convert to numpy array if stored as binary
        if isinstance(stored_embedding, (bytes, bytearray)):
            registered_embedding = np.frombuffer(stored_embedding, dtype=np.float32)
        else:
            registered_embedding = stored_embedding

        init_result = initialize_system(registered_embedding)
        if init_result is not None:
            return init_result

        # Capture username and role for threads
        user = username
        role = session.get('role')

        processing_thread = threading.Thread(target=process_frame, args=(user, role))
        processing_thread.daemon = True
        processing_thread.start()

        audio_thread = threading.Thread(target=monitor_audio, args=(user, role))
        audio_thread.daemon = True
        audio_thread.start()

        # Redirect to exam_questions page
        return jsonify({"status": "success", "redirect": url_for('exam_questions')})
    except Exception as e:
        import traceback
        print('Error in /start_exam:', traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500
# --- Results Page ---
@app.route('/results', methods=['GET'])
def results():
    if 'username' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    results = conn.execute('SELECT * FROM results ORDER BY timestamp DESC LIMIT 50').fetchall()
    conn.close()
    return render_template('results_page.html', results=results)

@app.route('/exam', methods=['GET', 'POST'])
def exam():
    if 'username' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))
    # Only show instructions and continue button
    return render_template('exam.html')

@app.route('/exam_questions', methods=['GET', 'POST'])
def exam_questions():
    if 'username' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))
    session['current_exam_page'] = 'exam_questions'  # Mark student is on questions page
    conn = get_db()
    duration = conn.execute('SELECT duration_minutes FROM exam_settings WHERE id = 1').fetchone()
    duration = duration[0] if duration else 30
    if request.method == 'POST':
        # Save student answers and grade
        answers = {}
        for key, value in request.form.items():
            if key.startswith('q'):
                answers[key] = value
        questions = conn.execute("SELECT * FROM questions").fetchall()
        score = 0
        for idx, q in enumerate(questions):
            q_key = f'q{idx}'
            if q_key in answers and answers[q_key] == q['answer']:
                score += 1
        total = len(questions)
        # Save result to DB
        conn.execute('INSERT INTO results (username, score, total) VALUES (?, ?, ?)', (session['username'], score, total))
        conn.commit()
        conn.close()
        session.pop('current_exam_page', None)  # Remove marker after submission
        reset_violations(session.get('username'))  # Reset violation counts after exam
        return render_template('exam_questions.html', questions=questions, score=score, total=total, submitted=True, duration=duration)
    questions = conn.execute("SELECT * FROM questions").fetchall()
    conn.close()
    return render_template('exam_questions.html', questions=questions, duration=duration)

@app.route('/verify_identity', methods=['POST'])
def verify_identity():
    if camera and face_auth:
        frame = camera.get_frame()
        if frame is not None:
            result = face_auth.verify_face(frame)
            return jsonify({"verified": bool(result)})
    return jsonify({"verified": False})

@app.route('/screen_activity', methods=['POST'])
def screen_activity():
    # Only log screen activity for students and only during the exam_questions page
    if session.get('role') != 'student':
        return jsonify({"status": "forbidden"}), 403
    # Only allow screen activity logging if the student is on the questions page
    if session.get('current_exam_page') != 'exam_questions':
        return jsonify({"status": "ignored"}), 200
    data = request.get_json()
    ALERTS.append({"type": "screen_activity", "event": data.get("event"), "time": time.time()})
    # Only log the alert if not 'You have left the exam screen!' or if user is not admin
    if data.get("event") == "You have left the exam screen!":
        # Do not log this for admin or anywhere else
        pass
    else:
        if increment_violation(session.get('username', 'unknown'), 'screen_activity'):
            add_alert(session.get('username', 'unknown'), 'screen_activity')
    return jsonify({"status": ""})

# --- Authentication routes ---
@csrf.exempt
@limiter.limit("5 per minute")
@app.route('/login', methods=['GET', 'POST'])
def login():
    import logging
    global face_auth
    if face_auth is None:
        face_auth = FaceAuthenticator()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        face_image_b64 = request.form.get('face_image')
        logging.info(f"Login attempt for user: {username}")
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            logging.info(f"Password verified for user: {username}")
            if user['role'] == 'admin':
                session['username'] = user['username']
                session['role'] = user['role']
                logging.info(f"Redirecting {username} to admin dashboard.")
                return redirect(url_for('admin'))
            elif face_image_b64:
                if ',' in face_image_b64:
                    face_image_b64 = face_image_b64.split(',')[1]
                try:
                    img_bytes = b64decode(face_image_b64)
                    img = Image.open(BytesIO(img_bytes)).convert('RGB')
                    frame = np.array(img)
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    stored_embedding = get_face_embedding(username)
                    result = face_auth.verify_face(frame, stored_embedding)
                    logging.info(f"Face verification result for {username}: {result}")
                    if not result['verified']:
                        logging.warning(f"Face not verified for {username}")
                        return render_template('login.html', error=result['message'])
                    session['username'] = user['username']
                    session['role'] = user['role']
                    logging.info(f"Redirecting {username} to dashboard: {user['role']}")
                    return redirect(url_for('student'))
                except Exception as e:
                    logging.error(f"Image decode error for {username}: {e}")
                    return render_template('login.html', error=f"Image decode error: {e}")
            else:
                logging.warning(f"No face image captured for {username}")
                return render_template('login.html', error="No face image captured. Please allow camera access.")
        else:
            logging.warning(f"Invalid credentials for {username}")
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@csrf.exempt
@limiter.limit("5 per minute")
@app.route('/register', methods=['GET', 'POST'])
def register():
    global face_auth
    if face_auth is None:
        face_auth = FaceAuthenticator()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        face_image_b64 = request.form.get('face_image')
        admin_code = request.form.get('admin_code', '')
        # Only allow admin registration if correct code is provided
        admin_secret = os.environ.get("EXAMGUARD_ADMIN_CODE", "asz62656453#")
        if admin_code != admin_secret:
            return render_template('register.html', error="Invalid admin registration code.")
        if face_image_b64:
            if ',' in face_image_b64:
                face_image_b64 = face_image_b64.split(',')[1]
            try:
                img_bytes = b64decode(face_image_b64)
                img = Image.open(BytesIO(img_bytes)).convert('RGB')
                frame = np.array(img)
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                result = face_auth.verify_face(frame)
                if result['verified'] and 'encoding' in result:
                    embedding_blob = result['encoding']
                    if add_user_with_embedding(username, password, embedding_blob, role):
                        return redirect(url_for('login'))
                    else:
                        return render_template('register.html', error="Username already exists.")
                else:
                    return render_template('register.html', error="Face not detected. Please try again.")
            except Exception as e:
                return render_template('register.html', error=f"Image decode error: {e}")
        else:
            return render_template('register.html', error="No face image captured. Please allow camera access.")
    return render_template('register.html')

@app.route('/delete_alert/<int:alert_id>', methods=['POST'])
def delete_alert(alert_id):
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'status': 'forbidden'}), 403
    conn = get_db()
    conn.execute('DELETE FROM alerts WHERE id = ?', (alert_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/delete_all_alerts', methods=['POST'])
def delete_all_alerts():
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'status': 'forbidden'}), 403
    conn = get_db()
    conn.execute('DELETE FROM alerts')
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/alerts_page')
def alerts_page():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    conn = get_db()
    alerts = conn.execute("SELECT * FROM alerts ORDER BY timestamp DESC").fetchall()
    conn.close()
    return render_template('alerts.html', alerts=alerts)

def add_alert(user, alert_type, timestamp=None, frame=None):
    if timestamp is None:
        import time
        timestamp = time.time()
    image_path = None
    if frame is not None:
        # Save screenshot to static/alert_images/
        img_dir = os.path.join('static', 'alert_images')
        os.makedirs(img_dir, exist_ok=True)
        filename = f"{user}_{alert_type}_{int(timestamp)}_{uuid.uuid4().hex[:8]}.jpg"
        img_path = os.path.join(img_dir, filename)
        cv2.imwrite(img_path, frame)
        image_path = img_path.replace('\\', '/').replace('static/', '')  # for web use
    conn = get_db()
    conn.execute("INSERT INTO alerts (user, alert_type, timestamp, image_path) VALUES (?, ?, ?, ?)", (user, alert_type, timestamp, image_path))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True, threaded=True)