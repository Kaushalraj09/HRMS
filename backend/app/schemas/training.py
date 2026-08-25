from typing import List, Optional
from datetime import date, datetime
from pydantic import BaseModel, Field, field_validator


# ─── Training Schemas ────────────────────────────────────────────────────────

class TrainingBase(BaseModel):
    title: str = Field(..., max_length=200)
    code: str = Field(..., max_length=50)
    category: str = Field(default="Technical", max_length=100)
    description: Optional[str] = None
    learning_objective: Optional[str] = None
    trainer_name: Optional[str] = None
    trainer_user_id: Optional[int] = None
    estimated_duration_minutes: int = Field(default=60, ge=1)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: str = Field(default="Draft")  # Draft, Published, Archived

    @field_validator("end_date")
    def validate_dates(cls, v, values):
        start = values.data.get("start_date")
        if start and v and v < start:
            raise ValueError("end_date cannot be earlier than start_date")
        return v


class TrainingCreate(TrainingBase):
    pass


class TrainingUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    code: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    learning_objective: Optional[str] = None
    trainer_name: Optional[str] = None
    trainer_user_id: Optional[int] = None
    estimated_duration_minutes: Optional[int] = Field(None, ge=1)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None


class TrainingMaterialResponse(BaseModel):
    id: int
    training_id: int
    file_name: str
    storage_path: str
    file_type: str
    mime_type: str
    file_size: int
    description: Optional[str] = None
    display_order: int
    is_required: bool
    uploaded_by_user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class MaterialReorderItem(BaseModel):
    material_id: int
    display_order: int


class MaterialReorderRequest(BaseModel):
    items: List[MaterialReorderItem]


class AssessmentOptionHrResponse(BaseModel):
    id: int
    question_id: int
    option_key: str
    option_text: str
    is_correct: bool
    display_order: int

    class Config:
        from_attributes = True


class AssessmentQuestionHrResponse(BaseModel):
    id: int
    assessment_id: int
    question_text: str
    marks: float
    difficulty: str
    display_order: int
    explanation: Optional[str] = None
    options: List[AssessmentOptionHrResponse] = []

    class Config:
        from_attributes = True


class AssessmentHrResponse(BaseModel):
    id: int
    training_id: int
    title: str
    description: Optional[str] = None
    instructions: Optional[str] = None
    duration_minutes: int
    passing_percentage: float
    max_attempts: int
    randomize_questions: bool
    randomize_options: bool
    show_result: bool
    show_correct_answers: bool
    status: str
    questions_count: int = 0
    questions: List[AssessmentQuestionHrResponse] = []

    class Config:
        from_attributes = True


class TrainingResponse(BaseModel):
    id: int
    title: str
    code: str
    category: str
    description: Optional[str] = None
    learning_objective: Optional[str] = None
    trainer_name: Optional[str] = None
    trainer_user_id: Optional[int] = None
    estimated_duration_minutes: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: str
    created_by_user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    materials: List[TrainingMaterialResponse] = []
    has_assessment: bool = False
    assigned_count: int = 0
    completed_count: int = 0
    completion_percentage: float = 0.0

    class Config:
        from_attributes = True


# ─── Assignment Schemas ──────────────────────────────────────────────────────

class AssignTrainingRequest(BaseModel):
    assignment_type: str = Field(..., description="All, Selected, Department, Team, Designation")
    employee_ids: Optional[List[int]] = None
    departments: Optional[List[str]] = None
    designations: Optional[List[str]] = None
    due_date: Optional[date] = None


class TrainingAssignmentResponse(BaseModel):
    id: int
    training_id: int
    employee_id: int
    employee_name: Optional[str] = None
    employee_code: Optional[str] = None
    department: Optional[str] = None
    assignment_type: str
    assigned_at: datetime
    due_date: Optional[date] = None
    status: str
    progress_percentage: float
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assessment_status: Optional[str] = "Not Attempted"
    assessment_score: Optional[str] = "N/A"

    class Config:
        from_attributes = True


# ─── Assessment & MCQ Question Builder Schemas (HR) ────────────────────────

class AssessmentCreateUpdate(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    instructions: Optional[str] = None
    duration_minutes: int = Field(default=30, ge=1)
    passing_percentage: float = Field(default=60.0, ge=0.0, le=100.0)
    max_attempts: int = Field(default=1, ge=1)
    randomize_questions: bool = False
    randomize_options: bool = False
    show_result: bool = True
    show_correct_answers: bool = False
    status: str = "Published"


class AssessmentOptionCreate(BaseModel):
    option_key: str = Field(..., description="A, B, C, or D")
    option_text: str = Field(..., min_length=1)
    is_correct: bool = False


class AssessmentQuestionCreate(BaseModel):
    question_text: str = Field(..., min_length=1)
    marks: float = Field(default=1.0, ge=0.5)
    difficulty: str = Field(default="Medium")
    explanation: Optional[str] = None
    display_order: int = 1
    options: List[AssessmentOptionCreate]

    @field_validator("options")
    def validate_four_options_and_one_correct(cls, opts):
        if len(opts) != 4:
            raise ValueError("Each question must contain exactly 4 options")
        correct_count = sum(1 for o in opts if o.is_correct)
        if correct_count != 1:
            raise ValueError("Exactly one option must be marked as correct")
        keys = [o.option_key.upper() for o in opts]
        if sorted(keys) != ["A", "B", "C", "D"]:
            raise ValueError("Option keys must be exactly A, B, C, D")
        return opts


# ─── Employee Exam & Attempt Schemas (SECURITY CRITICAL) ─────────────────────

class AssessmentOptionEmployeeResponse(BaseModel):
    id: int
    question_id: int
    option_key: str
    option_text: str
    display_order: int

    class Config:
        from_attributes = True


class AssessmentQuestionEmployeeResponse(BaseModel):
    id: int
    question_text: str
    marks: float
    difficulty: str
    display_order: int
    options: List[AssessmentOptionEmployeeResponse] = []

    class Config:
        from_attributes = True


class AssessmentAttemptStartResponse(BaseModel):
    attempt_id: int
    assessment_id: int
    assessment_title: str
    instructions: Optional[str] = None
    duration_minutes: int
    started_at: datetime
    time_remaining_seconds: int
    total_questions: int
    questions: List[AssessmentQuestionEmployeeResponse] = []
    saved_answers: dict = {}  # {question_id: selected_option_id}

    class Config:
        from_attributes = True


class SaveAnswerRequest(BaseModel):
    question_id: int
    selected_option_id: int


class SaveAnswerResponse(BaseModel):
    status: str
    question_id: int
    selected_option_id: int
    saved_at: datetime


class SubmitAttemptResponse(BaseModel):
    attempt_id: int
    status: str
    started_at: datetime
    submitted_at: datetime
    score: float
    total_marks: float
    percentage: float
    passed: bool
    total_questions: int
    correct_answers_count: int
    incorrect_answers_count: int
    unanswered_count: int
    show_correct_answers: bool
    review: Optional[List[dict]] = None


# ─── Employee Training View Schemas ──────────────────────────────────────────

class MaterialProgressRequest(BaseModel):
    progress_percentage: float = Field(default=100.0, ge=0.0, le=100.0)
    is_completed: bool = True


class EmployeeTrainingViewResponse(BaseModel):
    assignment_id: int
    training_id: int
    title: str
    code: str
    category: str
    description: Optional[str] = None
    learning_objective: Optional[str] = None
    trainer_name: Optional[str] = None
    estimated_duration_minutes: int
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    assignment_status: str
    progress_percentage: float
    materials: List[dict] = []
    has_assessment: bool = False
    assessment_id: Optional[int] = None
    assessment_title: Optional[str] = None
    assessment_duration_minutes: Optional[int] = None
    passing_percentage: Optional[float] = None
    max_attempts: Optional[int] = None
    user_attempts_count: int = 0
    can_take_assessment: bool = False
    last_attempt_result: Optional[dict] = None


# ─── Dashboard & Reports Schemas ─────────────────────────────────────────────

class TrainingDashboardKPI(BaseModel):
    total_trainings: int
    active_trainings: int
    assigned_employees: int
    completed_trainings: int
    pending_trainings: int
    avg_assessment_score: float
    completion_breakdown: dict  # {Completed, In Progress, Not Started}
    assessment_performance: dict  # {Passed, Failed, Not Attempted}
    department_completion: List[dict]  # [{department, completion_percentage, assigned_count}]
