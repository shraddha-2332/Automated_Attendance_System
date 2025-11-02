import cv2
import os
import sqlite3
from deepface import DeepFace
from datetime import datetime

conn = sqlite3.connect('attendance.db')
cursor = conn.cursor()

# Create tables if not exist
cursor.execute('''
CREATE TABLE IF NOT EXISTS students (
    name TEXT PRIMARY KEY,
    embedding TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS attendance (
    name TEXT,
    timestamp TEXT
)
''')

conn.commit()

def capture_faces():
    name = input("Enter student name: ").strip()
    folder_path = f"dataset/{name}"
    os.makedirs(folder_path, exist_ok=True)

    cam = cv2.VideoCapture(0)
    count = 0
    print("\nPress 'c' to capture image, 'q' to quit.\n")

    while True:
        ret, frame = cam.read()
        if not ret:
            break

        cv2.imshow("Capture Face", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('c'):
            img_path = f"{folder_path}/{count}.jpg"
            cv2.imwrite(img_path, frame)
            print(f"Image {count} captured.")
            count += 1

        elif key == ord('q'):
            break

    cam.release()
    cv2.destroyAllWindows()
    print(f"\n{count} images saved for {name}.")


def train_faces():
    dataset_path = "dataset"
    if not os.path.exists(dataset_path):
        print("No dataset folder found.")
        return

    for student in os.listdir(dataset_path):
        folder = os.path.join(dataset_path, student)
        if not os.path.isdir(folder):
            continue

        images = [f for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        if not images:
            print(f"No images found for {student}, skipping.")
            continue

        first_img = os.path.join(folder, images[0])
        try:
            embedding = DeepFace.represent(img_path=first_img, model_name='Facenet')[0]['embedding']
            cursor.execute("INSERT OR REPLACE INTO students VALUES (?, ?)", (student, str(embedding)))
            conn.commit()
            print(f"Stored face data for {student}")
        except Exception as e:
            print(f"Error processing {student}: {e}")

def recognize_faces():
    cam = cv2.VideoCapture(0)
    print("\nPress 'q' to quit camera.\n")

    while True:
        ret, frame = cam.read()
        if not ret:
            break

        try:
            # Compare current frame with database
            result = DeepFace.find(img_path=frame, db_path="dataset", model_name='Facenet', enforce_detection=False)

            if not result.empty:
                name = result.iloc[0]['identity'].split('/')[-2]
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f"{name} Present at {timestamp}")

                cursor.execute("INSERT INTO attendance VALUES (?, ?)", (name, timestamp))
                conn.commit()
        except Exception as e:
            pass

        cv2.imshow("Smart Attendance", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cam.release()
    cv2.destroyAllWindows()


def main():
    while True:
        print("\n===== Smart Attendance System =====")
        print("1. Capture Student Faces")
        print("2. Train Face Data")
        print("3. Start Attendance Recognition")
        print("4. Exit")

        choice = input("Enter your choice: ")

        if choice == '1':
            capture_faces()
        elif choice == '2':
            train_faces()
        elif choice == '3':
            recognize_faces()
        elif choice == '4':
            print("Exiting...")
            break
        else:
            print("Invalid choice! Try again.")

    conn.close()

if __name__ == "__main__":
    main()