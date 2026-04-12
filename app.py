from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import sqlite3
from datetime import datetime, timedelta
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database pad
DATABASE = 'bjj_coaching.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# --- DECORATORS ---

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
            if not user or not user['is_admin']:
                flash('Toegang geweigerd. Admin rechten vereist.')
                return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def approved_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
            if not user or (not user['is_approved'] and not user['is_admin']):
                return render_template('pending_approval.html')
        return f(*args, **kwargs)
    return decorated_function

# --- DATABASE INIT ---

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                is_approved INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS gyms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                location TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                belt TEXT NOT NULL,
                since_date TEXT NOT NULL,
                stripes INTEGER DEFAULT 0,
                competition_date TEXT,
                competition_prep_active INTEGER DEFAULT 0,
                current_weight REAL,
                gym_id INTEGER,
                FOREIGN KEY (gym_id) REFERENCES gyms (id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                techniques TEXT,
                note_goed TEXT,
                note_focus TEXT,
                note_algemeen TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students (id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS technique_mastery (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                technique TEXT NOT NULL,
                level TEXT DEFAULT 'introduced',
                mastery_percentage INTEGER DEFAULT 0,
                last_updated TEXT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students (id),
                UNIQUE(student_id, technique)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sparring_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                opponent_name TEXT NOT NULL,
                date TEXT NOT NULL,
                outcome TEXT,
                notes TEXT,
                what_worked TEXT,
                what_didnt TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students (id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS injuries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                injury_type TEXT NOT NULL,
                affected_area TEXT NOT NULL,
                restricted_techniques TEXT,
                start_date TEXT NOT NULL,
                end_date TEXT,
                notes TEXT,
                active INTEGER DEFAULT 1,
                FOREIGN KEY (student_id) REFERENCES students (id)
            )
        ''')
        conn.commit()

# --- ROUTES ---

@app.route('/')
@login_required
@approved_required
def index():
    gym_filter = request.args.get('gym_id', None)
    with get_db() as conn:
        gyms = conn.execute('SELECT * FROM gyms ORDER BY name').fetchall()
        query = '''
            SELECT s.*, g.name as gym_name,
            (SELECT COUNT(*) FROM sessions WHERE student_id = s.id) as session_count,
            (SELECT date FROM sessions WHERE student_id = s.id ORDER BY date DESC LIMIT 1) as last_session,
            (SELECT COUNT(*) FROM injuries WHERE student_id = s.id AND active = 1) as active_injuries
            FROM students s
            LEFT JOIN gyms g ON s.gym_id = g.id
        '''
        if gym_filter:
            students = conn.execute(query + ' WHERE s.gym_id = ? ORDER BY s.name', (gym_filter,)).fetchall()
        else:
            students = conn.execute(query + ' ORDER BY s.name').fetchall()
            
        avg_sessions = 0
        if students:
            avg_sessions = sum(s['session_count'] for s in students) / len(students)
            
    return render_template('index.html', students=students, avg_sessions=avg_sessions, gyms=gyms, current_gym=gym_filter)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['user_email'] = user['email']
                session['is_admin'] = user['is_admin']
                if not user['is_approved'] and not user['is_admin']:
                    return render_template('pending_approval.html')
                return redirect(url_for('index'))
            flash('Ongeldige email of wachtwoord')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if password != request.form.get('password_confirm'):
            flash('Wachtwoorden komen niet overeen')
            return render_template('register.html')
        
        with get_db() as conn:
            try:
                user_count = conn.execute('SELECT COUNT(*) as c FROM users').fetchone()['c']
                is_first = (user_count == 0)
                conn.execute('''
                    INSERT INTO users (email, password_hash, is_approved, is_admin, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (email, generate_password_hash(password), 1 if is_first else 0, 1 if is_first else 0, datetime.now().isoformat()))
                conn.commit()
                flash('Account aangemaakt!' if not is_first else 'Admin account aangemaakt!')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash('Email al in gebruik')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/student/<int:student_id>')
@login_required
@approved_required
def student_detail(student_id):
    with get_db() as conn:
        student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
        sessions = conn.execute('SELECT * FROM sessions WHERE student_id = ? ORDER BY date DESC LIMIT 20', (student_id,)).fetchall()
        sparring = conn.execute('SELECT * FROM sparring_sessions WHERE student_id = ? ORDER BY date DESC LIMIT 10', (student_id,)).fetchall()
        injuries = conn.execute('SELECT * FROM injuries WHERE student_id = ? AND active = 1', (student_id,)).fetchall()
        mastery = conn.execute('SELECT * FROM technique_mastery WHERE student_id = ? ORDER BY technique', (student_id,)).fetchall()
        
    return render_template('student_detail.html', student=student, sessions=sessions, sparring=sparring, injuries=injuries, mastery=mastery)

@app.route('/add_student', methods=['GET', 'POST'])
@login_required
@approved_required
def add_student():
    if request.method == 'POST':
        with get_db() as conn:
            conn.execute('INSERT INTO students (name, belt, since_date, stripes, gym_id) VALUES (?, ?, ?, ?, ?)',
                        (request.form['name'], request.form['belt'], request.form['since_date'], request.form.get('stripes', 0), request.form.get('gym_id')))
            conn.commit()
        return redirect(url_for('index'))
    with get_db() as conn:
        gyms = conn.execute('SELECT * FROM gyms ORDER BY name').fetchall()
    return render_template('add_student.html', gyms=gyms)

@app.route('/add_session/<int:student_id>', methods=['GET', 'POST'])
@login_required
@approved_required
def add_session(student_id):
    if request.method == 'POST':
        date = request.form['date']
        techs = request.form.getlist('techniques[]')
        with get_db() as conn:
            conn.execute('INSERT INTO sessions (student_id, date, techniques, note_goed, note_focus, note_algemeen, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (student_id, date, ', '.join(techs), request.form.get('note_goed'), request.form.get('note_focus'), request.form.get('note_algemeen'), datetime.now().isoformat()))
            conn.commit()
        return redirect(url_for('student_detail', student_id=student_id))
    
    with get_db() as conn:
        student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    return render_template('add_session.html', student=student, today=datetime.now().strftime('%Y-%m-%d'))

# --- SERVER START ---

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)