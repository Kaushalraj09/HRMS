"""
Purge Seeded E2E Test Data Script.
Safely removes all seeded test entities:
- Sarah Carter (hr.carter@hrms.com)
- Vikram Malhotra (manager.vikram@hrms.com)
- Ananya Sharma (emp.ananya@hrms.com)
- Associated attendance, time-off requests, approval tasks, payroll runs, payslips, and balances.
- Resets manager assignments on existing employees.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.database import SessionLocal
from app.models.user import User
from app.models.employee import Employee
from app.models.hr_user import HrUser
from app.models.attendance import Attendance
from app.models.timeoff import TimeOffRequest
from app.models.approval_task import ApprovalTask
from app.models.approval_log import ApprovalLog
from app.models.payroll import (
    PayrollRun,
    PayrollRecord,
    PayrollRecordItem,
    PayrollAdjustment,
    PayrollException,
    Payslip,
    EmployeeSalaryAssignment,
    PayrollAuditLog,
)
from app.models.leave_balance import EmployeeLeaveBalance


def purge_seeded_data():
    db = SessionLocal()
    try:
        print("================================================================================")
        print("                   PURGING SEEDED E2E TEST DATA                                 ")
        print("================================================================================")

        test_emails = [
            "hr.carter@hrms.com",
            "manager.vikram@hrms.com",
            "emp.ananya@hrms.com"
        ]

        test_users = db.query(User).filter(User.email.in_(test_emails)).all()
        test_user_ids = [u.id for u in test_users]
        print(f"Found {len(test_users)} test user(s): {[u.email for u in test_users]}")

        test_employees = db.query(Employee).filter(
            (Employee.user_id.in_(test_user_ids)) | (Employee.official_email.in_(test_emails))
        ).all()
        test_emp_ids = [e.id for e in test_employees]
        print(f"Found {len(test_employees)} test employee(s): {[e.employee_code for e in test_employees]}")

        # 1. Unlink any other employees pointing to test managers
        if test_emp_ids:
            unlinked = db.query(Employee).filter(
                Employee.reporting_manager_id.in_(test_emp_ids),
                ~Employee.id.in_(test_emp_ids)
            ).all()
            for emp in unlinked:
                emp.reporting_manager_id = None
                print(f"  • Unlinked manager from existing employee: {emp.first_name} {emp.last_name}")
            db.commit()

        # 2. Delete test payroll runs (e.g. PAY-202609-*)
        test_runs = db.query(PayrollRun).filter(PayrollRun.run_number.like("PAY-202609%")).all()
        for run in test_runs:
            print(f"  • Deleting test payroll run #{run.run_number}")
            records = db.query(PayrollRecord).filter(PayrollRecord.payroll_run_id == run.id).all()
            rec_ids = [r.id for r in records]
            if rec_ids:
                db.query(Payslip).filter(Payslip.payroll_record_id.in_(rec_ids)).delete(synchronize_session=False)
                db.query(PayrollAdjustment).filter(PayrollAdjustment.payroll_record_id.in_(rec_ids)).delete(synchronize_session=False)
                db.query(PayrollRecordItem).filter(PayrollRecordItem.record_id.in_(rec_ids)).delete(synchronize_session=False)
                db.query(PayrollRecord).filter(PayrollRecord.id.in_(rec_ids)).delete(synchronize_session=False)
            db.query(PayrollException).filter(PayrollException.payroll_run_id == run.id).delete(synchronize_session=False)
            db.query(PayrollAuditLog).filter(PayrollAuditLog.target_id == run.id, PayrollAuditLog.target_type == "PAYROLL_RUN").delete(synchronize_session=False)
            db.delete(run)
            db.commit()

        # Delete any audit logs referencing test users or employees
        if test_user_ids or test_emp_ids:
            db.query(PayrollAuditLog).filter(
                (PayrollAuditLog.user_id.in_(test_user_ids)) |
                (PayrollAuditLog.employee_id.in_(test_emp_ids))
            ).delete(synchronize_session=False)
            db.commit()

        # 3. Delete any remaining test payslips or payroll records for test employees
        if test_emp_ids:
            records = db.query(PayrollRecord).filter(PayrollRecord.employee_id.in_(test_emp_ids)).all()
            rec_ids = [r.id for r in records]
            if rec_ids:
                db.query(Payslip).filter(Payslip.payroll_record_id.in_(rec_ids)).delete(synchronize_session=False)
                db.query(PayrollRecordItem).filter(PayrollRecordItem.record_id.in_(rec_ids)).delete(synchronize_session=False)
                db.query(PayrollRecord).filter(PayrollRecord.id.in_(rec_ids)).delete(synchronize_session=False)
            db.query(EmployeeSalaryAssignment).filter(EmployeeSalaryAssignment.employee_id.in_(test_emp_ids)).delete(synchronize_session=False)

        # 4. Delete approval tasks, approval logs, time-off requests, attendance, leave balances
        if test_emp_ids or test_user_ids:
            test_requests = db.query(TimeOffRequest).filter(TimeOffRequest.employee_id.in_(test_emp_ids)).all()
            test_req_ids = [r.id for r in test_requests]

            if test_req_ids or test_user_ids:
                db.query(ApprovalLog).filter(
                    (ApprovalLog.timeoff_request_id.in_(test_req_ids)) |
                    (ApprovalLog.action_by_user_id.in_(test_user_ids))
                ).delete(synchronize_session=False)

            db.query(ApprovalTask).filter(
                (ApprovalTask.employee_id.in_(test_emp_ids)) |
                (ApprovalTask.submitted_by.in_(test_user_ids)) |
                (ApprovalTask.reviewed_by.in_(test_user_ids)) |
                (ApprovalTask.manager_reviewed_by.in_(test_user_ids))
            ).delete(synchronize_session=False)

            db.query(TimeOffRequest).filter(TimeOffRequest.employee_id.in_(test_emp_ids)).delete(synchronize_session=False)
            db.query(Attendance).filter(Attendance.employee_id.in_(test_emp_ids)).delete(synchronize_session=False)
            db.query(EmployeeLeaveBalance).filter(EmployeeLeaveBalance.employee_id.in_(test_emp_ids)).delete(synchronize_session=False)
            db.commit()
            print("  • Cleared attendance, time-off, approval logs, approval tasks, and leave balances for test employees.")

        # 5. Delete hr_user records
        if test_user_ids:
            db.query(HrUser).filter(HrUser.user_id.in_(test_user_ids)).delete(synchronize_session=False)
            db.commit()

        # 6. Delete employees
        if test_emp_ids:
            for emp in test_employees:
                db.delete(emp)
            db.commit()
            print(f"  • Deleted {len(test_employees)} test employee records.")

        # 7. Delete users
        if test_users:
            for u in test_users:
                db.delete(u)
            db.commit()
            print(f"  • Deleted {len(test_users)} test user accounts.")

        print("\n✓ SEEDED TEST DATA PURGED CLEANLY!")

    finally:
        db.close()


if __name__ == "__main__":
    purge_seeded_data()
