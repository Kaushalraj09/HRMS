import pytest
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app import models
from app.models.employee import Employee
from app.models.user import User, Role
from app.models.payroll import (
    SalaryComponent,
    SalaryStructure,
    SalaryStructureComponent,
    EmployeeSalaryAssignment,
    PayrollPeriod,
    PayrollRun,
    PayrollRecord,
    Payslip,
    StatutoryConfiguration,
)
from app.seeds.seed_master_data import seed_roles, seed_master_data, seed_payroll_master_data
from app.seeds.seed_demo_users import seed_users
from app.services.payroll_calculation_service import PayrollCalculationService
from app.services.payroll_service import PayrollService
from app.schemas.payroll import (
    EmployeeSalaryAssignmentCreate,
    SalaryRevisionCreate,
    SalaryRevisionAction,
    PayrollRunCreate,
    SalaryCalculationRequest,
)


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    seed_roles(db)
    seed_master_data(db)
    seed_payroll_master_data(db)
    seed_users(db)
    db.commit()

    yield db
    db.close()


def test_salary_breakdown_ctc_mode(db_session):
    """Test salary breakdown calculation under Mode 2 (Total CTC basis)."""
    structure = db_session.query(SalaryStructure).filter(SalaryStructure.code == "STD_EMP").first()
    assert structure is not None

    preview = PayrollCalculationService.calculate_salary_breakdown(
        db=db_session,
        structure=structure,
        ctc_amount=1200000.0,
        salary_type="Annual",
        salary_basis="CTC",
    )

    assert preview.annual_ctc == 1200000.0
    assert preview.monthly_ctc == 100000.0
    # Basic = 50% of monthly CTC
    assert preview.gross_monthly > 0
    assert preview.net_monthly > 0
    # Net + Deductions must equal Gross
    assert round(preview.net_monthly + preview.total_deductions_monthly, 2) == preview.gross_monthly
    # Gross + Employer Contributions must equal CTC
    assert round(preview.gross_monthly + preview.employer_contributions_monthly, 2) == preview.monthly_ctc


def test_salary_breakdown_gross_mode(db_session):
    """Test salary breakdown calculation under Mode 1 (Gross Salary basis)."""
    structure = db_session.query(SalaryStructure).filter(SalaryStructure.code == "EXEC_STRUCT").first()
    assert structure is not None

    preview = PayrollCalculationService.calculate_salary_breakdown(
        db=db_session,
        structure=structure,
        ctc_amount=600000.0,
        salary_type="Annual",
        salary_basis="GROSS",
    )

    assert preview.gross_annual == 600000.0
    assert preview.gross_monthly == 50000.0
    assert preview.net_monthly > 0
    assert round(preview.net_monthly + preview.total_deductions_monthly, 2) == 50000.0


def test_employee_salary_assignment(db_session):
    """Test assigning salary structure to an employee and retrieving active breakdown."""
    emp = db_session.query(Employee).first()
    assert emp is not None

    structure = db_session.query(SalaryStructure).filter(SalaryStructure.code == "STD_EMP").first()
    assert structure is not None

    assign_data = EmployeeSalaryAssignmentCreate(
        employee_id=emp.id,
        salary_structure_id=structure.id,
        salary_basis="CTC",
        salary_type="Annual",
        ctc_amount=900000.0,
        effective_from=date(2026, 1, 1),
    )

    assignment = PayrollService.assign_employee_salary(db_session, assign_data, user_id=1)
    assert assignment.id is not None
    assert assignment.is_active == True
    assert assignment.annual_ctc == 900000.0

    retrieved = PayrollService.get_employee_salary(db_session, emp.id)
    assert retrieved is not None
    assert retrieved["employee_id"] == emp.id
    assert retrieved["annual_ctc"] == 900000.0
    assert retrieved["breakdown"] is not None


def test_salary_revision_workflow(db_session):
    """Test creating and approving a salary revision."""
    emp = db_session.query(Employee).first()
    structure = db_session.query(SalaryStructure).filter(SalaryStructure.code == "STD_EMP").first()

    # Initial assignment
    PayrollService.assign_employee_salary(
        db_session,
        EmployeeSalaryAssignmentCreate(
            employee_id=emp.id,
            salary_structure_id=structure.id,
            salary_basis="CTC",
            salary_type="Annual",
            ctc_amount=600000.0,
            effective_from=date(2026, 1, 1),
        ),
        user_id=1,
    )

    # Submit revision
    rev = PayrollService.create_revision(
        db_session,
        SalaryRevisionCreate(
            employee_id=emp.id,
            new_salary_structure_id=structure.id,
            new_ctc_amount=750000.0,
            salary_type="Annual",
            effective_from=date(2026, 4, 1),
            reason="Annual Appraisal",
        ),
        user_id=1,
    )
    assert rev.status == "PENDING"
    assert rev.increment_amount == 150000.0
    assert rev.increment_percentage == 25.0

    # Approve revision
    action_res = PayrollService.action_revision(
        db_session,
        rev.id,
        SalaryRevisionAction(approved=True, remarks="Approved by Director"),
        user_id=1,
    )
    assert action_res["status"] == "APPROVED"

    # Verify new active salary
    latest_salary = PayrollService.get_employee_salary(db_session, emp.id)
    assert latest_salary["annual_ctc"] == 750000.0


def test_payroll_run_and_locking(db_session):
    """Test full payroll execution, calculations, and locking to generate payslips."""
    emp = db_session.query(Employee).first()
    structure = db_session.query(SalaryStructure).filter(SalaryStructure.code == "STD_EMP").first()

    PayrollService.assign_employee_salary(
        db_session,
        EmployeeSalaryAssignmentCreate(
            employee_id=emp.id,
            salary_structure_id=structure.id,
            salary_basis="CTC",
            salary_type="Annual",
            ctc_amount=840000.0,
            effective_from=date(2026, 1, 1),
        ),
        user_id=1,
    )

    # Execute payroll run for Jan 2026
    run_create = PayrollRunCreate(
        year=2026,
        month=1,
        selected_employee_ids=[emp.id],
    )
    run = PayrollService.execute_payroll_run(db_session, run_create, user_id=1)
    assert run.id is not None
    assert run.status == "DRAFT"
    assert run.processed_employees == 1
    assert run.total_net > 0

    # Verify records
    records = db_session.query(PayrollRecord).filter(PayrollRecord.payroll_run_id == run.id).all()
    assert len(records) == 1
    record = records[0]
    assert record.net_salary > 0
    assert len(record.items) > 0

    # Lock run
    lock_res = PayrollService.lock_payroll_run(db_session, run.id, user_id=1)
    assert lock_res["status"] == "LOCKED"

    # Verify payslip generated
    payslips = db_session.query(Payslip).filter(Payslip.employee_id == emp.id).all()
    assert len(payslips) == 1
    ps = payslips[0]
    assert ps.is_published == True
    assert ps.net_salary == record.net_salary
    assert ps.payroll_month == "2026-01"


def test_salary_structure_serialization(db_session):
    """Test that SalaryStructureResponse properly serializes structures and component fields."""
    from app.schemas.payroll import SalaryStructureResponse
    structures = PayrollService.get_structures(db_session)
    assert len(structures) > 0
    for s in structures:
        res = SalaryStructureResponse.model_validate(s)
        assert res.id == s.id
        assert len(res.components) > 0
        for comp in res.components:
            assert comp.component_code != ""
            assert comp.component_name != ""
            assert comp.component_type != ""


def test_salary_structure_update_and_delete(db_session):
    """Test updating and deleting a salary structure."""
    from app.schemas.payroll import SalaryStructureCreate, SalaryStructureUpdate, StructureComponentItem
    basic = db_session.query(SalaryComponent).filter(SalaryComponent.code == "BASIC").first()
    
    # Create new custom structure
    created = PayrollService.create_structure(
        db_session,
        SalaryStructureCreate(
            code="TEMP_STRUCT",
            name="Temporary Structure",
            salary_basis="CTC",
            description="Testing update and delete",
            components=[
                StructureComponentItem(
                    component_id=basic.id,
                    calculation_type="PERCENTAGE",
                    calculation_basis="CTC",
                    percentage_or_value=50.0,
                    sequence_order=1
                )
            ]
        ),
        user_id=1
    )
    assert created.id is not None
    assert created.name == "Temporary Structure"
    
    # Update structure
    updated = PayrollService.update_structure(
        db_session,
        created.id,
        SalaryStructureUpdate(
            name="Updated Temp Structure",
            description="Updated description"
        ),
        user_id=1
    )
    assert updated.name == "Updated Temp Structure"
    assert updated.description == "Updated description"

    # Delete structure
    del_res = PayrollService.delete_structure(db_session, created.id, user_id=1)
    assert del_res["id"] == created.id
    assert db_session.query(SalaryStructure).filter(SalaryStructure.id == created.id).first() is None


def test_salary_breakdown_ctc_216007_statutory(db_session):
    """
    Test statutory payroll calculation for Annual CTC ₹216,007 under standard rules.
    Monthly CTC = ₹18,000.58.
    Ensures ESI and PF statutory deduction, Special Allowance balance deduction,
    exact Total CTC reconciliation, and zero validation warning.
    """
    structure = db_session.query(SalaryStructure).filter(SalaryStructure.code == "STD_EMP").first()
    assert structure is not None

    preview = PayrollCalculationService.calculate_salary_breakdown(
        db=db_session,
        structure=structure,
        ctc_amount=216007.0,
        salary_type="Annual",
        salary_basis="CTC",
    )

    assert preview.annual_ctc == 216007.0
    assert preview.monthly_ctc == 18000.58

    # Extract component monthly values
    components = {c.code: c.monthly_amount for c in preview.earnings + preview.deductions + preview.employer_contributions}

    basic = components.get("BASIC")
    hra = components.get("HRA")
    special_allowance = components.get("SPECIAL_ALLOWANCE")
    employer_pf = components.get("PF_EMPLOYER")
    employer_esi = components.get("ESI_EMPLOYER")
    employee_pf = components.get("PF_EMP")
    employee_esi = components.get("ESI_EMP")

    # Formulas verification:
    # 1. Monthly CTC = Annual CTC / 12 = 18,000.58
    assert preview.monthly_ctc == 18000.58
    # 2. Basic = 50% of CTC = 9,000.29
    assert basic == 9000.29
    # 3. HRA = 40% of Basic = 3,600.12
    assert hra == 3600.12
    # 4. Employer PF = 12% of Basic = 1,080.03
    assert employer_pf == 1080.03
    # 5. Employer ESI statutory = 532.61 (Annual 6,391.32 reconciling with statutory rule)
    assert employer_esi == 532.61
    assert round(employer_esi * 12.0, 2) == 6391.32
    # 6. Gross Salary = Monthly CTC - Employer PF - Employer ESI = 16,387.94
    assert preview.gross_monthly == 16387.94
    assert round(preview.monthly_ctc - employer_pf - employer_esi, 2) == preview.gross_monthly
    # 7. Special Allowance = Gross Salary - Basic - HRA = 3,787.53
    assert special_allowance == 3787.53
    assert round(preview.gross_monthly - basic - hra, 2) == special_allowance
    # 8. Total CTC validation: Gross + Employer PF + Employer ESI == Monthly CTC
    assert round(preview.gross_monthly + employer_pf + employer_esi, 2) == preview.monthly_ctc
    assert preview.validation_warning is None
    # 9. Net Take-Home = Gross - Employee PF - Employee ESI (No PT since not applicable)
    assert employee_pf == 1080.03
    assert employee_esi == 122.91
    pt = components.get("PT", 0.0)
    assert pt == 0.0
    assert preview.net_monthly == round(preview.gross_monthly - employee_pf - employee_esi, 2)


def test_salary_breakdown_ctc_216007_with_550_esi_override(db_session):
    """
    Test user's specific bug scenario for Annual CTC ₹216,007 when Employer ESI = ₹550.00:
    Monthly CTC = ₹18,000.58
    Employer PF = ₹1,080.03
    Employer ESI = ₹550.00
    Gross Salary = ₹18,000.58 - ₹1,080.03 - ₹550.00 = ₹16,370.55
    Basic = ₹9,000.29, HRA = ₹3,600.12
    Special Allowance = ₹16,370.55 - ₹9,000.29 - ₹3,600.12 = ₹3,770.14
    Total CTC = Gross Salary + Employer PF + Employer ESI = ₹18,000.58 (reconciles perfectly)
    """
    structure = db_session.query(SalaryStructure).filter(SalaryStructure.code == "STD_EMP").first()
    assert structure is not None

    preview = PayrollCalculationService.calculate_salary_breakdown(
        db=db_session,
        structure=structure,
        ctc_amount=216007.0,
        salary_type="Annual",
        salary_basis="CTC",
        custom_overrides={"ESI_EMPLOYER": 550.0},
    )

    assert preview.monthly_ctc == 18000.58
    components = {c.code: c.monthly_amount for c in preview.earnings + preview.deductions + preview.employer_contributions}

    basic = components.get("BASIC")
    hra = components.get("HRA")
    special_allowance = components.get("SPECIAL_ALLOWANCE")
    employer_pf = components.get("PF_EMPLOYER")
    employer_esi = components.get("ESI_EMPLOYER")

    assert basic == 9000.29
    assert hra == 3600.12
    assert employer_pf == 1080.03
    assert employer_esi == 550.00

    # Gross Salary must be: 18,000.58 - 1,080.03 - 550.00 = 16,370.55
    assert preview.gross_monthly == 16370.55
    # Special Allowance must be: 16,370.55 - 9,000.29 - 3,600.12 = 3,770.14
    assert special_allowance == 3770.14

    # Total CTC validation:
    assert round(preview.gross_monthly + employer_pf + employer_esi, 2) == preview.monthly_ctc
    assert preview.validation_warning is None



