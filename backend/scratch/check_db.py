import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.attendance import Attendance

db = SessionLocal()
try:
    r = db.query(Attendance).filter(Attendance.id == 6).first()
    if r:
        print(f"Record ID: {r.id}")
        print(f"Date: {r.date}")
        print(f"Punch In: {r.punch_in}")
        print(f"Punch Out: {r.punch_out}")
        print(f"Created At: {r.created_at}")
        print(f"Updated At: {r.updated_at}")
        print(f"Is Working: {r.is_working}")
        print(f"Requires Regularization: {r.requires_regularization}")
        print(f"Flags: {r.flags}")
    else:
        print("Record not found")
finally:
    db.close()
