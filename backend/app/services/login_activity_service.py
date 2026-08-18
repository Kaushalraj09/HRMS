from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from typing import List, Optional
from app.models.login_activity import LoginActivity
from app.models.employee import Employee
from app.models.user import User
from app.services.notification_service import create_notification

def parse_user_agent(ua_string: str) -> tuple:
    if not ua_string:
        return "Unknown Browser", "Unknown Device", "Unknown OS"
        
    ua = ua_string.lower()
    
    # 1. Parse Operating System
    if "windows" in ua:
        os = "Windows"
    elif "macintosh" in ua or "mac os" in ua:
        os = "macOS"
    elif "iphone" in ua:
        os = "iOS"
    elif "ipad" in ua:
        os = "iOS"
    elif "android" in ua:
        os = "Android"
    elif "linux" in ua:
        os = "Linux"
    else:
        os = "Unknown OS"
        
    # 2. Parse Device
    if "mobi" in ua or "iphone" in ua or "android" in ua:
        device = "Mobile"
    elif "ipad" in ua or "tablet" in ua:
        device = "Tablet"
    else:
        device = "Desktop"
        
    # 3. Parse Browser
    if "edg" in ua:
        browser = "Microsoft Edge"
    elif "chrome" in ua and "safari" in ua:
        browser = "Chrome"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "safari" in ua and "chrome" not in ua:
        browser = "Safari"
    elif "trident" in ua or "msie" in ua:
        browser = "Internet Explorer"
    else:
        browser = "Unknown Browser"
        
    return browser, device, os

async def log_login_activity(
    db: Session,
    user_id: int,
    ip_address: str,
    user_agent_string: str,
    status: str = "Success"
) -> LoginActivity:
    browser, device, os = parse_user_agent(user_agent_string)
    
    # Get employee shadow record if exists
    employee = db.query(Employee).filter(Employee.user_id == user_id).first()
    emp_id = employee.id if employee else None
    
    activity = LoginActivity(
        user_id=user_id,
        employee_id=emp_id,
        browser=browser,
        device=device,
        operating_system=os,
        ip_address=ip_address,
        location="Local Network" if ip_address in ["127.0.0.1", "localhost", "::1"] else "Remote Connection",
        status=status
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    
    return activity

def get_login_activities(
    db: Session,
    filter_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    user_id: Optional[int] = None,
    exclude_admin: bool = False,
    hr_user_id: Optional[int] = None
) -> List[LoginActivity]:
    query = db.query(LoginActivity)
    
    if hr_user_id is not None:
        from app.models.user import User, Role
        from sqlalchemy import or_, func
        query = query.join(User, LoginActivity.user_id == User.id)\
                     .join(Role, User.role_id == Role.id)\
                     .filter(
                         or_(
                             func.lower(Role.name) == "employee",
                             LoginActivity.user_id == hr_user_id
                         )
                     )
    elif exclude_admin:
        from app.models.user import User, Role
        query = query.join(User, LoginActivity.user_id == User.id)\
                     .join(Role, User.role_id == Role.id)\
                     .filter(Role.name != "admin")
    
    if user_id is not None:
        query = query.filter(LoginActivity.user_id == user_id)
        
    today = date.today()
    if filter_type == "Today":
        query = query.filter(LoginActivity.login_time >= datetime.combine(today, datetime.min.time()))
    elif filter_type == "This Week":
        start_of_week = today - timedelta(days=today.weekday())
        query = query.filter(LoginActivity.login_time >= datetime.combine(start_of_week, datetime.min.time()))
    elif filter_type == "This Month":
        start_of_month = today.replace(day=1)
        query = query.filter(LoginActivity.login_time >= datetime.combine(start_of_month, datetime.min.time()))
    elif filter_type == "Custom" and start_date and end_date:
        query = query.filter(
            LoginActivity.login_time >= datetime.combine(start_date, datetime.min.time()),
            LoginActivity.login_time <= datetime.combine(end_date, datetime.max.time())
        )
        
    return query.order_by(LoginActivity.login_time.desc()).all()

def get_login_activities_with_names(
    db: Session,
    filter_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    user_id: Optional[int] = None,
    exclude_admin: bool = False,
    hr_user_id: Optional[int] = None
) -> List[LoginActivity]:
    activities = get_login_activities(db, filter_type, start_date, end_date, user_id, exclude_admin, hr_user_id)
    
    results = []
    for act in activities:
        user = db.query(User).filter(User.id == act.user_id).first()
        employee = db.query(Employee).filter(Employee.user_id == act.user_id).first()
        
        act.user_display_name = user.display_name if user else "Unknown User"
        act.employee_code = employee.employee_code if employee else "N/A"
        act.employee_name = f"{employee.first_name} {employee.last_name}" if employee else (user.display_name if user else "N/A")
        results.append(act)
        
    return results

def get_login_activity_by_id(db: Session, activity_id: int) -> Optional[LoginActivity]:
    act = db.query(LoginActivity).filter(LoginActivity.id == activity_id).first()
    if act:
        user = db.query(User).filter(User.id == act.user_id).first()
        employee = db.query(Employee).filter(Employee.user_id == act.user_id).first()
        
        act.user_display_name = user.display_name if user else "Unknown User"
        act.employee_code = employee.employee_code if employee else "N/A"
        act.employee_name = f"{employee.first_name} {employee.last_name}" if employee else (user.display_name if user else "N/A")
    return act
