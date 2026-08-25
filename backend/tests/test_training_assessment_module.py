import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.api.deps import get_current_user
from app.models.user import User, Role
from app.models.employee import Employee
from app.models.training import (
    Training,
    TrainingMaterial,
    TrainingAssignment,
    Assessment,
    AssessmentQuestion,
    AssessmentOption,
    AssessmentAttempt
)


@pytest.fixture(name="db_session")
def fixture_db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Seed roles
    admin_role = Role(name="Admin")
    hr_role = Role(name="HR")
    emp_role = Role(name="Employee")
    db.add_all([admin_role, hr_role, emp_role])
    db.commit()

    # Seed users
    user_hr = User(email="hr@example.com", password_hash="pw", display_name="HR Manager", role_id=hr_role.id)
    user_emp1 = User(email="emp1@example.com", password_hash="pw", display_name="Rahul Sharma", role_id=emp_role.id)
    user_emp2 = User(email="emp2@example.com", password_hash="pw", display_name="Priya Singh", role_id=emp_role.id)
    db.add_all([user_hr, user_emp1, user_emp2])
    db.commit()

    # Seed employees
    emp1 = Employee(
        user_id=user_emp1.id,
        first_name="Rahul",
        last_name="Sharma",
        employee_code="EMP001",
        official_email="emp1@example.com",
        mobile="9876543210",
        department="Engineering",
        status="Active"
    )
    emp2 = Employee(
        user_id=user_emp2.id,
        first_name="Priya",
        last_name="Singh",
        employee_code="EMP002",
        official_email="emp2@example.com",
        mobile="9876543211",
        department="HR",
        status="Active"
    )
    db.add_all([emp1, emp2])
    db.commit()

    yield db
    db.close()


@pytest.fixture(name="client")
def fixture_client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# ─── 1. HR Training CRUD Tests ──────────────────────────────────────────────

def test_hr_create_and_list_training(client, db_session):
    user_hr = db_session.query(User).filter(User.email == "hr@example.com").first()
    app.dependency_overrides[get_current_user] = lambda: user_hr

    payload = {
        "title": "Workplace Safety Training",
        "code": "TRN-SAFETY-01",
        "category": "Safety",
        "description": "Basic safety procedures",
        "learning_objective": "Understand emergency exits and fire drills",
        "trainer_name": "Safety Team",
        "estimated_duration_minutes": 45,
        "status": "Published"
    }

    res = client.post("/api/v1/trainings", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "Workplace Safety Training"
    assert data["code"] == "TRN-SAFETY-01"

    # List trainings
    list_res = client.get("/api/v1/trainings")
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1


def test_file_upload_validation_and_reorder(client, db_session):
    user_hr = db_session.query(User).filter(User.email == "hr@example.com").first()
    app.dependency_overrides[get_current_user] = lambda: user_hr

    # Create training
    t = Training(title="Tech Training", code="TRN-01", created_by_user_id=user_hr.id, status="Published")
    db_session.add(t)
    db_session.commit()

    # Attempt forbidden executable upload
    exe_file = ("script.exe", io.BytesIO(b"executable content"), "application/octet-stream")
    res_exe = client.post(
        f"/api/v1/trainings/{t.id}/materials",
        files={"file": exe_file},
        data={"description": "Malicious file", "is_required": "true"}
    )
    assert res_exe.status_code == 400
    assert "not permitted" in res_exe.json()["detail"].lower()

    # Upload valid PDF
    pdf_file = ("Safety_Guide.pdf", io.BytesIO(b"%PDF-1.4 dummy pdf content"), "application/pdf")
    res_pdf = client.post(
        f"/api/v1/trainings/{t.id}/materials",
        files={"file": pdf_file},
        data={"description": "PDF manual", "is_required": "true"}
    )
    assert res_pdf.status_code == 200
    assert res_pdf.json()["file_name"] == "Safety_Guide.pdf"


# ─── 2. Assignment Tests ────────────────────────────────────────────────────

def test_assign_training_to_department(client, db_session):
    user_hr = db_session.query(User).filter(User.email == "hr@example.com").first()
    app.dependency_overrides[get_current_user] = lambda: user_hr

    t = Training(title="Engineering Onboarding", code="TRN-ENG", created_by_user_id=user_hr.id, status="Published")
    db_session.add(t)
    db_session.commit()

    assign_payload = {
        "assignment_type": "Department",
        "departments": ["Engineering"]
    }
    res = client.post(f"/api/v1/trainings/{t.id}/assign", json=assign_payload)
    assert res.status_code == 200
    assert res.json()["assigned_count"] == 1  # Only emp1 (Rahul) is in Engineering

    assignments = client.get(f"/api/v1/trainings/{t.id}/assignments").json()
    assert len(assignments) == 1
    assert assignments[0]["employee_name"] == "Rahul Sharma"


# ─── 3. Assessment & MCQ Question Builder Tests ─────────────────────────────

def test_assessment_builder_4_options_validation(client, db_session):
    user_hr = db_session.query(User).filter(User.email == "hr@example.com").first()
    app.dependency_overrides[get_current_user] = lambda: user_hr

    t = Training(title="Compliance 101", code="TRN-COMP", created_by_user_id=user_hr.id, status="Published")
    db_session.add(t)
    db_session.commit()

    # Create assessment
    assess_payload = {
        "title": "Compliance Quiz",
        "duration_minutes": 15,
        "passing_percentage": 60.0,
        "max_attempts": 1,
        "show_result": True,
        "show_correct_answers": True
    }
    res_a = client.post(f"/api/v1/trainings/{t.id}/assessment", json=assess_payload)
    assert res_a.status_code == 200
    assessment_id = res_a.json()["assessment_id"]

    # Invalid question with 3 options
    invalid_q = {
        "question_text": "Is compliance mandatory?",
        "marks": 1.0,
        "difficulty": "Easy",
        "options": [
            {"option_key": "A", "option_text": "Yes", "is_correct": True},
            {"option_key": "B", "option_text": "No", "is_correct": False},
            {"option_key": "C", "option_text": "Optional", "is_correct": False}
        ]
    }
    res_iq = client.post(f"/api/v1/trainings/assessments/{assessment_id}/questions", json=invalid_q)
    assert res_iq.status_code == 422  # Validation error: must have 4 options

    # Valid question with 4 options and exactly 1 correct answer
    valid_q = {
        "question_text": "What should you do in case of a fire emergency?",
        "marks": 1.0,
        "difficulty": "Medium",
        "options": [
            {"option_key": "A", "option_text": "Continue working", "is_correct": False},
            {"option_key": "B", "option_text": "Use emergency exit", "is_correct": True},
            {"option_key": "C", "option_text": "Hide under desk", "is_correct": False},
            {"option_key": "D", "option_text": "Wait for instructions", "is_correct": False}
        ]
    }
    res_vq = client.post(f"/api/v1/trainings/assessments/{assessment_id}/questions", json=valid_q)
    assert res_vq.status_code == 200
    assert "question_id" in res_vq.json()


# ─── 4. Employee Exam Security & Evaluation Tests ───────────────────────────

def test_employee_exam_security_no_correct_answers_exposed(client, db_session):
    user_hr = db_session.query(User).filter(User.email == "hr@example.com").first()
    user_emp1 = db_session.query(User).filter(User.email == "emp1@example.com").first()
    emp1 = db_session.query(Employee).filter(Employee.user_id == user_emp1.id).first()

    # 1. Setup training, assignment, assessment & question as HR
    app.dependency_overrides[get_current_user] = lambda: user_hr
    t = Training(title="Fire Safety", code="TRN-FIRE", created_by_user_id=user_hr.id, status="Published")
    db_session.add(t)
    db_session.commit()

    db_session.add(TrainingAssignment(training_id=t.id, employee_id=emp1.id, status="IN_PROGRESS"))
    a = Assessment(training_id=t.id, title="Fire Test", duration_minutes=20, passing_percentage=50, max_attempts=1, created_by_user_id=user_hr.id)
    db_session.add(a)
    db_session.commit()

    q = AssessmentQuestion(assessment_id=a.id, question_text="What to do during fire?", marks=1.0)
    db_session.add(q)
    db_session.commit()

    o1 = AssessmentOption(question_id=q.id, option_key="A", option_text="Run", is_correct=False)
    o2 = AssessmentOption(question_id=q.id, option_key="B", option_text="Use Exit", is_correct=True)
    o3 = AssessmentOption(question_id=q.id, option_key="C", option_text="Wait", is_correct=False)
    o4 = AssessmentOption(question_id=q.id, option_key="D", option_text="Panic", is_correct=False)
    db_session.add_all([o1, o2, o3, o4])
    db_session.commit()

    # 2. Switch to Employee user
    app.dependency_overrides[get_current_user] = lambda: user_emp1

    # Start assessment attempt
    start_res = client.post(f"/api/v1/trainings/assessments/{a.id}/attempts/start")
    assert start_res.status_code == 200
    exam_payload = start_res.json()
    attempt_id = exam_payload["attempt_id"]

    # SECURITY ASSERTION: Verify 'is_correct' is NOT in options payload!
    for question in exam_payload["questions"]:
        for opt in question["options"]:
            assert "is_correct" not in opt, "SECURITY VIOLATION: is_correct field was leaked to employee API!"

    # Save answer draft (Select option B - id=o2.id)
    save_res = client.post(
        f"/api/v1/trainings/attempts/{attempt_id}/save-answer",
        json={"question_id": q.id, "selected_option_id": o2.id}
    )
    assert save_res.status_code == 200

    # Submit assessment attempt
    sub_res = client.post(f"/api/v1/trainings/attempts/{attempt_id}/submit")
    assert sub_res.status_code == 200
    result = sub_res.json()

    assert result["score"] == 1.0
    assert result["percentage"] == 100.0
    assert result["passed"] is True


# ─── 5. Security & RBAC Boundary Tests ──────────────────────────────────────

def test_employee_cannot_access_hr_creation_api(client, db_session):
    user_emp1 = db_session.query(User).filter(User.email == "emp1@example.com").first()
    app.dependency_overrides[get_current_user] = lambda: user_emp1

    payload = {
        "title": "Unauthorized Training",
        "code": "TRN-UNAUTH",
        "category": "Technical",
        "status": "Published"
    }

    res = client.post("/api/v1/trainings", json=payload)
    assert res.status_code == 403
    assert "access denied" in res.json()["detail"].lower()
