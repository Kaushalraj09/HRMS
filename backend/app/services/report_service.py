from sqlalchemy import or_, func, Date
from sqlalchemy.orm import Session
from datetime import date, time, datetime, timedelta
import io
import csv
from fastapi.responses import StreamingResponse
from app.models.employee import Employee
from app.models.attendance import Attendance, AttendanceRegularizationRequest
from app.models.timeoff import TimeOffRequest
from app.models.approval_log import ApprovalLog
from app.models.user import User, Role
from app.models.login_activity import LoginActivity
from app.services.time_calculator import calculate_late_minutes
from app.utils.employee_code import normalize_employee_code

def generate_report_csv(headers: list[str], rows: list[list[str]], filename: str) -> StreamingResponse:
    output = io.StringIO()
    # Write BOM for Excel UTF-8 compatibility
    output.write('\ufeff')
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    output.seek(0)
    
    response = StreamingResponse(
        iter([output.getvalue().encode("utf-8")]),
        media_type="text/csv"
    )
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response

def generate_report_pdf(headers: list[str], rows: list[list[str]], filename: str) -> StreamingResponse:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    
    buffer = io.BytesIO()
    title = filename.replace('.pdf', '').replace('_', ' ').title()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36, title=title)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        spaceAfter=20,
        textColor=colors.HexColor('#1E3A8A')
    )
    
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 10))
    
    data = [headers] + rows
    
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=7,
        leading=9
    )
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=9,
        textColor=colors.white
    )
    
    formatted_data = []
    for r_idx, row in enumerate(data):
        formatted_row = []
        for cell in row:
            text = str(cell)
            if r_idx == 0:
                formatted_row.append(Paragraph(text, header_style))
            else:
                formatted_row.append(Paragraph(text, cell_style))
        formatted_data.append(formatted_row)
        
    t = Table(formatted_data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
    ]))
    
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    
    response = StreamingResponse(
        io.BytesIO(buffer.getvalue()),
        media_type="application/pdf"
    )
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


def _apply_employee_filters(query, start_date: date | None, end_date: date | None, department: str | None, search: str | None, join_role: bool = False):
    if join_role:
        query = query.join(User, Employee.user_id == User.id).join(Role, User.role_id == Role.id).filter(func.lower(Role.name) != "admin")
    query = query.filter(Employee.status != "Deleted", User.status != "Deleted")
    if department:
        query = query.filter(Employee.department == department)
    if search:
        like_value = f"%{search}%"
        full_name = func.coalesce(Employee.first_name, "") + " " + func.coalesce(Employee.last_name, "")
        query = query.filter(
            or_(
                Employee.first_name.ilike(like_value),
                Employee.last_name.ilike(like_value),
                full_name.ilike(like_value),
                Employee.employee_code.ilike(like_value),
                Employee.department.ilike(like_value),
                Employee.official_email.ilike(like_value),
            )
        )
    return query

def get_attendance_summary_report(
    db: Session,
    start_date: date | None = None,
    end_date: date | None = None,
    department: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 10,
    export_all: bool = False
):
    # Set default dates if not provided
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()
        
    query = db.query(Employee).join(User, Employee.user_id == User.id).join(Role, User.role_id == Role.id).filter(func.lower(Role.name) != "admin")
    query = _apply_employee_filters(query, start_date, end_date, department, search)
    
    total = query.count()
    
    if export_all:
        employees = query.order_by(Employee.employee_code).all()
    else:
        offset = (page - 1) * limit
        employees = query.order_by(Employee.employee_code).offset(offset).limit(limit).all()
        
    data = []
    for emp in employees:
        # Get attendance records in range
        records = (
            db.query(Attendance)
            .filter(
                Attendance.employee_id == emp.id,
                Attendance.date >= start_date,
                Attendance.date <= end_date
            )
            .all()
        )
        
        # Get approved timeoff requests in range
        timeoff_reqs = (
            db.query(TimeOffRequest)
            .filter(
                TimeOffRequest.employee_id == emp.id,
                TimeOffRequest.date >= start_date,
                TimeOffRequest.date <= end_date,
                TimeOffRequest.status.ilike("Approved")
            )
            .all()
        )
        
        present_days = sum(1 for r in records if r.status in ["Present", "WORKING"])
        half_days = sum(1 for r in records if r.status == "Half-Day")
        absent_days = sum(1 for r in records if r.status == "Absent")
        
        # Calculate leaves
        leave_dates = {r.date for r in records if r.status == "Leave"}
        leave_dates.update(req.date for req in timeoff_reqs)
        leave_days = len(leave_dates)
        
        total_working_minutes = sum(r.total_working_minutes for r in records if r.total_working_minutes)
        total_overtime_minutes = sum(r.overtime_minutes for r in records if r.overtime_minutes)
        
        data.append({
            "employeeId": emp.id,
            "employeeCode": normalize_employee_code(emp.employee_code),
            "employeeName": f"{emp.first_name} {emp.last_name}",
            "department": emp.department,
            "presentDays": present_days,
            "absentDays": absent_days,
            "halfDays": half_days,
            "leaveDays": leave_days,
            "totalWorkingMinutes": total_working_minutes,
            "totalOvertimeMinutes": total_overtime_minutes
        })
        
    pages = (total + limit - 1) // limit if limit > 0 else 1
    return {
        "total": total,
        "page": page,
        "pageSize": limit,
        "pages": pages,
        "data": data
    }

def get_late_arrival_report(
    db: Session,
    start_date: date | None = None,
    end_date: date | None = None,
    department: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 10,
    export_all: bool = False
):
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()
        
    query = db.query(Attendance).join(Employee).filter(
        Attendance.punch_in != None,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    )
    query = _apply_employee_filters(query, start_date, end_date, department, search, join_role=True)
    
    records = query.order_by(Attendance.date.desc()).all()
    
    late_records = []
    for r in records:
        late_mins = calculate_late_minutes(r.punch_in)
        if late_mins > 0:
            late_records.append({
                "employeeId": r.employee.id,
                "employeeCode": normalize_employee_code(r.employee.employee_code),
                "employeeName": f"{r.employee.first_name} {r.employee.last_name}",
                "department": r.employee.department,
                "date": r.date,
                "scheduledStart": r.scheduled_start,
                "punchIn": r.punch_in,
                "lateMinutes": late_mins
            })
            
    total = len(late_records)
    if export_all:
        data = late_records
    else:
        offset = (page - 1) * limit
        data = late_records[offset : offset + limit]
        
    pages = (total + limit - 1) // limit if limit > 0 else 1
    return {
        "total": total,
        "page": page,
        "pageSize": limit,
        "pages": pages,
        "data": data
    }

def get_missing_punch_report(
    db: Session,
    start_date: date | None = None,
    end_date: date | None = None,
    department: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 10,
    export_all: bool = False
):
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()
        
    query = db.query(Attendance).join(Employee).filter(
        Attendance.date >= start_date,
        Attendance.date <= end_date
    )
    query = _apply_employee_filters(query, start_date, end_date, department, search, join_role=True)
    
    records = query.order_by(Attendance.date.desc()).all()
    today = date.today()
    
    missing_records = []
    for r in records:
        is_missing = False
        reason = ""
        
        # 1. punch_in is null but punch_out is not
        if r.punch_in is None and r.punch_out is not None:
            is_missing = True
            reason = "Missing Punch In"
        # 2. punch_in is not null but punch_out is null (for dates before today)
        elif r.punch_in is not None and r.punch_out is None and r.date < today:
            is_missing = True
            reason = "Missing Punch Out"
        # 3. MISSED_PUNCH inside flags
        elif "MISSED_PUNCH" in r.flags:
            is_missing = True
            reason = "Flagged as Missed Punch"
            
        if is_missing:
            missing_records.append({
                "employeeId": r.employee.id,
                "employeeCode": normalize_employee_code(r.employee.employee_code),
                "employeeName": f"{r.employee.first_name} {r.employee.last_name}",
                "department": r.employee.department,
                "date": r.date,
                "punchIn": r.punch_in,
                "punchOut": r.punch_out,
                "status": r.status,
                "reason": reason
            })
            
    total = len(missing_records)
    if export_all:
        data = missing_records
    else:
        offset = (page - 1) * limit
        data = missing_records[offset : offset + limit]
        
    pages = (total + limit - 1) // limit if limit > 0 else 1
    return {
        "total": total,
        "page": page,
        "pageSize": limit,
        "pages": pages,
        "data": data
    }

def get_leave_usage_report(
    db: Session,
    start_date: date | None = None,
    end_date: date | None = None,
    department: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 10,
    export_all: bool = False
):
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()
        
    query = db.query(TimeOffRequest).join(Employee).filter(
        TimeOffRequest.date >= start_date,
        TimeOffRequest.date <= end_date,
        TimeOffRequest.status.in_(["Approved", "Completed"])
    )
    query = _apply_employee_filters(query, start_date, end_date, department, search, join_role=True)
    
    total = query.count()
    if export_all:
        records = query.order_by(TimeOffRequest.date.desc()).all()
    else:
        offset = (page - 1) * limit
        records = query.order_by(TimeOffRequest.date.desc()).offset(offset).limit(limit).all()
        
    data = []
    for r in records:
        data.append({
            "employeeId": r.employee.id,
            "employeeCode": normalize_employee_code(r.employee.employee_code),
            "employeeName": f"{r.employee.first_name} {r.employee.last_name}",
            "department": r.employee.department,
            "leaveType": r.leave_type,
            "durationHours": r.duration_hours,
            "date": r.date,
            "status": r.status,
            "reason": r.reason
        })
        
    pages = (total + limit - 1) // limit if limit > 0 else 1
    return {
        "total": total,
        "page": page,
        "pageSize": limit,
        "pages": pages,
        "data": data
    }

def get_hr_workload_report(
    db: Session,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = 1,
    limit: int = 10,
    export_all: bool = False
):
    # Retrieve all users with admin or hr role
    hr_users = (
        db.query(User)
        .join(Role)
        .filter(Role.name.in_(["admin", "hr"]))
        .all()
    )
    
    # Processed requests filter subqueries
    timeoff_logs_q = db.query(ApprovalLog)
    reg_reqs_q = db.query(AttendanceRegularizationRequest).filter(
        AttendanceRegularizationRequest.status.in_(["approved", "rejected"])
    )
    
    if start_date:
        start_dt = datetime.combine(start_date, time.min)
        timeoff_logs_q = timeoff_logs_q.filter(ApprovalLog.created_at >= start_dt)
        reg_reqs_q = reg_reqs_q.filter(AttendanceRegularizationRequest.reviewed_at >= start_dt)
    if end_date:
        end_dt = datetime.combine(end_date, time.max)
        timeoff_logs_q = timeoff_logs_q.filter(ApprovalLog.created_at <= end_dt)
        reg_reqs_q = reg_reqs_q.filter(AttendanceRegularizationRequest.reviewed_at <= end_dt)
        
    timeoff_logs = timeoff_logs_q.all()
    reg_reqs = reg_reqs_q.all()
    
    rows = []
    
    # Calculate workloads for each HR user
    for user in hr_users:
        processed_to = sum(1 for log in timeoff_logs if log.action_by_user_id == user.id)
        processed_reg = sum(1 for reg in reg_reqs if reg.reviewed_by == user.id)
        
        rows.append({
            "hrName": user.display_name,
            "pendingTimeoff": 0,
            "pendingRegularization": 0,
            "processedTimeoff": processed_to,
            "processedRegularization": processed_reg,
            "totalHandled": processed_to + processed_reg
        })
        
    # Query unassigned (pending) counts
    pending_to_q = db.query(TimeOffRequest).filter(TimeOffRequest.status.ilike("Pending"))
    pending_reg_q = db.query(AttendanceRegularizationRequest).filter(AttendanceRegularizationRequest.status.ilike("pending"))
    
    if start_date:
        pending_to_q = pending_to_q.filter(TimeOffRequest.date >= start_date)
        pending_reg_q = pending_reg_q.filter(AttendanceRegularizationRequest.attendance_date >= start_date)
    if end_date:
        pending_to_q = pending_to_q.filter(TimeOffRequest.date <= end_date)
        pending_reg_q = pending_reg_q.filter(AttendanceRegularizationRequest.attendance_date <= end_date)
        
    pending_timeoff_count = pending_to_q.count()
    pending_reg_count = pending_reg_q.count()
    
    rows.append({
        "hrName": "Unassigned (Pending Queue)",
        "pendingTimeoff": pending_timeoff_count,
        "pendingRegularization": pending_reg_count,
        "processedTimeoff": 0,
        "processedRegularization": 0,
        "totalHandled": pending_timeoff_count + pending_reg_count
    })
    
    # Sort workload by total handled or pending desc
    rows.sort(key=lambda x: (x["totalHandled"], x["hrName"]), reverse=True)
    
    total = len(rows)
    if export_all:
        data = rows
    else:
        offset = (page - 1) * limit
        data = rows[offset : offset + limit]
        
    pages = (total + limit - 1) // limit if limit > 0 else 1
    return {
        "total": total,
        "page": page,
        "pageSize": limit,
        "pages": pages,
        "data": data
    }

def get_employee_status_report(
    db: Session,
    department: str | None = None,
    search: str | None = None,
    status: str | None = None,
    page: int = 1,
    limit: int = 10,
    export_all: bool = False
):
    query = (
        db.query(Employee)
        .join(User, Employee.user_id == User.id)
        .join(Role, User.role_id == Role.id)
        .filter(
            func.lower(Role.name) != "admin",
            Employee.status != "Deleted",
            User.status != "Deleted"
        )
    )
    if department:
        query = query.filter(Employee.department == department)
    if status:
        query = query.filter(Employee.status.ilike(status))
    if search:
        like_value = f"%{search}%"
        full_name = func.coalesce(Employee.first_name, "") + " " + func.coalesce(Employee.last_name, "")
        query = query.filter(
            or_(
                Employee.first_name.ilike(like_value),
                Employee.last_name.ilike(like_value),
                full_name.ilike(like_value),
                Employee.employee_code.ilike(like_value),
                Employee.department.ilike(like_value),
                Employee.official_email.ilike(like_value),
            )
        )
        
    total = query.count()
    if export_all:
        employees = query.order_by(Employee.employee_code).all()
    else:
        offset = (page - 1) * limit
        employees = query.order_by(Employee.employee_code).offset(offset).limit(limit).all()
        
    data = []
    for emp in employees:
        data.append({
            "employeeId": emp.id,
            "employeeCode": normalize_employee_code(emp.employee_code),
            "employeeName": f"{emp.first_name} {emp.last_name}",
            "department": emp.department,
            "designation": emp.designation,
            "status": emp.status,
            "doj": emp.doj,
            "timeoffBalanceHours": emp.timeoff_balance_hours
        })
        
    pages = (total + limit - 1) // limit if limit > 0 else 1
    return {
        "total": total,
        "page": page,
        "pageSize": limit,
        "pages": pages,
        "data": data
    }

def get_login_activity_summary_report(
    db: Session,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = 1,
    limit: int = 10,
    export_all: bool = False
):
    query = db.query(LoginActivity).outerjoin(Employee).join(User, LoginActivity.user_id == User.id)
    if start_date:
        start_dt = datetime.combine(start_date, time.min)
        query = query.filter(LoginActivity.login_time >= start_dt)
    if end_date:
        end_dt = datetime.combine(end_date, time.max)
        query = query.filter(LoginActivity.login_time <= end_dt)
        
    total = query.count()
    if export_all:
        records = query.order_by(LoginActivity.login_time.desc()).all()
    else:
        offset = (page - 1) * limit
        records = query.order_by(LoginActivity.login_time.desc()).offset(offset).limit(limit).all()
        
    data = []
    for r in records:
        emp_name = r.user.display_name
        emp_code = None
        if r.employee:
            emp_name = f"{r.employee.first_name} {r.employee.last_name}"
            emp_code = normalize_employee_code(r.employee.employee_code)
            
        data.append({
            "id": r.id,
            "employeeId": r.employee_id,
            "employeeCode": emp_code,
            "employeeName": emp_name,
            "email": r.user.email,
            "loginTime": r.login_time,
            "ipAddress": r.ip_address,
            "browser": r.browser,
            "device": r.device,
            "operatingSystem": r.operating_system,
            "status": r.status
        })
        
    pages = (total + limit - 1) // limit if limit > 0 else 1
    return {
        "total": total,
        "page": page,
        "pageSize": limit,
        "pages": pages,
        "data": data
    }
