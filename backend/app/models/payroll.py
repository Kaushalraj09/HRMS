from typing import Optional, List, Dict, Any
from datetime import date
from sqlalchemy import (
    Column,
    String,
    Integer,
    ForeignKey,
    DateTime,
    Date,
    Float,
    Boolean,
    Text,
    JSON,
    Numeric,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class SalaryComponent(Base):
    """Catalog of all earning, deduction, and contribution components."""
    __tablename__ = "salary_components"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(150), nullable=False)
    component_type = Column(String(30), nullable=False)  # EARNING, DEDUCTION, STATUTORY_EMPLOYER
    calculation_type = Column(String(30), nullable=False, default="PERCENTAGE")  # PERCENTAGE, FIXED, BALANCE, ATTENDANCE, HOURLY
    calculation_basis = Column(String(50), nullable=True)  # CTC, BASIC, GROSS, etc.
    default_value = Column(Float, default=0.0)  # default percentage or fixed amount
    is_taxable = Column(Boolean, default=True)
    is_statutory = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    description = Column(String(255), nullable=True)
    sequence_order = Column(Integer, default=1)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class SalaryStructure(Base):
    """Reusable salary structure template assigned to multiple employees."""
    __tablename__ = "salary_structures"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(150), nullable=False)
    salary_basis = Column(String(20), nullable=False, default="CTC")  # CTC or GROSS
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)

    components = relationship(
        "SalaryStructureComponent",
        back_populates="structure",
        cascade="all, delete-orphan",
        order_by="SalaryStructureComponent.sequence_order",
    )
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class SalaryStructureComponent(Base):
    """Component rule mapping inside a salary structure."""
    __tablename__ = "salary_structure_components"
    __table_args__ = (
        UniqueConstraint("structure_id", "component_id", name="uq_structure_component"),
    )

    id = Column(Integer, primary_key=True, index=True)
    structure_id = Column(Integer, ForeignKey("salary_structures.id", ondelete="CASCADE"), nullable=False)
    component_id = Column(Integer, ForeignKey("salary_components.id"), nullable=False)
    
    calculation_type = Column(String(30), nullable=False)  # PERCENTAGE, FIXED, BALANCE
    calculation_basis = Column(String(50), nullable=True)  # CTC, BASIC, GROSS
    percentage_or_value = Column(Float, default=0.0)
    sequence_order = Column(Integer, default=1)

    structure = relationship("SalaryStructure", back_populates="components")
    component = relationship("SalaryComponent", lazy="joined")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    @property
    def component_code(self) -> str:
        return self.component.code if self.component else ""

    @property
    def component_name(self) -> str:
        return self.component.name if self.component else ""

    @property
    def component_type(self) -> str:
        return self.component.component_type if self.component else ""


class EmployeeSalaryAssignment(Base):
    """Effective-dated employee salary configuration."""
    __tablename__ = "employee_salary_assignments"
    __table_args__ = (
        Index("ix_emp_sal_lookup", "employee_id", "is_active", "effective_from"),
    )

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    salary_structure_id = Column(Integer, ForeignKey("salary_structures.id"), nullable=False)
    
    salary_basis = Column(String(20), default="CTC")  # CTC or GROSS
    salary_type = Column(String(20), default="Monthly")  # Monthly or Annual
    
    annual_ctc = Column(Float, default=0.0, nullable=False)
    monthly_ctc = Column(Float, default=0.0, nullable=False)
    gross_monthly = Column(Float, default=0.0, nullable=False)
    net_monthly = Column(Float, default=0.0, nullable=False)
    total_deductions = Column(Float, default=0.0, nullable=False)
    employer_contributions = Column(Float, default=0.0, nullable=False)
    
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    auto_calculate = Column(Boolean, default=True)

    employee = relationship("Employee", backref="salary_assignments")
    structure = relationship("SalaryStructure")
    components = relationship("EmployeeSalaryComponent", back_populates="assignment", cascade="all, delete-orphan")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class EmployeeSalaryComponent(Base):
    """Specific breakdown amounts saved for an employee salary assignment."""
    __tablename__ = "employee_salary_components"

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("employee_salary_assignments.id", ondelete="CASCADE"), nullable=False)
    component_id = Column(Integer, ForeignKey("salary_components.id"), nullable=False)
    
    monthly_amount = Column(Float, default=0.0)
    annual_amount = Column(Float, default=0.0)
    percentage = Column(Float, default=0.0)

    assignment = relationship("EmployeeSalaryAssignment", back_populates="components")
    component = relationship("SalaryComponent")

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SalaryRevision(Base):
    """Salary increment/revision request and approval workflow."""
    __tablename__ = "salary_revisions"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    old_salary_assignment_id = Column(Integer, ForeignKey("employee_salary_assignments.id"), nullable=True)
    new_salary_structure_id = Column(Integer, ForeignKey("salary_structures.id"), nullable=False)
    
    old_annual_ctc = Column(Float, default=0.0)
    new_annual_ctc = Column(Float, default=0.0)
    old_monthly_gross = Column(Float, default=0.0)
    new_monthly_gross = Column(Float, default=0.0)
    
    increment_amount = Column(Float, default=0.0)
    increment_percentage = Column(Float, default=0.0)
    effective_from = Column(Date, nullable=False)
    reason = Column(String(100), default="Performance Increment")  # Promotion, Performance, Market Correction, Annual
    remarks = Column(String(500), nullable=True)
    
    status = Column(String(30), default="SUBMITTED")  # DRAFT, SUBMITTED, APPROVED, REJECTED
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    employee = relationship("Employee")
    structure = relationship("SalaryStructure")
    creator = relationship("User", foreign_keys=[created_by])
    approver = relationship("User", foreign_keys=[approved_by])

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class PayrollPeriod(Base):
    """Calendar/pay period for monthly payroll processing."""
    __tablename__ = "payroll_periods"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)  # e.g., September 2026
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    pay_date = Column(Date, nullable=False)
    total_days = Column(Integer, nullable=False)  # 30, 31, etc.
    working_days = Column(Integer, nullable=False)
    status = Column(String(30), default="OPEN")  # OPEN, PROCESSING, CLOSED

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class PayrollRun(Base):
    """Batch payroll execution for a period."""
    __tablename__ = "payroll_runs"

    id = Column(Integer, primary_key=True, index=True)
    period_id = Column(Integer, ForeignKey("payroll_periods.id"), nullable=False)
    run_number = Column(String(50), unique=True, index=True, nullable=False)  # PR-2026-09-001
    title = Column(String(150), nullable=False)
    
    status = Column(String(30), default="DRAFT", index=True)
    # DRAFT -> CALCULATING -> CALCULATED -> UNDER_REVIEW -> APPROVED -> LOCKED -> PAID
    
    total_employees = Column(Integer, default=0)
    processed_employees = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)

    total_gross = Column(Float, default=0.0)
    total_deductions = Column(Float, default=0.0)
    total_net = Column(Float, default=0.0)
    total_employer_cost = Column(Float, default=0.0)

    calculated_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    locked_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    paid_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    period = relationship("PayrollPeriod")
    records = relationship("PayrollRecord", back_populates="payroll_run", cascade="all, delete-orphan")
    exceptions = relationship("PayrollException", back_populates="payroll_run", cascade="all, delete-orphan")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class PayrollRecord(Base):
    """Employee payroll record snapshot within a run."""
    __tablename__ = "payroll_records"
    __table_args__ = (
        UniqueConstraint("payroll_run_id", "employee_id", name="uq_run_employee"),
    )

    id = Column(Integer, primary_key=True, index=True)
    payroll_run_id = Column(Integer, ForeignKey("payroll_runs.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    salary_assignment_id = Column(Integer, ForeignKey("employee_salary_assignments.id"), nullable=True)
    salary_structure_id = Column(Integer, ForeignKey("salary_structures.id"), nullable=True)

    status = Column(String(30), default="CALCULATED")  # CALCULATED, UNDER_REVIEW, APPROVED, EXCEPTION
    
    # Attendance & Leave Summary
    total_payroll_days = Column(Float, default=30.0)
    payable_days = Column(Float, default=30.0)
    present_days = Column(Float, default=0.0)
    absent_days = Column(Float, default=0.0)
    half_days = Column(Float, default=0.0)
    paid_leave_days = Column(Float, default=0.0)
    unpaid_leave_days = Column(Float, default=0.0)  # LOP days
    holidays_count = Column(Float, default=0.0)
    weekly_offs_count = Column(Float, default=0.0)

    # Overtime & Variables
    overtime_hours = Column(Float, default=0.0)
    overtime_rate = Column(Float, default=0.0)
    overtime_amount = Column(Float, default=0.0)
    bonus_amount = Column(Float, default=0.0)
    incentive_amount = Column(Float, default=0.0)
    other_earnings_amount = Column(Float, default=0.0)
    lop_deduction_amount = Column(Float, default=0.0)
    other_deductions_amount = Column(Float, default=0.0)

    # Financial Totals
    fixed_gross_salary = Column(Float, default=0.0)
    gross_earnings = Column(Float, default=0.0)
    total_deductions = Column(Float, default=0.0)
    net_salary = Column(Float, default=0.0)

    # Employer Contributions
    employer_pf = Column(Float, default=0.0)
    employer_esi = Column(Float, default=0.0)
    other_employer_contribution = Column(Float, default=0.0)
    total_employer_contribution = Column(Float, default=0.0)
    total_cost_to_company = Column(Float, default=0.0)

    # Payment info
    payment_status = Column(String(30), default="PENDING")  # PENDING, PROCESSED, PAID, FAILED
    payment_mode = Column(String(30), default="Bank Transfer")
    bank_name = Column(String(100), nullable=True)
    account_number = Column(String(50), nullable=True)
    ifsc_code = Column(String(30), nullable=True)
    
    # Complete frozen JSON calculation snapshot
    calculation_snapshot = Column(JSON, nullable=True)

    payroll_run = relationship("PayrollRun", back_populates="records")
    employee = relationship("Employee")
    items = relationship("PayrollRecordItem", back_populates="record", cascade="all, delete-orphan")
    payslip = relationship("Payslip", uselist=False, back_populates="record")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class PayrollRecordItem(Base):
    """Line item breakdown of earnings/deductions for a payroll record."""
    __tablename__ = "payroll_record_items"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("payroll_records.id", ondelete="CASCADE"), nullable=False)
    component_id = Column(Integer, ForeignKey("salary_components.id"), nullable=True)
    
    component_code = Column(String(50), nullable=False)
    component_name = Column(String(150), nullable=False)
    component_type = Column(String(30), nullable=False)  # EARNING, DEDUCTION, EMPLOYER_CONTRIBUTION
    amount = Column(Float, default=0.0, nullable=False)
    calculation_detail = Column(String(255), nullable=True)

    record = relationship("PayrollRecord", back_populates="items")
    component = relationship("SalaryComponent")


class PayrollInput(Base):
    """Monthly ad-hoc earnings/deductions (bonuses, sales incentive, OT adjustment)."""
    __tablename__ = "payroll_inputs"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    payroll_period_id = Column(Integer, ForeignKey("payroll_periods.id"), nullable=False)
    
    input_type = Column(String(50), nullable=False)  # BONUS, INCENTIVE, OVERTIME_OVERRIDE, OTHER_DEDUCTION, LOAN_ADVANCE, LOP_OVERRIDE
    title = Column(String(150), nullable=False)
    amount = Column(Float, default=0.0)
    hours = Column(Float, nullable=True)
    remarks = Column(String(255), nullable=True)
    status = Column(String(20), default="APPROVED")  # PENDING, APPROVED, REJECTED
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    employee = relationship("Employee")
    period = relationship("PayrollPeriod")

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PayrollException(Base):
    """Automatic pre-approval compliance and calculation exceptions."""
    __tablename__ = "payroll_exceptions"

    id = Column(Integer, primary_key=True, index=True)
    payroll_run_id = Column(Integer, ForeignKey("payroll_runs.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    
    severity = Column(String(20), default="WARNING")  # CRITICAL, WARNING, INFO
    error_code = Column(String(50), nullable=False)
    message = Column(String(500), nullable=False)
    is_resolved = Column(Boolean, default=False)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolution_notes = Column(String(500), nullable=True)

    payroll_run = relationship("PayrollRun", back_populates="exceptions")
    employee = relationship("Employee")

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PayrollAdjustment(Base):
    """Controlled post-calculation adjustment workflow."""
    __tablename__ = "payroll_adjustments"

    id = Column(Integer, primary_key=True, index=True)
    payroll_record_id = Column(Integer, ForeignKey("payroll_records.id", ondelete="CASCADE"), nullable=False)
    component_code = Column(String(50), nullable=False)
    
    old_amount = Column(Float, default=0.0)
    new_amount = Column(Float, default=0.0)
    difference = Column(Float, default=0.0)
    reason = Column(String(500), nullable=False)
    
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), default="PENDING")  # PENDING, APPROVED, REJECTED

    record = relationship("PayrollRecord")

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Payslip(Base):
    """Generated employee payslip record."""
    __tablename__ = "payslips"

    id = Column(Integer, primary_key=True, index=True)
    payroll_record_id = Column(Integer, ForeignKey("payroll_records.id", ondelete="CASCADE"), unique=True, nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    payslip_number = Column(String(50), unique=True, index=True, nullable=False)  # PS-202609-001
    payroll_month = Column(String(30), nullable=False)  # September 2026
    
    file_path = Column(String(255), nullable=True)
    is_published = Column(Boolean, default=True)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())

    record = relationship("PayrollRecord", back_populates="payslip")
    employee = relationship("Employee")

    @property
    def employee_code(self) -> str:
        return self.employee.employee_code if self.employee else ""

    @property
    def employee_name(self) -> str:
        if not self.employee:
            return ""
        return f"{self.employee.first_name} {self.employee.last_name}"

    @property
    def department(self) -> Optional[str]:
        return self.employee.department if self.employee else None

    @property
    def designation(self) -> Optional[str]:
        return self.employee.designation if self.employee else None

    @property
    def doj(self) -> Optional[date]:
        return self.employee.doj if self.employee else None

    @property
    def total_payroll_days(self) -> float:
        return self.record.total_payroll_days if self.record else 0.0

    @property
    def payable_days(self) -> float:
        return self.record.payable_days if self.record else 0.0

    @property
    def unpaid_leave_days(self) -> float:
        return self.record.unpaid_leave_days if self.record else 0.0

    @property
    def gross_earnings(self) -> float:
        return self.record.gross_earnings if self.record else 0.0

    @property
    def total_deductions(self) -> float:
        return self.record.total_deductions if self.record else 0.0

    @property
    def net_salary(self) -> float:
        return self.record.net_salary if self.record else 0.0

    @property
    def bank_name(self) -> Optional[str]:
        return self.record.bank_name if self.record else None

    @property
    def account_number(self) -> Optional[str]:
        return self.record.account_number if self.record else None

    @property
    def ifsc_code(self) -> Optional[str]:
        return self.record.ifsc_code if self.record else None

    @property
    def earnings(self) -> List[Dict[str, Any]]:
        if not self.record or not self.record.items:
            return []
        return [
            {"code": i.component_code, "name": i.component_name, "amount": i.amount, "detail": i.calculation_detail}
            for i in self.record.items if i.component_type == "EARNING"
        ]

    @property
    def deductions(self) -> List[Dict[str, Any]]:
        if not self.record or not self.record.items:
            return []
        return [
            {"code": i.component_code, "name": i.component_name, "amount": i.amount, "detail": i.calculation_detail}
            for i in self.record.items if i.component_type == "DEDUCTION"
        ]

    @property
    def employer_contributions(self) -> List[Dict[str, Any]]:
        if not self.record or not self.record.items:
            return []
        return [
            {"code": i.component_code, "name": i.component_name, "amount": i.amount, "detail": i.calculation_detail}
            for i in self.record.items if i.component_type == "EMPLOYER_CONTRIBUTION"
        ]


class PayrollAuditLog(Base):
    """Audit trail for all sensitive salary and payroll actions."""
    __tablename__ = "payroll_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False)  # SALARY_ASSIGNED, SALARY_REVISION_APPROVED, PAYROLL_CALCULATED, PAYROLL_LOCKED, etc.
    target_type = Column(String(50), nullable=False)  # EMPLOYEE_SALARY, PAYROLL_RUN, REVISION, ADJUSTMENT
    target_id = Column(Integer, nullable=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    reason = Column(String(500), nullable=True)

    user = relationship("User")
    employee = relationship("Employee")

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class StatutoryConfiguration(Base):
    """Configurable statutory rates and thresholds (EPF, ESI, PT, TDS)."""
    __tablename__ = "statutory_configurations"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(30), unique=True, index=True, nullable=False)  # PF, ESI, PT, TDS
    name = Column(String(100), nullable=False)
    
    employee_rate_pct = Column(Float, default=0.0)
    employer_rate_pct = Column(Float, default=0.0)
    wage_ceiling = Column(Float, nullable=True)  # e.g., 15000 for PF, 21000 for ESI
    min_wage_threshold = Column(Float, default=0.0)
    calculation_basis = Column(String(50), default="BASIC")  # BASIC, GROSS
    is_enabled = Column(Boolean, default=True)
    description = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
