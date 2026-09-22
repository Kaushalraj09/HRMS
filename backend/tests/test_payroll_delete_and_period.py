import pytest
from datetime import date
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app import models
from app.models.employee import Employee
from app.models.payroll import (
    SalaryStructure,
    PayrollPeriod,
    PayrollRun,
    PayrollRecord,
    Payslip,
)
from app.seeds.seed_master_data import seed_roles, seed_master_data, seed_payroll_master_data
from app.seeds.seed_demo_users import seed_users
from app.services.payroll_service import PayrollService
from app.schemas.payroll import (
    EmployeeSalaryAssignmentCreate,
    PayrollRunCreate,
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


def test_payroll_run_period_and_delete(db_session):
    emp = db_session.query(Employee).first()
    structure = db_session.query(SalaryStructure).filter(SalaryStructure.code == "STD_EMP").first()

    # Assign salary to employee
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

    # 1. Execute Payroll Run for September 2026
    run_create = PayrollRunCreate(year=2026, month=9, selected_employee_ids=[emp.id])
    run = PayrollService.execute_payroll_run(db_session, run_create, user_id=1)
    assert run is not None
    assert "202609" in run.run_number

    # 2. Test get_runs returns month, year, and period_name correctly
    runs = PayrollService.get_runs(db_session, year=2026)
    assert len(runs) >= 1
    target_run = next(r for r in runs if r["id"] == run.id)
    assert target_run["year"] == 2026
    assert target_run["month"] == 9
    assert target_run["period_name"] == "September 2026"
    assert target_run["status"] == "DRAFT"

    # 3. Test delete_payroll_run on DRAFT run
    run_id = run.id
    period_id = run.period_id
    del_result = PayrollService.delete_payroll_run(db_session, run_id, user_id=1)
    assert "deleted successfully" in del_result["message"]

    # Verify run is deleted
    assert db_session.query(PayrollRun).filter(PayrollRun.id == run_id).first() is None
    assert db_session.query(PayrollRecord).filter(PayrollRecord.payroll_run_id == run_id).first() is None

    # Period status should be reset to OPEN since no remaining runs exist
    period = db_session.query(PayrollPeriod).filter(PayrollPeriod.id == period_id).first()
    assert period.status == "OPEN"


def test_cannot_delete_paid_payroll_run(db_session):
    emp = db_session.query(Employee).first()
    structure = db_session.query(SalaryStructure).filter(SalaryStructure.code == "STD_EMP").first()

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

    run = PayrollService.execute_payroll_run(
        db_session,
        PayrollRunCreate(year=2026, month=9, selected_employee_ids=[emp.id]),
        user_id=1,
    )
    PayrollService.lock_payroll_run(db_session, run.id, user_id=1)
    PayrollService.mark_run_paid(db_session, run.id, user_id=1)

    # Attempting to delete a PAID run should raise HTTPException 400
    with pytest.raises(HTTPException) as exc_info:
        PayrollService.delete_payroll_run(db_session, run.id, user_id=1)
    assert exc_info.value.status_code == 400
    assert "Cannot delete a PAID payroll run" in exc_info.value.detail


def test_export_payroll_and_bank_pdf(db_session):
    emp = db_session.query(Employee).first()
    structure = db_session.query(SalaryStructure).filter(SalaryStructure.code == "STD_EMP").first()

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

    run = PayrollService.execute_payroll_run(
        db_session,
        PayrollRunCreate(year=2026, month=9, selected_employee_ids=[emp.id]),
        user_id=1,
    )

    import asyncio

    async def read_stream(response):
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode("utf-8"))
        return b"".join(chunks)

    # 1. Test export_payroll_pdf
    pdf_resp = PayrollService.export_payroll_pdf(db_session, run.id)
    assert pdf_resp.media_type == "application/pdf"
    assert "Payroll_Run_" in pdf_resp.headers["Content-Disposition"]
    assert ".pdf" in pdf_resp.headers["Content-Disposition"]
    body = asyncio.run(read_stream(pdf_resp))
    assert body.startswith(b"%PDF")
    assert len(body) > 500

    # 2. Test export_bank_transfer_pdf
    bank_resp = PayrollService.export_bank_transfer_pdf(db_session, run.id)
    assert bank_resp.media_type == "application/pdf"
    assert "Bank_Payout_" in bank_resp.headers["Content-Disposition"]
    assert ".pdf" in bank_resp.headers["Content-Disposition"]
    bank_body = asyncio.run(read_stream(bank_resp))
    assert bank_body.startswith(b"%PDF")
    assert len(bank_body) > 500

    # 3. Test generate_payslip_pdf
    from app.models.payroll import Payslip
    payslip = db_session.query(Payslip).first()
    if payslip:
        payslip_resp = PayrollService.generate_payslip_pdf(db_session, payslip.id)
        assert payslip_resp.media_type == "application/pdf"
        assert "Payslip_" in payslip_resp.headers["Content-Disposition"]
        assert ".pdf" in payslip_resp.headers["Content-Disposition"]
        payslip_body = asyncio.run(read_stream(payslip_resp))
        assert payslip_body.startswith(b"%PDF")
        assert len(payslip_body) > 500

    # 4. Test legacy CSV export methods also deliver PDF
    legacy_payroll = PayrollService.export_payroll_csv(db_session, run.id)
    assert legacy_payroll.media_type == "application/pdf"
    legacy_bank = PayrollService.export_bank_transfer_csv(db_session, run.id)
    assert legacy_bank.media_type == "application/pdf"
