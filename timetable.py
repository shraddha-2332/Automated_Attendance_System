import datetime

# Define your timetable
timetable = {
    "Monday": {
        "09": "Math",
        "10": "Physics",
        "11": "AI/ML"
    },
    "Tuesday": {
        "09": "English",
        "10": "Chemistry",
        "11": "AI/ML"
    },
    # Add other days similarly
}

def get_current_subject():
    now = datetime.datetime.now()
    day = now.strftime("%A")
    hour = now.strftime("%H")
    return timetable.get(day, {}).get(hour, "Unknown")