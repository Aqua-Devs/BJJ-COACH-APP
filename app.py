from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import sqlite3
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database path - use current directory
DATABASE = 'bjj_coaching.db'

# Initialize database before first request
@app.before_request
def initialize_database():
    if not os.path.exists(DATABASE):
        print(f"Database does not exist. Creating at {DATABASE}")
        init_db()
        print("Database created successfully!")
        
    # Remove this function after first run to avoid checking every request
    app.before_request_funcs[None].remove(initialize_database)

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

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
            CREATE TABLE IF NOT EXISTS curriculum (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gym_id INTEGER NOT NULL,
                technique_name TEXT NOT NULL,
                category TEXT,
                belt_level TEXT,
                description TEXT,
                date_from TEXT,
                date_to TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (gym_id) REFERENCES gyms (id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                gym_id INTEGER,
                date TEXT NOT NULL,
                techniques TEXT,
                note_goed TEXT,
                note_focus TEXT,
                note_algemeen TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students (id),
                FOREIGN KEY (gym_id) REFERENCES gyms (id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS technique_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                technique TEXT UNIQUE NOT NULL
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
        conn.execute('''
            CREATE TABLE IF NOT EXISTS belt_promotions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                from_belt TEXT NOT NULL,
                to_belt TEXT NOT NULL,
                promotion_date TEXT NOT NULL,
                notes TEXT,
                FOREIGN KEY (student_id) REFERENCES students (id)
            )
        ''')
        conn.commit()

@login_required
@approved_required
@app.route('/')
@login_required
@approved_required
def index():
    gym_filter = request.args.get('gym_id', None)
    
    with get_db() as conn:
        # Get all gyms for filter
        gyms = conn.execute('SELECT * FROM gyms ORDER BY name').fetchall()
        
        # Get pending users if admin
        pending_users = []
        if session.get('is_admin'):
            pending_users = conn.execute('''
                SELECT * FROM users 
                WHERE is_approved = 0 AND is_admin = 0
                ORDER BY created_at DESC
            ''').fetchall()
        
        # Build query with optional gym filter
        if gym_filter:
            students = conn.execute('''
                SELECT s.*, 
                       g.name as gym_name,
                       (SELECT COUNT(*) FROM sessions WHERE student_id = s.id) as session_count,
                       (SELECT date FROM sessions WHERE student_id = s.id ORDER BY date DESC LIMIT 1) as last_session,
                       (SELECT COUNT(*) FROM injuries WHERE student_id = s.id AND active = 1) as active_injuries
                FROM students s
                LEFT JOIN gyms g ON s.gym_id = g.id
                WHERE s.gym_id = ?
                ORDER BY s.name
            ''', (gym_filter,)).fetchall()
        else:
            students = conn.execute('''
                SELECT s.*, 
                       g.name as gym_name,
                       (SELECT COUNT(*) FROM sessions WHERE student_id = s.id) as session_count,
                       (SELECT date FROM sessions WHERE student_id = s.id ORDER BY date DESC LIMIT 1) as last_session,
                       (SELECT COUNT(*) FROM injuries WHERE student_id = s.id AND active = 1) as active_injuries
                FROM students s
                LEFT JOIN gyms g ON s.gym_id = g.id
                ORDER BY s.name
            ''').fetchall()
        
        # Calculate peer stats for comparison
        total_students = len(students)
        if total_students > 0:
            avg_sessions = sum(s['session_count'] for s in students) / total_students if total_students else 0
        else:
            avg_sessions = 0
            
    return render_template('index.html', 
                         students=students, 
                         avg_sessions=avg_sessions, 
                         gyms=gyms, 
                         current_gym=gym_filter,
                         pending_users=pending_users)

# Auth routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
            
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['user_email'] = user['email']
                session['is_admin'] = user['is_admin']
                
                if not user['is_approved'] and not user['is_admin']:
                    return render_template('pending_approval.html')
                
                return redirect(url_for('index'))
            else:
                flash('Ongeldige email of wachtwoord')
        
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        password_confirm = request.form['password_confirm']
        
        if password != password_confirm:
            flash('Wachtwoorden komen niet overeen')
            return render_template('register.html')
        
        password_hash = generate_password_hash(password)
        
        with get_db() as conn:
            try:
                # Check if this is the first user (make them admin)
                user_count = conn.execute('SELECT COUNT(*) as c FROM users').fetchone()['c']
                is_first_user = user_count == 0
                
                conn.execute('''
                    INSERT INTO users (email, password_hash, is_approved, is_admin, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (email, password_hash, 1 if is_first_user else 0, 1 if is_first_user else 0, datetime.now().isoformat()))
                conn.commit()
                
                if is_first_user:
                    flash('Account aangemaakt als admin!')
                    return redirect(url_for('login'))
                else:
                    flash('Account aangemaakt! Wacht op goedkeuring van de admin.')
                    return render_template('pending_approval.html')
            except sqlite3.IntegrityError:
                flash('Email is al in gebruik')
        
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/debug/session')
@login_required
def debug_session():
    """Debug route om session info te zien"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE id = %s', (session.get('user_id'),))
    user = dict_fetchone(cur)
    cur.close()
    conn.close()
    
    debug_info = f"""
    <h1>Debug Info</h1>
    <p><strong>Session user_id:</strong> {session.get('user_id')}</p>
    <p><strong>Session is_admin:</strong> {session.get('is_admin')}</p>
    <p><strong>Session email:</strong> {session.get('user_email')}</p>
    <hr>
    <p><strong>Database user:</strong></p>
    <pre>{user}</pre>
    <hr>
    <a href="/">Terug</a> | <a href="/logout">Logout</a>
    """
    return debug_info

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    with get_db() as conn:
        users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    
    # Simple HTML without template
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Gebruikersbeheer - BJJ Coach</title>
        <style>
            body { 
                font-family: -apple-system, sans-serif; 
                background: #0a0a0a; 
                color: #e0e0e0; 
                padding: 40px;
                max-width: 1000px;
                margin: 0 auto;
            }
            h1 { color: #ff6b35; margin-bottom: 30px; }
            .back { 
                display: inline-block;
                color: #ff6b35; 
                text-decoration: none; 
                margin-bottom: 20px;
                font-size: 14px;
            }
            .back:hover { text-decoration: underline; }
            .user { 
                background: #1a1a1a; 
                padding: 20px; 
                margin: 15px 0; 
                border-radius: 12px;
                border-left: 4px solid #ff6b35;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .user.pending { border-left-color: #FFC107; background: #1a1a0a; }
            .email { font-size: 18px; font-weight: 600; color: #ff6b35; }
            .meta { color: #888; font-size: 13px; margin-top: 5px; }
            .badge { 
                display: inline-block;
                padding: 4px 10px; 
                border-radius: 6px; 
                font-size: 12px;
                margin-right: 8px;
                font-weight: 600;
            }
            .badge-admin { background: #9C27B0; color: white; }
            .badge-approved { background: #4CAF50; color: white; }
            .badge-pending { background: #FFC107; color: #1a1a1a; }
            .btn { 
                padding: 10px 18px; 
                border: none; 
                border-radius: 8px;
                font-weight: 600;
                cursor: pointer;
                margin-left: 8px;
                font-size: 14px;
            }
            .btn-approve { background: #4CAF50; color: white; }
            .btn-delete { background: #d32f2f; color: white; }
            .flash { 
                background: #4CAF50; 
                color: white; 
                padding: 15px; 
                border-radius: 8px;
                margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        <a href="/" class="back">← Terug naar overzicht</a>
        <h1>👥 Gebruikersbeheer</h1>
        
        ''' + (''.join([f'<div class="flash">{msg}</div>' for msg in get_flashed_messages()])) + '''
        
        <div>
    '''
    
    for user in users:
        pending_class = 'pending' if not user['is_approved'] and not user['is_admin'] else ''
        html += f'''
        <div class="user {pending_class}">
            <div>
                <div class="email">{user['email']}</div>
                <div class="meta">
                    {'<span class="badge badge-admin">👑 Admin</span>' if user['is_admin'] else ''}
                    {'<span class="badge badge-approved">✅ Goedgekeurd</span>' if user['is_approved'] else '<span class="badge badge-pending">⏳ Wacht op goedkeuring</span>'}
                    <span>{user['created_at'][:16]}</span>
                </div>
            </div>
            <div>
        '''
        
        if not user['is_approved'] and not user['is_admin']:
            html += f'''
                <form action="/admin/approve_user/{user['id']}" method="POST" style="display:inline;">
                    <button type="submit" class="btn btn-approve">✓ Goedkeuren</button>
                </form>
            '''
        
        if not user['is_admin']:
            html += f'''
                <form action="/admin/delete_user/{user['id']}" method="POST" style="display:inline;"
                      onsubmit="return confirm('Weet je zeker dat je {user['email']} wilt verwijderen?');">
                    <button type="submit" class="btn btn-delete">🗑️ Verwijderen</button>
                </form>
            '''
        
        html += '''
            </div>
        </div>
        '''
    
    html += '''
        </div>
    </body>
    </html>
    '''
    
    return html

@app.route('/admin/approve_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def approve_user(user_id):
    with get_db() as conn:
        conn.execute('UPDATE users SET is_approved = 1 WHERE id = ?', (user_id,))
        conn.commit()
    flash('Gebruiker goedgekeurd!')
    return redirect(url_for('admin_users'))

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    with get_db() as conn:
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
    flash('Gebruiker verwijderd!')
    return redirect(url_for('admin_users'))

@login_required
@approved_required
@app.route('/student/<int:student_id>')
@login_required
@approved_required
def student_detail(student_id):
    with get_db() as conn:
        student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
        sessions = conn.execute('''
            SELECT * FROM sessions 
            WHERE student_id = ? 
            ORDER BY date DESC, created_at DESC
            LIMIT 20
        ''', (student_id,)).fetchall()
        
        # Get sparring sessions
        sparring = conn.execute('''
            SELECT * FROM sparring_sessions
            WHERE student_id = ?
            ORDER BY date DESC
            LIMIT 10
        ''', (student_id,)).fetchall()
        
        # Get active injuries
        injuries = conn.execute('''
            SELECT * FROM injuries
            WHERE student_id = ? AND active = 1
            ORDER BY start_date DESC
        ''', (student_id,)).fetchall()
        
        # Get technique mastery
        mastery = conn.execute('''
            SELECT * FROM technique_mastery
            WHERE student_id = ?
            ORDER BY technique
        ''', (student_id,)).fetchall()
        
        # Calculate training frequency (last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        freq = conn.execute('''
            SELECT COUNT(*) as count FROM sessions
            WHERE student_id = ? AND date >= ?
        ''', (student_id, thirty_days_ago)).fetchone()
        training_frequency = freq['count'] if freq else 0
        
        # Calculate streak
        all_dates = conn.execute('''
            SELECT DISTINCT date FROM sessions
            WHERE student_id = ?
            ORDER BY date DESC
        ''', (student_id,)).fetchall()
        
        streak = 0
        if all_dates:
            dates = [datetime.strptime(d['date'], '%Y-%m-%d') for d in all_dates]
            today = datetime.now().date()
            for i, d in enumerate(dates):
                if i == 0:
                    if (today - d.date()).days <= 1:
                        streak = 1
                    else:
                        break
                else:
                    diff = (dates[i-1].date() - d.date()).days
                    if diff <= 1:
                        streak += 1
                    else:
                        break
        
        # Sparring stats
        sparring_stats = {
            'total': len(sparring),
            'wins': len([s for s in sparring if s['outcome'] == 'win']),
            'losses': len([s for s in sparring if s['outcome'] == 'loss']),
            'draws': len([s for s in sparring if s['outcome'] == 'draw'])
        }
        
        # Belt progression
        belt_order = {'white': 0, 'blue': 1, 'purple': 2, 'brown': 3, 'black': 4}
        current_belt_idx = belt_order.get(student['belt'], 0)
        next_belt = None
        if current_belt_idx < 4:
            next_belt = list(belt_order.keys())[current_belt_idx + 1]
        
        # Calculate readiness percentage for next belt
        stripes = student['stripes'] or 0
        readiness = min(100, int((stripes / 4) * 100))
        
        # Peer comparison
        all_students = conn.execute('SELECT * FROM students').fetchall()
        same_belt = [s for s in all_students if s['belt'] == student['belt']]
        
        if len(same_belt) > 1:
            same_belt_sessions = []
            for s in same_belt:
                count = conn.execute('SELECT COUNT(*) as c FROM sessions WHERE student_id = ?', (s['id'],)).fetchone()
                same_belt_sessions.append(count['c'])
            avg_same_belt = sum(same_belt_sessions) / len(same_belt_sessions)
            peer_percentile = int((sum(1 for x in same_belt_sessions if x < freq['count']) / len(same_belt_sessions)) * 100)
        else:
            avg_same_belt = 0
            peer_percentile = 50
        
        suggestions = conn.execute('SELECT technique FROM technique_suggestions ORDER BY technique').fetchall()
    
    suggestion_list = [s['technique'] for s in suggestions]
    
    return render_template('student_detail.html', 
                         student=student, 
                         sessions=sessions, 
                         suggestions=suggestion_list,
                         sparring=sparring,
                         injuries=injuries,
                         mastery=mastery,
                         training_frequency=training_frequency,
                         streak=streak,
                         sparring_stats=sparring_stats,
                         next_belt=next_belt,
                         readiness=readiness,
                         avg_same_belt=avg_same_belt,
                         peer_percentile=peer_percentile)

@login_required
@approved_required
@app.route('/add_student', methods=['GET', 'POST'])
@login_required
@approved_required
def add_student():
    if request.method == 'POST':
        name = request.form['name']
        belt = request.form['belt']
        since_date = request.form['since_date']
        stripes = request.form.get('stripes', 0)
        gym_id = request.form.get('gym_id', None)
        
        with get_db() as conn:
            conn.execute('INSERT INTO students (name, belt, since_date, stripes, gym_id) VALUES (?, ?, ?, ?, ?)',
                        (name, belt, since_date, stripes, gym_id))
            conn.commit()
        return redirect(url_for('index'))
    
    with get_db() as conn:
        gyms = conn.execute('SELECT * FROM gyms ORDER BY name').fetchall()
    
    return render_template('add_student.html', gyms=gyms)

@login_required
@approved_required
@app.route('/add_session/<int:student_id>', methods=['GET', 'POST'])
@login_required
@approved_required
def add_session(student_id):
    if request.method == 'POST':
        date = request.form['date']
        techniques = request.form.getlist('techniques[]')  # Multiple select
        note_goed = request.form.get('note_goed', '')
        note_focus = request.form.get('note_focus', '')
        note_algemeen = request.form.get('note_algemeen', '')
        
        # Combine techniques into comma-separated string
        techniques_str = ', '.join(techniques) if techniques else ''
        
        with get_db() as conn:
            conn.execute('''
                INSERT INTO sessions (student_id, date, techniques, note_goed, note_focus, note_algemeen, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (student_id, date, techniques_str, note_goed, note_focus, note_algemeen, datetime.now().isoformat()))
            
            # Update technique mastery for selected techniques
            if techniques:
                for tech in techniques:
                    tech = tech.strip().lower()
                    
                    existing = conn.execute('''
                        SELECT * FROM technique_mastery 
                        WHERE student_id = ? AND technique = ?
                    ''', (student_id, tech)).fetchone()
                    
                    if existing:
                        # Auto-upgrade if note_goed is filled
                        if note_goed:
                            current_level = existing['level']
                            current_pct = existing['mastery_percentage'] or 0
                            new_pct = min(100, current_pct + 5)  # +5% per goede sessie
                            
                            # Determine level based on percentage
                            if new_pct < 25:
                                new_level = 'introduced'
                            elif new_pct < 50:
                                new_level = 'drilling'
                            elif new_pct < 75:
                                new_level = 'rolling'
                            else:
                                new_level = 'mastered'
                            
                            conn.execute('''
                                UPDATE technique_mastery 
                                SET mastery_percentage = ?, level = ?, last_updated = ?
                                WHERE student_id = ? AND technique = ?
                            ''', (new_pct, new_level, datetime.now().isoformat(), student_id, tech))
                    else:
                        # First time this technique is logged
                        initial_pct = 10 if note_goed else 5
                        conn.execute('''
                            INSERT INTO technique_mastery (student_id, technique, mastery_percentage, level, last_updated)
                            VALUES (?, ?, ?, 'introduced', ?)
                        ''', (student_id, tech, initial_pct, datetime.now().isoformat()))
            
            conn.commit()
        
        return redirect(url_for('student_detail', student_id=student_id))
    
    with get_db() as conn:
        student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
        injuries = conn.execute('''
            SELECT * FROM injuries WHERE student_id = ? AND active = 1
        ''', (student_id,)).fetchall()
        
        # Get curriculum for student's gym (current + no date restrictions)
        curriculum_techniques = []
        if student['gym_id']:
            today = datetime.now().strftime('%Y-%m-%d')
            curriculum_techniques = conn.execute('''
                SELECT DISTINCT technique_name FROM curriculum 
                WHERE gym_id = ? 
                AND (date_from IS NULL OR date_from <= ?)
                AND (date_to IS NULL OR date_to >= ?)
                ORDER BY technique_name
            ''', (student['gym_id'], today, today)).fetchall()
    
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('add_session.html', student=student, curriculum_techniques=curriculum_techniques, today=today, injuries=injuries)

@login_required
@approved_required
@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
@login_required
@approved_required
def edit_student(student_id):
    if request.method == 'POST':
        name = request.form['name']
        belt = request.form['belt']
        since_date = request.form['since_date']
        stripes = request.form.get('stripes', 0)
        competition_date = request.form.get('competition_date', None)
        competition_prep_active = 1 if request.form.get('competition_prep_active') else 0
        current_weight = request.form.get('current_weight', None)
        gym_id = request.form.get('gym_id', None)
        
        with get_db() as conn:
            conn.execute('''UPDATE students 
                           SET name = ?, belt = ?, since_date = ?, stripes = ?,
                               competition_date = ?, competition_prep_active = ?, current_weight = ?, gym_id = ?
                           WHERE id = ?''',
                        (name, belt, since_date, stripes, competition_date, 
                         competition_prep_active, current_weight, gym_id, student_id))
            conn.commit()
        
        return redirect(url_for('student_detail', student_id=student_id))
    
    with get_db() as conn:
        student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
        gyms = conn.execute('SELECT * FROM gyms ORDER BY name').fetchall()
    
    return render_template('edit_student.html', student=student, gyms=gyms)

@login_required
@approved_required
@app.route('/delete_session/<int:session_id>/<int:student_id>', methods=['POST'])
@login_required
@approved_required
def delete_session(session_id, student_id):
    with get_db() as conn:
        conn.execute('DELETE FROM sessions WHERE id = ?', (session_id,))
        conn.commit()
    return redirect(url_for('student_detail', student_id=student_id))

@login_required
@approved_required
@app.route('/add_sparring/<int:student_id>', methods=['GET', 'POST'])
@login_required
@approved_required
def add_sparring(student_id):
    if request.method == 'POST':
        opponent = request.form['opponent_name']
        date = request.form['date']
        outcome = request.form['outcome']
        notes = request.form.get('notes', '')
        what_worked = request.form.get('what_worked', '')
        what_didnt = request.form.get('what_didnt', '')
        
        with get_db() as conn:
            conn.execute('''
                INSERT INTO sparring_sessions 
                (student_id, opponent_name, date, outcome, notes, what_worked, what_didnt, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (student_id, opponent, date, outcome, notes, what_worked, what_didnt, datetime.now().isoformat()))
            conn.commit()
        
        return redirect(url_for('student_detail', student_id=student_id))
    
    with get_db() as conn:
        student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('add_sparring.html', student=student, today=today)

@login_required
@approved_required
@app.route('/add_injury/<int:student_id>', methods=['GET', 'POST'])
@login_required
@approved_required
def add_injury(student_id):
    if request.method == 'POST':
        injury_type = request.form['injury_type']
        affected_area = request.form['affected_area']
        restricted_techniques = request.form.get('restricted_techniques', '')
        start_date = request.form['start_date']
        notes = request.form.get('notes', '')
        
        with get_db() as conn:
            conn.execute('''
                INSERT INTO injuries 
                (student_id, injury_type, affected_area, restricted_techniques, start_date, notes, active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            ''', (student_id, injury_type, affected_area, restricted_techniques, start_date, notes))
            conn.commit()
        
        return redirect(url_for('student_detail', student_id=student_id))
    
    with get_db() as conn:
        student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('add_injury.html', student=student, today=today)

@login_required
@approved_required
@app.route('/close_injury/<int:injury_id>/<int:student_id>', methods=['POST'])
@login_required
@approved_required
def close_injury(injury_id, student_id):
    end_date = request.form.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    with get_db() as conn:
        conn.execute('UPDATE injuries SET active = 0, end_date = ? WHERE id = ?', (end_date, injury_id))
        conn.commit()
    
    return redirect(url_for('student_detail', student_id=student_id))

@login_required
@approved_required
@app.route('/promote/<int:student_id>', methods=['POST'])
@login_required
@approved_required
def promote_student(student_id):
    action = request.form.get('action', 'promote')
    
    with get_db() as conn:
        student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
        
        belt_order = {'white': 'blue', 'blue': 'purple', 'purple': 'brown', 'brown': 'black'}
        current_belt = student['belt']
        
        if action == 'demote':
            # Remove stripe
            if student['stripes'] > 0:
                conn.execute('UPDATE students SET stripes = stripes - 1 WHERE id = ?', (student_id,))
        else:
            # Check if stripes promotion or belt promotion
            if student['stripes'] < 4:
                # Add stripe
                conn.execute('UPDATE students SET stripes = stripes + 1 WHERE id = ?', (student_id,))
            else:
                # Belt promotion
                if current_belt in belt_order:
                    new_belt = belt_order[current_belt]
                    conn.execute('UPDATE students SET belt = ?, stripes = 0 WHERE id = ?', (new_belt, student_id))
                    
                    # Log promotion
                    conn.execute('''
                        INSERT INTO belt_promotions (student_id, from_belt, to_belt, promotion_date, notes)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (student_id, current_belt, new_belt, datetime.now().strftime('%Y-%m-%d'), 
                          f'Promoted from {current_belt} to {new_belt}'))
        
        conn.commit()
    
    return redirect(url_for('student_detail', student_id=student_id))

@login_required
@approved_required
@app.route('/stats')
@login_required
@approved_required
def stats():
    with get_db() as conn:
        # Overall stats
        total_students = conn.execute('SELECT COUNT(*) as c FROM students').fetchone()['c']
        total_sessions = conn.execute('SELECT COUNT(*) as c FROM sessions').fetchone()['c']
        
        # Belt distribution
        belt_dist = conn.execute('''
            SELECT belt, COUNT(*) as count 
            FROM students 
            GROUP BY belt
            ORDER BY 
                CASE belt
                    WHEN 'white' THEN 1
                    WHEN 'blue' THEN 2
                    WHEN 'purple' THEN 3
                    WHEN 'brown' THEN 4
                    WHEN 'black' THEN 5
                END
        ''').fetchall()
        
        # Most active students
        active_students = conn.execute('''
            SELECT s.name, s.belt, COUNT(sess.id) as session_count
            FROM students s
            LEFT JOIN sessions sess ON s.id = sess.student_id
            GROUP BY s.id
            ORDER BY session_count DESC
            LIMIT 10
        ''').fetchall()
        
        # Training frequency by belt
        from datetime import datetime, timedelta
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        freq_by_belt = conn.execute('''
            SELECT s.belt, COUNT(sess.id) / COUNT(DISTINCT s.id) as avg_sessions
            FROM students s
            LEFT JOIN sessions sess ON s.id = sess.student_id AND sess.date >= ?
            GROUP BY s.belt
        ''', (thirty_days_ago,)).fetchall()
        
        # Per-student sparring analysis
        students_sparring = conn.execute('''
            SELECT s.id, s.name, s.belt,
                   COUNT(sp.id) as sparring_count,
                   SUM(CASE WHEN sp.outcome = 'win' THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN sp.outcome = 'loss' THEN 1 ELSE 0 END) as losses
            FROM students s
            LEFT JOIN sparring_sessions sp ON s.id = sp.student_id
            GROUP BY s.id
            HAVING sparring_count > 0
            ORDER BY s.name
        ''').fetchall()
        
        # Get all "what worked" and "what didn't" per student
        sparring_insights = {}
        for student in students_sparring:
            student_id = student['id']
            
            # Get all "what worked" entries
            worked = conn.execute('''
                SELECT what_worked FROM sparring_sessions
                WHERE student_id = ? AND what_worked IS NOT NULL AND what_worked != ''
                ORDER BY date DESC
            ''', (student_id,)).fetchall()
            
            # Get all "what didn't work" entries
            didnt_work = conn.execute('''
                SELECT what_didnt FROM sparring_sessions
                WHERE student_id = ? AND what_didnt IS NOT NULL AND what_didnt != ''
                ORDER BY date DESC
            ''', (student_id,)).fetchall()
            
            sparring_insights[student_id] = {
                'worked': [w['what_worked'] for w in worked],
                'didnt_work': [d['what_didnt'] for d in didnt_work]
            }
    
    return render_template('stats.html', 
                         total_students=total_students,
                         total_sessions=total_sessions,
                         belt_dist=belt_dist,
                         active_students=active_students,
                         freq_by_belt=freq_by_belt,
                         students_sparring=students_sparring,
                         sparring_insights=sparring_insights)

@login_required
@approved_required
@app.route('/gyms')
@login_required
@approved_required
def gyms():
    with get_db() as conn:
        gyms = conn.execute('SELECT * FROM gyms ORDER BY name').fetchall()
    return render_template('gyms.html', gyms=gyms)

@login_required
@approved_required
@app.route('/add_gym', methods=['GET', 'POST'])
@login_required
@approved_required
def add_gym():
    if request.method == 'POST':
        name = request.form['name']
        location = request.form.get('location', '')
        
        with get_db() as conn:
            conn.execute('INSERT INTO gyms (name, location, created_at) VALUES (?, ?, ?)',
                        (name, location, datetime.now().isoformat()))
            conn.commit()
        return redirect(url_for('gyms'))
    
    return render_template('add_gym.html')

@login_required
@approved_required
@app.route('/curriculum/<int:gym_id>')
@login_required
@approved_required
def curriculum(gym_id):
    view = request.args.get('view', 'current')  # current, upcoming, past, all
    
    with get_db() as conn:
        gym = conn.execute('SELECT * FROM gyms WHERE id = ?', (gym_id,)).fetchone()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Build query based on view
        if view == 'current':
            # Active now: date_from <= today AND (date_to >= today OR date_to IS NULL)
            techniques = conn.execute('''
                SELECT * FROM curriculum 
                WHERE gym_id = ? 
                AND (date_from IS NULL OR date_from <= ?)
                AND (date_to IS NULL OR date_to >= ?)
                ORDER BY 
                    CASE belt_level
                        WHEN 'white' THEN 1
                        WHEN 'blue' THEN 2
                        WHEN 'purple' THEN 3
                        WHEN 'brown' THEN 4
                        WHEN 'black' THEN 5
                    END,
                    category, technique_name
            ''', (gym_id, today, today)).fetchall()
        elif view == 'upcoming':
            # Future: date_from > today
            techniques = conn.execute('''
                SELECT * FROM curriculum 
                WHERE gym_id = ? 
                AND date_from IS NOT NULL 
                AND date_from > ?
                ORDER BY date_from, technique_name
            ''', (gym_id, today)).fetchall()
        elif view == 'past':
            # Past: date_to < today
            techniques = conn.execute('''
                SELECT * FROM curriculum 
                WHERE gym_id = ? 
                AND date_to IS NOT NULL 
                AND date_to < ?
                ORDER BY date_to DESC, technique_name
            ''', (gym_id, today)).fetchall()
        else:  # all
            techniques = conn.execute('''
                SELECT * FROM curriculum 
                WHERE gym_id = ? 
                ORDER BY 
                    CASE belt_level
                        WHEN 'white' THEN 1
                        WHEN 'blue' THEN 2
                        WHEN 'purple' THEN 3
                        WHEN 'brown' THEN 4
                        WHEN 'black' THEN 5
                    END,
                    category, technique_name
            ''', (gym_id,)).fetchall()
    
    return render_template('curriculum.html', gym=gym, techniques=techniques, current_view=view, today=today)

@login_required
@approved_required
@app.route('/add_curriculum/<int:gym_id>', methods=['GET', 'POST'])
@login_required
@approved_required
def add_curriculum(gym_id):
    if request.method == 'POST':
        technique_name = request.form['technique_name']
        category = request.form['category']
        belt_level = request.form['belt_level']
        description = request.form.get('description', '')
        date_from = request.form.get('date_from', None)
        date_to = request.form.get('date_to', None)
        
        # Convert empty strings to None
        if date_from == '':
            date_from = None
        if date_to == '':
            date_to = None
        
        with get_db() as conn:
            conn.execute('''
                INSERT INTO curriculum (gym_id, technique_name, category, belt_level, description, date_from, date_to, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (gym_id, technique_name, category, belt_level, description, date_from, date_to, datetime.now().isoformat()))
            conn.commit()
        
        return redirect(url_for('curriculum', gym_id=gym_id))
    
    with get_db() as conn:
        gym = conn.execute('SELECT * FROM gyms WHERE id = ?', (gym_id,)).fetchone()
    
    return render_template('add_curriculum.html', gym=gym)

@login_required
@approved_required
@app.route('/delete_curriculum/<int:technique_id>/<int:gym_id>', methods=['POST'])
@login_required
@approved_required
def delete_curriculum(technique_id, gym_id):
    with get_db() as conn:
        conn.execute('DELETE FROM curriculum WHERE id = ?', (technique_id,))
        conn.commit()
    return redirect(url_for('curriculum', gym_id=gym_id))

@login_required
@approved_required
@app.route('/student_mastery/<int:student_id>')
@login_required
@approved_required
def student_mastery(student_id):
    with get_db() as conn:
        student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
        
        # Get curriculum for student's gym
        if student['gym_id']:
            curriculum_items = conn.execute('''
                SELECT * FROM curriculum 
                WHERE gym_id = ? 
                ORDER BY 
                    CASE belt_level
                        WHEN 'white' THEN 1
                        WHEN 'blue' THEN 2
                        WHEN 'purple' THEN 3
                        WHEN 'brown' THEN 4
                        WHEN 'black' THEN 5
                    END,
                    category, technique_name
            ''', (student['gym_id'],)).fetchall()
        else:
            curriculum_items = []
        
        # Get existing mastery levels
        mastery_data = conn.execute('''
            SELECT * FROM technique_mastery WHERE student_id = ?
        ''', (student_id,)).fetchall()
        
        # Create dict for easy lookup
        mastery_dict = {m['technique']: m['mastery_percentage'] for m in mastery_data}
    
    return render_template('student_mastery.html', 
                         student=student, 
                         curriculum_items=curriculum_items,
                         mastery_dict=mastery_dict)

@login_required
@approved_required
@app.route('/update_mastery/<int:student_id>', methods=['POST'])
@login_required
@approved_required
def update_mastery(student_id):
    technique = request.form['technique']
    percentage = int(request.form['percentage'])
    
    with get_db() as conn:
        # Check if exists
        existing = conn.execute('''
            SELECT * FROM technique_mastery 
            WHERE student_id = ? AND technique = ?
        ''', (student_id, technique)).fetchone()
        
        # Determine level based on percentage
        if percentage < 25:
            level = 'introduced'
        elif percentage < 50:
            level = 'drilling'
        elif percentage < 75:
            level = 'rolling'
        else:
            level = 'mastered'
        
        if existing:
            conn.execute('''
                UPDATE technique_mastery 
                SET mastery_percentage = ?, level = ?, last_updated = ?
                WHERE student_id = ? AND technique = ?
            ''', (percentage, level, datetime.now().isoformat(), student_id, technique))
        else:
            conn.execute('''
                INSERT INTO technique_mastery 
                (student_id, technique, mastery_percentage, level, last_updated)
                VALUES (?, ?, ?, ?, ?)
            ''', (student_id, technique, percentage, level, datetime.now().isoformat()))
        
        conn.commit()
    
    return redirect(url_for('student_mastery', student_id=student_id))

if __name__ == '__main__':
    # Ensure database exists
    if not os.path.exists(DATABASE):
        print(f"Creating database at {DATABASE}")
        init_db()
        print("Database created successfully!")
    
    # Get port from environment (Render uses PORT env variable)
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
