from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, DateTime, Date, Float, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Training(Base):
    __tablename__ = "trainings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    category = Column(String(100), nullable=False, default="Technical", index=True)
    description = Column(Text, nullable=True)
    learning_objective = Column(Text, nullable=True)
    trainer_name = Column(String(150), nullable=True)
    trainer_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    estimated_duration_minutes = Column(Integer, default=60)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    status = Column(String(50), default="Draft", index=True)  # Draft, Published, Archived
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    trainer = relationship("User", foreign_keys=[trainer_user_id])
    materials = relationship("TrainingMaterial", back_populates="training", cascade="all, delete-orphan")
    assignments = relationship("TrainingAssignment", back_populates="training", cascade="all, delete-orphan")
    assessment = relationship("Assessment", back_populates="training", uselist=False, cascade="all, delete-orphan")


class TrainingMaterial(Base):
    __tablename__ = "training_materials"

    id = Column(Integer, primary_key=True, index=True)
    training_id = Column(Integer, ForeignKey("trainings.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)  # document, video, audio, image
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)  # bytes
    description = Column(Text, nullable=True)
    display_order = Column(Integer, default=1)
    is_required = Column(Boolean, default=True)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    training = relationship("Training", back_populates="materials")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_user_id])


class TrainingAssignment(Base):
    __tablename__ = "training_assignments"

    id = Column(Integer, primary_key=True, index=True)
    training_id = Column(Integer, ForeignKey("trainings.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    assignment_type = Column(String(50), default="Selected")  # All, Selected, Department, Team, Designation
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    due_date = Column(Date, nullable=True)
    status = Column(String(50), default="NOT_STARTED", index=True)  # NOT_STARTED, IN_PROGRESS, COMPLETED
    progress_percentage = Column(Float, default=0.0)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    training = relationship("Training", back_populates="assignments")
    employee = relationship("Employee", foreign_keys=[employee_id])
    material_progress = relationship("TrainingMaterialProgress", back_populates="assignment", cascade="all, delete-orphan")


class TrainingMaterialProgress(Base):
    __tablename__ = "training_material_progress"

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("training_assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    material_id = Column(Integer, ForeignKey("training_materials.id", ondelete="CASCADE"), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    progress_percentage = Column(Float, default=0.0)
    status = Column(String(50), default="NOT_STARTED")  # NOT_STARTED, IN_PROGRESS, COMPLETED

    # Relationships
    assignment = relationship("TrainingAssignment", back_populates="material_progress")
    material = relationship("TrainingMaterial")


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    training_id = Column(Integer, ForeignKey("trainings.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)
    duration_minutes = Column(Integer, default=30)
    passing_percentage = Column(Float, default=60.0)
    max_attempts = Column(Integer, default=1)
    randomize_questions = Column(Boolean, default=False)
    randomize_options = Column(Boolean, default=False)
    show_result = Column(Boolean, default=True)
    show_correct_answers = Column(Boolean, default=False)
    status = Column(String(50), default="Published")  # Draft, Published

    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    training = relationship("Training", back_populates="assessment")
    questions = relationship("AssessmentQuestion", back_populates="assessment", cascade="all, delete-orphan", order_by="AssessmentQuestion.display_order")
    attempts = relationship("AssessmentAttempt", back_populates="assessment", cascade="all, delete-orphan")


class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    marks = Column(Float, default=1.0)
    difficulty = Column(String(20), default="Medium")  # Easy, Medium, Hard
    display_order = Column(Integer, default=1)
    explanation = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    assessment = relationship("Assessment", back_populates="questions")
    options = relationship("AssessmentOption", back_populates="question", cascade="all, delete-orphan", order_by="AssessmentOption.display_order")


class AssessmentOption(Base):
    __tablename__ = "assessment_options"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("assessment_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    option_key = Column(String(10), nullable=False)  # A, B, C, D
    option_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)
    display_order = Column(Integer, default=1)

    # Relationships
    question = relationship("AssessmentQuestion", back_populates="options")


class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="IN_PROGRESS", index=True)  # IN_PROGRESS, SUBMITTED, EXPIRED
    score = Column(Float, default=0.0)
    total_marks = Column(Float, default=0.0)
    percentage = Column(Float, default=0.0)
    passed = Column(Boolean, default=False)
    attempt_number = Column(Integer, default=1)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    assessment = relationship("Assessment", back_populates="attempts")
    employee = relationship("Employee", foreign_keys=[employee_id])
    answers = relationship("AssessmentAnswer", back_populates="attempt", cascade="all, delete-orphan")


class AssessmentAnswer(Base):
    __tablename__ = "assessment_answers"

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("assessment_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("assessment_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    selected_option_id = Column(Integer, ForeignKey("assessment_options.id", ondelete="SET NULL"), nullable=True)
    is_correct = Column(Boolean, nullable=True)
    marks_obtained = Column(Float, default=0.0)
    answered_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    attempt = relationship("AssessmentAttempt", back_populates="answers")
    question = relationship("AssessmentQuestion")
    selected_option = relationship("AssessmentOption")
