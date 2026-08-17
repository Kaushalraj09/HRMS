from datetime import date, time
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.employee import EmployeeShift
from app.models.master_data import Shift

class ShiftRepository:
    @staticmethod
    def get_assigned_shift(db: Session, employee_id: int, target_date: date) -> Shift:
        """
        Resolve the assigned shift for a given employee on a specific date.
        Checks Employee.shift_id first, then employee_shifts table, then first active shift.
        """
        from app.models.employee import Employee
        emp = db.query(Employee).filter(Employee.id == employee_id).first()
        if emp and emp.shift_id:
            shift = db.query(Shift).filter(Shift.id == emp.shift_id).first()
            if shift:
                return shift

        mapping = (
            db.query(EmployeeShift)
            .filter(
                EmployeeShift.employee_id == employee_id,
                EmployeeShift.effective_from <= target_date,
                or_(
                    EmployeeShift.effective_to.is_(None),
                    EmployeeShift.effective_to >= target_date
                )
            )
            .order_by(EmployeeShift.effective_from.desc())
            .first()
        )
        if mapping:
            shift = db.query(Shift).filter(Shift.id == mapping.shift_id).first()
            if shift:
                return shift
        
        # Fallback 1: Query first active shift
        first_shift = db.query(Shift).filter(Shift.is_active == True).first()
        if first_shift:
            return first_shift
            
        # Fallback 2: Build a default shift object
        default_shift = Shift(
            id=0,
            name="General Shift",
            code="GEN_SHIFT",
            start_time=time(9, 0),
            end_time=time(18, 0),
            working_hours=8.0,
            required_work_minutes=480,
            grace_minutes=15,
            lunch_duration_minutes=60,
            half_day_hours=4.0,
            minimum_half_day_minutes=240,
            present_hours=8.0,
            minimum_present_minutes=480,
            overtime_allowed=True,
            max_overtime_minutes=120,
            timezone="Asia/Kolkata",
            is_active=True
        )
        return default_shift
