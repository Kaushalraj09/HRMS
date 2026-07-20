from app.core.enums import UserRole


PRIVILEGED_ROLES = {UserRole.ADMIN, UserRole.HR}


def resolve_attendance_employee_id(current_user, own_employee_id, requested_employee_id, allow_correction=False):
    """Resolve attendance ownership without trusting a client-supplied employee ID."""
    role_name = (current_user.role.name if current_user.role else "").lower()
    if role_name in PRIVILEGED_ROLES and allow_correction and requested_employee_id:
        return requested_employee_id
    if own_employee_id is None:
        raise PermissionError("Only employees can mark attendance")
    if requested_employee_id and requested_employee_id != own_employee_id:
        raise PermissionError("You cannot mark attendance for another employee")
    return own_employee_id
