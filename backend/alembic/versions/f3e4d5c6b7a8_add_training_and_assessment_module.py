"""add_training_and_assessment_module

Revision ID: f3e4d5c6b7a8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-22 12:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'f3e4d5c6b7a8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. trainings
    op.create_table(
        'trainings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False, server_default='Technical'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('learning_objective', sa.Text(), nullable=True),
        sa.Column('trainer_name', sa.String(length=150), nullable=True),
        sa.Column('trainer_user_id', sa.Integer(), nullable=True),
        sa.Column('estimated_duration_minutes', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='Draft'),
        sa.Column('created_by_user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['trainer_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_trainings_id'), 'trainings', ['id'], unique=False)
    op.create_index(op.f('ix_trainings_title'), 'trainings', ['title'], unique=False)
    op.create_index(op.f('ix_trainings_code'), 'trainings', ['code'], unique=True)
    op.create_index(op.f('ix_trainings_category'), 'trainings', ['category'], unique=False)
    op.create_index(op.f('ix_trainings_status'), 'trainings', ['status'], unique=False)

    # 2. training_materials
    op.create_table(
        'training_materials',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('training_id', sa.Integer(), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('uploaded_by_user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['training_id'], ['trainings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_training_materials_id'), 'training_materials', ['id'], unique=False)
    op.create_index(op.f('ix_training_materials_training_id'), 'training_materials', ['training_id'], unique=False)

    # 3. training_assignments
    op.create_table(
        'training_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('training_id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('assignment_type', sa.String(length=50), nullable=False, server_default='Selected'),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='NOT_STARTED'),
        sa.Column('progress_percentage', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['training_id'], ['trainings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('training_id', 'employee_id', name='uq_training_employee_assignment')
    )
    op.create_index(op.f('ix_training_assignments_id'), 'training_assignments', ['id'], unique=False)
    op.create_index(op.f('ix_training_assignments_training_id'), 'training_assignments', ['training_id'], unique=False)
    op.create_index(op.f('ix_training_assignments_employee_id'), 'training_assignments', ['employee_id'], unique=False)
    op.create_index(op.f('ix_training_assignments_status'), 'training_assignments', ['status'], unique=False)

    # 4. training_material_progress
    op.create_table(
        'training_material_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('assignment_id', sa.Integer(), nullable=False),
        sa.Column('material_id', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('progress_percentage', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='NOT_STARTED'),
        sa.ForeignKeyConstraint(['assignment_id'], ['training_assignments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['material_id'], ['training_materials.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_training_material_progress_id'), 'training_material_progress', ['id'], unique=False)
    op.create_index(op.f('ix_training_material_progress_assignment_id'), 'training_material_progress', ['assignment_id'], unique=False)
    op.create_index(op.f('ix_training_material_progress_material_id'), 'training_material_progress', ['material_id'], unique=False)

    # 5. assessments
    op.create_table(
        'assessments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('training_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('passing_percentage', sa.Float(), nullable=False, server_default='60.0'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('randomize_questions', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('randomize_options', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('show_result', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('show_correct_answers', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='Published'),
        sa.Column('created_by_user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['training_id'], ['trainings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('training_id')
    )
    op.create_index(op.f('ix_assessments_id'), 'assessments', ['id'], unique=False)
    op.create_index(op.f('ix_assessments_training_id'), 'assessments', ['training_id'], unique=True)

    # 6. assessment_questions
    op.create_table(
        'assessment_questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('assessment_id', sa.Integer(), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('marks', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('difficulty', sa.String(length=20), nullable=False, server_default='Medium'),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_assessment_questions_id'), 'assessment_questions', ['id'], unique=False)
    op.create_index(op.f('ix_assessment_questions_assessment_id'), 'assessment_questions', ['assessment_id'], unique=False)

    # 7. assessment_options
    op.create_table(
        'assessment_options',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('option_key', sa.String(length=10), nullable=False),
        sa.Column('option_text', sa.Text(), nullable=False),
        sa.Column('is_correct', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['question_id'], ['assessment_questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_assessment_options_id'), 'assessment_options', ['id'], unique=False)
    op.create_index(op.f('ix_assessment_options_question_id'), 'assessment_options', ['question_id'], unique=False)

    # 8. assessment_attempts
    op.create_table(
        'assessment_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('assessment_id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='IN_PROGRESS'),
        sa.Column('score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_marks', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('percentage', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('passed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('attempt_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_assessment_attempts_id'), 'assessment_attempts', ['id'], unique=False)
    op.create_index(op.f('ix_assessment_attempts_assessment_id'), 'assessment_attempts', ['assessment_id'], unique=False)
    op.create_index(op.f('ix_assessment_attempts_employee_id'), 'assessment_attempts', ['employee_id'], unique=False)
    op.create_index(op.f('ix_assessment_attempts_status'), 'assessment_attempts', ['status'], unique=False)

    # 9. assessment_answers
    op.create_table(
        'assessment_answers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('attempt_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('selected_option_id', sa.Integer(), nullable=True),
        sa.Column('is_correct', sa.Boolean(), nullable=True),
        sa.Column('marks_obtained', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('answered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['attempt_id'], ['assessment_attempts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['question_id'], ['assessment_questions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['selected_option_id'], ['assessment_options.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_assessment_answers_id'), 'assessment_answers', ['id'], unique=False)
    op.create_index(op.f('ix_assessment_answers_attempt_id'), 'assessment_answers', ['attempt_id'], unique=False)
    op.create_index(op.f('ix_assessment_answers_question_id'), 'assessment_answers', ['question_id'], unique=False)


def downgrade() -> None:
    op.drop_table('assessment_answers')
    op.drop_table('assessment_attempts')
    op.drop_table('assessment_options')
    op.drop_table('assessment_questions')
    op.drop_table('assessments')
    op.drop_table('training_material_progress')
    op.drop_table('training_assignments')
    op.drop_table('training_materials')
    op.drop_table('trainings')
