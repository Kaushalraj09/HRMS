"""add payroll management module tables

Revision ID: a3b4c5d6e7f8
Revises: fb2c3d4e5f60
Create Date: 2026-09-08
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, Sequence[str], None] = ("fb2c3d4e5f60", "a2b3c4d5e6f7")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Salary Components
    op.create_table(
        "salary_components",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("component_type", sa.String(length=30), nullable=False),
        sa.Column("calculation_type", sa.String(length=30), nullable=False, server_default="PERCENTAGE"),
        sa.Column("calculation_basis", sa.String(length=50), nullable=True),
        sa.Column("default_value", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("is_taxable", sa.Boolean(), nullable=True, server_default="1"),
        sa.Column("is_statutory", sa.Boolean(), nullable=True, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="1"),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("sequence_order", sa.Integer(), nullable=True, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )
    op.create_index("ix_salary_components_code", "salary_components", ["code"], unique=True)
    op.create_index("ix_salary_components_id", "salary_components", ["id"], unique=False)

    # 2. Salary Structures
    op.create_table(
        "salary_structures",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("salary_basis", sa.String(length=20), nullable=False, server_default="CTC"),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )
    op.create_index("ix_salary_structures_code", "salary_structures", ["code"], unique=True)
    op.create_index("ix_salary_structures_id", "salary_structures", ["id"], unique=False)

    # 3. Salary Structure Components
    op.create_table(
        "salary_structure_components",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("structure_id", sa.Integer(), sa.ForeignKey("salary_structures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_id", sa.Integer(), sa.ForeignKey("salary_components.id"), nullable=False),
        sa.Column("calculation_type", sa.String(length=30), nullable=False),
        sa.Column("calculation_basis", sa.String(length=50), nullable=True),
        sa.Column("percentage_or_value", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("sequence_order", sa.Integer(), nullable=True, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.UniqueConstraint("structure_id", "component_id", name="uq_structure_component"),
    )
    op.create_index("ix_salary_structure_components_id", "salary_structure_components", ["id"], unique=False)

    # 4. Employee Salary Assignments
    op.create_table(
        "employee_salary_assignments",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("salary_structure_id", sa.Integer(), sa.ForeignKey("salary_structures.id"), nullable=False),
        sa.Column("salary_basis", sa.String(length=20), nullable=True, server_default="CTC"),
        sa.Column("salary_type", sa.String(length=20), nullable=True, server_default="Monthly"),
        sa.Column("annual_ctc", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("monthly_ctc", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("gross_monthly", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("net_monthly", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("total_deductions", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("employer_contributions", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="1"),
        sa.Column("auto_calculate", sa.Boolean(), nullable=True, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )
    op.create_index("ix_employee_salary_assignments_id", "employee_salary_assignments", ["id"], unique=False)
    op.create_index("ix_employee_salary_assignments_employee_id", "employee_salary_assignments", ["employee_id"], unique=False)
    op.create_index("ix_emp_sal_lookup", "employee_salary_assignments", ["employee_id", "is_active", "effective_from"], unique=False)

    # 5. Employee Salary Components
    op.create_table(
        "employee_salary_components",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("employee_salary_assignments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_id", sa.Integer(), sa.ForeignKey("salary_components.id"), nullable=False),
        sa.Column("monthly_amount", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("annual_amount", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("percentage", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )
    op.create_index("ix_employee_salary_components_id", "employee_salary_components", ["id"], unique=False)

    # 6. Salary Revisions
    op.create_table(
        "salary_revisions",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("old_salary_assignment_id", sa.Integer(), sa.ForeignKey("employee_salary_assignments.id"), nullable=True),
        sa.Column("new_salary_structure_id", sa.Integer(), sa.ForeignKey("salary_structures.id"), nullable=False),
        sa.Column("old_annual_ctc", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("new_annual_ctc", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("old_monthly_gross", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("new_monthly_gross", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("increment_amount", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("increment_percentage", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("reason", sa.String(length=100), nullable=True, server_default="Performance Increment"),
        sa.Column("remarks", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=True, server_default="SUBMITTED"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )
    op.create_index("ix_salary_revisions_id", "salary_revisions", ["id"], unique=False)
    op.create_index("ix_salary_revisions_employee_id", "salary_revisions", ["employee_id"], unique=False)

    # 7. Payroll Periods
    op.create_table(
        "payroll_periods",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("pay_date", sa.Date(), nullable=False),
        sa.Column("total_days", sa.Integer(), nullable=False),
        sa.Column("working_days", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=True, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )
    op.create_index("ix_payroll_periods_id", "payroll_periods", ["id"], unique=False)

    # 8. Payroll Runs
    op.create_table(
        "payroll_runs",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("period_id", sa.Integer(), sa.ForeignKey("payroll_periods.id"), nullable=False),
        sa.Column("run_number", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=True, server_default="DRAFT"),
        sa.Column("total_employees", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("processed_employees", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("warning_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("total_gross", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("total_deductions", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("total_net", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("total_employer_cost", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )
    op.create_index("ix_payroll_runs_id", "payroll_runs", ["id"], unique=False)
    op.create_index("ix_payroll_runs_run_number", "payroll_runs", ["run_number"], unique=True)
    op.create_index("ix_payroll_runs_status", "payroll_runs", ["status"], unique=False)

    # 9. Payroll Records
    op.create_table(
        "payroll_records",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("payroll_run_id", sa.Integer(), sa.ForeignKey("payroll_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("salary_assignment_id", sa.Integer(), sa.ForeignKey("employee_salary_assignments.id"), nullable=True),
        sa.Column("salary_structure_id", sa.Integer(), sa.ForeignKey("salary_structures.id"), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=True, server_default="CALCULATED"),
        sa.Column("total_payroll_days", sa.Float(), nullable=True, server_default="30.0"),
        sa.Column("payable_days", sa.Float(), nullable=True, server_default="30.0"),
        sa.Column("present_days", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("absent_days", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("half_days", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("paid_leave_days", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("unpaid_leave_days", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("holidays_count", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("weekly_offs_count", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("overtime_hours", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("overtime_rate", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("overtime_amount", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("bonus_amount", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("incentive_amount", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("other_earnings_amount", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("lop_deduction_amount", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("other_deductions_amount", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("fixed_gross_salary", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("gross_earnings", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("total_deductions", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("net_salary", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("employer_pf", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("employer_esi", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("other_employer_contribution", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("total_employer_contribution", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("total_cost_to_company", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("payment_status", sa.String(length=30), nullable=True, server_default="PENDING"),
        sa.Column("payment_mode", sa.String(length=30), nullable=True, server_default="Bank Transfer"),
        sa.Column("bank_name", sa.String(length=100), nullable=True),
        sa.Column("account_number", sa.String(length=50), nullable=True),
        sa.Column("ifsc_code", sa.String(length=30), nullable=True),
        sa.Column("calculation_snapshot", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.UniqueConstraint("payroll_run_id", "employee_id", name="uq_run_employee"),
    )
    op.create_index("ix_payroll_records_id", "payroll_records", ["id"], unique=False)
    op.create_index("ix_payroll_records_employee_id", "payroll_records", ["employee_id"], unique=False)

    # 10. Payroll Record Items
    op.create_table(
        "payroll_record_items",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("record_id", sa.Integer(), sa.ForeignKey("payroll_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_id", sa.Integer(), sa.ForeignKey("salary_components.id"), nullable=True),
        sa.Column("component_code", sa.String(length=50), nullable=False),
        sa.Column("component_name", sa.String(length=150), nullable=False),
        sa.Column("component_type", sa.String(length=30), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("calculation_detail", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_payroll_record_items_id", "payroll_record_items", ["id"], unique=False)

    # 11. Payroll Inputs
    op.create_table(
        "payroll_inputs",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("payroll_period_id", sa.Integer(), sa.ForeignKey("payroll_periods.id"), nullable=False),
        sa.Column("input_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("amount", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("hours", sa.Float(), nullable=True),
        sa.Column("remarks", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True, server_default="APPROVED"),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )
    op.create_index("ix_payroll_inputs_id", "payroll_inputs", ["id"], unique=False)
    op.create_index("ix_payroll_inputs_employee_id", "payroll_inputs", ["employee_id"], unique=False)

    # 12. Payroll Exceptions
    op.create_table(
        "payroll_exceptions",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("payroll_run_id", sa.Integer(), sa.ForeignKey("payroll_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=True, server_default="WARNING"),
        sa.Column("error_code", sa.String(length=50), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("is_resolved", sa.Boolean(), nullable=True, server_default="0"),
        sa.Column("resolved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resolution_notes", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )
    op.create_index("ix_payroll_exceptions_id", "payroll_exceptions", ["id"], unique=False)
    op.create_index("ix_payroll_exceptions_employee_id", "payroll_exceptions", ["employee_id"], unique=False)

    # 13. Payroll Adjustments
    op.create_table(
        "payroll_adjustments",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("payroll_record_id", sa.Integer(), sa.ForeignKey("payroll_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_code", sa.String(length=50), nullable=False),
        sa.Column("old_amount", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("new_amount", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("difference", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("requested_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )
    op.create_index("ix_payroll_adjustments_id", "payroll_adjustments", ["id"], unique=False)

    # 14. Payslips
    op.create_table(
        "payslips",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("payroll_record_id", sa.Integer(), sa.ForeignKey("payroll_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("payslip_number", sa.String(length=50), nullable=False),
        sa.Column("payroll_month", sa.String(length=30), nullable=False),
        sa.Column("file_path", sa.String(length=255), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=True, server_default="1"),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.UniqueConstraint("payroll_record_id", name="uq_payslip_record"),
    )
    op.create_index("ix_payslips_id", "payslips", ["id"], unique=False)
    op.create_index("ix_payslips_employee_id", "payslips", ["employee_id"], unique=False)
    op.create_index("ix_payslips_payslip_number", "payslips", ["payslip_number"], unique=True)

    # 15. Payroll Audit Logs
    op.create_table(
        "payroll_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=True),
        sa.Column("old_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )
    op.create_index("ix_payroll_audit_logs_id", "payroll_audit_logs", ["id"], unique=False)

    # 16. Statutory Configurations
    op.create_table(
        "statutory_configurations",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("employee_rate_pct", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("employer_rate_pct", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("wage_ceiling", sa.Float(), nullable=True),
        sa.Column("min_wage_threshold", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("calculation_basis", sa.String(length=50), nullable=True, server_default="BASIC"),
        sa.Column("is_enabled", sa.Boolean(), nullable=True, server_default="1"),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )
    op.create_index("ix_statutory_configurations_code", "statutory_configurations", ["code"], unique=True)
    op.create_index("ix_statutory_configurations_id", "statutory_configurations", ["id"], unique=False)


def downgrade() -> None:
    op.drop_table("statutory_configurations")
    op.drop_table("payroll_audit_logs")
    op.drop_table("payslips")
    op.drop_table("payroll_adjustments")
    op.drop_table("payroll_exceptions")
    op.drop_table("payroll_inputs")
    op.drop_table("payroll_record_items")
    op.drop_table("payroll_records")
    op.drop_table("payroll_runs")
    op.drop_table("payroll_periods")
    op.drop_table("salary_revisions")
    op.drop_table("employee_salary_components")
    op.drop_table("employee_salary_assignments")
    op.drop_table("salary_structure_components")
    op.drop_table("salary_structures")
    op.drop_table("salary_components")
