import calendar
import math
from typing import Optional, List, Dict, Any, Union
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
            emp_status = "Not Marked"

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
        sf = status_filter.strip()
        patterns = [sf, sf.replace(" ", "_"), sf.replace("_", " ")]
        if sf.lower() in ["on leave", "leave"]:
            patterns.extend(["LEAVE", "On Leave", "leave"])
        elif sf.lower() in ["half day", "half_day"]:
            patterns.extend(["HALF_DAY", "Half Day", "half_day"])
        query = query.filter(or_(*[Attendance.status.ilike(p) for p in set(patterns)]))

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

    today_dt = date.today()
    include_today_unmarked = (
        (from_date is None or from_date <= today_dt) and
        (to_date is None or to_date >= today_dt)
    )

    unmarked_items = []
    if include_today_unmarked:
        if manager_employee:
            team_candidates = db.query(Employee).filter(
                Employee.reporting_manager_id == manager_employee.id,
                Employee.status != "Deleted"
            ).all()
        else:
            team_candidates = db.query(Employee).filter(Employee.status != "Deleted").all()

        if is_admin and (not manager_employee or len(team_candidates) == 0):
            admin_id = manager_employee.id if manager_employee else None
            team_candidates = db.query(Employee).filter(
                Employee.id != admin_id if admin_id else True,
                Employee.status != "Deleted"
            ).all()

        if employee_id:
            team_candidates = [e for e in team_candidates if e.id == employee_id]

        if team_candidates:
            cand_ids = [e.id for e in team_candidates]
            existing_today_ids = {
                r[0] for r in db.query(Attendance.employee_id).filter(
                    Attendance.date == today_dt,
                    Attendance.employee_id.in_(cand_ids)
                ).all()
            }

            from app.schemas.attendance import WorkMode, AttendanceResponse
            for emp in team_candidates:
                if emp.id not in existing_today_ids:
                    on_leave = db.query(TimeOffRequest).filter(
                        TimeOffRequest.employee_id == emp.id,
                        or_(
                            TimeOffRequest.date == today_dt,
                            and_(TimeOffRequest.start_date <= today_dt, TimeOffRequest.end_date >= today_dt)
                        ),
                        TimeOffRequest.status.in_(["Approved", "Active", "approved", "active"])
                    ).first()
                    live_status = "On Leave" if on_leave else "Not Marked"

                    sf = (status_filter or "").strip().lower()
                    status_match = True
                    if sf:
                        if sf in ["on leave", "leave"]:
                            status_match = (live_status == "On Leave")
                        elif sf in ["absent", "not marked", "not_marked"]:
                            status_match = (live_status == "Not Marked")
                        else:
                            status_match = False

                    search_match = True
                    if search and search.strip():
                        s_term = search.strip().lower()
                        emp_full = f"{emp.first_name} {emp.last_name}".lower()
                        emp_cd = (emp.employee_code or "").lower()
                        status_str = live_status.lower()
                        search_match = (s_term in emp_full or s_term in emp_cd or s_term in status_str)

                    if status_match and search_match:
                        unmarked_items.append(
                            AttendanceResponse(
                                id=0,
                                employee_id=emp.id,
                                shift_id=None,
                                employee=f"{emp.first_name} {emp.last_name}".strip(),
                                employee_name=f"{emp.first_name} {emp.last_name}".strip(),
                                employee_code=emp.employee_code or f"EMP-{str(emp.id).zfill(4)}",
                                department=emp.department,
                                designation=emp.designation,
                                total_working_hours="—",
                                shift=None,
                                date=today_dt,
                                scheduled_start=None,
                                scheduled_end=None,
                                task_description=None,
                                punch_in=None,
                                punch_out=None,
                                status=live_status,
                                work_mode=WorkMode.office,
                                late_minutes=0
                            )
                        )

    db_items = [attendance_service.to_attendance_response(r, db) for r in query.order_by(Attendance.date.desc(), Attendance.id.desc()).all()]
    all_combined = unmarked_items + db_items
    all_combined.sort(key=lambda x: (x.date, x.id), reverse=True)

    total_items = len(all_combined)
    total_pages = math.ceil(total_items / limit) if total_items > 0 else 0
    offset = (page - 1) * limit
    paged_items = all_combined[offset : offset + limit]

    return {
        "items": paged_items,
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


async def send_team_attendance_reminders(
    db: Session,
    manager_user: User,
    manager_employee: Optional[Employee],
    is_admin: bool = False
) -> dict:
    from app.services import notification_service
    from app.models.attendance import Attendance
    from app.models.timeoff import TimeOffRequest
    from datetime import date
    from sqlalchemy import or_, and_

    today = date.today()
    if manager_employee:
        team_members = db.query(Employee).filter(
            Employee.reporting_manager_id == manager_employee.id,
            Employee.status == "Active"
        ).all()
        mgr_name = f"{manager_employee.first_name} {manager_employee.last_name}".strip()
    elif is_admin:
        team_members = db.query(Employee).filter(
            Employee.user_id != manager_user.id,
            Employee.status == "Active"
        ).all()
        mgr_name = "Management"
    else:
        team_members = []
        mgr_name = "Manager"

    if not team_members:
        return {
            "success": True,
            "count": 0,
            "recipients": [],
            "message": "No active team members found to send reminders to."
        }

    # Find who has already punched in today
    team_ids = [e.id for e in team_members]
    existing_punches = db.query(Attendance.employee_id).filter(
        Attendance.employee_id.in_(team_ids),
        Attendance.date == today,
        Attendance.punch_in.isnot(None)
    ).all()
    punched_in_ids = {p[0] for p in existing_punches}

    # Also check who is on approved leave today
    on_leave = db.query(TimeOffRequest.employee_id).filter(
        TimeOffRequest.employee_id.in_(team_ids),
        or_(
            TimeOffRequest.date == today,
            and_(TimeOffRequest.start_date <= today, TimeOffRequest.end_date >= today)
        ),
        TimeOffRequest.status.in_(["Approved", "Active", "approved", "active"])
    ).all()
    leave_ids = {l[0] for l in on_leave}

    reminded_names = []
    for emp in team_members:
        # Only remind employees who haven't punched in and aren't on leave
        if emp.id in punched_in_ids:
            continue
        if emp.id in leave_ids:
            continue
        if not emp.user_id:
            continue

        emp_full_name = f"{emp.first_name} {emp.last_name}".strip()
        await notification_service.create_notification(
            db=db,
            user_id=emp.user_id,
            type="ATTENDANCE",
            title="Punch In Reminder",
            message=f"Reminder from your manager {mgr_name}: Please remember to clock in for your shift today.",
            category="PUNCH_IN_REMINDER",
            severity="WARNING",
            employee_id=emp.id,
            created_by=manager_user.id,
            receiver_role="employee",
            notification_metadata={
                "manager_id": manager_employee.id if manager_employee else None,
                "manager_name": mgr_name,
                "reminder_type": "PUNCH_IN",
                "date": today.isoformat()
            }
        )
        reminded_names.append(emp_full_name)

    if reminded_names:
        names_str = ", ".join(reminded_names)
        msg = f"Punch-in reminder sent to {len(reminded_names)} team member(s): {names_str}."
    else:
        msg = "All team members have already clocked in or are on approved leave today."

    return {
        "success": True,
        "count": len(reminded_names),
        "recipients": reminded_names,
        "message": msg
    }


def get_manager_team_performance(
    db: Session,
    manager_employee: Optional[Employee],
    is_admin: bool = False
) -> list[dict]:
    from app.models.attendance import Attendance
    from app.models.training import TrainingAssignment
    from datetime import date, timedelta

    if manager_employee:
        team_members = db.query(Employee).filter(
            Employee.reporting_manager_id == manager_employee.id,
            Employee.status == "Active"
        ).all()
    elif is_admin:
        team_members = db.query(Employee).filter(
            Employee.status == "Active"
        ).all()
    else:
        team_members = []

    today = date.today()
    month_start = today.replace(day=1)
    
    # Calculate working days so far this month (excluding Sundays)
    days_in_range = (today - month_start).days + 1
    working_days = sum(1 for i in range(days_in_range) if (month_start + timedelta(days=i)).weekday() != 6)
    working_days = max(working_days, 1)

    result = []
    for emp in team_members:
        full_name = f"{emp.first_name} {emp.last_name}".strip()
        
        # 1. Real Attendance Rate
        att_records = db.query(Attendance).filter(
            Attendance.employee_id == emp.id,
            Attendance.date >= month_start,
            Attendance.date <= today
        ).all()
        
        present_count = sum(1 for a in att_records if a.status in ["Present", "Working", "Late", "Half Day", "Half-Day"] or a.punch_in is not None)
        late_count = sum(1 for a in att_records if (a.late_minutes and a.late_minutes > 0) or (a.status and "LATE" in a.status.upper()))
        
        if len(att_records) == 0:
            att_pct_str = "—"
            att_score = 100.0
            punctuality_pct_str = "—"
            punctuality_score = 100.0
        else:
            att_pct = round((present_count / max(working_days, len(att_records))) * 100, 1)
            att_pct = min(att_pct, 100.0)
            att_pct_str = f"{att_pct:.0f}%"
            att_score = att_pct
            
            if present_count > 0:
                on_time = max(0, present_count - late_count)
                punc_pct = round((on_time / present_count) * 100, 1)
                punctuality_pct_str = f"{punc_pct:.0f}%"
                punctuality_score = punc_pct
            else:
                punctuality_pct_str = "—"
                punctuality_score = 0.0

        # 2. Real Training Compliance
        trainings = db.query(TrainingAssignment).filter(
            TrainingAssignment.employee_id == emp.id
        ).all()
        
        if len(trainings) == 0:
            training_pct_str = "100%"
            training_score = 100.0
        else:
            completed_tr = sum(1 for t in trainings if t.status == "COMPLETED" or (t.progress_percentage and t.progress_percentage >= 100.0))
            tr_pct = round((completed_tr / len(trainings)) * 100, 1)
            training_pct_str = f"{tr_pct:.0f}%"
            training_score = tr_pct

        # 3. Overall Grade calculation based on real weighted formula
        if len(att_records) == 0 and len(trainings) == 0:
            overall_grade = "A"
        else:
            weighted = (att_score * 0.4) + (punctuality_score * 0.3) + (training_score * 0.3)
            if weighted >= 90:
                overall_grade = "A+"
            elif weighted >= 80:
                overall_grade = "A"
            elif weighted >= 70:
                overall_grade = "B"
            elif weighted >= 60:
                overall_grade = "C"
            else:
                overall_grade = "D"

        result.append({
            "id": emp.id,
            "employeeCode": emp.employee_code,
            "name": full_name,
            "department": emp.department or "N/A",
            "attendance": att_pct_str,
            "tasks": punctuality_pct_str,
            "training": training_pct_str,
            "overall": overall_grade
        })

    return result



