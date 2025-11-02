import face_recognition
import os
import pickle
from pathlib import Path

DATASET_DIR = Path('dataset')
MODELS_DIR = Path('models')
MODELS_DIR.mkdir(exist_ok=True)

known_encodings = []
known_names = []

for person in os.listdir(DATASET_DIR):
    person_dir = DATASET_DIR / person
    if not person_dir.is_dir():
        continue
    for img_name in os.listdir(person_dir):
        img_path = person_dir / img_name
        try:
            image = face_recognition.load_image_file(str(img_path))
            boxes = face_recognition.face_locations(image, model='hog')
            encs = face_recognition.face_encodings(image, boxes)
            if len(encs) > 0:
                known_encodings.append(encs[0])
                known_names.append(person)
                print(f"Encoded {person}/{img_name}")
        except Exception as e:
            print('Skipping', img_path, e)

with open(MODELS_DIR / 'encodings.pkl', 'wb') as f:
    pickle.dump({'encodings': known_encodings, 'names': known_names}, f)

print('Saved encodings:', len(known_names))