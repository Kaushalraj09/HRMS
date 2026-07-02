import asyncio
import logging
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.domain.events.dispatcher import EventDispatcher
from app.domain.events import types as ev_types
from app.services.notification_service import create_notification, create_notification_for_roles
from app.models.employee import Employee
from datetime import datetime

logger = logging.getLogger(__name__)

def _run_async(coro):
    """Run an async coroutine from a synchronous context safely."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        asyncio.run_coroutine_threadsafe(coro, loop)
    else:
        loop.run_until_complete(coro)

def handle_attendance_punched_in(event: ev_types.AttendancePunchedIn):
    db: Session = SessionLocal()
    try:
        emp = db.query(Employee).filter(Employee.id == event.employee_id).first()
        if emp:
            time_str = event.punch_time.strftime("%I:%M %p")
            # 1. Notify Employee
            _run_async(create_notification(
                db=db,
                user_id=emp.user_id,
                type="ATTENDANCE",
                title="Attendance Marked",
                message=f"You punched in at {time_str}.",
                reference_id=event.attendance_id,
                employee_id=emp.id
            ))
            # 2. Notify HR & Admin roles
            _run_async(create_notification_for_roles(
                db=db,
                roles=["HR", "Admin"],
                type="ATTENDANCE",
                title="Employee Punched In",
                message=f"{emp.first_name} {emp.last_name} punched in at {time_str}.",
                category="PUNCH_IN",
                severity="SUCCESS",
                employee_id=emp.id,
                created_by=emp.user_id,
                reference_id=event.attendance_id,
                notification_metadata={"work_mode": event.work_mode}
            ))
    except Exception as e:
        logger.error(f"Error handling AttendancePunchedIn notification: {e}")
    finally:
        db.close()

def handle_attendance_punched_out(event: ev_types.AttendancePunchedOut):
    db: Session = SessionLocal()
    try:
        emp = db.query(Employee).filter(Employee.id == event.employee_id).first()
        if emp:
            time_str = event.punch_time.strftime("%I:%M %p")
            # 1. Notify Employee
            _run_async(create_notification(
                db=db,
                user_id=emp.user_id,
                type="ATTENDANCE",
                title="Attendance Completed",
                message=f"You punched out at {time_str}.",
                reference_id=event.attendance_id,
                employee_id=emp.id
            ))
            # 2. Notify HR & Admin
            _run_async(create_notification_for_roles(
                db=db,
                roles=["HR", "Admin"],
                type="ATTENDANCE",
                title="Employee Punched Out",
                message=f"{emp.first_name} {emp.last_name} punched out at {time_str}.",
                category="PUNCH_OUT",
                severity="SUCCESS",
                employee_id=emp.id,
                created_by=emp.user_id,
                reference_id=event.attendance_id,
                notification_metadata={"work_mode": event.work_mode}
            ))
    except Exception as e:
        logger.error(f"Error handling AttendancePunchedOut notification: {e}")
    finally:
        db.close()

def handle_attendance_auto_checked_out(event: ev_types.AttendanceAutoCheckedOut):
    db: Session = SessionLocal()
    try:
        emp = db.query(Employee).filter(Employee.id == event.employee_id).first()
        if emp:
            # 1. Notify Employee
            _run_async(create_notification(
                db=db,
                user_id=emp.user_id,
                type="ATTENDANCE_AUTO_CHECKOUT",
                title="Automatic Check-Out",
                message=f"You forgot to check out on {event.date}. The system checked you out automatically at {event.checkout_time.strftime('%I:%M %p')}.",
                reference_id=event.attendance_id,
                employee_id=emp.id
            ))
            
            # Send live WebSocket message to trigger dynamic UI update
            from app.core.websocket_manager import manager
            _run_async(manager.send_personal_message(
                {"type": "AUTO_CHECKOUT", "title": "Automatic Check-Out", "message": f"You forgot to check out. System auto checked you out at {event.checkout_time.strftime('%H:%M')}."},
                emp.user_id
            ))
    except Exception as e:
        logger.error(f"Error handling AttendanceAutoCheckedOut notification: {e}")
    finally:
        db.close()

def handle_shift_ending_soon(event: ev_types.ShiftEndingSoon):
    db: Session = SessionLocal()
    try:
        emp = db.query(Employee).filter(Employee.id == event.employee_id).first()
        if emp:
            _run_async(create_notification(
                db=db,
                user_id=emp.user_id,
                type="SHIFT_END_REMINDER",
                title="Shift Ended",
                message="Your shift has ended. Please punch out or request to continue working.",
                reference_id=event.attendance_id,
                employee_id=emp.id
            ))
            
            from app.core.websocket_manager import manager
            _run_async(manager.send_personal_message(
                {"type": "SHIFT_END_REMINDER", "title": "Shift Ended", "message": "Your shift has ended. Please punch out or request to continue working."},
                emp.user_id
            ))
    except Exception as e:
        logger.error(f"Error handling ShiftEndingSoon notification: {e}")
    finally:
        db.close()

def handle_overtime_started(event: ev_types.OvertimeStarted):
    db: Session = SessionLocal()
    try:
        emp = db.query(Employee).filter(Employee.id == event.employee_id).first()
        if emp:
            _run_async(create_notification(
                db=db,
                user_id=emp.user_id,
                type="OVERTIME_REMINDER",
                title="Overtime Limit",
                message="Your overtime is ending. Please punch out or request an extension.",
                reference_id=event.attendance_id,
                employee_id=emp.id
            ))
            
            from app.core.websocket_manager import manager
            _run_async(manager.send_personal_message(
                {"type": "OVERTIME_REMINDER", "title": "Overtime Limit", "message": "Your overtime is ending. Please punch out or request an extension."},
                emp.user_id
            ))
    except Exception as e:
        logger.error(f"Error handling OvertimeStarted notification: {e}")
    finally:
        db.close()

def handle_overtime_approved(event: ev_types.OvertimeApproved):
    db: Session = SessionLocal()
    try:
        from app.models.attendance import OvertimeRequest
        req = db.query(OvertimeRequest).filter(OvertimeRequest.id == event.overtime_request_id).first()
        if req:
            emp = req.employee
            _run_async(create_notification(
                db=db,
                user_id=emp.user_id,
                type="OVERTIME",
                title="Overtime Request Approved",
                message=f"Your overtime request for {req.requested_minutes} minutes has been approved.",
                reference_id=req.id,
                employee_id=emp.id
            ))
    except Exception as e:
        logger.error(f"Error handling OvertimeApproved notification: {e}")
    finally:
        db.close()

def handle_leave_requested(event: ev_types.LeaveRequested):
    db: Session = SessionLocal()
    try:
        from app.models.timeoff import TimeOffRequest
        req = db.query(TimeOffRequest).filter(TimeOffRequest.id == event.leave_request_id).first()
        if req:
            emp = req.employee
            # 1. Notify Employee
            _run_async(create_notification(
                db=db,
                user_id=emp.user_id,
                type="TIMEOFF_APPLY",
                title="Time Off Request Submitted",
                message=f"You have successfully applied for time off ({req.leave_type}) on {req.date}.",
                reference_id=req.id,
                employee_id=emp.id
            ))
            # 2. Notify HR & Admin roles
            _run_async(create_notification_for_roles(
                db=db,
                roles=["HR", "Admin"],
                type="LEAVE",
                title="New Time Off Request",
                message=f"{emp.first_name} {emp.last_name} requested {req.leave_type} for {req.date}.",
                category="LEAVE_REQUEST",
                severity="WARNING",
                employee_id=emp.id,
                created_by=emp.user_id,
                reference_id=req.id,
                notification_metadata={
                    "leave_type": req.leave_type,
                    "date": str(req.date),
                    "duration_hours": req.duration_hours
                }
            ))
            
            # Send live WebSocket message to trigger dynamic updates in active dashboards
            from app.core.websocket_manager import manager
            _run_async(manager.broadcast(
                {
                    "type": "TIMEOFF_REQUEST",
                    "message": f"New time off request from employee #{emp.id}",
                    "request": {
                        "id": req.id,
                        "employee_id": req.employee_id,
                        "date": str(req.date),
                        "leave_type": req.leave_type,
                        "start_time": str(req.start_time) if req.start_time else None,
                        "end_time": str(req.end_time) if req.end_time else None,
                        "duration_hours": req.duration_hours,
                        "status": req.status,
                        "employee_name": f"{emp.first_name} {emp.last_name}",
                        "reason": req.reason,
                        "attachment_name": req.attachment_name,
                    },
                }
            ))
    except Exception as e:
        logger.error(f"Error handling LeaveRequested notification: {e}")
    finally:
        db.close()

def handle_leave_approved(event: ev_types.LeaveApproved):
    db: Session = SessionLocal()
    try:
        from app.models.timeoff import TimeOffRequest
        req = db.query(TimeOffRequest).filter(TimeOffRequest.id == event.leave_request_id).first()
        if req:
            emp = req.employee
            # 1. Notify Employee
            _run_async(create_notification(
                db=db,
                user_id=emp.user_id,
                type="TIMEOFF_UPDATE",
                title="Time Off Request Approved",
                message=f"Your time off request for {req.date} has been approved.",
                reference_id=req.id,
                employee_id=emp.id
            ))
            # 2. Notify HR & Admin
            _run_async(create_notification_for_roles(
                db=db,
                roles=["HR", "Admin"],
                type="LEAVE",
                title="Time Off Request Approved",
                message=f"Leave request approved for {emp.first_name} {emp.last_name}.",
                category="LEAVE_APPROVED",
                severity="SUCCESS",
                employee_id=emp.id,
                reference_id=req.id,
                notification_metadata={
                    "leave_type": req.leave_type,
                    "date": str(req.date),
                    "action": "APPROVE"
                }
            ))
            
            # WebSocket live update
            from app.core.websocket_manager import manager
            _run_async(manager.send_personal_message(
                {
                    "type": "TIMEOFF_UPDATE", 
                    "status": "Approved", 
                    "duration": req.duration_hours,
                    "message": f"Your time-off request for {req.date} has been approved."
                },
                emp.user_id
            ))
    except Exception as e:
        logger.error(f"Error handling LeaveApproved notification: {e}")
    finally:
        db.close()

def handle_leave_rejected(event: ev_types.LeaveRejected):
    db: Session = SessionLocal()
    try:
        from app.models.timeoff import TimeOffRequest
        req = db.query(TimeOffRequest).filter(TimeOffRequest.id == event.leave_request_id).first()
        if req:
            emp = req.employee
            # 1. Notify Employee
            _run_async(create_notification(
                db=db,
                user_id=emp.user_id,
                type="TIMEOFF_UPDATE",
                title="Time Off Request Rejected",
                message=f"Your time off request for {req.date} has been rejected.",
                reference_id=req.id,
                employee_id=emp.id
            ))
            # 2. Notify HR & Admin
            _run_async(create_notification_for_roles(
                db=db,
                roles=["HR", "Admin"],
                type="LEAVE",
                title="Time Off Request Rejected",
                message=f"Leave request rejected for {emp.first_name} {emp.last_name}.",
                category="LEAVE_REJECTED",
                severity="ERROR",
                employee_id=emp.id,
                reference_id=req.id,
                notification_metadata={
                    "leave_type": req.leave_type,
                    "date": str(req.date),
                    "action": "REJECT"
                }
            ))
            
            # WebSocket live update
            from app.core.websocket_manager import manager
            _run_async(manager.send_personal_message(
                {
                    "type": "TIMEOFF_UPDATE", 
                    "status": "Rejected", 
                    "duration": req.duration_hours,
                    "message": f"Your time-off request for {req.date} has been rejected."
                },
                emp.user_id
            ))
    except Exception as e:
        logger.error(f"Error handling LeaveRejected notification: {e}")
    finally:
        db.close()

def handle_leave_cancelled(event: ev_types.LeaveCancelled):
    db: Session = SessionLocal()
    try:
        from app.models.timeoff import TimeOffRequest
        req = db.query(TimeOffRequest).filter(TimeOffRequest.id == event.leave_request_id).first()
        if req:
            emp = req.employee
            # 1. Notify Employee
            _run_async(create_notification(
                db=db,
                user_id=emp.user_id,
                type="TIMEOFF_UPDATE",
                title="Time Off Request Cancelled",
                message=f"Your time off request for {req.date} has been cancelled.",
                reference_id=req.id,
                employee_id=emp.id
            ))
            # 2. Notify HR & Admin
            _run_async(create_notification_for_roles(
                db=db,
                roles=["HR", "Admin"],
                type="LEAVE",
                title="Time Off Request Cancelled",
                message=f"{emp.first_name} {emp.last_name} cancelled their leave request.",
                category="LEAVE_CANCELLED",
                severity="INFO",
                employee_id=emp.id,
                reference_id=req.id,
                notification_metadata={
                    "leave_type": req.leave_type,
                    "date": str(req.date)
                }
            ))
    except Exception as e:
        logger.error(f"Error handling LeaveCancelled notification: {e}")
    finally:
        db.close()

def handle_regularization_requested(event: ev_types.AttendanceRegularizationRequested):
    db: Session = SessionLocal()
    try:
        from app.models.attendance import AttendanceRegularizationRequest
        req = db.query(AttendanceRegularizationRequest).filter(AttendanceRegularizationRequest.id == event.regularization_request_id).first()
        if req:
            emp = req.employee
            # 1. Notify Employee
            _run_async(create_notification(
                db=db,
                user_id=emp.user_id,
                type="REGULARIZATION_APPLY",
                title="Attendance Regularization Submitted",
                message=f"You applied for attendance regularization for {event.date}.",
                reference_id=req.id,
                employee_id=emp.id
            ))
            # 2. Notify HR & Admin
            _run_async(create_notification_for_roles(
                db=db,
                roles=["HR", "Admin"],
                type="ATTENDANCE",
                title="New Regularization Request",
                message=f"Attendance regularization request from {emp.first_name} {emp.last_name} for {event.date}.",
                category="REGULARIZATION_REQUEST",
                severity="WARNING",
                employee_id=emp.id,
                created_by=emp.user_id,
                reference_id=req.id
            ))
    except Exception as e:
        logger.error(f"Error handling AttendanceRegularizationRequested notification: {e}")
    finally:
        db.close()

def handle_regularization_approved(event: ev_types.AttendanceRegularizationApproved):
    db: Session = SessionLocal()
    try:
        from app.models.attendance import AttendanceRegularizationRequest
        req = db.query(AttendanceRegularizationRequest).filter(AttendanceRegularizationRequest.id == event.regularization_request_id).first()
        if req:
            emp = req.employee
            # 1. Notify Employee
            _run_async(create_notification(
                db=db,
                user_id=emp.user_id,
                type="REGULARIZATION_UPDATE",
                title="Regularization Request Approved",
                message=f"Your regularization request for {event.date} has been approved.",
                reference_id=req.id,
                employee_id=emp.id
            ))
            # 2. Notify HR & Admin
            _run_async(create_notification_for_roles(
                db=db,
                roles=["HR", "Admin"],
                type="ATTENDANCE",
                title="Regularization Request Approved",
                message=f"Regularization request approved for {emp.first_name} {emp.last_name} on {event.date}.",
                category="REGULARIZATION_APPROVED",
                severity="SUCCESS",
                employee_id=emp.id,
                reference_id=req.id
            ))
    except Exception as e:
        logger.error(f"Error handling AttendanceRegularizationApproved notification: {e}")
    finally:
        db.close()

def register_all_listeners():
    """Register all listeners in the EventDispatcher."""
    EventDispatcher.clear()
    EventDispatcher.register(ev_types.AttendancePunchedIn, handle_attendance_punched_in)
    EventDispatcher.register(ev_types.AttendancePunchedOut, handle_attendance_punched_out)
    EventDispatcher.register(ev_types.AttendanceAutoCheckedOut, handle_attendance_auto_checked_out)
    EventDispatcher.register(ev_types.ShiftEndingSoon, handle_shift_ending_soon)
    EventDispatcher.register(ev_types.OvertimeStarted, handle_overtime_started)
    EventDispatcher.register(ev_types.OvertimeApproved, handle_overtime_approved)
    EventDispatcher.register(ev_types.LeaveRequested, handle_leave_requested)
    EventDispatcher.register(ev_types.LeaveApproved, handle_leave_approved)
    EventDispatcher.register(ev_types.LeaveRejected, handle_leave_rejected)
    EventDispatcher.register(ev_types.LeaveCancelled, handle_leave_cancelled)
    EventDispatcher.register(ev_types.AttendanceRegularizationRequested, handle_regularization_requested)
    EventDispatcher.register(ev_types.AttendanceRegularizationApproved, handle_regularization_approved)
