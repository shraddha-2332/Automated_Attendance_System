from flask import Flask, render_template, request, redirect, url_for, jsonify
from database import init_db, get_conn
from datetime import datetime
import json
from pathlib import Path

app = Flask(__name__)
init_db()

# Camera configuration
CONFIG_FILE = Path('camera_config.json')

def load_camera_config():
    default_config = {'camera_index': 1}  # Default to external camera
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return default_config
    return default_config

def save_camera_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

@app.route('/')
def index():
    conn = get_conn()
    cur = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    cur.execute('''
        SELECT s.id, sub.name as subject, s.teacher, s.date, s.start_time, s.end_time, s.active 
        FROM sessions s LEFT JOIN subjects sub ON s.subject_id=sub.id 
        WHERE date=?
    ''', (today,))
    sessions = cur.fetchall()
    conn.close()
    
    camera_config = load_camera_config()
    return render_template('index.html', sessions=sessions, camera_index=camera_config['camera_index'])

@app.route('/camera_settings', methods=['GET', 'POST'])
def camera_settings():
    if request.method == 'POST':
        camera_index = int(request.form.get('camera_index', 1))
        config = {'camera_index': camera_index}
        save_camera_config(config)
        return redirect(url_for('index'))
    
    camera_config = load_camera_config()
    return render_template('camera_settings.html', camera_index=camera_config['camera_index'])

@app.route('/test_camera/<int:camera_index>')
def test_camera(camera_index):
    """Test if camera is accessible"""
    import cv2
    cap = cv2.VideoCapture(camera_index)
    if cap.isOpened():
        ret, frame = cap.read()
        cap.release()
        if ret:
            return jsonify({'status': 'success', 'message': f'Camera {camera_index} is working'})
    return jsonify({'status': 'error', 'message': f'Camera {camera_index} not accessible'})

@app.route('/create_session', methods=['POST'])
def create_session():
    subject = request.form.get('subject')
    teacher = request.form.get('teacher')
    date = request.form.get('date')
    start = request.form.get('start_time')
    end = request.form.get('end_time')
    
    conn = get_conn()
    cur = conn.cursor()
    # Ensure subject exists
    cur.execute('INSERT OR IGNORE INTO subjects(name) VALUES (?)', (subject,))
    conn.commit()
    cur.execute('SELECT id FROM subjects WHERE name=?', (subject,))
    sid = cur.fetchone()['id']
    
    cur.execute('''
        INSERT INTO sessions(subject_id, teacher, date, start_time, end_time, active) 
        VALUES (?, ?, ?, ?, ?, 0)
    ''', (sid, teacher, date, start, end))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/start_session/<int:session_id>')
def start_session(session_id):
    conn = get_conn()
    cur = conn.cursor()
    # Deactivate all other sessions
    cur.execute('UPDATE sessions SET active=0')
    # Activate this session
    cur.execute('UPDATE sessions SET active=1 WHERE id=?', (session_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/end_session/<int:session_id>')
def end_session(session_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('UPDATE sessions SET active=0 WHERE id=?', (session_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/attendance/<int:session_id>')
def view_attendance(session_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
        SELECT a.id, st.name, st.roll_no, a.entry_time, a.exit_time, a.duration_sec, a.status
        FROM attendance a JOIN students st ON a.student_id=st.id 
        WHERE a.session_id=?
    ''', (session_id,))
    rows = cur.fetchall()
    conn.close()
    return render_template('session.html', records=rows, session_id=session_id)

@app.route('/manual_update', methods=['POST'])
def manual_update():
    att_id = request.form.get('att_id')
    status = request.form.get('status')
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('UPDATE attendance SET status=? WHERE id=?', (status, att_id))
    conn.commit()
    conn.close()
    return ('', 204)

if __name__ == '_main_':
    app.run(debug=True, host='0.0.0.0', port=5000)