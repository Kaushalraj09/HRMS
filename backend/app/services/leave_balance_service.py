from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any, Optional
from datetime import date
from fastapi import HTTPException, status

from app.models.employee import Employee
from app.models.master_data import LeaveType
from app.models.leave_balance import EmployeeLeaveBalance
from app.models.timeoff import TimeOffRequest


class LeaveBalanceService:
    """
    Yearly Leave Balance & Entitlement Lifecycle Service.
    Maintains annual allocations, dynamic pending reservations,
    and consumption tracking without modifying historical records.
    """

    @staticmethod
    def resolve_leave_type(db: Session, leave_type_identifier: Any) -> Optional[LeaveType]:
        """Resolves a LeaveType by ID, code, or name."""
        if isinstance(leave_type_identifier, int) or (isinstance(leave_type_identifier, str) and leave_type_identifier.isdigit()):
            return db.query(LeaveType).filter(LeaveType.id == int(leave_type_identifier)).first()
        
        name_str = str(leave_type_identifier or "").strip().lower()
        if not name_str:
            return None
        
        # Try direct name/code match
        lt = db.query(LeaveType).filter(
            (func.lower(LeaveType.code) == name_str) |
            (func.lower(LeaveType.name) == name_str)
        ).first()
        if lt:
            return lt

        # Fuzzy match for standard categories
        if "casual" in name_str or name_str in ("full-day", "full day", "fullday"):
            matched = db.query(LeaveType).filter(
                (func.lower(LeaveType.name).like("%casual%")) | (LeaveType.code == "CL")
            ).first()
            if matched:
                return matched
        if "sick" in name_str:
            matched = db.query(LeaveType).filter(
                (func.lower(LeaveType.name).like("%sick%")) | (LeaveType.code == "SL")
            ).first()
            if matched:
                return matched
        if "earned" in name_str or "privilege" in name_str:
            matched = db.query(LeaveType).filter(
                (func.lower(LeaveType.name).like("%earned%")) | (LeaveType.code.in_(["EL", "PL"]))
            ).first()
            if matched:
                return matched
        if "comp" in name_str:
            matched = db.query(LeaveType).filter(
                (func.lower(LeaveType.name).like("%comp%")) | (LeaveType.code == "CO")
            ).first()
            if matched:
                return matched
        if "half" in name_str:
            matched = db.query(LeaveType).filter(
                (func.lower(LeaveType.name).like("%half%")) | (LeaveType.code == "HD")
            ).first()
            if matched:
                return matched

        # Fallback for unseeded test environments/fixtures
        if db.query(LeaveType).count() == 0:
            LeaveBalanceService.ensure_default_leave_types(db)
            return LeaveBalanceService.resolve_leave_type(db, leave_type_identifier)

        # Fallback to first active leave type if full-day is passed
        if name_str in ("full-day", "full day", "fullday"):
            return db.query(LeaveType).filter(LeaveType.is_active == True).first()
            
        return None

    @classmethod
    def ensure_default_leave_types(cls, db: Session) -> List[LeaveType]:
        """Ensures standard leave types exist in database (useful for unseeded test environments)."""
        active_leave_types = db.query(LeaveType).filter(LeaveType.is_active == True).all()
        if not active_leave_types:
            default_types = [
                LeaveType(name="Casual Leave", code="CL", unit_type="full_day", default_balance_hours=96.0, is_active=True),
                LeaveType(name="Sick Leave", code="SL", unit_type="full_day", default_balance_hours=64.0, is_active=True),
                LeaveType(name="Earned Leave", code="EL", unit_type="full_day", default_balance_hours=144.0, is_active=True),
                LeaveType(name="Half Day", code="HD", unit_type="half_day", default_balance_hours=32.0, is_active=True),
                LeaveType(name="Comp Off", code="CO", unit_type="full_day", default_balance_hours=16.0, is_active=True)
            ]
            db.add_all(default_types)
            db.commit()
            active_leave_types = db.query(LeaveType).filter(LeaveType.is_active == True).all()
        return active_leave_types

    @classmethod
    def get_or_initialize_yearly_balances(
        cls, db: Session, employee_id: int, year: Optional[int] = None
    ) -> List[EmployeeLeaveBalance]:
        """
        Retrieves yearly leave balance records for an employee.
        If any active LeaveType does not yet have a record for the specified year,
        initializes it based on the current Master Data quota.
        """
        if year is None:
            year = date.today().year

        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            return []

        active_leave_types = cls.ensure_default_leave_types(db)
        existing_balances = db.query(EmployeeLeaveBalance).filter(
            EmployeeLeaveBalance.employee_id == employee_id,
            EmployeeLeaveBalance.year == year
        ).all()
        existing_lt_ids = {b.leave_type_id: b for b in existing_balances}

        created_any = False
        for lt in active_leave_types:
            if lt.id not in existing_lt_ids:
                # Calculate annual days allocation (default_balance_hours / 8.0) as integer days
                alloc_days = float(round(float(lt.default_balance_hours) / 8.0)) if lt.default_balance_hours else 0.0
                new_bal = EmployeeLeaveBalance(
                    employee_id=employee_id,
                    leave_type_id=lt.id,
                    year=year,
                    allocated_days=alloc_days,
                    used_days=0.0,
                    pending_days=0.0,
                    available_days=alloc_days,
                    carry_forward_days=0.0
                )
                db.add(new_bal)
                existing_balances.append(new_bal)
                created_any = True

        if created_any:
            db.commit()

        # Recalculate balances dynamically from TimeOffRequest to ensure exact sync
        cls.sync_balances_from_requests(db, employee_id, year)

        return db.query(EmployeeLeaveBalance).filter(
            EmployeeLeaveBalance.employee_id == employee_id,
            EmployeeLeaveBalance.year == year
        ).all()

    @classmethod
    def sync_balances_from_requests(cls, db: Session, employee_id: int, year: int) -> None:
        """
        Synchronizes used_days and pending_days against TimeOffRequests for the given year,
        guaranteeing zero desynchronization or double-counting.
        """
        balances = db.query(EmployeeLeaveBalance).filter(
            EmployeeLeaveBalance.employee_id == employee_id,
            EmployeeLeaveBalance.year == year
        ).all()
        if not balances:
            return

        # Fetch requests in that calendar year
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)
        requests = db.query(TimeOffRequest).filter(
            TimeOffRequest.employee_id == employee_id,
            TimeOffRequest.date >= year_start,
            TimeOffRequest.date <= year_end
        ).all()

        for bal in balances:
            lt = bal.leave_type
            if not lt:
                continue

            used_days = 0.0
            pending_days = 0.0

            # Match requests to this leave type
            for req in requests:
                req_lt = cls.resolve_leave_type(db, req.leave_type)
                if not req_lt or req_lt.id != lt.id:
                    continue

                dur_days = float(req.total_days) if (req.total_days and req.total_days > 0) else (
                    float(round(float(req.duration_hours) / 8.0)) if req.duration_hours and req.duration_hours > 0 else 1.0
                )
                if dur_days <= 0:
                    dur_days = 1.0

                if req.status in ["Approved", "Active", "Completed"]:
                    used_days += dur_days
                elif req.status == "Pending":
                    pending_days += dur_days

            bal.allocated_days = float(round(bal.allocated_days))
            bal.used_days = float(round(used_days))
            bal.pending_days = float(round(pending_days))
            bal.available_days = max(
                0.0,
                float(round(bal.allocated_days + bal.carry_forward_days - bal.used_days - bal.pending_days))
            )

        db.commit()

    @classmethod
    def reserve_pending_balance(
        cls, db: Session, employee_id: int, leave_type_identifier: Any, year: int, days: float
    ) -> EmployeeLeaveBalance:
        """
        Validates and reserves leave balance when an application is submitted.
        Reduces available_days by increasing pending_days.
        """
        lt = cls.resolve_leave_type(db, leave_type_identifier)
        if not lt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid leave type '{leave_type_identifier}'"
            )

        balances = cls.get_or_initialize_yearly_balances(db, employee_id, year)
        bal = next((b for b in balances if b.leave_type_id == lt.id), None)
        if not bal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No leave allocation found for {lt.name} in year {year}"
            )

        if days > (bal.available_days + 1e-4):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient {lt.name} balance. Requested {days:.1f} days, but only {bal.available_days:.1f} days available for year {year}."
            )

        bal.pending_days = round(bal.pending_days + days, 1)
        bal.available_days = max(
            0.0,
            round(bal.allocated_days + bal.carry_forward_days - bal.used_days - bal.pending_days, 1)
        )
        db.commit()
        db.refresh(bal)
        return bal

    @classmethod
    def consume_approved_balance(
        cls, db: Session, employee_id: int, leave_type_identifier: Any, year: int, days: float
    ) -> EmployeeLeaveBalance:
        """
        Transfers reserved pending balance into used balance upon manager/HR approval.
        """
        lt = cls.resolve_leave_type(db, leave_type_identifier)
        if not lt:
            return None

        balances = cls.get_or_initialize_yearly_balances(db, employee_id, year)
        bal = next((b for b in balances if b.leave_type_id == lt.id), None)
        if not bal:
            return None

        bal.pending_days = max(0.0, round(bal.pending_days - days, 1))
        bal.used_days = round(bal.used_days + days, 1)
        bal.available_days = max(
            0.0,
            round(bal.allocated_days + bal.carry_forward_days - bal.used_days - bal.pending_days, 1)
        )
        db.commit()
        db.refresh(bal)
        return bal

    @classmethod
    def release_rejected_balance(
        cls, db: Session, employee_id: int, leave_type_identifier: Any, year: int, days: float
    ) -> EmployeeLeaveBalance:
        """
        Releases reserved pending balance back to available balance upon rejection or cancellation.
        """
        lt = cls.resolve_leave_type(db, leave_type_identifier)
        if not lt:
            return None

        balances = cls.get_or_initialize_yearly_balances(db, employee_id, year)
        bal = next((b for b in balances if b.leave_type_id == lt.id), None)
        if not bal:
            return None

        bal.pending_days = max(0.0, round(bal.pending_days - days, 1))
        bal.available_days = max(
            0.0,
            round(bal.allocated_days + bal.carry_forward_days - bal.used_days - bal.pending_days, 1)
        )
        db.commit()
        db.refresh(bal)
        return bal

    @classmethod
    def release_cancelled_approved_balance(
        cls, db: Session, employee_id: int, leave_type_identifier: Any, year: int, days: float
    ) -> EmployeeLeaveBalance:
        """
        Releases consumed balance back to available when an approved request is cancelled.
        """
        lt = cls.resolve_leave_type(db, leave_type_identifier)
        if not lt:
            return None

        balances = cls.get_or_initialize_yearly_balances(db, employee_id, year)
        bal = next((b for b in balances if b.leave_type_id == lt.id), None)
        if not bal:
            return None

        bal.used_days = max(0.0, round(bal.used_days - days, 1))
        bal.available_days = max(
            0.0,
            round(bal.allocated_days + bal.carry_forward_days - bal.used_days - bal.pending_days, 1)
        )
        db.commit()
        db.refresh(bal)
        return bal

    @classmethod
    def get_employee_balances_summary(
        cls, db: Session, employee_id: int, year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Returns a clean list of yearly balances with leave metadata for dashboard and modal consumption.
        """
        if year is None:
            year = date.today().year

        balances = cls.get_or_initialize_yearly_balances(db, employee_id, year)
        result = []
        for bal in balances:
            lt = bal.leave_type
            if not lt or lt.is_active is False:
                continue

            # Exclude WFH and hourly leave types completely
            code_upper = (lt.code or "").upper()
            name_lower = (lt.name or "").lower()
            unit_lower = (lt.unit_type or "").lower()
            if code_upper == "WFH" or "work from home" in name_lower or "wfh" in name_lower or unit_lower == "hourly":
                continue

            result.append({
                "leave_type_id": lt.id,
                "code": lt.code,
                "name": lt.name,
                "unit_type": lt.unit_type,
                "year": bal.year,
                "allocated_days": int(round(bal.allocated_days or 0.0)),
                "used_days": int(round(bal.used_days or 0.0)),
                "pending_days": int(round(bal.pending_days or 0.0)),
                "available_days": int(round(bal.available_days or 0.0)),
                "carry_forward_days": int(round(bal.carry_forward_days or 0.0)),
                "counts_as_leave": lt.counts_as_leave,
                "attendance_required": lt.attendance_required,
                "remote_punch_allowed": lt.remote_punch_allowed,
                "applicable_employee_type": lt.applicable_employee_type,
            })

        # Priority sort: CL -> SL -> EL -> CO -> HD -> Others
        def sort_key(item: Dict[str, Any]) -> int:
            c = (item["code"] or "").upper()
            n = (item["name"] or "").lower()
            if c == "CL" or "casual" in n:
                return 1
            if c == "SL" or "sick" in n:
                return 2
            if c in ("EL", "PL") or "earned" in n or "privilege" in n:
                return 3
            if c == "CO" or "comp" in n:
                return 4
            if c == "HD" or "half" in n:
                return 5
            return 6

        result.sort(key=sort_key)
        return result
