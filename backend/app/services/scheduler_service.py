import logging
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.timeoff import TimeOffRequest

logger = logging.getLogger(__name__)
APP_TIMEZONE = ZoneInfo("Asia/Kolkata")

def send_notification_sync(db: Session, user_id: int, type: str, title: str, message: str, reference_id: int = None):
    """Sync wrapper to execute the async create_notification coroutine within the scheduler thread."""
    try:
        from app.services.notification_service import create_notification
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(
                create_notification(db, user_id, type, title, message, reference_id),
                loop
            )
        else:
            loop.run_until_complete(create_notification(db, user_id, type, title, message, reference_id))
    except Exception as e:
        logger.error(f"Error sending sync notification: {e}")

def check_timeoff_status():
    """Scheduled job to activate and complete time-off requests."""
    db = SessionLocal()
    try:
        now = datetime.now()
        current_date = now.date()
        current_time = now.time()

        # 1. Activate APPROVED requests that have reached their start_time
        approved_requests = db.query(TimeOffRequest).filter(
            TimeOffRequest.status == "Approved",
            TimeOffRequest.date == current_date
        ).all()

        for req in approved_requests:
            if req.start_time and current_time >= req.start_time:
                req.status = "Active"
                logger.info(f"Activated TimeOffRequest {req.id}")
                db.commit()

        # 2. Complete ACTIVE requests that have reached their end_time
        active_requests = db.query(TimeOffRequest).filter(
            TimeOffRequest.status == "Active",
            TimeOffRequest.date == current_date
        ).all()

        for req in active_requests:
            if req.end_time and current_time >= req.end_time:
                req.status = "Completed"
                logger.info(f"Completed TimeOffRequest {req.id}")
                db.commit()
    except Exception as e:
        logger.error(f"Error in check_timeoff_status: {e}")
        db.rollback()
    finally:
        db.close()

def send_websocket_message_sync(user_id: int, message: dict):
    """Sync wrapper to broadcast websocket messages from the scheduler thread."""
    try:
        from app.core.websocket_manager import manager
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(
                manager.send_personal_message(message, user_id),
                loop
            )
        else:
            loop.run_until_complete(manager.send_personal_message(message, user_id))
    except Exception as e:
        logger.error(f"Error sending sync websocket message: {e}")

def auto_checkout_forgotten_punches():
    """Scheduled job to check out employees who forgot to check out today or in the past, running every 5 minutes."""
    db = SessionLocal()
    try:
        from app.models.attendance import Attendance
        from app.models.user import User
        from app.services.time_calculator import calculate_times
        from zoneinfo import ZoneInfo
        
        APP_TIMEZONE = ZoneInfo("Asia/Kolkata")
        current_dt = datetime.now(APP_TIMEZONE)
        today = current_dt.date()
        current_time = current_dt.time()
        
        # Find all active attendance records up to today where punch_in is set but punch_out is missing
        active_records = db.query(Attendance).filter(
            Attendance.date <= today,
            Attendance.punch_in != None,
            Attendance.punch_out == None,
            Attendance.is_working == 1
        ).all()
        
        for record in active_records:
            user = db.query(User).filter(User.id == record.employee.user_id).first()
            if not user:
                continue
            
            is_past_day = record.date < today
            
            # Phase 1: Shift End Reminders (18:05 - 20:00) - only if overtime is NOT approved
            if not record.overtime_approved:
                # If the day has already passed, or we've reached 20:00 today, perform auto checkout.
                if is_past_day or current_time >= time(20, 0):
                    # Auto checkout
                    record.punch_out = time(18, 0)
                    record.is_working = 0
                    record.checkout_source = "AUTO"
                    record.requires_regularization = True
                    
                    # Ensure AUTO_CHECKOUT and MISSED_PUNCH flags are set
                    current_flags = record.flags or []
                    if "AUTO_CHECKOUT" not in current_flags:
                        current_flags.append("AUTO_CHECKOUT")
                    if "MISSED_PUNCH" not in current_flags:
                        current_flags.append("MISSED_PUNCH")
                    record.flags = current_flags
                    
                    calculate_times(record)
                    db.commit()
                    
                    from app.services.attendance_service import log_audit_trail_sync
                    reason_msg = f"Auto-checked out at 20:00 (or on a subsequent day catch-up) with checkout time 18:00 due to missed checkout." if not is_past_day else f"Auto-checked out past record {record.date} with checkout time 18:00 due to missed checkout."
                    log_audit_trail_sync(db, "AUTO_CHECKOUT", record.employee_id, reason_msg)
                    
                    send_notification_sync(db, user.id, "ATTENDANCE_AUTO_CHECKOUT", "Automatic Check-Out", f"You forgot to check out on {record.date}. The system checked you out automatically at 18:00.", record.id)
                    send_websocket_message_sync(user.id, {"type": "AUTO_CHECKOUT", "title": "Automatic Check-Out", "message": f"You forgot to check out. System auto checked you out at 18:00."})
                
                # Reminders are only relevant on today's active session
                elif not is_past_day:
                    # 18:05 to 18:20
                    if current_time >= time(18, 5) and current_time < time(18, 20):
                        if record.shift_end_reminder_sent < 1:
                            record.shift_end_reminder_sent = 1
                            db.commit()
                            send_notification_sync(db, user.id, "SHIFT_END_REMINDER", "Shift Ended", "Your shift has ended. Please punch out or request to continue working.", record.id)
                            send_websocket_message_sync(user.id, {"type": "SHIFT_END_REMINDER", "title": "Shift Ended", "message": "Your shift has ended. Please punch out or request to continue working."})
                    # 18:20 to 18:45
                    elif current_time >= time(18, 20) and current_time < time(18, 45):
                        if record.shift_end_reminder_sent < 2:
                            record.shift_end_reminder_sent = 2
                            db.commit()
                            send_notification_sync(db, user.id, "SHIFT_END_REMINDER", "Shift Ended - Warning 2", "Second warning: Please punch out or request to continue working.", record.id)
                            send_websocket_message_sync(user.id, {"type": "SHIFT_END_REMINDER", "title": "Shift Ended - Warning 2", "message": "Second warning: Please punch out or request to continue working."})
                    # 18:45 to 20:00
                    elif current_time >= time(18, 45) and current_time < time(20, 0):
                        if record.shift_end_reminder_sent < 3:
                            record.shift_end_reminder_sent = 3
                            db.commit()
                            send_notification_sync(db, user.id, "SHIFT_END_REMINDER", "Shift Ended - Final Warning", "Final warning: You will be auto-checked out at 20:00.", record.id)
                            send_websocket_message_sync(user.id, {"type": "SHIFT_END_REMINDER", "title": "Shift Ended - Final Warning", "message": "Final warning: You will be auto-checked out at 20:00."})
            
            # Phase 2: Overtime Reminders (20:00 - 20:45) - if overtime approved but NOT extended
            elif record.overtime_approved and not record.overtime_extended:
                # If the day has already passed, or we've reached 20:45 today, perform auto checkout.
                if is_past_day or current_time >= time(20, 45):
                    # Auto checkout
                    record.punch_out = time(20, 0)
                    record.is_working = 0
                    record.checkout_source = "AUTO"
                    record.requires_regularization = True
                    
                    # Ensure OVERTIME, AUTO_CHECKOUT and MISSED_PUNCH flags are set
                    current_flags = record.flags or []
                    for f in ["OVERTIME", "AUTO_CHECKOUT", "MISSED_PUNCH"]:
                        if f not in current_flags:
                            current_flags.append(f)
                    record.flags = current_flags
                    
                    calculate_times(record)
                    db.commit()
                    
                    from app.services.attendance_service import log_audit_trail_sync
                    reason_msg = f"Auto-checked out at 20:45 (or on a subsequent day catch-up) with checkout time 20:00 due to missed overtime checkout." if not is_past_day else f"Auto-checked out past record {record.date} with checkout time 20:00 due to missed overtime checkout."
                    log_audit_trail_sync(db, "AUTO_CHECKOUT", record.employee_id, reason_msg)
                    
                    send_notification_sync(db, user.id, "ATTENDANCE_AUTO_CHECKOUT", "Automatic Check-Out", f"Your overtime ended on {record.date}. The system checked you out automatically at 20:00.", record.id)
                    send_websocket_message_sync(user.id, {"type": "AUTO_CHECKOUT", "title": "Automatic Check-Out", "message": f"Your overtime ended. System auto checked you out at 20:00."})
                
                # Reminders are only relevant on today's active session
                elif not is_past_day:
                    # 20:00 to 20:15
                    if current_time >= time(20, 0) and current_time < time(20, 15):
                        if record.overtime_reminder_sent < 1:
                            record.overtime_reminder_sent = 1
                            db.commit()
                            send_notification_sync(db, user.id, "OVERTIME_REMINDER", "Overtime Limit", "Your overtime is ending. Please punch out or request an extension.", record.id)
                            send_websocket_message_sync(user.id, {"type": "OVERTIME_REMINDER", "title": "Overtime Limit", "message": "Your overtime is ending. Please punch out or request an extension."})
                    # 20:15 to 20:30
                    elif current_time >= time(20, 15) and current_time < time(20, 30):
                        if record.overtime_reminder_sent < 2:
                            record.overtime_reminder_sent = 2
                            db.commit()
                            send_notification_sync(db, user.id, "OVERTIME_REMINDER", "Overtime Limit - Warning 2", "Second warning: Please punch out or extend.", record.id)
                            send_websocket_message_sync(user.id, {"type": "OVERTIME_REMINDER", "title": "Overtime Limit - Warning 2", "message": "Second warning: Please punch out or extend."})
                    # 20:30 to 20:45
                    elif current_time >= time(20, 30) and current_time < time(20, 45):
                        if record.overtime_reminder_sent < 3:
                            record.overtime_reminder_sent = 3
                            db.commit()
                            send_notification_sync(db, user.id, "OVERTIME_REMINDER", "Overtime Limit - Final Warning", "Final warning: You will be auto-checked out at 20:45.", record.id)
                            send_websocket_message_sync(user.id, {"type": "OVERTIME_REMINDER", "title": "Overtime Limit - Final Warning", "message": "Final warning: You will be auto-checked out at 20:45."})
            
            # Phase 3: Extended Overtime Auto-Checkout (22:00 onwards)
            elif record.overtime_approved and record.overtime_extended:
                if is_past_day or current_time >= time(22, 0):
                    # Auto checkout
                    record.punch_out = time(22, 0)
                    record.is_working = 0
                    record.checkout_source = "AUTO"
                    record.requires_regularization = False  # Authorized extension
                    
                    # Clean auto checkout flag
                    current_flags = record.flags or []
                    for f in ["OVERTIME", "AUTO_CHECKOUT"]:
                        if f not in current_flags:
                            current_flags.append(f)
                    if "MISSED_PUNCH" in current_flags:
                        current_flags.remove("MISSED_PUNCH")
                    record.flags = current_flags
                    
                    calculate_times(record)
                    db.commit()
                    
                    from app.services.attendance_service import log_audit_trail_sync
                    reason_msg = f"Auto-checked out at 22:00 (or on a subsequent day catch-up) with checkout time 22:00 (authorized extension)." if not is_past_day else f"Auto-checked out past record {record.date} with checkout time 22:00 (authorized extension)."
                    log_audit_trail_sync(db, "AUTO_CHECKOUT", record.employee_id, reason_msg)
                    
                    send_notification_sync(db, user.id, "ATTENDANCE_AUTO_CHECKOUT", "Automatic Check-Out", f"You were checked out automatically at 22:00 on {record.date} (extended overtime limit reached).", record.id)
                    send_websocket_message_sync(user.id, {"type": "AUTO_CHECKOUT", "title": "Automatic Check-Out", "message": "Extended overtime limit reached. System checked you out at 22:00."})
    except Exception as e:
        logger.error(f"Error in auto_checkout_forgotten_punches: {e}")
        db.rollback()
    finally:
        db.close()

def auto_expire_pending_timeoff():
    """Scheduled job to expire pending time-off requests whose dates are in the past or today (if the time has passed)."""
    db = SessionLocal()
    try:
        from app.models.timeoff import TimeOffRequest
        from app.models.user import User
        from app.models.employee import Employee
        
        now = datetime.now()
        current_date = now.date()
        current_time = now.time()
        
        # 1. Expire requests with dates in the past (date < current_date)
        expired_past_requests = db.query(TimeOffRequest).filter(
            TimeOffRequest.status == "Pending",
            TimeOffRequest.date < current_date
        ).all()
        
        for req in expired_past_requests:
            req.status = "Expired"
            db.commit()
            logger.info(f"Auto-expired pending past TimeOffRequest {req.id} (date: {req.date})")
            
            # Notify the employee
            employee = db.query(Employee).filter(Employee.id == req.employee_id).first()
            if employee:
                user = db.query(User).filter(User.id == employee.user_id).first()
                if user:
                    send_notification_sync(
                        db=db,
                        user_id=user.id,
                        type="TIMEOFF_EXPIRED",
                        title="Time-Off Request Expired",
                        message=f"Your time-off request for {req.date} has expired without review.",
                        reference_id=req.id
                    )
                    
        # 2. Expire requests for today if their start_time has passed (date == current_date and start_time < current_time)
        expired_today_requests = db.query(TimeOffRequest).filter(
            TimeOffRequest.status == "Pending",
            TimeOffRequest.date == current_date
        ).all()
        
        for req in expired_today_requests:
            if req.start_time and current_time > req.start_time:
                req.status = "Expired"
                db.commit()
                logger.info(f"Auto-expired pending today TimeOffRequest {req.id} (date: {req.date}, start_time: {req.start_time})")
                
                # Notify the employee
                employee = db.query(Employee).filter(Employee.id == req.employee_id).first()
                if employee:
                    user = db.query(User).filter(User.id == employee.user_id).first()
                    if user:
                        send_notification_sync(
                            db=db,
                            user_id=user.id,
                            type="TIMEOFF_EXPIRED",
                            title="Time-Off Request Expired",
                            message=f"Your time-off request for today ({req.date}) has expired without review.",
                            reference_id=req.id
                        )
    except Exception as e:
        logger.error(f"Error in auto_expire_pending_timeoff: {e}")
        db.rollback()
    finally:
        db.close()

def remind_hr_pending_timeoff():
    """Scheduled job to remind HR of pending time-off requests starting tomorrow."""
    db = SessionLocal()
    try:
        from app.models.timeoff import TimeOffRequest
        from app.models.user import User, Role
        from app.models.employee import Employee
        from sqlalchemy import func
        
        tomorrow = date.today() + timedelta(days=1)
        
        pending_tomorrow = db.query(TimeOffRequest).filter(
            TimeOffRequest.status == "Pending",
            TimeOffRequest.date == tomorrow
        ).all()
        
        if pending_tomorrow:
            hr_users = db.query(User).join(Role).filter(func.lower(Role.name) == "hr").all()
            
            for req in pending_tomorrow:
                employee = db.query(Employee).filter(Employee.id == req.employee_id).first()
                emp_name = f"{employee.first_name} {employee.last_name}".strip() if employee else f"Employee #{req.employee_id}"
                
                for hr_user in hr_users:
                    send_notification_sync(
                        db=db,
                        user_id=hr_user.id,
                        type="TIMEOFF_REMINDER",
                        title="Pending Time-Off Reminder",
                        message=f"Reminder: Time-off request from {emp_name} for tomorrow ({req.date}) is still pending approval.",
                        reference_id=req.id
                    )
            logger.info(f"Sent HR reminders for {len(pending_tomorrow)} pending tomorrow time-off requests.")
    except Exception as e:
        logger.error(f"Error in remind_hr_pending_timeoff: {e}")
    finally:
        db.close()

scheduler = BackgroundScheduler(
    timezone=APP_TIMEZONE,
    job_defaults={
        "coalesce": True,
        "max_instances": 1,
        "misfire_grace_time": 120,
    },
)
scheduler.add_job(check_timeoff_status, 'interval', minutes=1, id="check_timeoff_status", replace_existing=True)
scheduler.add_job(auto_checkout_forgotten_punches, 'interval', minutes=5, id="auto_checkout_forgotten_punches", replace_existing=True)
scheduler.add_job(auto_expire_pending_timeoff, 'interval', minutes=15, id="auto_expire_pending_timeoff", replace_existing=True)
scheduler.add_job(remind_hr_pending_timeoff, 'cron', hour=9, minute=0, id="remind_hr_pending_timeoff", replace_existing=True)

def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started.")

def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shutdown.")
