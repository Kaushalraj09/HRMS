import calendar
import math
from datetime import date, datetime, timedelta, time
from zoneinfo import ZoneInfo
from fastapi import HTTPException, status
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.user import User
from app.models.attendance import Attendance
from app.models.timeoff import TimeOffRequest
from app.models.approval_task import ApprovalTask
from app.models.approval_log import ApprovalLog
from app.services import attendance_service, approval_service

APP_TIMEZONE = ZoneInfo("Asia/Kolkata")


def enrich_timeoff_with_manager_info(db: Session, req: TimeOffRequest) -> TimeOffRequest:
    """Enrich a TimeOffRequest with manager and HR review metadata for UI display."""
    if req.employee:
        req.employee_name = f"{req.employee.first_name} {req.employee.last_name}".strip()
        req.employee_code = req.employee.employee_code
        if req.employee.reporting_manager:
            req.manager_name = f"{req.employee.reporting_manager.first_name} {req.employee.reporting_manager.last_name}".strip()

    task = db.query(ApprovalTask).filter(
        ApprovalTask.request_type == "timeoff",
        ApprovalTask.request_id == req.id
    ).first()

    if task:
        if task.manager_reviewed_by:
            if not getattr(req, "manager_name", None):
                mgr_user = db.query(User).filter(User.id == task.manager_reviewed_by).first()
                if mgr_user:
                    req.manager_name = mgr_user.display_name
            req.manager_comment = task.manager_decision_comment
            req.manager_reviewed_at = task.manager_reviewed_at
            if task.assigned_role == "hr" or (task.status == "approved" and task.reviewed_at):
                req.manager_decision = "Approved"
            elif task.status == "rejected" and task.reviewed_by == task.manager_reviewed_by:
                req.manager_decision = "Rejected"
            else:
                req.manager_decision = "Approved" if req.approval_stage == "HR" else "Pending"
        else:
            req.manager_decision = "Pending" if (req.employee and req.employee.reporting_manager_id) else None

        if task.reviewed_by and task.assigned_role != "manager":
            req.hr_reviewed_at = task.reviewed_at
            req.hr_comment = task.decision_comment

    return req


def get_manager_dashboard_stats(db: Session, manager_employee: Employee | None, is_admin: bool = False) -> dict:
    today = datetime.now(APP_TIMEZONE).date()

    # Base query for all employees assigned to this manager
    if manager_employee:
        assigned_team = db.query(Employee).filter(
            Employee.reporting_manager_id == manager_employee.id,
            Employee.status == "Active"
        ).all()
    else:
        assigned_team = []

    assigned_ids = [e.id for e in assigned_team]

    # If admin and has no direct reports assigned, show active employees so dashboard reflects real data
    if len(assigned_ids) == 0 and is_admin:
        admin_id = manager_employee.id if manager_employee else None
        assigned_team = db.query(Employee).filter(
            Employee.id != admin_id if admin_id else True,
            Employee.status == "Active"
        ).all()
        assigned_ids = [e.id for e in assigned_team]

    total_employees = len(assigned_ids)

    if total_employees == 0:
        return {
            "totalEmployees": 0,
            "presentToday": 0,
            "absentToday": 0,
            "onLeaveToday": 0,
            "lateToday": 0,
            "currentlyWorking": 0,
            "pendingApprovals": 0,
            "teamOverview": []
        }

    # 1. Today's attendance records for the team
    attendance_records = db.query(Attendance).filter(
        Attendance.employee_id.in_(assigned_ids),
        Attendance.date == today
    ).all()

    att_map = {att.employee_id: att for att in attendance_records}

    # 2. Approved leaves for today
    on_leave_requests = db.query(TimeOffRequest).filter(
        TimeOffRequest.employee_id.in_(assigned_ids),
        or_(
            TimeOffRequest.date == today,
            and_(TimeOffRequest.start_date <= today, TimeOffRequest.end_date >= today)
        ),
        TimeOffRequest.status.in_(["Approved", "Active", "approved", "active"])
    ).all()
    leave_emp_ids = {lr.employee_id for lr in on_leave_requests}

    present_count = 0
    currently_working_count = 0
    late_count = 0
    absent_count = 0

    team_overview = []
    for emp in assigned_team:
        att = att_map.get(emp.id)
        is_on_leave = emp.id in leave_emp_ids
        emp_status = "Absent"

        if att:
            raw_st = (att.status or "").upper()
            if "LATE" in raw_st or (att.late_minutes and att.late_minutes > 0):
                late_count += 1
                present_count += 1
                emp_status = "Late"
            elif "PRESENT" in raw_st or "WORKING" in raw_st:
                present_count += 1
                emp_status = "Present"
            elif "HALF" in raw_st:
                present_count += 1
                emp_status = "Half-Day"
            elif "LEAVE" in raw_st:
                emp_status = "On Leave"
            elif "ABSENT" in raw_st:
                absent_count += 1
                emp_status = "Absent"
            elif att.punch_in:
                present_count += 1
                emp_status = "Present"
            else:
                absent_count += 1
                emp_status = "Absent"

            if att.punch_in and not att.punch_out:
                currently_working_count += 1
                if emp_status == "Present":
                    emp_status = "Working"
        elif is_on_leave:
            emp_status = "On Leave"
        else:
            absent_count += 1

        team_overview.append({
            "employeeId": emp.id,
            "employeeCode": emp.employee_code,
            "name": f"{emp.first_name} {emp.last_name}".strip(),
            "department": emp.department or "N/A",
            "designation": emp.designation or "N/A",
            "status": emp_status,
            "punchIn": att.punch_in.strftime("%I:%M %p") if att and att.punch_in else None,
            "punchOut": att.punch_out.strftime("%I:%M %p") if att and att.punch_out else None,
        })

    # 3. Pending approvals for this manager
    if manager_employee:
        pending_tasks = db.query(ApprovalTask).join(Employee, ApprovalTask.employee_id == Employee.id).outerjoin(
            TimeOffRequest,
            and_(ApprovalTask.request_id == TimeOffRequest.id, ApprovalTask.request_type == "timeoff")
        ).filter(
            ApprovalTask.assigned_role == "manager",
            ApprovalTask.status == "pending",
            Employee.reporting_manager_id == manager_employee.id,
            or_(
                ApprovalTask.request_type != "timeoff",
                TimeOffRequest.status.ilike("pending")
            )
        ).count()
    else:
        pending_tasks = 0

    if pending_tasks == 0 and is_admin:
        pending_tasks = db.query(ApprovalTask).outerjoin(
            TimeOffRequest,
            and_(ApprovalTask.request_id == TimeOffRequest.id, ApprovalTask.request_type == "timeoff")
        ).filter(
            ApprovalTask.status == "pending",
            or_(
                ApprovalTask.request_type != "timeoff",
                TimeOffRequest.status.ilike("pending")
            )
        ).count()

    return {
        "totalEmployees": total_employees,
        "presentToday": present_count,
        "absentToday": absent_count,
        "onLeaveToday": len(leave_emp_ids),
        "lateToday": late_count,
        "currentlyWorking": currently_working_count,
        "pendingApprovals": pending_tasks,
        "teamOverview": team_overview[:10]
    }


def get_manager_team_employees(
    db: Session,
    manager_employee: Employee | None,
    page: int = 1,
    limit: int = 10,
    search: str = "",
    is_admin: bool = False
) -> dict:
    if manager_employee:
        query = db.query(Employee).filter(
            Employee.reporting_manager_id == manager_employee.id,
            Employee.status != "Deleted"
        )
    else:
        query = db.query(Employee).filter(Employee.status != "Deleted")

    if is_admin and (not manager_employee or query.count() == 0):
        admin_id = manager_employee.id if manager_employee else None
        query = db.query(Employee).filter(
            Employee.id != admin_id if admin_id else True,
            Employee.status != "Deleted"
        )

    if search and search.strip():
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Employee.first_name.ilike(s),
                Employee.last_name.ilike(s),
                Employee.employee_code.ilike(s),
                Employee.official_email.ilike(s),
                Employee.department.ilike(s),
                Employee.designation.ilike(s)
            )
        )

    total_items = query.count()
    total_pages = math.ceil(total_items / limit) if total_items > 0 else 0
    offset = (page - 1) * limit
    employees = query.order_by(Employee.first_name, Employee.last_name).offset(offset).limit(limit).all()

    return {
        "data": employees,
        "total": total_items,
        "page": page,
        "limit": limit,
        "totalPages": total_pages
    }


def get_manager_team_attendance(
    db: Session,
    manager_employee: Employee | None,
    page: int = 1,
    limit: int = 10,
    from_date: date | None = None,
    to_date: date | None = None,
    employee_id: int | None = None,
    status_filter: str = "",
    search: str = "",
    is_admin: bool = False
) -> dict:
    if manager_employee:
        query = (
            db.query(Attendance)
            .join(Employee, Attendance.employee_id == Employee.id)
            .filter(Employee.reporting_manager_id == manager_employee.id)
        )
    else:
        query = db.query(Attendance).join(Employee, Attendance.employee_id == Employee.id)

    if is_admin and (not manager_employee or query.count() == 0):
        admin_id = manager_employee.id if manager_employee else None
        query = (
            db.query(Attendance)
            .join(Employee, Attendance.employee_id == Employee.id)
            .filter(Employee.id != admin_id if admin_id else True)
        )

    if employee_id:
        # Strictly verify employee reports to this manager
        query = query.filter(Attendance.employee_id == employee_id)

    if from_date:
        query = query.filter(Attendance.date >= from_date)
    if to_date:
        query = query.filter(Attendance.date <= to_date)
    if status_filter and status_filter.strip():
        query = query.filter(Attendance.status.ilike(status_filter.strip()))

    if search and search.strip():
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Employee.first_name.ilike(s),
                Employee.last_name.ilike(s),
                Employee.employee_code.ilike(s),
                Attendance.status.ilike(s)
            )
        )

    total_items = query.count()
    total_pages = math.ceil(total_items / limit) if total_items > 0 else 0
    offset = (page - 1) * limit
    results = query.order_by(Attendance.date.desc(), Attendance.id.desc()).offset(offset).limit(limit).all()

    items = [attendance_service.to_attendance_response(r, db) for r in results]

    return {
        "items": items,
        "total": total_items,
        "page": page,
        "limit": limit,
        "totalPages": total_pages
    }


def get_manager_leave_requests(
    db: Session,
    manager_employee: Employee | None,
    status_filter: str = "",
    page: int = 1,
    limit: int = 10,
    is_admin: bool = False
) -> dict:
    if manager_employee:
        query = (
            db.query(TimeOffRequest)
            .join(Employee, TimeOffRequest.employee_id == Employee.id)
            .filter(Employee.reporting_manager_id == manager_employee.id)
        )
    else:
        query = db.query(TimeOffRequest).join(Employee, TimeOffRequest.employee_id == Employee.id)

    if is_admin and (not manager_employee or query.count() == 0):
        query = db.query(TimeOffRequest).join(Employee, TimeOffRequest.employee_id == Employee.id)

    if status_filter:
        sf = status_filter.lower().strip()
        if sf == "pending":
            # Pending manager approval
            query = query.filter(
                TimeOffRequest.status == "Pending",
                TimeOffRequest.approval_stage == "Manager"
            )
        elif sf == "approved":
            # Manager approved (may be pending HR or fully approved)
            query = query.filter(
                or_(
                    TimeOffRequest.approval_stage == "HR",
                    TimeOffRequest.status == "Approved"
                )
            )
        elif sf == "rejected":
            query = query.filter(TimeOffRequest.status == "Rejected")

    total_items = query.count()
    total_pages = math.ceil(total_items / limit) if total_items > 0 else 0
    offset = (page - 1) * limit
    requests = query.order_by(TimeOffRequest.created_at.desc()).offset(offset).limit(limit).all()

    items = [enrich_timeoff_with_manager_info(db, r) for r in requests]

    return {
        "items": items,
        "page": page,
        "pageSize": limit,
        "totalItems": total_items,
        "totalPages": total_pages
    }


def decide_leave_request(
    db: Session,
    manager_user: User,
    manager_employee: Employee,
    request_id: int,
    decision: str,
    comment: str = None
) -> dict:
    # 1. Fetch timeoff request
    req = db.query(TimeOffRequest).filter(TimeOffRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")

    # 2. Strict backend verification: Employee must be assigned to this manager
    if not req.employee or req.employee.reporting_manager_id != manager_employee.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to decide leave requests for this employee."
        )

    # 3. Find matching approval task
    task = db.query(ApprovalTask).filter(
        ApprovalTask.request_type == "timeoff",
        ApprovalTask.request_id == request_id,
        ApprovalTask.status == "pending"
    ).first()

    if not task:
        raise HTTPException(
            status_code=400,
            detail="No pending approval task found for this leave request."
        )

    if task.assigned_role != "manager":
        raise HTTPException(
            status_code=400,
            detail="This request is currently not at the Manager approval stage."
        )

    # 4. Use approval_service to make decision
    result_task = approval_service.decide_task(
        db=db,
        task_id=task.id,
        reviewer_id=manager_user.id,
        decision=decision.lower(),
        comment=comment
    )

    db.refresh(req)
    enrich_timeoff_with_manager_info(db, req)

    return {
        "success": True,
        "message": f"Leave request {decision.lower()} successfully by Manager.",
        "request": req
    }


def get_manager_attendance_trend(
    db: Session,
    manager_employee: Employee | None,
    period: str = "This Month",
    is_admin: bool = False
) -> dict:
    today = datetime.now(APP_TIMEZONE).date()

    if manager_employee:
        assigned_team = db.query(Employee).filter(
            Employee.reporting_manager_id == manager_employee.id,
            Employee.status == "Active"
        ).all()
    else:
        assigned_team = []

    assigned_ids = [e.id for e in assigned_team]

    if len(assigned_ids) == 0 and is_admin:
        admin_id = manager_employee.id if manager_employee else None
        assigned_team = db.query(Employee).filter(
            Employee.id != admin_id if admin_id else True,
            Employee.status == "Active"
        ).all()
        assigned_ids = [e.id for e in assigned_team]

    total_team = len(assigned_ids)

    # Determine date checkpoints
    checkpoints: list[date] = []
    clean_period = (period or "this month").strip().lower()

    if clean_period == "today":
        hour_checkpoints = [
            (time(9, 0), "9 AM"),
            (time(11, 0), "11 AM"),
            (time(13, 0), "1 PM"),
            (time(15, 0), "3 PM"),
            (time(17, 0), "5 PM"),
            (time(19, 0), "7 PM")
        ]
        labels: list[str] = [lbl for _, lbl in hour_checkpoints]
        present_data: list[float] = []
        leave_data: list[float] = []
        absent_data: list[float] = []

        if total_team == 0:
            return {
                "period": period,
                "labels": labels,
                "present": [0.0] * len(labels),
                "leave": [0.0] * len(labels),
                "absent": [0.0] * len(labels)
            }

        att_rows = db.query(Attendance).filter(
            Attendance.employee_id.in_(assigned_ids),
            Attendance.date == today
        ).all()

        leave_count = db.query(TimeOffRequest).filter(
            TimeOffRequest.employee_id.in_(assigned_ids),
            TimeOffRequest.date == today,
            TimeOffRequest.status.in_(["Approved", "Active"])
        ).count()

        now_time = datetime.now(APP_TIMEZONE).time()

        for slot_time, _ in hour_checkpoints:
            present_count = 0
            for att in att_rows:
                if att.punch_in:
                    if att.punch_in <= slot_time or now_time >= slot_time:
                        present_count += 1
                elif att.status in ["Present", "Working", "Late", "Half Day", "Half-Day"]:
                    if now_time >= slot_time:
                        present_count += 1

            if now_time < slot_time and present_count == 0 and not any(a.punch_in for a in att_rows):
                present_data.append(0.0)
                leave_data.append(0.0)
                absent_data.append(0.0)
                continue

            present_pct = round((present_count / total_team) * 100, 1)
            leave_pct = round((min(leave_count, total_team - present_count) / total_team) * 100, 1)
            absent_pct = round(max(0.0, 100.0 - present_pct - leave_pct), 1)

            present_data.append(present_pct)
            leave_data.append(leave_pct)
            absent_data.append(absent_pct)

        return {
            "period": period,
            "labels": labels,
            "present": present_data,
            "leave": leave_data,
            "absent": absent_data
        }

    elif clean_period == "last month":
        first_of_this_month = today.replace(day=1)
        last_of_last_month = first_of_this_month - timedelta(days=1)
        year = last_of_last_month.year
        month = last_of_last_month.month
        _, num_days = calendar.monthrange(year, month)
        raw_days = [1, 5, 10, 15, 20, 25, num_days]
        checkpoints = [date(year, month, min(d, num_days)) for d in raw_days]
    elif clean_period == "last 30 days":
        checkpoints = [today - timedelta(days=offset) for offset in [30, 25, 20, 15, 10, 5, 0]]
    else:  # "this month"
        year = today.year
        month = today.month
        _, num_days = calendar.monthrange(year, month)
        raw_days = [1, 5, 10, 15, 20, 25, num_days]
        checkpoints = [date(year, month, min(d, num_days)) for d in raw_days]

    labels: list[str] = []
    present_data: list[float] = []
    leave_data: list[float] = []
    absent_data: list[float] = []

    if total_team == 0:
        for cp in checkpoints:
            labels.append(cp.strftime("%d %b").lstrip("0"))
            present_data.append(0.0)
            leave_data.append(0.0)
            absent_data.append(0.0)
        return {
            "period": period,
            "labels": labels,
            "present": present_data,
            "leave": leave_data,
            "absent": absent_data
        }

    for cp in checkpoints:
        lbl = cp.strftime("%d %b").lstrip("0")
        labels.append(lbl)

        # If date is in the future relative to today
        if cp > today:
            present_data.append(0.0)
            leave_data.append(0.0)
            absent_data.append(0.0)
            continue

        # Query attendance on checkpoint date
        att_rows = db.query(Attendance).filter(
            Attendance.employee_id.in_(assigned_ids),
            Attendance.date == cp
        ).all()

        leave_count = db.query(TimeOffRequest).filter(
            TimeOffRequest.employee_id.in_(assigned_ids),
            TimeOffRequest.date == cp,
            TimeOffRequest.status.in_(["Approved", "Active"])
        ).count()

        present_count = 0
        for att in att_rows:
            if att.status in ["Present", "Working", "Late", "Half Day", "Half-Day"] or (att.punch_in is not None):
                present_count += 1
            elif att.status in ["Leave", "On Leave"]:
                leave_count += 1

        # Check weekend fallback if no punches and no leaves recorded
        if cp.weekday() == 6 and present_count == 0 and leave_count == 0:
            friday = cp - timedelta(days=2)
            fri_att = db.query(Attendance).filter(
                Attendance.employee_id.in_(assigned_ids),
                Attendance.date == friday
            ).all()
            if fri_att:
                present_count = sum(
                    1 for a in fri_att
                    if a.status in ["Present", "Working", "Late", "Half Day", "Half-Day"] or a.punch_in is not None
                )
                leave_count = db.query(TimeOffRequest).filter(
                    TimeOffRequest.employee_id.in_(assigned_ids),
                    TimeOffRequest.date == friday,
                    TimeOffRequest.status.in_(["Approved", "Active"])
                ).count()

        present_pct = round((present_count / total_team) * 100, 1)
        leave_pct = round((min(leave_count, total_team - present_count) / total_team) * 100, 1)
        absent_pct = round(max(0.0, 100.0 - present_pct - leave_pct), 1)

        present_data.append(present_pct)
        leave_data.append(leave_pct)
        absent_data.append(absent_pct)

    return {
        "period": period,
        "labels": labels,
        "present": present_data,
        "leave": leave_data,
        "absent": absent_data
    }

