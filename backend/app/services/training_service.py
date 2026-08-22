import os
import uuid
import logging
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, date, timezone, timedelta
from pathlib import Path
import random

from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, and_

from app.models.training import (
    Training,
    TrainingMaterial,
    TrainingAssignment,
    TrainingMaterialProgress,
    Assessment,
    AssessmentQuestion,
    AssessmentOption,
    AssessmentAttempt,
    AssessmentAnswer
)
from app.models.employee import Employee
from app.models.user import User
from app.models.master_data import Department, Designation
from app.schemas.training import (
    TrainingCreate,
    TrainingUpdate,
    AssignTrainingRequest,
    AssessmentCreateUpdate,
    AssessmentQuestionCreate,
    SaveAnswerRequest,
    MaterialProgressRequest,
    TrainingDashboardKPI
)

logger = logging.getLogger(__name__)

STORAGE_BASE_DIR = Path(__file__).resolve().parents[2] / "storage" / "trainings"

ALLOWED_EXTENSIONS = {
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt",
    "jpg", "jpeg", "png", "webp", "svg",
    "mp4", "webm", "mov",
    "mp3", "wav", "m4a", "ogg"
}

ALLOWED_MIME_PREFIXES = [
    "application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument",
    "application/vnd.ms-excel", "application/vnd.ms-powerpoint", "text/plain",
    "image/", "video/", "audio/"
]

FORBIDDEN_EXTENSIONS = {"exe", "bat", "cmd", "sh", "ps1", "vbs", "jar", "msi", "com", "scr"}


def _ensure_storage_dir(training_id: int) -> Path:
    target_dir = STORAGE_BASE_DIR / str(training_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def _run_async_notification(coro):
    """Run an async notification safely from synchronous context."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        asyncio.run_coroutine_threadsafe(coro, loop)
    else:
        loop.run_until_complete(coro)


# ─── 1. Training CRUD & Management ──────────────────────────────────────────

def create_training(db: Session, training_in: TrainingCreate, current_user: User) -> Training:
    existing = db.query(Training).filter(Training.code == training_in.code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Training with code '{training_in.code}' already exists.")

    training = Training(
        **training_in.model_dump(),
        created_by_user_id=current_user.id
    )
    db.add(training)
    db.commit()
    db.refresh(training)
    return training


def update_training(db: Session, training_id: int, training_in: TrainingUpdate) -> Training:
    training = db.query(Training).filter(Training.id == training_id).first()
    if not training:
        raise HTTPException(status_code=404, detail="Training not found.")

    update_data = training_in.model_dump(exclude_unset=True)
    if "code" in update_data and update_data["code"] != training.code:
        existing = db.query(Training).filter(Training.code == update_data["code"]).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Training with code '{update_data['code']}' already exists.")

    for field, val in update_data.items():
        setattr(training, field, val)

    db.commit()
    db.refresh(training)
    return training


def get_training(db: Session, training_id: int) -> Training:
    training = (
        db.query(Training)
        .options(
            joinedload(Training.materials),
            joinedload(Training.assessment).joinedload(Assessment.questions).joinedload(AssessmentQuestion.options)
        )
        .filter(Training.id == training_id)
        .first()
    )
    if not training:
        raise HTTPException(status_code=404, detail="Training not found.")
    return training


def list_trainings(
    db: Session,
    search: Optional[str] = None,
    category: Optional[str] = None,
    status_filter: Optional[str] = None,
    department: Optional[str] = None,
    page: int = 1,
    limit: int = 50
) -> Tuple[List[Dict[str, Any]], int]:
    query = db.query(Training)

    if search:
        s = f"%{search}%"
        query = query.filter(or_(Training.title.ilike(s), Training.code.ilike(s), Training.description.ilike(s)))

    if category:
        query = query.filter(Training.category == category)

    if status_filter:
        query = query.filter(Training.status == status_filter)

    if department:
        # Filter trainings assigned to employees in department
        query = query.join(TrainingAssignment).join(Employee).filter(Employee.department == department)

    total = query.distinct(Training.id).count()
    offset = (page - 1) * limit
    trainings = query.order_by(Training.created_at.desc()).offset(offset).limit(limit).all()

    result = []
    for t in trainings:
        assigned_count = db.query(TrainingAssignment).filter(TrainingAssignment.training_id == t.id).count()
        completed_count = db.query(TrainingAssignment).filter(
            TrainingAssignment.training_id == t.id,
            TrainingAssignment.status == "COMPLETED"
        ).count()
        completion_pct = round((completed_count / assigned_count * 100), 1) if assigned_count > 0 else 0.0
        has_assessment = db.query(Assessment).filter(Assessment.training_id == t.id).first() is not None

        result.append({
            "id": t.id,
            "title": t.title,
            "code": t.code,
            "category": t.category,
            "description": t.description,
            "learning_objective": t.learning_objective,
            "trainer_name": t.trainer_name,
            "estimated_duration_minutes": t.estimated_duration_minutes,
            "start_date": t.start_date,
            "end_date": t.end_date,
            "status": t.status,
            "created_by_user_id": t.created_by_user_id,
            "created_at": t.created_at,
            "updated_at": t.updated_at,
            "materials": t.materials,
            "has_assessment": has_assessment,
            "assigned_count": assigned_count,
            "completed_count": completed_count,
            "completion_percentage": completion_pct
        })

    return result, total


def archive_training(db: Session, training_id: int) -> Training:
    training = db.query(Training).filter(Training.id == training_id).first()
    if not training:
        raise HTTPException(status_code=404, detail="Training not found.")
    training.status = "Archived"
    db.commit()
    db.refresh(training)
    return training


# ─── 2. Training Material Management ───────────────────────────────────────

async def upload_training_material(
    db: Session,
    training_id: int,
    file: UploadFile,
    current_user: User,
    description: Optional[str] = None,
    is_required: bool = True
) -> TrainingMaterial:
    training = db.query(Training).filter(Training.id == training_id).first()
    if not training:
        raise HTTPException(status_code=404, detail="Training not found.")

    file_name = file.filename or "file"
    ext = file_name.split(".")[-1].lower() if "." in file_name else ""

    if ext in FORBIDDEN_EXTENSIONS or ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File format '.{ext}' is not permitted. Supported formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    mime_type = file.content_type or "application/octet-stream"
    mime_ok = any(mime_type.startswith(prefix) for prefix in ALLOWED_MIME_PREFIXES)
    if not mime_ok and mime_type != "application/octet-stream":
        raise HTTPException(status_code=400, detail=f"MIME type '{mime_type}' is not supported.")

    contents = await file.read()
    file_size = len(contents)

    # 50MB limit
    max_bytes = 50 * 1024 * 1024
    if file_size > max_bytes:
        raise HTTPException(status_code=400, detail="File size exceeds maximum limit of 50 MB.")
    if file_size == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Determine file_type category
    if ext in ["mp4", "webm", "mov"]:
        file_type = "video"
    elif ext in ["mp3", "wav", "m4a", "ogg"]:
        file_type = "audio"
    elif ext in ["jpg", "jpeg", "png", "webp", "svg"]:
        file_type = "image"
    else:
        file_type = "document"

    target_dir = _ensure_storage_dir(training_id)
    unique_filename = f"{uuid.uuid4().hex[:12]}_{file_name.replace(' ', '_')}"
    saved_path = target_dir / unique_filename

    with open(saved_path, "wb") as f:
        f.write(contents)

    # Next display order
    max_order = db.query(func.max(TrainingMaterial.display_order)).filter(
        TrainingMaterial.training_id == training_id
    ).scalar() or 0

    material = TrainingMaterial(
        training_id=training_id,
        file_name=file_name,
        storage_path=str(saved_path),
        file_type=file_type,
        mime_type=mime_type,
        file_size=file_size,
        description=description,
        display_order=max_order + 1,
        is_required=is_required,
        uploaded_by_user_id=current_user.id
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def delete_training_material(db: Session, training_id: int, material_id: int) -> bool:
    material = db.query(TrainingMaterial).filter(
        TrainingMaterial.id == material_id,
        TrainingMaterial.training_id == training_id
    ).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found.")

    if os.path.exists(material.storage_path):
        try:
            os.remove(material.storage_path)
        except Exception as e:
            logger.warning(f"Could not remove physical file {material.storage_path}: {e}")

    db.delete(material)
    db.commit()
    return True


def reorder_training_materials(db: Session, training_id: int, items: List[Dict[str, int]]) -> bool:
    for item in items:
        mat_id = item.get("material_id")
        order = item.get("display_order", 1)
        mat = db.query(TrainingMaterial).filter(
            TrainingMaterial.id == mat_id,
            TrainingMaterial.training_id == training_id
        ).first()
        if mat:
            mat.display_order = order
    db.commit()
    return True


# ─── 3. Training Assignment Management ──────────────────────────────────────

def assign_training(db: Session, training_id: int, req: AssignTrainingRequest, current_user: User) -> List[TrainingAssignment]:
    training = db.query(Training).filter(Training.id == training_id).first()
    if not training:
        raise HTTPException(status_code=404, detail="Training not found.")

    target_employees: List[Employee] = []

    if req.assignment_type == "All":
        target_employees = db.query(Employee).filter(Employee.status == "Active").all()
    elif req.assignment_type == "Selected" and req.employee_ids:
        target_employees = db.query(Employee).filter(
            Employee.id.in_(req.employee_ids),
            Employee.status == "Active"
        ).all()
    elif req.assignment_type == "Department" and req.departments:
        target_employees = db.query(Employee).filter(
            Employee.department.in_(req.departments),
            Employee.status == "Active"
        ).all()
    elif req.assignment_type == "Designation" and req.designations:
        target_employees = db.query(Employee).filter(
            Employee.designation.in_(req.designations),
            Employee.status == "Active"
        ).all()
    else:
        raise HTTPException(status_code=400, detail="Invalid assignment parameters or empty employee list.")

    created_assignments = []
    from app.services.notification_service import create_notification

    for emp in target_employees:
        existing = db.query(TrainingAssignment).filter(
            TrainingAssignment.training_id == training_id,
            TrainingAssignment.employee_id == emp.id
        ).first()
        if not existing:
            assignment = TrainingAssignment(
                training_id=training_id,
                employee_id=emp.id,
                assignment_type=req.assignment_type,
                due_date=req.due_date or training.end_date,
                status="NOT_STARTED",
                progress_percentage=0.0
            )
            db.add(assignment)
            created_assignments.append(assignment)

            # Notify Employee
            if emp.user_id:
                _run_async_notification(create_notification(
                    db=db,
                    user_id=emp.user_id,
                    type="TRAINING_ASSIGNED",
                    title="New Training Program Assigned",
                    message=f"You have been assigned to complete '{training.title}'.",
                    category="TRAINING",
                    severity="INFO",
                    employee_id=emp.id,
                    reference_id=training_id
                ))

    db.commit()
    return created_assignments


def get_training_assignments(db: Session, training_id: int) -> List[Dict[str, Any]]:
    assignments = (
        db.query(TrainingAssignment)
        .options(joinedload(TrainingAssignment.employee))
        .filter(TrainingAssignment.training_id == training_id)
        .all()
    )

    assessment = db.query(Assessment).filter(Assessment.training_id == training_id).first()

    res = []
    for a in assignments:
        emp = a.employee
        assessment_status = "Not Attempted"
        assessment_score = "N/A"

        if assessment:
            last_attempt = (
                db.query(AssessmentAttempt)
                .filter(
                    AssessmentAttempt.assessment_id == assessment.id,
                    AssessmentAttempt.employee_id == a.employee_id
                )
                .order_by(AssessmentAttempt.attempt_number.desc())
                .first()
            )
            if last_attempt:
                assessment_status = "Passed" if last_attempt.passed else "Failed" if last_attempt.status == "SUBMITTED" else "In Progress"
                assessment_score = f"{last_attempt.score}/{last_attempt.total_marks} ({last_attempt.percentage:.0f}%)"

        res.append({
            "id": a.id,
            "training_id": a.training_id,
            "employee_id": a.employee_id,
            "employee_name": f"{emp.first_name} {emp.last_name}" if emp else "Unknown",
            "employee_code": emp.employee_code if emp else "",
            "department": emp.department if emp else "",
            "assignment_type": a.assignment_type,
            "assigned_at": a.assigned_at,
            "due_date": a.due_date,
            "status": a.status,
            "progress_percentage": a.progress_percentage,
            "started_at": a.started_at,
            "completed_at": a.completed_at,
            "assessment_status": assessment_status,
            "assessment_score": assessment_score
        })
    return res


# ─── 4. Assessment & MCQ Question Builder (HR) ────────────────────────────

def create_or_update_assessment(db: Session, training_id: int, data: AssessmentCreateUpdate, current_user: User) -> Assessment:
    training = db.query(Training).filter(Training.id == training_id).first()
    if not training:
        raise HTTPException(status_code=404, detail="Training not found.")

    assessment = db.query(Assessment).filter(Assessment.training_id == training_id).first()
    if assessment:
        for field, val in data.model_dump().items():
            setattr(assessment, field, val)
    else:
        assessment = Assessment(
            training_id=training_id,
            **data.model_dump(),
            created_by_user_id=current_user.id
        )
        db.add(assessment)

    db.commit()
    db.refresh(assessment)
    return assessment


def add_question_to_assessment(db: Session, assessment_id: int, q_in: AssessmentQuestionCreate) -> AssessmentQuestion:
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found.")

    max_order = db.query(func.max(AssessmentQuestion.display_order)).filter(
        AssessmentQuestion.assessment_id == assessment_id
    ).scalar() or 0

    question = AssessmentQuestion(
        assessment_id=assessment_id,
        question_text=q_in.question_text,
        marks=q_in.marks,
        difficulty=q_in.difficulty,
        explanation=q_in.explanation,
        display_order=q_in.display_order or (max_order + 1)
    )
    db.add(question)
    db.flush()

    for idx, opt in enumerate(q_in.options, start=1):
        option = AssessmentOption(
            question_id=question.id,
            option_key=opt.option_key.upper(),
            option_text=opt.option_text,
            is_correct=opt.is_correct,
            display_order=idx
        )
        db.add(option)

    db.commit()
    db.refresh(question)
    return question


def delete_assessment_question(db: Session, assessment_id: int, question_id: int) -> bool:
    q = db.query(AssessmentQuestion).filter(
        AssessmentQuestion.id == question_id,
        AssessmentQuestion.assessment_id == assessment_id
    ).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found.")
    db.delete(q)
    db.commit()
    return True


# ─── 5. Employee Training & Material Viewer Logic ─────────────────────────

def get_employee_trainings(db: Session, employee_id: int) -> List[Dict[str, Any]]:
    assignments = (
        db.query(TrainingAssignment)
        .options(joinedload(TrainingAssignment.training))
        .filter(TrainingAssignment.employee_id == employee_id)
        .order_by(TrainingAssignment.assigned_at.desc())
        .all()
    )

    res = []
    for a in assignments:
        t = a.training
        if not t or t.status == "Archived":
            continue

        assessment = db.query(Assessment).filter(Assessment.training_id == t.id).first()
        assessment_info = None
        if assessment:
            last_attempt = (
                db.query(AssessmentAttempt)
                .filter(
                    AssessmentAttempt.assessment_id == assessment.id,
                    AssessmentAttempt.employee_id == employee_id
                )
                .order_by(AssessmentAttempt.attempt_number.desc())
                .first()
            )
            assessment_info = {
                "assessment_id": assessment.id,
                "title": assessment.title,
                "duration_minutes": assessment.duration_minutes,
                "passing_percentage": assessment.passing_percentage,
                "max_attempts": assessment.max_attempts,
                "attempt_count": db.query(AssessmentAttempt).filter(
                    AssessmentAttempt.assessment_id == assessment.id,
                    AssessmentAttempt.employee_id == employee_id
                ).count(),
                "last_attempt_passed": last_attempt.passed if last_attempt else None,
                "last_attempt_score": f"{last_attempt.score}/{last_attempt.total_marks}" if last_attempt else None
            }

        res.append({
            "assignment_id": a.id,
            "training_id": t.id,
            "title": t.title,
            "code": t.code,
            "category": t.category,
            "description": t.description,
            "trainer_name": t.trainer_name,
            "estimated_duration_minutes": t.estimated_duration_minutes,
            "assigned_at": a.assigned_at,
            "due_date": a.due_date,
            "status": a.status,
            "progress_percentage": a.progress_percentage,
            "completed_at": a.completed_at,
            "assessment": assessment_info
        })
    return res


def get_employee_training_details(db: Session, employee_id: int, training_id: int) -> Dict[str, Any]:
    assignment = db.query(TrainingAssignment).filter(
        TrainingAssignment.training_id == training_id,
        TrainingAssignment.employee_id == employee_id
    ).first()
    if not assignment:
        raise HTTPException(status_code=403, detail="You are not assigned to this training.")

    training = get_training(db, training_id)

    # Get material progress
    materials_list = []
    required_count = 0
    completed_required_count = 0

    for mat in training.materials:
        progress = db.query(TrainingMaterialProgress).filter(
            TrainingMaterialProgress.assignment_id == assignment.id,
            TrainingMaterialProgress.material_id == mat.id
        ).first()

        is_completed = progress.status == "COMPLETED" if progress else False
        if mat.is_required:
            required_count += 1
            if is_completed:
                completed_required_count += 1

        materials_list.append({
            "id": mat.id,
            "file_name": mat.file_name,
            "file_type": mat.file_type,
            "mime_type": mat.mime_type,
            "file_size": mat.file_size,
            "description": mat.description,
            "display_order": mat.display_order,
            "is_required": mat.is_required,
            "is_completed": is_completed,
            "download_url": f"/api/v1/trainings/{training_id}/materials/{mat.id}/download"
        })

    assessment = db.query(Assessment).filter(Assessment.training_id == training_id).first()
    assessment_data = None
    can_take_assessment = False
    attempts_count = 0
    last_attempt_result = None

    if assessment:
        attempts_count = db.query(AssessmentAttempt).filter(
            AssessmentAttempt.assessment_id == assessment.id,
            AssessmentAttempt.employee_id == employee_id
        ).count()

        last_attempt = (
            db.query(AssessmentAttempt)
            .filter(
                AssessmentAttempt.assessment_id == assessment.id,
                AssessmentAttempt.employee_id == employee_id
            )
            .order_by(AssessmentAttempt.attempt_number.desc())
            .first()
        )

        if last_attempt:
            last_attempt_result = {
                "attempt_id": last_attempt.id,
                "score": last_attempt.score,
                "total_marks": last_attempt.total_marks,
                "percentage": last_attempt.percentage,
                "passed": last_attempt.passed,
                "submitted_at": last_attempt.submitted_at
            }

        # Employee can take assessment if required materials complete & attempts remaining
        materials_done = (required_count == 0) or (completed_required_count >= required_count)
        can_take_assessment = materials_done and (attempts_count < assessment.max_attempts)

        assessment_data = {
            "id": assessment.id,
            "title": assessment.title,
            "description": assessment.description,
            "instructions": assessment.instructions,
            "duration_minutes": assessment.duration_minutes,
            "passing_percentage": assessment.passing_percentage,
            "max_attempts": assessment.max_attempts,
            "show_result": assessment.show_result
        }

    return {
        "assignment_id": assignment.id,
        "training_id": training.id,
        "title": training.title,
        "code": training.code,
        "category": training.category,
        "description": training.description,
        "learning_objective": training.learning_objective,
        "trainer_name": training.trainer_name,
        "estimated_duration_minutes": training.estimated_duration_minutes,
        "start_date": training.start_date,
        "due_date": assignment.due_date,
        "assignment_status": assignment.status,
        "progress_percentage": assignment.progress_percentage,
        "materials": materials_list,
        "has_assessment": assessment is not None,
        "assessment": assessment_data,
        "user_attempts_count": attempts_count,
        "can_take_assessment": can_take_assessment,
        "last_attempt_result": last_attempt_result
    }


def record_material_progress(
    db: Session,
    employee_id: int,
    training_id: int,
    material_id: int,
    req: MaterialProgressRequest
) -> Dict[str, Any]:
    assignment = db.query(TrainingAssignment).filter(
        TrainingAssignment.training_id == training_id,
        TrainingAssignment.employee_id == employee_id
    ).first()
    if not assignment:
        raise HTTPException(status_code=403, detail="Assignment not found.")

    mat_prog = db.query(TrainingMaterialProgress).filter(
        TrainingMaterialProgress.assignment_id == assignment.id,
        TrainingMaterialProgress.material_id == material_id
    ).first()

    if not mat_prog:
        mat_prog = TrainingMaterialProgress(
            assignment_id=assignment.id,
            material_id=material_id,
            started_at=datetime.now(timezone.utc),
            progress_percentage=req.progress_percentage,
            status="COMPLETED" if req.is_completed else "IN_PROGRESS"
        )
        db.add(mat_prog)
    else:
        mat_prog.progress_percentage = max(mat_prog.progress_percentage, req.progress_percentage)
        if req.is_completed:
            mat_prog.status = "COMPLETED"
            mat_prog.completed_at = datetime.now(timezone.utc)

    db.flush()

    # Recalculate overall assignment progress
    materials = db.query(TrainingMaterial).filter(TrainingMaterial.training_id == training_id).all()
    required_materials = [m for m in materials if m.is_required]

    if not required_materials:
        assignment.progress_percentage = 100.0
        assignment.status = "COMPLETED"
    else:
        completed_req_count = 0
        for rm in required_materials:
            p = db.query(TrainingMaterialProgress).filter(
                TrainingMaterialProgress.assignment_id == assignment.id,
                TrainingMaterialProgress.material_id == rm.id
            ).first()
            if p and p.status == "COMPLETED":
                completed_req_count += 1

        pct = round((completed_req_count / len(required_materials)) * 100, 1)
        assignment.progress_percentage = pct
        if assignment.status == "NOT_STARTED":
            assignment.status = "IN_PROGRESS"
            assignment.started_at = datetime.now(timezone.utc)

        # Note: If no assessment, 100% material completion marks assignment COMPLETED
        assessment = db.query(Assessment).filter(Assessment.training_id == training_id).first()
        if not assessment and pct >= 100.0:
            assignment.status = "COMPLETED"
            assignment.completed_at = datetime.now(timezone.utc)

    db.commit()
    return {
        "assignment_id": assignment.id,
        "progress_percentage": assignment.progress_percentage,
        "status": assignment.status
    }


# ─── 6. Exam & Assessment Attempt Security Logic (SECURITY CRITICAL) ──────

def start_assessment_attempt(db: Session, assessment_id: int, employee_id: int) -> Dict[str, Any]:
    assessment = (
        db.query(Assessment)
        .options(joinedload(Assessment.questions).joinedload(AssessmentQuestion.options))
        .filter(Assessment.id == assessment_id)
        .first()
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found.")

    assignment = db.query(TrainingAssignment).filter(
        TrainingAssignment.training_id == assessment.training_id,
        TrainingAssignment.employee_id == employee_id
    ).first()
    if not assignment:
        raise HTTPException(status_code=403, detail="You are not assigned to this training.")

    existing_attempts = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.assessment_id == assessment_id,
        AssessmentAttempt.employee_id == employee_id
    ).count()

    # Check active IN_PROGRESS attempt
    active_attempt = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.assessment_id == assessment_id,
        AssessmentAttempt.employee_id == employee_id,
        AssessmentAttempt.status == "IN_PROGRESS"
    ).first()

    if not active_attempt:
        if existing_attempts >= assessment.max_attempts:
            raise HTTPException(status_code=400, detail="Maximum allowed attempts reached.")

        active_attempt = AssessmentAttempt(
            assessment_id=assessment_id,
            employee_id=employee_id,
            started_at=datetime.now(timezone.utc),
            status="IN_PROGRESS",
            attempt_number=existing_attempts + 1
        )
        db.add(active_attempt)
        db.commit()
        db.refresh(active_attempt)

    # Check timeout expiry
    max_duration = timedelta(minutes=assessment.duration_minutes, seconds=30)  # 30s grace
    time_elapsed = datetime.now(timezone.utc) - active_attempt.started_at.replace(tzinfo=timezone.utc)
    if time_elapsed > max_duration:
        # Auto-submit / expire attempt
        active_attempt.status = "EXPIRED"
        active_attempt.submitted_at = active_attempt.started_at + timedelta(minutes=assessment.duration_minutes)
        db.commit()
        raise HTTPException(status_code=400, detail="Assessment attempt has expired.")

    remaining_seconds = max(0, int((timedelta(minutes=assessment.duration_minutes) - time_elapsed).total_seconds()))

    # Build question payload SECURELY (EXCLUDING is_correct)
    questions_list = []
    questions_source = list(assessment.questions)
    if assessment.randomize_questions:
        random.shuffle(questions_source)

    for q in questions_source:
        opts_source = list(q.options)
        if assessment.randomize_options:
            random.shuffle(opts_source)

        opts_payload = [
            {
                "id": opt.id,
                "question_id": opt.question_id,
                "option_key": opt.option_key,
                "option_text": opt.option_text,
                "display_order": opt.display_order
            }
            for opt in opts_source
        ]

        questions_list.append({
            "id": q.id,
            "question_text": q.question_text,
            "marks": q.marks,
            "difficulty": q.difficulty,
            "display_order": q.display_order,
            "options": opts_payload
        })

    # Fetch already saved draft answers
    saved_answers = {}
    drafts = db.query(AssessmentAnswer).filter(AssessmentAnswer.attempt_id == active_attempt.id).all()
    for d in drafts:
        saved_answers[d.question_id] = d.selected_option_id

    return {
        "attempt_id": active_attempt.id,
        "assessment_id": assessment.id,
        "assessment_title": assessment.title,
        "instructions": assessment.instructions,
        "duration_minutes": assessment.duration_minutes,
        "started_at": active_attempt.started_at,
        "time_remaining_seconds": remaining_seconds,
        "total_questions": len(questions_list),
        "questions": questions_list,
        "saved_answers": saved_answers
    }


def save_assessment_answer(db: Session, attempt_id: int, employee_id: int, req: SaveAnswerRequest) -> Dict[str, Any]:
    attempt = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.id == attempt_id,
        AssessmentAttempt.employee_id == employee_id
    ).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found.")

    if attempt.status != "IN_PROGRESS":
        raise HTTPException(status_code=400, detail="Cannot modify answers for a submitted or expired test.")

    answer = db.query(AssessmentAnswer).filter(
        AssessmentAnswer.attempt_id == attempt_id,
        AssessmentAnswer.question_id == req.question_id
    ).first()

    if not answer:
        answer = AssessmentAnswer(
            attempt_id=attempt_id,
            question_id=req.question_id,
            selected_option_id=req.selected_option_id
        )
        db.add(answer)
    else:
        answer.selected_option_id = req.selected_option_id

    attempt.last_activity_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "status": "Saved",
        "question_id": req.question_id,
        "selected_option_id": req.selected_option_id,
        "saved_at": datetime.now(timezone.utc)
    }


def submit_assessment_attempt(db: Session, attempt_id: int, employee_id: int) -> Dict[str, Any]:
    attempt = (
        db.query(AssessmentAttempt)
        .options(joinedload(AssessmentAttempt.assessment).joinedload(Assessment.questions).joinedload(AssessmentQuestion.options))
        .filter(
            AssessmentAttempt.id == attempt_id,
            AssessmentAttempt.employee_id == employee_id
        )
        .first()
    )
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found.")

    if attempt.status != "IN_PROGRESS":
        raise HTTPException(status_code=400, detail="This assessment attempt has already been submitted or expired.")

    assessment = attempt.assessment
    questions = assessment.questions

    # Evaluate answers against server-side option correctness
    total_marks = 0.0
    obtained_marks = 0.0
    correct_count = 0
    incorrect_count = 0
    unanswered_count = 0
    review_details = []

    for q in questions:
        total_marks += q.marks
        correct_option = next((o for o in q.options if o.is_correct), None)

        user_answer = db.query(AssessmentAnswer).filter(
            AssessmentAnswer.attempt_id == attempt_id,
            AssessmentAnswer.question_id == q.id
        ).first()

        selected_opt = None
        is_correct = False
        marks_for_q = 0.0

        if user_answer and user_answer.selected_option_id:
            selected_opt = db.query(AssessmentOption).filter(AssessmentOption.id == user_answer.selected_option_id).first()
            if selected_opt and selected_opt.is_correct:
                is_correct = True
                marks_for_q = q.marks
                obtained_marks += q.marks
                correct_count += 1
            else:
                incorrect_count += 1

            user_answer.is_correct = is_correct
            user_answer.marks_obtained = marks_for_q
        else:
            unanswered_count += 1

        review_details.append({
            "question_id": q.id,
            "question_text": q.question_text,
            "your_option": f"Option {selected_opt.option_key}: {selected_opt.option_text}" if selected_opt else "Unanswered",
            "correct_option": f"Option {correct_option.option_key}: {correct_option.option_text}" if correct_option else "N/A",
            "is_correct": is_correct,
            "explanation": q.explanation
        })

    pct = round((obtained_marks / total_marks * 100), 1) if total_marks > 0 else 0.0
    passed = (pct >= assessment.passing_percentage)

    attempt.submitted_at = datetime.now(timezone.utc)
    attempt.status = "SUBMITTED"
    attempt.score = obtained_marks
    attempt.total_marks = total_marks
    attempt.percentage = pct
    attempt.passed = passed

    # Update training assignment status if passed
    assignment = db.query(TrainingAssignment).filter(
        TrainingAssignment.training_id == assessment.training_id,
        TrainingAssignment.employee_id == employee_id
    ).first()

    if assignment and passed:
        assignment.status = "COMPLETED"
        assignment.completed_at = datetime.now(timezone.utc)
        assignment.progress_percentage = 100.0

    db.commit()

    # Dispatch real-time Notifications
    from app.services.notification_service import create_notification, create_notification_for_roles
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    emp_name = f"{emp.first_name} {emp.last_name}" if emp else "Employee"

    # Notify Employee
    if emp and emp.user_id:
        _run_async_notification(create_notification(
            db=db,
            user_id=emp.user_id,
            type="ASSESSMENT_COMPLETED",
            title="Assessment Submitted",
            message=f"You completed '{assessment.title}' with a score of {obtained_marks}/{total_marks} ({pct:.0f}% - {'PASSED' if passed else 'FAILED'}).",
            category="TRAINING",
            severity="SUCCESS" if passed else "WARNING",
            employee_id=employee_id,
            reference_id=attempt.id
        ))

    # Notify HR Team
    _run_async_notification(create_notification_for_roles(
        db=db,
        roles=["hr", "admin"],
        type="ASSESSMENT_SUBMITTED",
        title="Assessment Result Submitted",
        message=f"{emp_name} submitted '{assessment.title}'. Score: {obtained_marks}/{total_marks} ({pct:.0f}%).",
        category="TRAINING",
        severity="INFO",
        employee_id=employee_id,
        reference_id=attempt.id
    ))

    return {
        "attempt_id": attempt.id,
        "status": attempt.status,
        "started_at": attempt.started_at,
        "submitted_at": attempt.submitted_at,
        "score": attempt.score,
        "total_marks": attempt.total_marks,
        "percentage": attempt.percentage,
        "passed": attempt.passed,
        "total_questions": len(questions),
        "correct_answers_count": correct_count,
        "incorrect_answers_count": incorrect_count,
        "unanswered_count": unanswered_count,
        "show_correct_answers": assessment.show_correct_answers,
        "review": review_details if assessment.show_correct_answers else None
    }


def get_assessment_result(db: Session, attempt_id: int, employee_id: int, current_user: User) -> Dict[str, Any]:
    attempt = (
        db.query(AssessmentAttempt)
        .options(joinedload(AssessmentAttempt.assessment).joinedload(Assessment.questions).joinedload(AssessmentQuestion.options))
        .filter(AssessmentAttempt.id == attempt_id)
        .first()
    )
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt result not found.")

    is_hr = current_user.role and current_user.role.name.lower() in ["admin", "hr"]
    if not is_hr and attempt.employee_id != employee_id:
        raise HTTPException(status_code=403, detail="You are not authorized to view another employee's attempt.")

    assessment = attempt.assessment
    questions = assessment.questions

    review_details = []
    for q in questions:
        user_ans = db.query(AssessmentAnswer).filter(
            AssessmentAnswer.attempt_id == attempt_id,
            AssessmentAnswer.question_id == q.id
        ).first()

        selected_opt = db.query(AssessmentOption).filter(AssessmentOption.id == user_ans.selected_option_id).first() if (user_ans and user_ans.selected_option_id) else None
        correct_opt = next((o for o in q.options if o.is_correct), None)

        review_details.append({
            "question_id": q.id,
            "question_text": q.question_text,
            "your_option": f"Option {selected_opt.option_key}: {selected_opt.option_text}" if selected_opt else "Unanswered",
            "correct_option": f"Option {correct_opt.option_key}: {correct_opt.option_text}" if correct_opt else "N/A",
            "is_correct": user_ans.is_correct if user_ans else False,
            "explanation": q.explanation
        })

    show_review = is_hr or assessment.show_correct_answers

    return {
        "attempt_id": attempt.id,
        "assessment_id": assessment.id,
        "assessment_title": assessment.title,
        "employee_id": attempt.employee_id,
        "status": attempt.status,
        "started_at": attempt.started_at,
        "submitted_at": attempt.submitted_at,
        "score": attempt.score,
        "total_marks": attempt.total_marks,
        "percentage": attempt.percentage,
        "passed": attempt.passed,
        "show_correct_answers": show_review,
        "review": review_details if show_review else None
    }


# ─── 7. HR Dashboard & Reports Service ────────────────────────────────────

def get_training_dashboard_kpis(db: Session) -> TrainingDashboardKPI:
    total_trainings = db.query(Training).filter(Training.status != "Archived").count()
    active_trainings = db.query(Training).filter(Training.status == "Published").count()
    assigned_employees = db.query(TrainingAssignment.employee_id).distinct().count()
    completed_trainings = db.query(TrainingAssignment).filter(TrainingAssignment.status == "COMPLETED").count()
    pending_trainings = db.query(TrainingAssignment).filter(TrainingAssignment.status.in_(["NOT_STARTED", "IN_PROGRESS"])).count()

    avg_score = db.query(func.avg(AssessmentAttempt.percentage)).filter(AssessmentAttempt.status == "SUBMITTED").scalar() or 0.0

    # Completion breakdown
    comp_breakdown = {
        "Completed": completed_trainings,
        "In Progress": db.query(TrainingAssignment).filter(TrainingAssignment.status == "IN_PROGRESS").count(),
        "Not Started": db.query(TrainingAssignment).filter(TrainingAssignment.status == "NOT_STARTED").count()
    }

    # Assessment performance
    passed_attempts = db.query(AssessmentAttempt).filter(AssessmentAttempt.status == "SUBMITTED", AssessmentAttempt.passed == True).count()
    failed_attempts = db.query(AssessmentAttempt).filter(AssessmentAttempt.status == "SUBMITTED", AssessmentAttempt.passed == False).count()
    not_attempted = assigned_employees - (passed_attempts + failed_attempts)

    assess_perf = {
        "Passed": passed_attempts,
        "Failed": failed_attempts,
        "Not Attempted": max(0, not_attempted)
    }

    # Department wise completion
    departments = db.query(Department).filter(Department.is_active == True).all()
    dept_stats = []
    for d in departments:
        total_assigned = db.query(TrainingAssignment).join(Employee).filter(Employee.department == d.name).count()
        completed = db.query(TrainingAssignment).join(Employee).filter(Employee.department == d.name, TrainingAssignment.status == "COMPLETED").count()
        pct = round((completed / total_assigned * 100), 1) if total_assigned > 0 else 0.0
        dept_stats.append({
            "department": d.name,
            "completion_percentage": pct,
            "assigned_count": total_assigned,
            "completed_count": completed
        })

    return TrainingDashboardKPI(
        total_trainings=total_trainings,
        active_trainings=active_trainings,
        assigned_employees=assigned_employees,
        completed_trainings=completed_trainings,
        pending_trainings=pending_trainings,
        avg_assessment_score=round(float(avg_score), 1),
        completion_breakdown=comp_breakdown,
        assessment_performance=assess_perf,
        department_completion=dept_stats
    )


def get_training_reports(
    db: Session,
    training_id: Optional[int] = None,
    department: Optional[str] = None,
    employee_id: Optional[int] = None,
    status_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    query = db.query(TrainingAssignment).options(
        joinedload(TrainingAssignment.training),
        joinedload(TrainingAssignment.employee)
    )

    if training_id:
        query = query.filter(TrainingAssignment.training_id == training_id)

    if department:
        query = query.join(Employee).filter(Employee.department == department)

    if employee_id:
        query = query.filter(TrainingAssignment.employee_id == employee_id)

    if status_filter:
        query = query.filter(TrainingAssignment.status == status_filter)

    assignments = query.order_by(TrainingAssignment.assigned_at.desc()).all()

    report = []
    for a in assignments:
        t = a.training
        emp = a.employee

        assessment = db.query(Assessment).filter(Assessment.training_id == a.training_id).first()
        assessment_title = "N/A"
        score_str = "N/A"
        pct_str = "N/A"
        result_str = "Not Attempted"

        if assessment:
            assessment_title = assessment.title
            last_attempt = (
                db.query(AssessmentAttempt)
                .filter(
                    AssessmentAttempt.assessment_id == assessment.id,
                    AssessmentAttempt.employee_id == a.employee_id
                )
                .order_by(AssessmentAttempt.attempt_number.desc())
                .first()
            )
            if last_attempt and last_attempt.status == "SUBMITTED":
                score_str = f"{last_attempt.score}/{last_attempt.total_marks}"
                pct_str = f"{last_attempt.percentage:.0f}%"
                result_str = "Passed" if last_attempt.passed else "Failed"

        report.append({
            "assignment_id": a.id,
            "employee_id": a.employee_id,
            "employee_name": f"{emp.first_name} {emp.last_name}" if emp else "Unknown",
            "employee_code": emp.employee_code if emp else "",
            "department": emp.department if emp else "",
            "training_title": t.title if t else "",
            "category": t.category if t else "",
            "assigned_date": a.assigned_at,
            "started_date": a.started_at,
            "completed_date": a.completed_at,
            "due_date": a.due_date,
            "progress_percentage": a.progress_percentage,
            "assignment_status": a.status,
            "assessment_title": assessment_title,
            "score": score_str,
            "percentage": pct_str,
            "result": result_str
        })

    return report
