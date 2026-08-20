import io
import pytest
from datetime import datetime, date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app import models  # noqa: F401
from app.models.user import User, Role
from app.models.employee import Employee
from app.models.document import DocumentType, EmployeeDocument, EmployeeDocumentRequirement, EmployeeDocumentVersion
from app.core.security import hash_password, create_access_token
from app.services.document_service import seed_default_document_types, initialize_employee_requirements, get_employee_documents_data
from app.main import app

from sqlalchemy.pool import StaticPool

# In-memory SQLite for isolated unit testing with StaticPool
@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        # Seed basic roles
        admin_role = Role(id=1, name="Admin")
        hr_role = Role(id=2, name="HR")
        emp_role = Role(id=3, name="Employee")
        db.add_all([admin_role, hr_role, emp_role])
        db.commit()

        # Seed document types
        seed_default_document_types(db)
        db.commit()

        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_data(db_session):
    # 1. Admin User
    admin_user = User(
        email="admin@test.com",
        password_hash=hash_password("admin123"),
        display_name="Admin User",
        role_id=1,
        status="Active"
    )
    # 2. HR User
    hr_user = User(
        email="hr@test.com",
        password_hash=hash_password("hr123"),
        display_name="HR User",
        role_id=2,
        status="Active"
    )
    # 3. Employee 1 User & Profile
    emp1_user = User(
        email="emp1@test.com",
        password_hash=hash_password("emp123"),
        display_name="Employee One",
        role_id=3,
        status="Active"
    )
    # 4. Employee 2 User & Profile
    emp2_user = User(
        email="emp2@test.com",
        password_hash=hash_password("emp123"),
        display_name="Employee Two",
        role_id=3,
        status="Active"
    )
    db_session.add_all([admin_user, hr_user, emp1_user, emp2_user])
    db_session.commit()

    emp1 = Employee(
        user_id=emp1_user.id,
        employee_code="0001",
        first_name="Employee",
        last_name="One",
        official_email="emp1@test.com",
        mobile="9876543210",
        department="Engineering",
        designation="Software Engineer",
        status="Active"
    )
    emp2 = Employee(
        user_id=emp2_user.id,
        employee_code="0002",
        first_name="Employee",
        last_name="Two",
        official_email="emp2@test.com",
        mobile="9876543211",
        department="Design",
        designation="UI Designer",
        status="Active"
    )
    db_session.add_all([emp1, emp2])
    db_session.commit()

    # Initialize requirements
    initialize_employee_requirements(db_session, emp1.id)
    initialize_employee_requirements(db_session, emp2.id)

    admin_token = create_access_token(admin_user.email)
    hr_token = create_access_token(hr_user.email)
    emp1_token = create_access_token(emp1_user.email)
    emp2_token = create_access_token(emp2_user.email)

    return {
        "admin_user": admin_user,
        "hr_user": hr_user,
        "emp1_user": emp1_user,
        "emp2_user": emp2_user,
        "emp1": emp1,
        "emp2": emp2,
        "admin_token": admin_token,
        "hr_token": hr_token,
        "emp1_token": emp1_token,
        "emp2_token": emp2_token,
    }


# ─── 1. Document Types & Requirements Tests ──────────────────────────────────

def test_document_types_seeded_and_listed(client, test_data):
    res = client.get(
        "/api/v1/documents/types",
        headers={"Authorization": f"Bearer {test_data['emp1_token']}"}
    )
    assert res.status_code == 200
    types = res.json()
    assert len(types) >= 10
    names = [t["name"] for t in types]
    assert "Aadhaar Card" in names
    assert "PAN Card" in names
    assert "Bank Passbook / Cancelled Cheque" in names


def test_employee_initial_documents_summary(client, test_data):
    res = client.get(
        "/api/v1/documents/my-documents",
        headers={"Authorization": f"Bearer {test_data['emp1_token']}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["employee_id"] == test_data["emp1"].id
    assert data["summary"]["completion_percentage"] == 0.0
    assert data["summary"]["total_required"] > 0
    assert data["summary"]["missing"] == data["summary"]["total_required"]


# ─── 2. Document Upload & Validation Tests ───────────────────────────────────

def test_employee_upload_valid_document(client, test_data, db_session):
    doc_type = db_session.query(DocumentType).filter(DocumentType.code == "AADHAAR").first()
    assert doc_type is not None

    file_content = b"%PDF-1.4 dummy pdf content for testing document upload"
    files = {"file": ("aadhaar.pdf", io.BytesIO(file_content), "application/pdf")}
    data = {"document_type_id": str(doc_type.id), "remarks": "My Aadhaar"}

    res = client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {test_data['emp1_token']}"},
        files=files,
        data=data
    )
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["success"] is True
    assert res_data["status"] == "PENDING_REVIEW"
    assert res_data["version"] == 1

    # Verify requirement is now PENDING_REVIEW
    summary_res = client.get(
        "/api/v1/documents/my-documents",
        headers={"Authorization": f"Bearer {test_data['emp1_token']}"}
    )
    summary_data = summary_res.json()
    assert summary_data["summary"]["pending_review"] == 1
    assert summary_data["summary"]["uploaded"] == 1


def test_employee_upload_invalid_extension_rejected(client, test_data, db_session):
    doc_type = db_session.query(DocumentType).filter(DocumentType.code == "PHOTO").first()
    assert doc_type is not None

    # Try uploading an executable/unsupported format like .exe
    files = {"file": ("malicious.exe", io.BytesIO(b"executable content"), "application/octet-stream")}
    data = {"document_type_id": str(doc_type.id)}

    res = client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {test_data['emp1_token']}"},
        files=files,
        data=data
    )
    assert res.status_code == 400
    assert "Invalid file extension" in res.json()["detail"]


# ─── 3. Verification & Rejection Workflows ───────────────────────────────────

def test_hr_verification_workflow(client, test_data, db_session):
    doc_type = db_session.query(DocumentType).filter(DocumentType.code == "PAN").first()

    # Employee uploads PAN
    files = {"file": ("pan_card.png", io.BytesIO(b"dummy image bytes"), "image/png")}
    upload_res = client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {test_data['emp1_token']}"},
        files=files,
        data={"document_type_id": str(doc_type.id)}
    )
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["document_id"]

    # Employee cannot verify own document
    emp_verify_res = client.post(
        f"/api/v1/documents/hr/{doc_id}/verify",
        headers={"Authorization": f"Bearer {test_data['emp1_token']}"},
        json={"remarks": "Attempt self-verify"}
    )
    assert emp_verify_res.status_code == 403

    # HR verifies document
    hr_verify_res = client.post(
        f"/api/v1/documents/hr/{doc_id}/verify",
        headers={"Authorization": f"Bearer {test_data['hr_token']}"},
        json={"remarks": "PAN card verified against database"}
    )
    assert hr_verify_res.status_code == 200
    assert hr_verify_res.json()["status"] == "VERIFIED"

    # Verify completion percentage increased
    summary_res = client.get(
        "/api/v1/documents/my-documents",
        headers={"Authorization": f"Bearer {test_data['emp1_token']}"}
    )
    summary = summary_res.json()["summary"]
    assert summary["verified"] == 1
    assert summary["completion_percentage"] > 0


def test_hr_rejection_and_employee_resubmission(client, test_data, db_session):
    doc_type = db_session.query(DocumentType).filter(DocumentType.code == "AADHAAR").first()

    # 1. Employee uploads Version 1
    files1 = {"file": ("aadhaar_blurry.jpg", io.BytesIO(b"version 1 blurry content"), "image/jpeg")}
    up1 = client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {test_data['emp1_token']}"},
        files=files1,
        data={"document_type_id": str(doc_type.id)}
    )
    doc_id = up1.json()["document_id"]

    # 2. HR rejects without reason -> should fail validation
    bad_reject = client.post(
        f"/api/v1/documents/hr/{doc_id}/reject",
        headers={"Authorization": f"Bearer {test_data['hr_token']}"},
        json={"reason": ""}
    )
    assert bad_reject.status_code == 400

    # 3. HR rejects with reason
    hr_reject = client.post(
        f"/api/v1/documents/hr/{doc_id}/reject",
        headers={"Authorization": f"Bearer {test_data['hr_token']}"},
        json={"reason": "Uploaded document is blurry and not readable."}
    )
    assert hr_reject.status_code == 200
    assert hr_reject.json()["status"] == "REJECTED"

    # Check employee sees rejection reason
    emp_summary = client.get(
        "/api/v1/documents/my-documents",
        headers={"Authorization": f"Bearer {test_data['emp1_token']}"}
    ).json()
    aadhaar_item = next(d for d in emp_summary["documents"] if d["document_type_code"] == "AADHAAR")
    assert aadhaar_item["status"] == "REJECTED"
    assert "blurry" in aadhaar_item["rejection_reason"]

    # 4. Employee re-uploads Version 2 (Resubmission)
    files2 = {"file": ("aadhaar_clear.pdf", io.BytesIO(b"version 2 clear content"), "application/pdf")}
    up2 = client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {test_data['emp1_token']}"},
        files=files2,
        data={"document_type_id": str(doc_type.id)}
    )
    assert up2.status_code == 200
    assert up2.json()["version"] == 2
    assert up2.json()["status"] == "PENDING_REVIEW"

    # 5. Check version history contains both Version 1 (rejected) and Version 2 (pending)
    history_res = client.get(
        f"/api/v1/documents/{doc_id}/history",
        headers={"Authorization": f"Bearer {test_data['emp1_token']}"}
    )
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history) == 2
    assert history[0]["version_number"] == 2
    assert history[1]["version_number"] == 1
    assert history[1]["status"] == "REJECTED"


# ─── 4. Security & Isolation Boundaries ──────────────────────────────────────

def test_cross_employee_document_isolation(client, test_data, db_session):
    doc_type = db_session.query(DocumentType).filter(DocumentType.code == "PAN").first()

    # Employee 1 uploads PAN
    files = {"file": ("emp1_pan.pdf", io.BytesIO(b"emp1 secret doc"), "application/pdf")}
    up_res = client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {test_data['emp1_token']}"},
        files=files,
        data={"document_type_id": str(doc_type.id)}
    )
    doc_id = up_res.json()["document_id"]

    # Employee 2 tries to download Employee 1's document -> Forbidden (403)
    e2_dl = client.get(
        f"/api/v1/documents/{doc_id}/download",
        headers={"Authorization": f"Bearer {test_data['emp2_token']}"}
    )
    assert e2_dl.status_code == 403

    # Employee 1 can download own document -> Success (200)
    e1_dl = client.get(
        f"/api/v1/documents/{doc_id}/download",
        headers={"Authorization": f"Bearer {test_data['emp1_token']}"}
    )
    assert e1_dl.status_code == 200
    assert e1_dl.content == b"emp1 secret doc"

    # HR can download Employee 1's document -> Success (200)
    hr_dl = client.get(
        f"/api/v1/documents/{doc_id}/download",
        headers={"Authorization": f"Bearer {test_data['hr_token']}"}
    )
    assert hr_dl.status_code == 200
    assert hr_dl.content == b"emp1 secret doc"


def test_hr_upload_on_behalf_of_employee(client, test_data, db_session):
    doc_type = db_session.query(DocumentType).filter(DocumentType.code == "OFFER_LETTER").first()

    files = {"file": ("offer_letter.pdf", io.BytesIO(b"Signed offer letter"), "application/pdf")}
    hr_up = client.post(
        f"/api/v1/documents/hr/employees/{test_data['emp2'].id}/upload",
        headers={"Authorization": f"Bearer {test_data['hr_token']}"},
        files=files,
        data={"document_type_id": str(doc_type.id), "remarks": "Uploaded by HR upon hiring"}
    )
    assert hr_up.status_code == 200
    assert hr_up.json()["success"] is True

    # Employee 2 sees document
    emp2_docs = client.get(
        "/api/v1/documents/my-documents",
        headers={"Authorization": f"Bearer {test_data['emp2_token']}"}
    ).json()
    offer_doc = next(d for d in emp2_docs["documents"] if d["document_type_code"] == "OFFER_LETTER")
    assert offer_doc["file_name"] == "offer_letter.pdf"
    assert offer_doc["uploaded_by_name"] == "HR User"


def test_hr_kpi_overview_endpoint(client, test_data):
    res = client.get(
        "/api/v1/documents/hr/overview",
        headers={"Authorization": f"Bearer {test_data['hr_token']}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_employees"] == 2
    assert "overall_compliance_rate" in data
