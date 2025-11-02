import serial
import time
import cv2
import face_recognition
import os
import sqlite3
import datetime

# ---------- CONFIG ----------
SERIAL_PORT = 'COM6'   # ⚠️ Change this based on your Arduino port (e.g., COM4, /dev/ttyUSB0)
BAUD_RATE = 9600

# ---------- DATABASE ----------
def init_db():
    conn = sqlite3.connect("attendance.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    date TEXT,
                    time TEXT
                )""")
    conn.commit()
    conn.close()

def insert_log(name):
    conn = sqlite3.connect("attendance.db")
    c = conn.cursor()
    now = datetime.datetime.now()
    c.execute("INSERT INTO attendance (name, date, time) VALUES (?, ?, ?)",
              (name, now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")))
    conn.commit()
    conn.close()

# ---------- FACE RECOGNITION ----------
known_faces = []
known_names = []

# Load known faces from dataset/
for file in os.listdir("dataset"):
    path = os.path.join("dataset", file)
    image = face_recognition.load_image_file(path)
    encoding = face_recognition.face_encodings(image)[0]
    known_faces.append(encoding)
    known_names.append(file.split(".")[0])

def recognize_face():
    for i in range(4):
        cam = cv2.VideoCapture(i)
        if cam.isOpened():
            print(f"✅ Camera found at index {i}")
            ret, frame = cam.read()
            cam.release()
            if not ret:
                continue
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            encodings = face_recognition.face_encodings(rgb)
            if len(encodings) == 0:
                continue
            matches = face_recognition.compare_faces(known_faces, encodings[0])
            if True in matches:
                return known_names[matches.index(True)]
            return "Unknown"
    return None

# ---------- ARDUINO LISTENER ----------
def listen_arduino():
    print("[INFO] Waiting for sensor trigger...")
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)  # wait for Arduino to reset
    init_db()

    while True:
        data = arduino.readline().decode().strip()
        if "Detected" in data:
            print("[EVENT] Sensor triggered — capturing image...")
            name = recognize_face()
            if name:
                insert_log(name)
                print(f"[+] Attendance logged for: {name}")
            else:
                print("[-] No face detected.")
        time.sleep(1)

if __name__ == "__main__":
    listen_arduino()

