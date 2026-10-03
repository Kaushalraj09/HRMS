import pytest
from datetime import date
from app.core.database import SessionLocal
from app.models.employee import Employee
from app.models.attendance import Attendance
from app.services.manager_service import get_manager_team_attendance

def test_manager_team_attendance_status_filter_and_dates():
    db = SessionLocal()
    try:
        # Manager 2 has direct reports (e.g. employee 20, 26)
        mgr = db.query(Employee).filter(Employee.id == 2).first()
        if not mgr:
            pytest.skip("Manager 2 not found in seed db")

        # 1. Total records for today without filter includes unpunched team members
        res_all = get_manager_team_attendance(db, mgr)
        assert res_all["total"] > 0

        # 2. Resilient status filter matches NOT MARKED for today when unpunched
        res_unpunched = get_manager_team_attendance(db, mgr, status_filter="Not Marked")
        assert res_unpunched["total"] >= 1
        for item in res_unpunched["items"]:
            assert item.status.upper() in ("NOT MARKED", "ABSENT")
            assert item.employee_name is not None
            assert item.employee_code is not None
    finally:
        db.close()

