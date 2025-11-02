import time
from datetime import datetime

# Threshold for marking present (percentage of session duration)
PRESENCE_THRESHOLD = 0.6  # 60% default

def secs_between(t1, t2):
    fmt = '%Y-%m-%d %H:%M:%S'
    try:
        dt1 = datetime.strptime(t1, fmt)
        dt2 = datetime.strptime(t2, fmt)
        return int((dt2 - dt1).total_seconds())
    except Exception:
        return 0