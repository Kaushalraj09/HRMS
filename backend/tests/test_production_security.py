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


def test_production_config_rejects_placeholder_jwt_secret(monkeypatch):
    from app.core.config import Settings
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://hrms:pass@localhost:5432/hrms")
    monkeypatch.setenv("JWT_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_JWT_SECRET_MIN_32_CHARACTERS_LONG")
    monkeypatch.setenv("FRONTEND_URL", "https://hrms.aivan360.com")
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "https://hrms.aivan360.com")
    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_USER", "alerts@aivan360.com")
    monkeypatch.setenv("SMTP_PASSWORD", "valid_smtp_pass_123")
    monkeypatch.setenv("SMTP_FROM", "no-reply@aivan360.com")

    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings()


def test_production_config_rejects_placeholder_smtp(monkeypatch):
    from app.core.config import Settings
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://hrms:pass@localhost:5432/hrms")
    monkeypatch.setenv("JWT_SECRET_KEY", "super_secret_production_key_random_string_exceeding_32_chars")
    monkeypatch.setenv("FRONTEND_URL", "https://hrms.aivan360.com")
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "https://hrms.aivan360.com")
    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_USER", "alerts@aivan360.com")
    monkeypatch.setenv("SMTP_PASSWORD", "CHANGE_ME_SMTP_PASSWORD")
    monkeypatch.setenv("SMTP_FROM", "no-reply@aivan360.com")

    with pytest.raises(ValueError, match="SMTP configuration"):
        Settings()


def test_production_config_succeeds_with_secure_settings(monkeypatch):
    from app.core.config import Settings
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://hrms:pass@localhost:5432/hrms")
    monkeypatch.setenv("JWT_SECRET_KEY", "super_secret_production_key_random_string_exceeding_32_chars")
    monkeypatch.setenv("FRONTEND_URL", "https://hrms.aivan360.com")
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "https://hrms.aivan360.com")
    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_USER", "alerts@aivan360.com")
    monkeypatch.setenv("SMTP_PASSWORD", "real_production_smtp_password_987")
    monkeypatch.setenv("SMTP_FROM", "no-reply@aivan360.com")

    settings = Settings()
    assert settings.APP_ENV == "production"
    assert settings.FRONTEND_URL == "https://hrms.aivan360.com"

