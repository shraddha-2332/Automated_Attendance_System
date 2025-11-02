import subprocess
import sys
import os

# --- Step 1: Create virtual environment ---
venv_folder = "venv"

if not os.path.exists(venv_folder):
    print(f"Creating virtual environment '{venv_folder}'...")
    subprocess.check_call([sys.executable, "-m", "venv", venv_folder])
    print("Virtual environment created successfully!")
else:
    print(f"Virtual environment '{venv_folder}' already exists.")

# --- Step 2: Activate instructions ---
print("\n✅ Virtual environment created. Please activate it before installing libraries:")
if os.name == 'nt':  # Windows
    print(f"Windows: {venv_folder}\\Scripts\\activate")
else:  # Linux / Mac
    print(f"Linux/Mac: source {venv_folder}/bin/activate")

# --- Step 3: List of required libraries ---
libraries = {
    "cv2": "opencv-python",
    "deepface": "deepface",
    "flask": "flask",
    "pandas": "pandas",
    "reportlab": "reportlab",
    "mysql.connector": "mysql-connector-python"  # optional, if using MySQL
}

# --- Step 4: Install libraries ---
print("\nInstalling required libraries...")
for module, pip_name in libraries.items():
    try:
        __import__(module)
        print(f"[✅] {module} is already installed")
    except ImportError:
        print(f"[⚠] {module} not found. Installing {pip_name}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])

print("\n🎉 All libraries are installed and ready! Make sure to activate your virtual environment before running project scripts.")