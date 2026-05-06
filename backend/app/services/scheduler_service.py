import logging
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, date
from app.core.database import SessionLocal
from app.models.timeoff import TimeOffRequest

logger = logging.getLogger(__name__)

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


scheduler = BackgroundScheduler()
scheduler.add_job(check_timeoff_status, 'interval', minutes=1)

def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started.")

def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shutdown.")
