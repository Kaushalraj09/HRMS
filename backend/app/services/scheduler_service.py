import logging
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, date, time, timedelta
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.timeoff import TimeOffRequest

logger = logging.getLogger(__name__)

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
            loop.create_task(create_notification(db, user_id, type, title, message, reference_id))
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

def auto_checkout_forgotten_punches():
    """Scheduled job to check out employees who forgot to check out today."""
    db = SessionLocal()
    try:
        from app.models.attendance import Attendance
        from app.models.user import User
        from app.services.time_calculator import calculate_times
        
        today = date.today()
        # Find all active attendance records for today where punch_in is set but punch_out is missing
        active_records = db.query(Attendance).filter(
            Attendance.date == today,
            Attendance.punch_in != None,
            Attendance.punch_out == None,
            Attendance.is_working == 1
        ).all()
        
        for record in active_records:
            # Auto check-out at 18:00 (scheduled end time) unless punch-in was at/after 18:00
            in_hour = record.punch_in.hour
            if in_hour >= 18:
                record.punch_out = time(23, 59)
            else:
                record.punch_out = time(18, 0)
                
            record.is_working = 0
            
            # Recalculate metrics (working minutes, break minutes, overtime)
            calculate_times(record)
            
            # Override status to "Auto Checked-out"
            record.status = "Auto Checked-out"
            db.commit()
            
            logger.info(f"Auto-checked out employee {record.employee_id} for date {record.date}")
            
            # Send notification to the employee
            user = db.query(User).filter(User.id == record.employee.user_id).first()
            if user:
                send_notification_sync(
                    db=db,
                    user_id=user.id,
                    type="ATTENDANCE_AUTO_CHECKOUT",
                    title="Automatic Check-Out",
                    message=f"You forgot to check out today ({record.date}). The system checked you out automatically at {record.punch_out.strftime('%H:%M')}.",
                    reference_id=record.id
                )
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
            hr_users = db.query(User).join(Role).filter(func.lower(Role.name).in_(["hr", "admin"])).all()
            
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

scheduler = BackgroundScheduler()
scheduler.add_job(check_timeoff_status, 'interval', minutes=1)
scheduler.add_job(auto_checkout_forgotten_punches, 'cron', hour=23, minute=59)
scheduler.add_job(auto_expire_pending_timeoff, 'interval', minutes=15)
scheduler.add_job(remind_hr_pending_timeoff, 'cron', hour=9, minute=0)

def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started.")

def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shutdown.")
