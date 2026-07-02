import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.attendance import Attendance
from app.services.attendance_service import to_attendance_response

db = SessionLocal()
try:
    record = db.query(Attendance).filter(Attendance.id == 6).first()
    if record:
        resp = to_attendance_response(record, db)
        print("API Response for ID 6:")
        print(resp.model_dump())
    else:
        print("Record ID 6 not found!")
finally:
    db.close()
