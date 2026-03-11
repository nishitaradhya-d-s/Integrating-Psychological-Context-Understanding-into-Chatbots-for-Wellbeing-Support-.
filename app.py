from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os, csv
from models.database import get_db, query_db, execute_db, close_connection
from models.chatbot_model import analyze_sentiment, generate_response



app = Flask(__name__)
app.secret_key = 'replace_with_a_secure_random_key'
close_connection(app)
def get_user_by_email(email):
    return query_db('SELECT * FROM users WHERE email=?', (email,), one=True)
@app.route('/')
def index():
    return render_template('index.html')
@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name').strip()
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        gender = request.form.get('gender')
        age = request.form.get('age') or None
        if not name or not email or not password or not confirm:
            return jsonify({'status':'error','message':'Please fill required fields.'})
        if password != confirm:
            return jsonify({'status':'error','message':'Passwords do not match.'})
        if get_user_by_email(email):
            return jsonify({'status':'exists','message':'Email already registered, please log in.'})
        hashed = generate_password_hash(password)
        execute_db('INSERT INTO users (name,email,password,gender,age) VALUES (?,?,?,?,?)',
                   (name,email,hashed,gender,age))
        return jsonify({'status':'ok','message':'Registration successful! Please log in.'})
    return render_template('signup.html')
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        user = get_user_by_email(email)
        if not user:
            return jsonify({'status':'noemail','message':'Email not registered.'})
        if not check_password_hash(user['password'], password):
            return jsonify({'status':'wrongpass','message':'Incorrect password.'})
        session['user_id'] = user['id']
        session['email'] = user['email']
        session['name'] = user['name']
        session['role'] = user['role']
        execute_db('UPDATE users SET last_login=? WHERE id=?', (datetime.utcnow().isoformat(), user['id']))
        if user['email'] == 'nraja@gmail.com':
            return jsonify({'status':'admin','message':'Admin login success.'})
        return jsonify({'status':'ok','message':'Login successful.'})
    return render_template('login.html')
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))
def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'user_id' in session:
            return f(*args, **kwargs)
        return redirect(url_for('login'))
    return wrap
@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    user = query_db('SELECT * FROM users WHERE id=?', (user_id,), one=True)
    last_login = user['last_login']
    quote = query_db('SELECT * FROM quotes ORDER BY RANDOM() LIMIT 1', (), one=True)
    chats = query_db('SELECT * FROM chats WHERE user_id=? ORDER BY timestamp DESC LIMIT 5', (user_id,))
    sentiment_points = [{'sentiment':c['sentiment'],'polarity':c['polarity'],'timestamp':c['timestamp']} for c in chats]
    return render_template('user_dashboard.html', user=user, last_login=last_login, quote=quote, sentiment_points=sentiment_points)
@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    user_id = session['user_id']
    data = request.get_json()
    message = data.get('message','').strip()
    if not message:
        return jsonify({'status':'error','message':'Empty message.'})
    result = analyze_sentiment(message)
    sentiment_label = result['label']
    polarity = result['polarity']
    bot = generate_response(sentiment_label, message)
    execute_db('INSERT INTO chats (user_id, message, sentiment, polarity, timestamp) VALUES (?,?,?,?,?)',
               (user_id, message, sentiment_label, polarity, datetime.utcnow().isoformat()))
    execute_db('INSERT INTO chats (user_id, message, sentiment, polarity, timestamp) VALUES (?,?,?,?,?)',
               (user_id, bot['reply'], sentiment_label, polarity, datetime.utcnow().isoformat()))
    suggestions = {}
    if sentiment_label == 'negative':
        docs = query_db('SELECT * FROM doctors LIMIT 5')
        rems = query_db('SELECT * FROM remedies WHERE condition LIKE ? LIMIT 5', (f'%stress%',))
        suggestions['doctors'] = [dict(d) for d in docs]
        suggestions['remedies'] = [dict(r) for r in rems]
    response = {
        'status':'ok',
        'reply': bot['reply'],
        'sentiment': sentiment_label,
        'polarity': polarity,
        'suggestions': suggestions
    }
    return jsonify(response)
@app.route('/admin')
def admin_dashboard():
    if not (session.get('role') == 'admin' and session.get('email') == 'nraja@gmail.com'):
        return redirect(url_for('login'))
    users = query_db('SELECT id,name,email,role,last_login FROM users')
    sentiment_counts = query_db('SELECT sentiment, COUNT(*) as cnt FROM chats GROUP BY sentiment')
    return render_template('admin_dashboard.html', users=users, sentiment_counts=sentiment_counts)
@app.route('/admin/add_doctor', methods=['POST'])
def admin_add_doctor():
    if not (session.get('role') == 'admin' and session.get('email') == 'nraja@gmail.com'):
        return redirect(url_for('login'))
    name = request.form.get('name')
    specialization = request.form.get('specialization')
    city = request.form.get('city')
    contact = request.form.get('contact')
    map_link = request.form.get('map_link')
    execute_db('INSERT INTO doctors (name, specialization, city, contact, map_link) VALUES (?,?,?,?,?)',
               (name,specialization,city,contact,map_link))
    flash('Doctor added.')
    return redirect(url_for('admin_dashboard'))
@app.route('/admin/delete_user/<int:user_id>')
def admin_delete_user(user_id):
    if not (session.get('role') == 'admin' and session.get('email') == 'nraja@gmail.com'):
        return redirect(url_for('login'))
    execute_db('DELETE FROM users WHERE id=?', (user_id,))
    flash('User deleted.')
    return redirect(url_for('admin_dashboard'))
@app.route('/admin/export_chats')
def admin_export_chats():
    if not (session.get('role') == 'admin' and session.get('email') == 'nraja@gmail.com'):
        return redirect(url_for('login'))
    db = get_db()
    cur = db.execute('SELECT * FROM chats ORDER BY timestamp')
    rows = cur.fetchall()
    path = 'export_chats.csv'
    with open(path, 'w', newline='', encoding='utf-8') as f:
        import csv
        writer = csv.writer(f)
        writer.writerow(['id','user_id','message','sentiment','polarity','timestamp'])
        for r in rows:
            writer.writerow([r['id'], r['user_id'], r['message'], r['sentiment'], r['polarity'], r['timestamp']])
    return send_file(path, as_attachment=True)
@app.route('/profile', methods=['GET','POST'])
@login_required
def profile():
    user_id = session['user_id']
    if request.method == 'POST':
        name = request.form.get('name')
        avatar = request.files.get('avatar')
        avatar_filename = None
        if avatar:
            afn = f'avatar_{user_id}_{avatar.filename}'
            upath = os.path.join('static','uploads')
            os.makedirs(upath, exist_ok=True)
            avatar.save(os.path.join(upath,afn))
            avatar_filename = afn
        if name:
            execute_db('UPDATE users SET name=?, avatar=? WHERE id=?', (name, avatar_filename, user_id))
        flash('Profile updated.')
        return redirect(url_for('dashboard'))
    user = query_db('SELECT * FROM users WHERE id=?', (user_id,), one=True)
    return render_template('profile.html', user=user)
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', message="Page not found."), 404
if __name__ == '__main__':
    app.run(debug=True)





# Initialize chatbot
chatbot = chatbot_model()

@app.route('/api/chatbot_model', methods=['POST'])
def chatbot_model():
    """Enhanced chatbot API endpoint"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        user_id = session.get('user_id', 'anonymous')
        
        if not message:
            return jsonify({
                'error': 'No message provided',
                'reply': 'Please type a message to start chatting.'
            }), 400
        
        # Get response from enhanced chatbot
        response = chatbot.generate_response(user_id, message)
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'reply': 'I apologize, but I encountered an error. Please try again.'
        }), 500

@app.route('/api/user_insights')
def user_insights():
    """Get user's emotional insights"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    insights = chatbot.get_user_insights(session['user_id'])
    return jsonify(insights)

@app.route('/api/clear_chat_history', methods=['POST'])
def clear_chat_history():
    """Clear user's chat history"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    success = chatbot.clear_user_context(session['user_id'])
    return jsonify({'success': success})


# In your app.py, update the chat endpoint:
@app.route('/api/chat', methods=['POST'])
def api_chat():
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        user_id = session.get('user_id', 'anonymous')
        
        if not message:
            return jsonify({
                'error': 'No message provided',
                'reply': 'Please type a message to start chatting! 😊'
            }), 400
        
        # Use the enhanced chatbot
        response = generate_response(user_id, message)
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'reply': 'I apologize, but I encountered an error. Please try again! 😅'
        }), 500

# Add these routes to your Flask app

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    # Get all users
    users = get_all_users()  # Your function to get users
    total_chats = get_total_chats()
    active_sessions = get_active_sessions()
    crisis_flags = get_crisis_flags()
    sentiment_counts = get_sentiment_counts()
    doctors = get_all_doctors()
    activity_logs = get_recent_activity_logs()
    recent_chats = get_recent_chats()
    settings = get_system_settings()
    
    return render_template('admin_dashboard.html',
                         users=users,
                         total_chats=total_chats,
                         active_sessions=active_sessions,
                         crisis_flags=crisis_flags,
                         sentiment_counts=sentiment_counts,
                         doctors=doctors,
                         activity_logs=activity_logs,
                         recent_chats=recent_chats,
                         settings=settings)

@app.route('/admin/user/<int:user_id>')
@admin_required
def admin_view_user(user_id):
    user = get_user_by_id(user_id)
    user_chats = get_user_chats(user_id)
    user_moods = get_user_moods(user_id)
    return render_template('admin_user_details.html', user=user, chats=user_chats, moods=user_moods)

@app.route('/admin/user/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_user(user_id):
    if request.method == 'POST':
        # Update user logic
        pass
    user = get_user_by_id(user_id)
    return render_template('admin_edit_user.html', user=user)

@app.route('/admin/user/<int:user_id>/reset-password')
@admin_required
def admin_reset_password(user_id):
    # Reset password logic
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/user/<int:user_id>/delete')
@admin_required
def admin_delete_user(user_id):
    # Delete user logic
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add-user', methods=['POST'])
@admin_required
def admin_add_user():
    # Add new user logic
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/export/users')
@admin_required
def admin_export_users():
    # Export users to CSV logic
    pass

@app.route('/admin/export/chats')
@admin_required
def admin_export_chats():
    # Export chats to CSV logic
    pass

@app.route('/admin/doctors')
@admin_required
def admin_doctors():
    # View all doctors
    pass

@app.route('/admin/doctor/add', methods=['POST'])
@admin_required
def admin_add_doctor():
    # Add doctor logic
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/doctor/<int:doctor_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_doctor(doctor_id):
    # Edit doctor logic
    pass

@app.route('/admin/doctor/<int:doctor_id>/delete')
@admin_required
def admin_delete_doctor(doctor_id):
    # Delete doctor logic
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/logs')
@admin_required
def admin_system_logs():
    # View system logs
    pass

@app.route('/admin/settings/update', methods=['POST'])
@admin_required
def admin_update_settings():
    # Update system settings
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/chat/<int:chat_id>/details')
@admin_required
def admin_chat_details(chat_id):
    # Get chat details for modal
    chat = get_chat_by_id(chat_id)
    return jsonify(chat)

@app.route('/admin/dashboard/refresh')
@admin_required
def admin_refresh_dashboard():
    # AJAX endpoint to refresh dashboard data
    data = {
        'total_users': get_total_users(),
        'total_chats': get_total_chats(),
        'active_sessions': get_active_sessions(),
        'crisis_flags': get_crisis_flags(),
        'success': True
    }
    return jsonify(data)

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Admin access required')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
# app.py - Updated with all admin routes
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from functools import wraps
import sqlite3
import csv
import io
from datetime import datetime, timedelta
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this!

# Database helper functions
def get_db_connection():
    conn = sqlite3.connect('mental_health.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # Chats table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            sentiment TEXT,
            crisis_flag BOOLEAN DEFAULT 0,
            crisis_reason TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Moods table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS moods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            mood INTEGER,
            source TEXT,
            notes TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Doctors table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialization TEXT NOT NULL,
            city TEXT NOT NULL,
            contact TEXT NOT NULL,
            email TEXT,
            hospital TEXT,
            map_link TEXT,
            description TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Activity logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            action TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # System settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT UNIQUE NOT NULL,
            setting_value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert default admin user if not exists
    cursor.execute("SELECT * FROM users WHERE email = 'admin@example.com'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, ?)",
            ('Admin', 'admin@example.com', 'admin123', 1)
        )
    
    # Insert default settings
    default_settings = [
        ('email_alerts', '1'),
        ('monitor_chats', '1'),
        ('crisis_detection', '1'),
        ('site_name', 'Mental Health Chatbot')
    ]
    
    for key, value in default_settings:
        cursor.execute(
            "INSERT OR IGNORE INTO system_settings (setting_key, setting_value) VALUES (?, ?)",
            (key, value)
        )
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Helper functions
def log_activity(user_id, user_name, action):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO activity_logs (user_id, user_name, action, ip_address) VALUES (?, ?, ?, ?)",
        (user_id, user_name, action, request.remote_addr)
    )
    conn.commit()
    conn.close()

def get_system_settings():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT setting_key, setting_value FROM system_settings")
    settings = {row['setting_key']: row['setting_value'] for row in cursor.fetchall()}
    conn.close()
    return settings

# Decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first')
            return redirect(url_for('login'))
        if not session.get('is_admin'):
            flash('Admin access required')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('is_admin'):
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()
        
        if user and user['password'] == password:  # In production, use proper password hashing!
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['email'] = user['email']
            session['is_admin'] = bool(user['is_admin'])
            
            # Update last login
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user['id'],))
            conn.commit()
            conn.close()
            
            # Log activity
            log_activity(user['id'], user['name'], 'User logged in')
            
            if user['is_admin']:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('dashboard'))
        
        flash('Invalid email or password')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    if 'user_id' in session:
        log_activity(session['user_id'], session['name'], 'User logged out')
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))
    
    # Get user's data for dashboard
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get user's recent moods
    cursor.execute(
        "SELECT mood, timestamp FROM moods WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10",
        (session['user_id'],)
    )
    mood_data = cursor.fetchall()
    
    # Get user's recent chats
    cursor.execute(
        "SELECT message, response, sentiment, timestamp FROM chats WHERE user_id = ? ORDER BY timestamp DESC LIMIT 5",
        (session['user_id'],)
    )
    chat_data = cursor.fetchall()
    
    conn.close()
    
    return render_template('dashboard.html', 
                         mood_data=mood_data, 
                         chat_data=chat_data,
                         userName=session['name'])

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    data = request.json
    message = data.get('message', '')
    
    # Your chatbot logic here
    # For now, return a simple response
    response = f"I understand you said: '{message}'. How can I help you with your mental health today?"
    
    # Save chat to database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chats (user_id, message, response, sentiment) VALUES (?, ?, ?, ?)",
        (session['user_id'], message, response, 'neutral')
    )
    conn.commit()
    conn.close()
    
    # Log activity
    log_activity(session['user_id'], session['name'], f'Sent chat message: {message[:50]}...')
    
    return jsonify({'reply': response})

# ADMIN ROUTES
@app.route('/admin')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all users
    cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
    users = cursor.fetchall()
    
    # Get sentiment counts
    cursor.execute("""
        SELECT sentiment, COUNT(*) as count 
        FROM chats 
        WHERE sentiment IS NOT NULL 
        GROUP BY sentiment
    """)
    sentiment_counts = {row['sentiment']: row['count'] for row in cursor.fetchall()}
    
    # Get total counts
    cursor.execute("SELECT COUNT(*) as count FROM users")
    total_users = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM chats")
    total_chats = cursor.fetchone()['count']
    
    # Get active sessions (users who logged in today)
    cursor.execute("""
        SELECT COUNT(DISTINCT user_id) as count 
        FROM activity_logs 
        WHERE DATE(timestamp) = DATE('now') 
        AND action LIKE '%login%'
    """)
    active_sessions = cursor.fetchone()['count']
    
    # Get crisis flags
    cursor.execute("SELECT COUNT(*) as count FROM chats WHERE crisis_flag = 1")
    crisis_flags = cursor.fetchone()['count']
    
    # Get recent doctors
    cursor.execute("SELECT * FROM doctors WHERE is_active = 1 ORDER BY created_at DESC LIMIT 5")
    doctors = cursor.fetchall()
    
    # Get recent activity logs
    cursor.execute("""
        SELECT * FROM activity_logs 
        ORDER BY timestamp DESC 
        LIMIT 10
    """)
    activity_logs = cursor.fetchall()
    
    # Get recent chats
    cursor.execute("""
        SELECT c.*, u.name as user_name 
        FROM chats c 
        JOIN users u ON c.user_id = u.id 
        ORDER BY c.timestamp DESC 
        LIMIT 10
    """)
    recent_chats = cursor.fetchall()
    
    # Get system settings
    settings = get_system_settings()
    
    conn.close()
    
    return render_template('admin_dashboard.html',
                         users=users,
                         total_users=total_users,
                         total_chats=total_chats,
                         active_sessions=active_sessions,
                         crisis_flags=crisis_flags,
                         sentiment_counts=sentiment_counts,
                         doctors=doctors,
                         activity_logs=activity_logs,
                         recent_chats=recent_chats,
                         settings=settings)

@app.route('/admin/user/<int:user_id>')
@admin_required
def admin_view_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        flash('User not found')
        return redirect(url_for('admin_dashboard'))
    
    # Get user's chats
    cursor.execute(
        "SELECT * FROM chats WHERE user_id = ? ORDER BY timestamp DESC",
        (user_id,)
    )
    chats = cursor.fetchall()
    
    # Get user's moods
    cursor.execute(
        "SELECT * FROM moods WHERE user_id = ? ORDER BY timestamp DESC",
        (user_id,)
    )
    moods = cursor.fetchall()
    
    conn.close()
    
    return render_template('admin_user_details.html', user=user, chats=chats, moods=moods)

@app.route('/admin/user/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        is_admin = 1 if request.form.get('is_admin') else 0
        is_active = 1 if request.form.get('is_active') else 0
        
        cursor.execute(
            "UPDATE users SET name = ?, email = ?, is_admin = ?, is_active = ? WHERE id = ?",
            (name, email, is_admin, is_active, user_id)
        )
        conn.commit()
        
        log_activity(session['user_id'], session['name'], f'Edited user: {name}')
        flash('User updated successfully')
        
        conn.close()
        return redirect(url_for('admin_view_user', user_id=user_id))
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    return render_template('admin_edit_user.html', user=user)

@app.route('/admin/user/<int:user_id>/reset-password')
@admin_required
def admin_reset_password(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    
    if user:
        # Reset to default password (in production, send reset email instead)
        default_password = 'reset123'  # Change this to something more secure
        cursor.execute(
            "UPDATE users SET password = ? WHERE id = ?",
            (default_password, user_id)
        )
        conn.commit()
        
        log_activity(session['user_id'], session['name'], f'Reset password for user: {user["name"]}')
        flash(f"Password reset to '{default_password}' for user {user['name']}")
    
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/user/<int:user_id>/delete')
@admin_required
def admin_delete_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    
    if user:
        # Instead of deleting, we can deactivate the user
        cursor.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
        conn.commit()
        
        log_activity(session['user_id'], session['name'], f'Deactivated user: {user["name"]}')
        flash(f"User {user['name']} has been deactivated")
    
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/user/add', methods=['POST'])
@admin_required
def admin_add_user():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    user_type = request.form['user_type']
    is_admin = 1 if user_type == 'admin' else 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, ?)",
            (name, email, password, is_admin)
        )
        conn.commit()
        
        log_activity(session['user_id'], session['name'], f'Added new user: {name}')
        flash('User added successfully')
    except sqlite3.IntegrityError:
        flash('Email already exists')
    
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/export/users')
@admin_required
def admin_export_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, email, is_admin, is_active, 
               created_at, last_login 
        FROM users 
        ORDER BY created_at DESC
    """)
    users = cursor.fetchall()
    conn.close()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['ID', 'Name', 'Email', 'Is Admin', 'Is Active', 'Created At', 'Last Login'])
    
    # Write data
    for user in users:
        writer.writerow([
            user['id'],
            user['name'],
            user['email'],
            'Yes' if user['is_admin'] else 'No',
            'Yes' if user['is_active'] else 'No',
            user['created_at'],
            user['last_login'] or 'Never'
        ])
    
    # Create response
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=users_export.csv'
    response.headers['Content-type'] = 'text/csv'
    
    log_activity(session['user_id'], session['name'], 'Exported users data')
    return response

@app.route('/admin/export/chats')
@admin_required
def admin_export_chats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT c.id, u.name as user_name, c.message, c.response, 
               c.sentiment, c.crisis_flag, c.timestamp 
        FROM chats c 
        JOIN users u ON c.user_id = u.id 
        ORDER BY c.timestamp DESC
    """)
    chats = cursor.fetchall()
    conn.close()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['ID', 'User', 'Message', 'Response', 'Sentiment', 'Crisis Flag', 'Timestamp'])
    
    # Write data
    for chat in chats:
        writer.writerow([
            chat['id'],
            chat['user_name'],
            chat['message'][:200],  # Limit message length
            chat['response'][:200], # Limit response length
            chat['sentiment'] or 'N/A',
            'Yes' if chat['crisis_flag'] else 'No',
            chat['timestamp']
        ])
    
    # Create response
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=chats_export.csv'
    response.headers['Content-type'] = 'text/csv'
    
    log_activity(session['user_id'], session['name'], 'Exported chats data')
    return response

@app.route('/admin/export/data')
@admin_required
def admin_export_data():
    # This exports all data in a zip file
    log_activity(session['user_id'], session['name'], 'Exported all data')
    flash('Full data export feature coming soon!')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/doctors')
@admin_required
def admin_doctors():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM doctors ORDER BY created_at DESC")
    doctors = cursor.fetchall()
    conn.close()
    
    return render_template('admin_doctors.html', doctors=doctors)

@app.route('/admin/doctor/add', methods=['POST'])
@admin_required
def admin_add_doctor():
    name = request.form['name']
    specialization = request.form['specialization']
    city = request.form['city']
    contact = request.form['contact']
    email = request.form.get('email', '')
    hospital = request.form.get('hospital', '')
    map_link = request.form.get('map_link', '')
    description = request.form.get('description', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """INSERT INTO doctors 
           (name, specialization, city, contact, email, hospital, map_link, description) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (name, specialization, city, contact, email, hospital, map_link, description)
    )
    conn.commit()
    conn.close()
    
    log_activity(session['user_id'], session['name'], f'Added doctor: {name}')
    flash('Doctor added successfully')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/doctor/<int:doctor_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_doctor(doctor_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        name = request.form['name']
        specialization = request.form['specialization']
        city = request.form['city']
        contact = request.form['contact']
        email = request.form.get('email', '')
        hospital = request.form.get('hospital', '')
        map_link = request.form.get('map_link', '')
        description = request.form.get('description', '')
        is_active = 1 if request.form.get('is_active') else 0
        
        cursor.execute(
            """UPDATE doctors SET 
               name = ?, specialization = ?, city = ?, contact = ?, 
               email = ?, hospital = ?, map_link = ?, description = ?, is_active = ? 
               WHERE id = ?""",
            (name, specialization, city, contact, email, hospital, map_link, description, is_active, doctor_id)
        )
        conn.commit()
        
        log_activity(session['user_id'], session['name'], f'Edited doctor: {name}')
        flash('Doctor updated successfully')
        
        conn.close()
        return redirect(url_for('admin_doctors'))
    
    cursor.execute("SELECT * FROM doctors WHERE id = ?", (doctor_id,))
    doctor = cursor.fetchone()
    conn.close()
    
    if not doctor:
        flash('Doctor not found')
        return redirect(url_for('admin_doctors'))
    
    return render_template('admin_edit_doctor.html', doctor=doctor)

@app.route('/admin/doctor/<int:doctor_id>/delete')
@admin_required
def admin_delete_doctor(doctor_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM doctors WHERE id = ?", (doctor_id,))
    doctor = cursor.fetchone()
    
    if doctor:
        # Instead of deleting, deactivate
        cursor.execute("UPDATE doctors SET is_active = 0 WHERE id = ?", (doctor_id,))
        conn.commit()
        
        log_activity(session['user_id'], session['name'], f'Deactivated doctor: {doctor["name"]}')
        flash(f"Doctor {doctor['name']} has been deactivated")
    
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/export/doctors')
@admin_required
def admin_export_doctors():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM doctors ORDER BY created_at DESC")
    doctors = cursor.fetchall()
    conn.close()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['ID', 'Name', 'Specialization', 'City', 'Contact', 'Email', 'Hospital', 'Map Link', 'Description', 'Active', 'Created At'])
    
    # Write data
    for doctor in doctors:
        writer.writerow([
            doctor['id'],
            doctor['name'],
            doctor['specialization'],
            doctor['city'],
            doctor['contact'],
            doctor['email'] or '',
            doctor['hospital'] or '',
            doctor['map_link'] or '',
            doctor['description'] or '',
            'Yes' if doctor['is_active'] else 'No',
            doctor['created_at']
        ])
    
    # Create response
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=doctors_export.csv'
    response.headers['Content-type'] = 'text/csv'
    
    log_activity(session['user_id'], session['name'], 'Exported doctors data')
    return response

@app.route('/admin/logs')
@admin_required
def admin_system_logs():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM activity_logs 
        ORDER BY timestamp DESC 
        LIMIT 100
    """)
    logs = cursor.fetchall()
    conn.close()
    
    return render_template('admin_logs.html', logs=logs)

@app.route('/admin/settings/update', methods=['POST'])
@admin_required
def admin_update_settings():
    email_alerts = request.form.get('email_alerts', '0')
    monitor_chats = request.form.get('monitor_chats', '0')
    crisis_detection = request.form.get('crisis_detection', '0')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    settings = [
        ('email_alerts', email_alerts),
        ('monitor_chats', monitor_chats),
        ('crisis_detection', crisis_detection)
    ]
    
    for key, value in settings:
        cursor.execute(
            "UPDATE system_settings SET setting_value = ?, updated_at = CURRENT_TIMESTAMP WHERE setting_key = ?",
            (value, key)
        )
    
    conn.commit()
    conn.close()
    
    log_activity(session['user_id'], session['name'], 'Updated system settings')
    flash('Settings updated successfully')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/chat/<int:chat_id>/details')
@admin_required
def admin_chat_details(chat_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT c.*, u.name as user_name 
        FROM chats c 
        JOIN users u ON c.user_id = u.id 
        WHERE c.id = ?
    """, (chat_id,))
    
    chat = cursor.fetchone()
    conn.close()
    
    if chat:
        return jsonify({
            'id': chat['id'],
            'user_name': chat['user_name'],
            'message': chat['message'],
            'response': chat['response'],
            'sentiment': chat['sentiment'],
            'crisis_flag': bool(chat['crisis_flag']),
            'crisis_reason': chat['crisis_reason'],
            'timestamp': chat['timestamp']
        })
    
    return jsonify({'error': 'Chat not found'}), 404

@app.route('/admin/dashboard/refresh')
@admin_required
def admin_refresh_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as count FROM users")
    total_users = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM chats")
    total_chats = cursor.fetchone()['count']
    
    cursor.execute("""
        SELECT COUNT(DISTINCT user_id) as count 
        FROM activity_logs 
        WHERE DATE(timestamp) = DATE('now') 
        AND action LIKE '%login%'
    """)
    active_sessions = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM chats WHERE crisis_flag = 1")
    crisis_flags = cursor.fetchone()['count']
    
    conn.close()
    
    return jsonify({
        'total_users': total_users,
        'total_chats': total_chats,
        'active_sessions': active_sessions,
        'crisis_flags': crisis_flags,
        'success': True
    })

@app.route('/admin/chat-analytics')
@admin_required
def admin_chat_analytics():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get chat statistics by date
    cursor.execute("""
        SELECT DATE(timestamp) as date, 
               COUNT(*) as total_chats,
               SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END) as positive,
               SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) as negative,
               SUM(CASE WHEN sentiment = 'neutral' THEN 1 ELSE 0 END) as neutral,
               SUM(CASE WHEN crisis_flag = 1 THEN 1 ELSE 0 END) as crisis_flags
        FROM chats 
        WHERE timestamp >= DATE('now', '-30 days')
        GROUP BY DATE(timestamp)
        ORDER BY date DESC
    """)
    daily_stats = cursor.fetchall()
    
    # Get top users by chat count
    cursor.execute("""
        SELECT u.name, COUNT(c.id) as chat_count
        FROM users u
        LEFT JOIN chats c ON u.id = c.user_id
        GROUP BY u.id
        ORDER BY chat_count DESC
        LIMIT 10
    """)
    top_users = cursor.fetchall()
    
    conn.close()
    
    return render_template('admin_chat_analytics.html', 
                         daily_stats=daily_stats,
                         top_users=top_users)

# Helper function for time ago
def time_ago(dt):
    if dt is None:
        return "Never"
    
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 365:
        return f"{diff.days // 365} years ago"
    elif diff.days > 30:
        return f"{diff.days // 30} months ago"
    elif diff.days > 0:
        return f"{diff.days} days ago"
    elif diff.seconds > 3600:
        return f"{diff.seconds // 3600} hours ago"
    elif diff.seconds > 60:
        return f"{diff.seconds // 60} minutes ago"
    else:
        return "Just now"

# Add time_ago function to Jinja2 context
app.jinja_env.globals.update(time_ago=time_ago)

if __name__ == '__main__':
    app.run(debug=True, port=5000)