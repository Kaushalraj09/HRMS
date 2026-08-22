from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.training import (
    TrainingCreate,
    TrainingUpdate,
    TrainingResponse,
    TrainingMaterialResponse,
    MaterialReorderRequest,
    AssignTrainingRequest,
    TrainingAssignmentResponse,
    AssessmentCreateUpdate,
    AssessmentQuestionCreate,
    AssessmentHrResponse,
    AssessmentQuestionHrResponse,
    AssessmentAttemptStartResponse,
    SaveAnswerRequest,
    SaveAnswerResponse,
    SubmitAttemptResponse,
    EmployeeTrainingViewResponse,
    MaterialProgressRequest,
    TrainingDashboardKPI
)
import app.services.training_service as service

router = APIRouter(prefix="/trainings", tags=["Trainings & Assessments"])


def _require_hr_admin(user: User):
    role_name = user.role.name.lower() if user.role else ""
    if role_name not in ["admin", "hr"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: HR or Admin privileges required."
        )


def _get_employee_id(user: User) -> int:
    emp_id = user.linked_employee_id
    if not emp_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active employee record linked to user profile."
        )
    return emp_id


# ─── HR Training Management Endpoints ─────────────────────────────────────

@router.post("", response_model=TrainingResponse)
def create_training(
    training_in: TrainingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _require_hr_admin(current_user)
    return service.create_training(db, training_in, current_user)


@router.get("/kpi-dashboard", response_model=TrainingDashboardKPI)
def get_kpi_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _require_hr_admin(current_user)
    return service.get_training_dashboard_kpis(db)


@router.get("/reports/completion")
def get_training_reports(
    training_id: Optional[int] = None,
    department: Optional[str] = None,
    employee_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _require_hr_admin(current_user)
    return service.get_training_reports(db, training_id, department, employee_id, status_filter)


@router.get("", response_model=dict)
def list_trainings(
    search: Optional[str] = None,
    category: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    department: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    items, total = service.list_trainings(db, search, category, status_filter, department, page, limit)
    return {"items": items, "total": total, "page": page, "limit": limit}


@router.get("/{training_id}", response_model=dict)
def get_training_detail(
    training_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    training = service.get_training(db, training_id)
    assigned_count = len(training.assignments)
    completed_count = sum(1 for a in training.assignments if a.status == "COMPLETED")
    return {
        "id": training.id,
        "title": training.title,
        "code": training.code,
        "category": training.category,
        "description": training.description,
        "learning_objective": training.learning_objective,
        "trainer_name": training.trainer_name,
        "estimated_duration_minutes": training.estimated_duration_minutes,
        "start_date": training.start_date,
        "end_date": training.end_date,
        "status": training.status,
        "created_by_user_id": training.created_by_user_id,
        "created_at": training.created_at,
        "updated_at": training.updated_at,
        "materials": training.materials,
        "has_assessment": training.assessment is not None,
        "assigned_count": assigned_count,
        "completed_count": completed_count
    }


@router.put("/{training_id}", response_model=dict)
def update_training(
    training_id: int,
    training_in: TrainingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _require_hr_admin(current_user)
    updated = service.update_training(db, training_id, training_in)
    return {"status": "success", "id": updated.id, "title": updated.title}


@router.delete("/{training_id}")
def archive_training(
    training_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _require_hr_admin(current_user)
    service.archive_training(db, training_id)
    return {"message": f"Training {training_id} archived successfully."}


# ─── Training Material Endpoints ──────────────────────────────────────────

@router.post("/{training_id}/materials", response_model=TrainingMaterialResponse)
async def upload_material(
    training_id: int,
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    is_required: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _require_hr_admin(current_user)
    return await service.upload_training_material(db, training_id, file, current_user, description, is_required)


@router.delete("/{training_id}/materials/{material_id}")
def delete_material(
    training_id: int,
    material_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _require_hr_admin(current_user)
    service.delete_training_material(db, training_id, material_id)
    return {"message": "Material deleted successfully."}


@router.put("/{training_id}/materials/reorder")
def reorder_materials(
    training_id: int,
    reorder_in: MaterialReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _require_hr_admin(current_user)
    service.reorder_training_materials(db, training_id, [i.model_dump() for i in reorder_in.items])
    return {"message": "Materials reordered successfully."}


@router.get("/{training_id}/materials/{material_id}/download")
def download_material(
    training_id: int,
    material_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify assignment or HR rights
    is_hr = current_user.role and current_user.role.name.lower() in ["admin", "hr"]
    if not is_hr:
        emp_id = _get_employee_id(current_user)
        assignment = service.db.query(service.TrainingAssignment).filter(
            service.TrainingAssignment.training_id == training_id,
            service.TrainingAssignment.employee_id == emp_id
        ).first()
        if not assignment:
            raise HTTPException(status_code=403, detail="Access denied.")

    mat = db.query(service.TrainingMaterial).filter(
        service.TrainingMaterial.id == material_id,
        service.TrainingMaterial.training_id == training_id
    ).first()

    if not mat or not service.os.path.exists(mat.storage_path):
        raise HTTPException(status_code=404, detail="File not found.")

    return FileResponse(
        path=mat.storage_path,
        filename=mat.file_name,
        media_type=mat.mime_type
    )


# ─── Training Assignment Endpoints ────────────────────────────────────────

@router.post("/{training_id}/assign")
def assign_training(
    training_id: int,
    assign_in: AssignTrainingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _require_hr_admin(current_user)
    assignments = service.assign_training(db, training_id, assign_in, current_user)
    return {"status": "success", "assigned_count": len(assignments)}


@router.get("/{training_id}/assignments")
def get_assignments(
    training_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _require_hr_admin(current_user)
    return service.get_training_assignments(db, training_id)


# ─── Assessment & MCQ Question Builder (HR) Endpoints ────────────────────

@router.post("/{training_id}/assessment")
def create_or_update_assessment(
    training_id: int,
    assessment_in: AssessmentCreateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _require_hr_admin(current_user)
    assessment = service.create_or_update_assessment(db, training_id, assessment_in, current_user)
    return {"status": "success", "assessment_id": assessment.id, "title": assessment.title}


@router.get("/{training_id}/assessment")
def get_assessment(
    training_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _require_hr_admin(current_user)
    assessment = db.query(service.Assessment).filter(service.Assessment.training_id == training_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="No assessment found for this training.")
    return assessment


@router.post("/assessments/{assessment_id}/questions")
def add_question(
    assessment_id: int,
    question_in: AssessmentQuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _require_hr_admin(current_user)
    question = service.add_question_to_assessment(db, assessment_id, question_in)
    return {"status": "success", "question_id": question.id}


@router.delete("/assessments/{assessment_id}/questions/{question_id}")
def delete_question(
    assessment_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _require_hr_admin(current_user)
    service.delete_assessment_question(db, assessment_id, question_id)
    return {"message": "Question deleted successfully."}


# ─── Employee Endpoints (SECURITY SAFE) ───────────────────────────────────

@router.get("/my/all")
def get_my_trainings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    emp_id = _get_employee_id(current_user)
    return service.get_employee_trainings(db, emp_id)


@router.get("/my/{training_id}")
def get_my_training_detail(
    training_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    emp_id = _get_employee_id(current_user)
    return service.get_employee_training_details(db, emp_id, training_id)


@router.post("/my/{training_id}/materials/{material_id}/progress")
def record_material_progress(
    training_id: int,
    material_id: int,
    req: MaterialProgressRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    emp_id = _get_employee_id(current_user)
    return service.record_material_progress(db, emp_id, training_id, material_id, req)


# ─── Assessment Exam Attempt & Evaluation Endpoints ─────────────────────

@router.post("/assessments/{assessment_id}/attempts/start")
def start_attempt(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    emp_id = _get_employee_id(current_user)
    return service.start_assessment_attempt(db, assessment_id, emp_id)


@router.post("/attempts/{attempt_id}/save-answer", response_model=SaveAnswerResponse)
def save_answer(
    attempt_id: int,
    req: SaveAnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    emp_id = _get_employee_id(current_user)
    return service.save_assessment_answer(db, attempt_id, emp_id, req)


@router.post("/attempts/{attempt_id}/submit")
def submit_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    emp_id = _get_employee_id(current_user)
    return service.submit_assessment_attempt(db, attempt_id, emp_id)


@router.get("/attempts/{attempt_id}/result")
def get_attempt_result(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    emp_id = current_user.linked_employee_id or 0
    return service.get_assessment_result(db, attempt_id, emp_id, current_user)
