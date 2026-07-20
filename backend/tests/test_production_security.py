from types import SimpleNamespace

import pytest


def test_employee_cannot_select_another_employee_for_attendance():
    from app.core.access import resolve_attendance_employee_id

    employee_user = SimpleNamespace(id=10, role=SimpleNamespace(name="employee"))

    with pytest.raises(PermissionError):
        resolve_attendance_employee_id(employee_user, own_employee_id=5, requested_employee_id=8)


def test_hr_can_select_an_employee_only_for_explicit_correction():
    from app.core.access import resolve_attendance_employee_id

    hr_user = SimpleNamespace(id=20, role=SimpleNamespace(name="hr"))

    with pytest.raises(PermissionError):
        resolve_attendance_employee_id(hr_user, own_employee_id=None, requested_employee_id=8)

    assert resolve_attendance_employee_id(
        hr_user,
        own_employee_id=None,
        requested_employee_id=8,
        allow_correction=True,
    ) == 8


def test_credentials_response_never_contains_a_password():
    from app.schemas.employee import EmployeeCredentialsResponse

    payload = EmployeeCredentialsResponse(
        employee_id=1,
        employee_code="EMP-0001",
        employee_name="Test Employee",
        username="employee@example.com",
        email="employee@example.com",
        activation_required=True,
        status="Active",
    )

    assert "password" not in payload.model_dump()
