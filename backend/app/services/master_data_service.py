from sqlalchemy.orm import Session
from app.models.master_data import Department, Designation, Shift, WorkLocation, LeaveType, Holiday
from app.core.shift_rules import normalize_shift_rule_values
from typing import List, Dict, Any

def _invalidate_cache(db: Session):
    try:
        from app.services.dashboard_service import invalidate_dashboard_cache
        invalidate_dashboard_cache(db)
    except Exception:
        pass

def get_bootstrap_data(db: Session) -> Dict[str, Any]:
    return {
        "departments": db.query(Department).filter(Department.is_active == True).all(),
        "designations": db.query(Designation).filter(Designation.is_active == True).all(),
        "shifts": db.query(Shift).filter(Shift.is_active == True).all(),
        "workLocations": db.query(WorkLocation).filter(WorkLocation.is_active == True).all(),
        "leaveTypes": db.query(LeaveType).filter(LeaveType.is_active == True).all(),
        "holidays": db.query(Holiday).filter(Holiday.is_active == True).order_by(Holiday.holiday_date).all()
    }

# Department CRUD
def list_departments(db: Session, active_only: bool = False) -> List[Department]:
    query = db.query(Department)
    if active_only:
        query = query.filter(Department.is_active == True)
    return query.order_by(Department.name).all()

def create_department(db: Session, payload) -> Department:
    db_dept = Department(
        name=payload.name,
        code=payload.code,
        description=payload.description,
        is_active=payload.is_active
    )
    db.add(db_dept)
    db.commit()
    db.refresh(db_dept)
    _invalidate_cache(db)
    return db_dept

def update_department(db: Session, dept_id: int, payload) -> Department:
    db_dept = db.query(Department).filter(Department.id == dept_id).first()
    if not db_dept:
        return None
    db_dept.name = payload.name
    db_dept.code = payload.code
    db_dept.description = payload.description
    db_dept.is_active = payload.is_active
    db.commit()
    db.refresh(db_dept)
    _invalidate_cache(db)
    return db_dept

def change_department_status(db: Session, dept_id: int, is_active: bool) -> Department:
    db_dept = db.query(Department).filter(Department.id == dept_id).first()
    if not db_dept:
        return None
    db_dept.is_active = is_active
    db.commit()
    db.refresh(db_dept)
    _invalidate_cache(db)
    return db_dept

# Designation CRUD
def list_designations(db: Session, active_only: bool = False) -> List[Designation]:
    query = db.query(Designation)
    if active_only:
        query = query.filter(Designation.is_active == True)
    return query.order_by(Designation.name).all()

def create_designation(db: Session, payload) -> Designation:
    db_designation = Designation(
        name=payload.name,
        code=payload.code,
        description=payload.description,
        is_active=payload.is_active
    )
    db.add(db_designation)
    db.commit()
    db.refresh(db_designation)
    _invalidate_cache(db)
    return db_designation

def update_designation(db: Session, designation_id: int, payload) -> Designation:
    db_designation = db.query(Designation).filter(Designation.id == designation_id).first()
    if not db_designation:
        return None
    db_designation.name = payload.name
    db_designation.code = payload.code
    db_designation.description = payload.description
    db_designation.is_active = payload.is_active
    db.commit()
    db.refresh(db_designation)
    _invalidate_cache(db)
    return db_designation

# Shift CRUD
def list_shifts(db: Session, active_only: bool = False) -> List[Shift]:
    query = db.query(Shift)
    if active_only:
        query = query.filter(Shift.is_active == True)
    return query.order_by(Shift.name).all()

def create_shift(db: Session, payload) -> Shift:
    shift_data = normalize_shift_rule_values(payload.model_dump())
    db_shift = Shift(**shift_data)
    db.add(db_shift)
    db.commit()
    db.refresh(db_shift)
    _invalidate_cache(db)
    return db_shift

def update_shift(db: Session, shift_id: int, payload) -> Shift:
    db_shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not db_shift:
        return None
    updates = normalize_shift_rule_values(payload.model_dump(exclude_unset=True))
    for field, value in updates.items():
        setattr(db_shift, field, value)
    db.commit()
    db.refresh(db_shift)
    _invalidate_cache(db)
    return db_shift

# WorkLocation CRUD
def list_work_locations(db: Session, active_only: bool = False) -> List[WorkLocation]:
    query = db.query(WorkLocation)
    if active_only:
        query = query.filter(WorkLocation.is_active == True)
    return query.order_by(WorkLocation.name).all()

def create_work_location(db: Session, payload) -> WorkLocation:
    db_loc = WorkLocation(
        name=payload.name,
        code=payload.code,
        description=payload.description,
        location_type=getattr(payload, "location_type", "office") or "office",
        latitude=getattr(payload, "latitude", None),
        longitude=getattr(payload, "longitude", None),
        geofence_radius_meters=getattr(payload, "geofence_radius_meters", 40.0) or 40.0,
        is_active=payload.is_active
    )
    db.add(db_loc)
    db.commit()
    db.refresh(db_loc)
    _invalidate_cache(db)
    return db_loc

def update_work_location(db: Session, loc_id: int, payload) -> WorkLocation:
    db_loc = db.query(WorkLocation).filter(WorkLocation.id == loc_id).first()
    if not db_loc:
        return None
    db_loc.name = payload.name
    db_loc.code = payload.code
    db_loc.description = payload.description
    if hasattr(payload, "location_type") and payload.location_type is not None:
        db_loc.location_type = payload.location_type
    if hasattr(payload, "latitude"):
        db_loc.latitude = payload.latitude
    if hasattr(payload, "longitude"):
        db_loc.longitude = payload.longitude
    if hasattr(payload, "geofence_radius_meters") and payload.geofence_radius_meters is not None:
        db_loc.geofence_radius_meters = payload.geofence_radius_meters
    db_loc.is_active = payload.is_active
    db.commit()
    db.refresh(db_loc)
    _invalidate_cache(db)
    return db_loc

# LeaveType CRUD
def list_leave_types(db: Session, active_only: bool = False) -> List[LeaveType]:
    query = db.query(LeaveType)
    if active_only:
        query = query.filter(LeaveType.is_active == True)
    return query.order_by(LeaveType.name).all()

def create_leave_type(db: Session, payload) -> LeaveType:
    db_lt = LeaveType(
        name=payload.name,
        code=payload.code,
        unit_type=payload.unit_type,
        default_balance_hours=payload.default_balance_hours,
        requires_approval=payload.requires_approval,
        applicable_employee_type=getattr(payload, "applicable_employee_type", "all") or "all",
        carry_forward=getattr(payload, "carry_forward", False) or False,
        max_consecutive_days=getattr(payload, "max_consecutive_days", None),
        counts_as_leave=getattr(payload, "counts_as_leave", True) if getattr(payload, "counts_as_leave", None) is not None else True,
        attendance_required=getattr(payload, "attendance_required", False) or False,
        remote_punch_allowed=getattr(payload, "remote_punch_allowed", False) or False,
        is_active=payload.is_active
    )
    db.add(db_lt)
    db.commit()
    db.refresh(db_lt)
    _invalidate_cache(db)
    return db_lt

def update_leave_type(db: Session, lt_id: int, payload) -> LeaveType:
    db_lt = db.query(LeaveType).filter(LeaveType.id == lt_id).first()
    if not db_lt:
        return None
    db_lt.name = payload.name
    db_lt.code = payload.code
    db_lt.unit_type = payload.unit_type
    db_lt.default_balance_hours = payload.default_balance_hours
    db_lt.requires_approval = payload.requires_approval
    if hasattr(payload, "applicable_employee_type") and payload.applicable_employee_type is not None:
        db_lt.applicable_employee_type = payload.applicable_employee_type
    if hasattr(payload, "carry_forward") and payload.carry_forward is not None:
        db_lt.carry_forward = payload.carry_forward
    if hasattr(payload, "max_consecutive_days"):
        db_lt.max_consecutive_days = payload.max_consecutive_days
    if hasattr(payload, "counts_as_leave") and payload.counts_as_leave is not None:
        db_lt.counts_as_leave = payload.counts_as_leave
    if hasattr(payload, "attendance_required") and payload.attendance_required is not None:
        db_lt.attendance_required = payload.attendance_required
    if hasattr(payload, "remote_punch_allowed") and payload.remote_punch_allowed is not None:
        db_lt.remote_punch_allowed = payload.remote_punch_allowed
    db_lt.is_active = payload.is_active
    db.commit()
    db.refresh(db_lt)
    _invalidate_cache(db)
    return db_lt

# Holiday CRUD
def list_holidays(db: Session, active_only: bool = False) -> List[Holiday]:
    query = db.query(Holiday)
    if active_only:
        query = query.filter(Holiday.is_active == True)
    return query.order_by(Holiday.holiday_date).all()

def create_holiday(db: Session, payload) -> Holiday:
    db_holiday = Holiday(
        holiday_date=payload.holiday_date,
        name=payload.name,
        description=payload.description,
        is_optional=payload.is_optional,
        is_active=payload.is_active
    )
    db.add(db_holiday)
    db.commit()
    db.refresh(db_holiday)
    _invalidate_cache(db)
    return db_holiday

def update_holiday(db: Session, h_id: int, payload) -> Holiday:
    db_holiday = db.query(Holiday).filter(Holiday.id == h_id).first()
    if not db_holiday:
        return None
    db_holiday.holiday_date = payload.holiday_date
    db_holiday.name = payload.name
    db_holiday.description = payload.description
    db_holiday.is_optional = payload.is_optional
    db_holiday.is_active = payload.is_active
    db.commit()
    db.refresh(db_holiday)
    _invalidate_cache(db)
    return db_holiday


# Delete Operations
def delete_department(db: Session, dept_id: int) -> bool:
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        return False
    from app.models.employee import Employee
    assigned_count = db.query(Employee).filter(
        (Employee.department == dept.name) | (Employee.department == dept.code)
    ).count()
    if assigned_count > 0:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete department '{dept.name}' as it is currently assigned to {assigned_count} employee(s). Please reassign them first."
        )
    db.delete(dept)
    db.commit()
    _invalidate_cache(db)
    return True


def delete_designation(db: Session, designation_id: int) -> bool:
    desig = db.query(Designation).filter(Designation.id == designation_id).first()
    if not desig:
        return False
    from app.models.employee import Employee
    assigned_count = db.query(Employee).filter(
        (Employee.designation == desig.name) | (Employee.designation == desig.code)
    ).count()
    if assigned_count > 0:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete designation '{desig.name}' as it is currently assigned to {assigned_count} employee(s). Please reassign them first."
        )
    db.delete(desig)
    db.commit()
    _invalidate_cache(db)
    return True


def delete_shift(db: Session, shift_id: int) -> bool:
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not shift:
        return False
    from app.models.employee import Employee, EmployeeShift
    assigned_emp_count = db.query(Employee).filter(Employee.shift_id == shift_id).count()
    assigned_shift_count = db.query(EmployeeShift).filter(EmployeeShift.shift_id == shift_id).count()
    total_assigned = assigned_emp_count + assigned_shift_count
    if total_assigned > 0:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete shift '{shift.name}' as it is currently assigned to active employee shift schedules. Please reassign them first."
        )
    db.delete(shift)
    db.commit()
    _invalidate_cache(db)
    return True


def delete_work_location(db: Session, loc_id: int) -> bool:
    loc = db.query(WorkLocation).filter(WorkLocation.id == loc_id).first()
    if not loc:
        return False
    from app.models.employee import Employee
    assigned_count = db.query(Employee).filter(
        (Employee.work_location == loc.name) | (Employee.work_location == loc.code)
    ).count()
    if assigned_count > 0:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete location '{loc.name}' as it is currently assigned to {assigned_count} employee(s). Please reassign them first."
        )
    db.delete(loc)
    db.commit()
    _invalidate_cache(db)
    return True


def delete_leave_type(db: Session, lt_id: int) -> bool:
    lt = db.query(LeaveType).filter(LeaveType.id == lt_id).first()
    if not lt:
        return False
    from app.models.timeoff import TimeOffRequest
    req_count = db.query(TimeOffRequest).filter(
        (TimeOffRequest.leave_type == lt.name) | (TimeOffRequest.leave_type == lt.code)
    ).count()
    if req_count > 0:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete leave type '{lt.name}' as there are {req_count} time-off request(s) associated with it."
        )
    db.delete(lt)
    db.commit()
    _invalidate_cache(db)
    return True


def delete_holiday(db: Session, h_id: int) -> bool:
    h = db.query(Holiday).filter(Holiday.id == h_id).first()
    if not h:
        return False
    db.delete(h)
    db.commit()
    _invalidate_cache(db)
    return True

