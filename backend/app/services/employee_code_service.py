from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.employee import Employee, EmployeeCodeSequence, EmployeeCodeHistory
from app.utils.employee_code import (
    format_employee_code,
    normalize_employee_code,
    extract_employee_code_number,
)


def get_or_create_sequence(
    db: Session, prefix: str = "AIVAN", padding: int = 3
) -> EmployeeCodeSequence:
    """Retrieve existing sequence or initialize from highest existing employee code."""
    clean_prefix = (prefix or "AIVAN").strip().upper()
    seq = (
        db.query(EmployeeCodeSequence)
        .filter(EmployeeCodeSequence.prefix == clean_prefix)
        .first()
    )
    if not seq:
        # Determine highest existing code in Employee table matching prefix
        highest_num = 0
        all_codes = db.query(Employee.employee_code).all()
        for (c,) in all_codes:
            num = extract_employee_code_number(c, clean_prefix)
            if num is not None and num > highest_num:
                highest_num = num

        next_val = (highest_num + 1) if highest_num > 0 else 1
        seq = EmployeeCodeSequence(
            prefix=clean_prefix,
            next_number=next_val,
            padding=padding,
            active=True,
        )
        db.add(seq)
        db.commit()
        db.refresh(seq)
    return seq


def allocate_next_employee_code(db: Session, prefix: str = "AIVAN") -> str:
    """Atomically allocates and increments the next sequential employee code.
    
    Uses database row-level locking (SELECT ... FOR UPDATE) to guarantee that
    concurrent creations never receive duplicate codes.
    """
    clean_prefix = (prefix or "AIVAN").strip().upper()

    # Query with row lock
    seq = (
        db.query(EmployeeCodeSequence)
        .filter(
            EmployeeCodeSequence.prefix == clean_prefix,
            EmployeeCodeSequence.active == True,
        )
        .with_for_update()
        .first()
    )

    if not seq:
        # Fallback creation if not yet initialized
        try:
            seq = get_or_create_sequence(db, prefix=clean_prefix)
        except Exception:
            db.rollback()
            seq = (
                db.query(EmployeeCodeSequence)
                .filter(EmployeeCodeSequence.prefix == clean_prefix)
                .first()
            )

        # Re-lock
        if seq:
            seq = (
                db.query(EmployeeCodeSequence)
                .filter(EmployeeCodeSequence.id == seq.id)
                .with_for_update()
                .first()
            )

    current_number = seq.next_number
    code = format_employee_code(
        current_number, prefix=clean_prefix, padding=seq.padding or 3
    )

    # Double check uniqueness against Employee table to never reuse or overwrite
    while db.query(Employee).filter(func.upper(Employee.employee_code) == code.upper()).first():
        current_number += 1
        code = format_employee_code(
            current_number, prefix=clean_prefix, padding=seq.padding or 3
        )

    # Advance sequence to next number
    seq.next_number = current_number + 1
    seq.updated_at = func.now()
    db.flush()

    return code


def record_code_history(
    db: Session,
    employee_id: int,
    old_code: Optional[str],
    new_code: str,
    reason: str,
    changed_by: str,
) -> EmployeeCodeHistory:
    """Record an audit trail entry for an employee code assignment or modification."""
    history = EmployeeCodeHistory(
        employee_id=employee_id,
        old_employee_code=old_code,
        new_employee_code=new_code,
        reason=reason,
        changed_by=changed_by,
    )
    db.add(history)
    db.flush()
    return history


def change_employee_code(
    db: Session,
    employee_id: int,
    new_code: str,
    reason: str,
    changed_by: str,
) -> Employee:
    """Authorized change of an employee code with audit logging and uniqueness enforcement."""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise ValueError(f"Employee with ID {employee_id} not found")

    if not new_code or not new_code.strip():
        raise ValueError("New employee code cannot be empty")

    if not reason or not reason.strip():
        raise ValueError("Reason is mandatory when changing an employee code")

    normalized_new_code = normalize_employee_code(new_code)
    current_code = employee.employee_code

    if normalized_new_code.upper() == (current_code or "").upper():
        raise ValueError(f"Employee already has code {current_code}")

    # Check uniqueness
    duplicate = (
        db.query(Employee)
        .filter(
            func.upper(Employee.employee_code) == normalized_new_code.upper(),
            Employee.id != employee_id,
        )
        .first()
    )
    if duplicate:
        raise ValueError(
            f"Employee code '{normalized_new_code}' is already assigned to {duplicate.first_name} {duplicate.last_name}"
        )

    # If legacy_employee_code is not set and current code was non-AIVAN, preserve it
    if not employee.legacy_employee_code and current_code:
        employee.legacy_employee_code = current_code

    # Apply change
    employee.employee_code = normalized_new_code
    employee.updated_at = func.now()

    # Record history
    record_code_history(
        db=db,
        employee_id=employee.id,
        old_code=current_code,
        new_code=normalized_new_code,
        reason=reason.strip(),
        changed_by=changed_by,
    )

    db.commit()
    db.refresh(employee)
    return employee


def get_code_history_for_employee(
    db: Session, employee_id: int
) -> List[EmployeeCodeHistory]:
    """Retrieve full audit history of code changes for an employee."""
    return (
        db.query(EmployeeCodeHistory)
        .filter(EmployeeCodeHistory.employee_id == employee_id)
        .order_by(EmployeeCodeHistory.changed_at.desc())
        .all()
    )
