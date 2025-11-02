import cv2
import pickle
import time
from pathlib import Path
from datetime import datetime
import face_recognition
from database import get_conn
from utils import secs_between, PRESENCE_THRESHOLD
import threading
import json

# Load camera configuration
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

# Optional serial (Arduino) integration
try:
    import serial
    SERIAL_AVAILABLE = True
except Exception:
    SERIAL_AVAILABLE = False
    print("Serial not available - running without Arduino")

# Load encodings
enc_path = Path('models/encodings.pkl')
if not enc_path.exists():
    print('Encodings not found. Run encode_faces.py first.')
    exit(1)

with open(enc_path, 'rb') as f:
    data = pickle.load(f)
known_encodings = data['encodings']
known_names = data['names']

print(f"Loaded {len(known_names)} known face encodings")

# Runtime structures
current_session_id = None
present_track = {}  # name -> {first_seen, last_seen}

# Camera initialization with external camera preference
camera_config = load_camera_config()
camera_index = camera_config['camera_index']

print(f"Attempting to initialize camera index: {camera_index} (External USB)")
video_capture = cv2.VideoCapture(camera_index)
video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if not video_capture.isOpened():
    print(f"Failed to open camera index {camera_index}. Trying index 0...")
    video_capture = cv2.VideoCapture(0)
    if not video_capture.isOpened():
        print("No camera found. Please check connections.")
        exit(1)
    print("Using fallback camera index 0")

print("Camera initialized successfully")

# Serial listener thread
serial_port = None

def serial_listener(port_name):
    global serial_port
    try:
        ser = serial.Serial(port_name, 9600, timeout=1)
        serial_port = ser
        print(f'Serial connected to {port_name}')
        while True:
            line = ser.readline().decode(errors='ignore').strip()
            if line:
                print('SERIAL:', line)
            time.sleep(0.01)
    except Exception as e:
        print('Serial error:', e)

# Start serial thread if needed
# threading.Thread(target=serial_listener, args=("COM3",), daemon=True).start()

def mark_entry(name):
    global present_track, current_session_id
    if current_session_id is None:
        print(f"No active session. Cannot mark entry for {name}")
        return
        
    # Ensure student exists in DB
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT id FROM students WHERE name=?', (name,))
    row = cur.fetchone()
    if not row:
        # Auto-insert student record
        cur.execute('INSERT OR IGNORE INTO students(name) VALUES (?)', (name,))
        conn.commit()
        cur.execute('SELECT id FROM students WHERE name=?', (name,))
        row = cur.fetchone()
    student_id = row['id']
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # If already tracked, update last_seen
    if name in present_track:
        present_track[name]['last_seen'] = now
        print(f"Updated presence: {name}")
    else:
        present_track[name] = {'student_id': student_id, 'first_seen': now, 'last_seen': now}
        print(f"New entry: {name} at {now}")
    
    conn.close()

def flush_attendance_records():
    """Write present_track to DB for the current session"""
    global present_track, current_session_id
    if current_session_id is None:
        print('No active session. Cannot flush attendance.')
        return
        
    conn = get_conn()
    cur = conn.cursor()
    
    # Get session info to compute threshold
    cur.execute('SELECT date, start_time, end_time FROM sessions WHERE id=?', (current_session_id,))
    srow = cur.fetchone()
    if srow:
        session_start = f"{srow['date']} {srow['start_time']}"
        session_end = f"{srow['date']} {srow['end_time']}"
        session_length = secs_between(session_start, session_end)
    else:
        session_length = None

    records_processed = 0
    for name, rec in present_track.items():
        student_id = rec['student_id']
        entry_time = rec['first_seen']
        exit_time = rec['last_seen']
        duration = secs_between(entry_time, exit_time)
        status = 'Absent'
        
        if session_length is None:
            # Fallback: if present > 60 sec -> present
            if duration >= 60:
                status = 'Present'
        else:
            if duration >= int(session_length * PRESENCE_THRESHOLD):
                status = 'Present'
            else:
                status = 'Absent'

        cur.execute('''INSERT INTO attendance(session_id, student_id, entry_time, exit_time, duration_sec, status)
                       VALUES (?, ?, ?, ?, ?, ?)''', 
                       (current_session_id, student_id, entry_time, exit_time, duration, status))
        records_processed += 1
        
    conn.commit()
    conn.close()
    print(f'Attendance flushed for session {current_session_id}: {records_processed} records')
    present_track = {}

def get_active_session():
    """Check for active session in database"""
    global current_session_id
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT id FROM sessions WHERE active=1')
    row = cur.fetchone()
    conn.close()
    
    if row:
        current_session_id = row['id']
        return True
    return False

print('Starting face recognition system...')
print('Press q to quit, f to flush attendance, s to check session status')

frame_count = 0
process_every_n_frames = 2  # Process every 2nd frame for performance

while True:
    ret, frame = video_capture.read()
    if not ret:
        print("Failed to grab frame")
        break
    
    frame_count += 1
    
    # Only process every nth frame for better performance
    if frame_count % process_every_n_frames == 0:
        # Resize frame for faster processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        rgb_small_frame = small_frame[:, :, ::-1]  # BGR to RGB
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        
        for encoding, location in zip(face_encodings, face_locations):
            matches = face_recognition.compare_faces(known_encodings, encoding, tolerance=0.48)
            name = "Unknown"
            
            if True in matches:
                first_match_index = matches.index(True)
                name = known_names[first_match_index]
                
                # Scale location back to original frame size
                top, right, bottom, left = [v * 2 for v in location]
                
                # Check if we have an active session
                if get_active_session():
                    mark_entry(name)
                    color = (0, 255, 0)  # Green for recognized
                else:
                    color = (255, 255, 0)  # Yellow for recognized but no session
                
                # Draw rectangle and name
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                cv2.putText(frame, name, (left, top - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            else:
                # Unknown face
                top, right, bottom, left = [v * 2 for v in location]
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                cv2.putText(frame, name, (left, top - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    # Display session status on frame
    status_text = f"Session: {'Active' if current_session_id else 'Inactive'}"
    cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, f"Tracking: {len(present_track)} students", (10, 60), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    cv2.imshow('Smart Attendance System - External Camera', frame)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('f'):
        flush_attendance_records()
    elif key == ord('s'):
        get_active_session()
        print(f"Session status: {'Active' if current_session_id else 'Inactive'}")

# Cleanup
video_capture.release()
cv2.destroyAllWindows()
if serial_port:
    serial_port.close()
print("System shutdown complete")