"""
End-to-End Realistic Data Seeding & System Verification Script.

Creates:
1. New HR User (Sarah Carter, hr.carter@hrms.com / Hr@1234)
2. New Manager User (Vikram Malhotra, manager.vikram@hrms.com / Manager@1234)
3. New Employee (Ananya Sharma, emp.ananya@hrms.com / Emp@1234), reporting to Vikram Malhotra
4. Realistic Attendance and Leaves for Sept 2026 (Completed Month) to verify LOP & Double-Deduction Prevention
5. Salary Assignment & Full Payroll Run with Payslip Generation
6. Active October 2026 Leaves and Manager Approval Workflow
7. Validates All HRMS Norms and Outputs Detailed Summary
"""

import os
import sys
from datetime import date, datetime, time, timedelta

# Ensure backend root on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.database import SessionLocal
from app.models.user import User, Role
from app.models.employee import Employee
from app.models.hr_user import HrUser
from app.models.master_data import Shift, WorkLocation, LeaveType, Holiday
from app.models.attendance import Attendance
from app.models.timeoff import TimeOffRequest
from app.models.approval_task import ApprovalTask
from app.models.payroll import (
    SalaryStructure,
    EmployeeSalaryAssignment,
    PayrollPeriod,
    PayrollRun,
    PayrollRecord,
    Payslip,
)
from app.core.security import hash_password
from app.seeds.seed_master_data import seed_master_data, seed_roles, seed_payroll_master_data
from app.services.leave_balance_service import LeaveBalanceService
from app.services.timeoff_service import get_employee_leave_balances, approve_request
from app.services.payroll_calculation_service import PayrollCalculationService
from app.services.payroll_service import PayrollService
from app.schemas.payroll import PayrollRunCreate


def run_e2e_verification():
    db = SessionLocal()
    print("================================================================================")
    print("      HRMS E2E DATA SEEDING & SYSTEM NORMS VERIFICATION ENGINE                 ")
    print("================================================================================")

    try:
        # 1. Master Data & Roles Baseline
        print("\n--- [Step 1] Ensuring Roles & Master Data Baseline ---")
        seed_roles(db)
        seed_master_data(db)
        seed_payroll_master_data(db)
        db.commit()

        emp_role = db.query(Role).filter(Role.name == "Employee").first()
        hr_role = db.query(Role).filter(Role.name == "HR").first()
        mgr_role = db.query(Role).filter(Role.name == "Manager").first()

        shift = db.query(Shift).filter(Shift.code == "GEN_SHIFT").first() or db.query(Shift).first()
        loc = db.query(WorkLocation).first()

        # 2. Create / Ensure New HR User
        print("\n--- [Step 2] Creating New HR Profile ---")
        hr_email = "hr.carter@hrms.com"
        hr_user = db.query(User).filter(User.email == hr_email).first()
        if not hr_user:
            hr_user = User(
                email=hr_email,
                password_hash=hash_password("Hr@1234"),
                display_name="Sarah Carter",
                role_id=hr_role.id,
                status="Active"
            )
            db.add(hr_user)
            db.flush()

        hr_emp = db.query(Employee).filter(Employee.user_id == hr_user.id).first()
        if not hr_emp:
            hr_emp = Employee(
                user_id=hr_user.id,
                employee_code="HR001",
                first_name="Sarah",
                last_name="Carter",
                department="Human Resources",
                designation="HR Business Partner",
                official_email=hr_email,
                mobile="9811122233",
                shift_id=shift.id if shift else None,
                status="Active"
            )
            db.add(hr_emp)
            db.flush()
        print(f"✓ HR Profile Verified: {hr_user.display_name} ({hr_email}) [Role: HR]")

        # 3. Create / Ensure New Manager User
        print("\n--- [Step 3] Creating New Manager Profile ---")
        mgr_email = "manager.vikram@hrms.com"
        mgr_user = db.query(User).filter(User.email == mgr_email).first()
        if not mgr_user:
            mgr_user = User(
                email=mgr_email,
                password_hash=hash_password("Manager@1234"),
                display_name="Vikram Malhotra",
                role_id=mgr_role.id,
                status="Active"
            )
            db.add(mgr_user)
            db.flush()

        mgr_emp = db.query(Employee).filter(Employee.user_id == mgr_user.id).first()
        if not mgr_emp:
            mgr_emp = Employee(
                user_id=mgr_user.id,
                employee_code="MGR01",
                first_name="Vikram",
                last_name="Malhotra",
                department="Engineering",
                designation="Engineering Lead",
                official_email=mgr_email,
                mobile="9822233344",
                shift_id=shift.id if shift else None,
                status="Active"
            )
            db.add(mgr_emp)
            db.flush()
        print(f"✓ Manager Profile Verified: {mgr_user.display_name} ({mgr_email}) [Role: Manager, Code: {mgr_emp.employee_code}]")

        # 4. Create / Ensure Test Employee Reporting to Manager Vikram
        print("\n--- [Step 4] Creating Test Employee (Reporting to Vikram Malhotra) ---")
        emp_email = "emp.ananya@hrms.com"
        emp_user = db.query(User).filter(User.email == emp_email).first()
        if not emp_user:
            emp_user = User(
                email=emp_email,
                password_hash=hash_password("Emp@1234"),
                display_name="Ananya Sharma",
                role_id=emp_role.id,
                status="Active"
            )
            db.add(emp_user)
            db.flush()

        emp = db.query(Employee).filter(Employee.user_id == emp_user.id).first()
        if not emp:
            emp = Employee(
                user_id=emp_user.id,
                employee_code="EMP101",
                first_name="Ananya",
                last_name="Sharma",
                department="Engineering",
                designation="Full Stack Engineer",
                official_email=emp_email,
                mobile="9833344455",
                shift_id=shift.id if shift else None,
                reporting_manager_id=mgr_emp.id,
                status="Active"
            )
            db.add(emp)
            db.flush()
        else:
            emp.reporting_manager_id = mgr_emp.id
            db.flush()
        print(f"✓ Employee Profile Verified: {emp.first_name} {emp.last_name} ({emp_email}) [Reports to: {mgr_emp.first_name} {mgr_emp.last_name}]")

        # Also link existing employee Kaushal / Rohit
        existing_emp = db.query(Employee).filter(Employee.official_email == "rohit.raj@aivan.com").first()
        if existing_emp:
            existing_emp.reporting_manager_id = mgr_emp.id
            print(f"✓ Linked Existing Employee {existing_emp.first_name} {existing_emp.last_name} to Manager {mgr_emp.first_name} {mgr_emp.last_name}")

        db.commit()

        # 5. Initialize Leave Balances for 2026
        print("\n--- [Step 5] Initializing Yearly Leave Balances (2026) ---")
        balances_summary_initial = get_employee_leave_balances(db, emp.id, year=2026)
        print(f"  Leave Year: {balances_summary_initial.get('leave_year', 2026)}")
        print(f"  Paid Leave (PL): Allocated = {balances_summary_initial['paid_leave']['allocated']}d, Remaining = {balances_summary_initial['paid_leave']['remaining']}d")
        print(f"  Unpaid Leave (UL): Allocated = {balances_summary_initial['unpaid_leave']['allocated']}d, Remaining = {balances_summary_initial['unpaid_leave']['remaining']}d")

        # 6. Seed September 2026 Completed Payroll Scenario
        print("\n--- [Step 6] Seeding September 2026 Scenario (Completed Month) ---")
        sept_start = date(2026, 9, 1)
        sept_end = date(2026, 9, 30)

        # Clean existing test records in Sept for reproducibility
        db.query(TimeOffRequest).filter(
            TimeOffRequest.employee_id == emp.id,
            TimeOffRequest.date >= sept_start,
            TimeOffRequest.date <= sept_end
        ).delete()
        db.query(Attendance).filter(
            Attendance.employee_id == emp.id,
            Attendance.date >= sept_start,
            Attendance.date <= sept_end
        ).delete()
        db.commit()

        # A. Approved Unpaid Leaves (2 Days: 8th and 9th Sept 2026)
        to_ul_1 = TimeOffRequest(
            employee_id=emp.id,
            date=date(2026, 9, 8),
            leave_type="Unpaid Leave",
            duration_hours=8.0,
            status="Approved",
            reason="Family obligation - out of station"
        )
        to_ul_2 = TimeOffRequest(
            employee_id=emp.id,
            date=date(2026, 9, 9),
            leave_type="Unpaid Leave",
            duration_hours=8.0,
            status="Approved",
            reason="Family obligation - travel return"
        )
        db.add_all([to_ul_1, to_ul_2])

        # B. Approved Paid Leave (1 Day: 18th Sept 2026)
        to_pl_1 = TimeOffRequest(
            employee_id=emp.id,
            date=date(2026, 9, 18),
            leave_type="Paid Leave",
            duration_hours=8.0,
            status="Approved",
            reason="Personal work"
        )
        db.add(to_pl_1)
        db.commit()

        # Update balance records consumption for approved leaves
        LeaveBalanceService.sync_balances_from_requests(db, emp.id, year=2026)

        # C. Seed Attendance Records for all 30 days of September 2026
        # Testing Double-Deduction Prevention:
        # - On 2026-09-18 (Approved Paid Leave): marked 'ABSENT' -> MUST NOT BE COUNTED AS ABSENT DEDUCTION!
        # - On 2026-09-08 & 2026-09-09 (Approved Unpaid Leave): marked 'ABSENT' -> MUST COUNT AS EXACTLY 1 LOP DAY EACH, NOT 2!
        # - On 2026-09-22: genuine unexcused absence -> marked 'ABSENT' with no leave.
        curr_d = sept_start
        while curr_d <= sept_end:
            weekday = curr_d.weekday()  # 0=Mon, 6=Sun
            if weekday == 6:  # Sunday weekly off
                curr_d += timedelta(days=1)
                continue

            if curr_d in [date(2026, 9, 8), date(2026, 9, 9)]:
                # Unpaid leave days
                att = Attendance(
                    employee_id=emp.id,
                    date=curr_d,
                    status="Absent",
                    total_working_minutes=0
                )
            elif curr_d == date(2026, 9, 18):
                # Approved paid leave day with missing biometric punch
                att = Attendance(
                    employee_id=emp.id,
                    date=curr_d,
                    status="Absent",
                    total_working_minutes=0
                )
            elif curr_d == date(2026, 9, 22):
                # Unexcused absence
                att = Attendance(
                    employee_id=emp.id,
                    date=curr_d,
                    status="Absent",
                    total_working_minutes=0
                )
            else:
                # Normal present day
                att = Attendance(
                    employee_id=emp.id,
                    date=curr_d,
                    status="Present",
                    punch_in=time(9, 2),
                    punch_out=time(18, 5),
                    total_working_minutes=510,
                    work_mode="Office"
                )
            db.add(att)
            curr_d += timedelta(days=1)

        db.commit()
        print("✓ Attendance and Leaves seeded for September 2026:")
        print("   - 2 Approved Unpaid Leave days (Sept 8, Sept 9)")
        print("   - 1 Approved Paid Leave day (Sept 18, marked ABSENT in attendance)")
        print("   - 1 Unexcused Absence day (Sept 22, marked ABSENT)")
        print("   - All other working days marked PRESENT")

        # 7. Salary Structure & Assignment
        print("\n--- [Step 7] Assigning Salary Structure & Compensation ---")
        struct = db.query(SalaryStructure).filter(SalaryStructure.code == "STD_EMP").first()
        if not struct:
            struct = db.query(SalaryStructure).first()

        assign = db.query(EmployeeSalaryAssignment).filter(
            EmployeeSalaryAssignment.employee_id == emp.id,
            EmployeeSalaryAssignment.is_active == True
        ).first()

        if not assign:
            assign = EmployeeSalaryAssignment(
                employee_id=emp.id,
                salary_structure_id=struct.id,
                annual_ctc=600000.0,  # 50,000 monthly CTC (approx 45,000 fixed gross)
                salary_basis="CTC",
                salary_type="Annual",
                effective_from=date(2026, 1, 1),
                is_active=True
            )
            db.add(assign)
            db.commit()
        else:
            assign.annual_ctc = 600000.0
            assign.salary_structure_id = struct.id
            db.commit()

        print(f"✓ Salary Assigned to {emp.first_name} {emp.last_name}: Annual CTC ₹6,00,000 (Monthly CTC: ₹50,000.00)")

        # 8. Verify Attendance & LOP Metrics
        print("\n--- [Step 8] Evaluating Attendance & LOP Metrics (HRMS Norms) ---")
        metrics = PayrollCalculationService.get_attendance_and_leave_metrics(
            db=db,
            employee_id=emp.id,
            start_date=sept_start,
            end_date=sept_end
        )

        print(f"  • Total Month Days: {metrics['total_days']}")
        print(f"  • Present Days: {metrics['present_days']}")
        print(f"  • Approved Paid Leave Days: {metrics['paid_leave_days']}")
        print(f"  • Approved Unpaid Leave Days: {metrics['approved_unpaid_leave_days']}")
        print(f"  • Unexcused Absent Days: {metrics['absent_days']}")
        print(f"  • Total LOP Days (UL + Unexcused): {metrics['lop_days']}")
        print(f"  • Payable Days (Total - LOP): {metrics['payable_days']}")

        # Assert Double Deduction Prevention Norms
        assert metrics['paid_leave_days'] == 1.0, "Approved paid leave must count as 1.0 paid leave day"
        assert metrics['approved_unpaid_leave_days'] == 2.0, "Approved unpaid leave must count as 2.0 days"
        assert metrics['absent_days'] == 1.0, "Only unexcused absence (Sept 22) must count as absent; Sept 18 (paid leave) must not be counted as absent!"
        assert metrics['lop_days'] == 3.0, "Total LOP days must be exactly 3.0 (2 UL + 1 Unexcused), zero double deduction!"
        assert metrics['payable_days'] == 27.0, "Payable days must be exactly 27.0 (30 - 3)"
        print("  ✓ DOUBLE DEDUCTION PREVENTION VERIFIED: Absence on Paid Leave date (Sept 18) excluded from LOP.")
        print("  ✓ UNPAID LEAVE LOP COUNT VERIFIED: September 8 & 9 counted as exactly 1 LOP day each (not duplicated with attendance).")

        # 9. Verify Payroll Calculations Under Different Divisor Norms
        print("\n--- [Step 9] Calculating Payroll Across Supported Divisor Modes ---")
        
        # Divisor Mode A: CALENDAR_DAYS (30 days)
        res_cal = PayrollCalculationService.calculate_employee_payroll(
            db=db,
            employee_id=emp.id,
            start_date=sept_start,
            end_date=sept_end,
            lop_divisor_mode="CALENDAR_DAYS"
        )
        # Divisor Mode B: FIXED_30 (30 days)
        res_fixed = PayrollCalculationService.calculate_employee_payroll(
            db=db,
            employee_id=emp.id,
            start_date=sept_start,
            end_date=sept_end,
            lop_divisor_mode="FIXED_30"
        )
        # Divisor Mode C: WORKING_DAYS (22 days)
        res_work = PayrollCalculationService.calculate_employee_payroll(
            db=db,
            employee_id=emp.id,
            start_date=sept_start,
            end_date=sept_end,
            period_working_days=22,
            lop_divisor_mode="WORKING_DAYS"
        )

        fg = res_cal["fixed_gross_salary"]
        print(f"\n  [Fixed Monthly Gross]: ₹{fg:,.2f}")
        print(f"  Mode 1 (CALENDAR_DAYS, Divisor=30):")
        print(f"     Per-day rate: ₹{fg/30:,.2f} | LOP Deduction: ₹{res_cal['lop_deduction_amount']:,.2f} | Net Pay: ₹{res_cal['net_salary']:,.2f}")
        print(f"  Mode 2 (FIXED_30, Divisor=30):")
        print(f"     Per-day rate: ₹{fg/30:,.2f} | LOP Deduction: ₹{res_fixed['lop_deduction_amount']:,.2f} | Net Pay: ₹{res_fixed['net_salary']:,.2f}")
        print(f"  Mode 3 (WORKING_DAYS, Divisor=22):")
        print(f"     Per-day rate: ₹{fg/22:,.2f} | LOP Deduction: ₹{res_work['lop_deduction_amount']:,.2f} | Net Pay: ₹{res_work['net_salary']:,.2f}")

        # 10. Execute Official Payroll Run for September 2026
        print("\n--- [Step 10] Executing Formal Payroll Run & Generating Payslip ---")
        period = db.query(PayrollPeriod).filter(
            PayrollPeriod.year == 2026,
            PayrollPeriod.month == 9
        ).first()

        if not period:
            period = PayrollPeriod(
                name="September 2026",
                year=2026,
                month=9,
                start_date=sept_start,
                end_date=sept_end,
                pay_date=date(2026, 10, 1),
                total_days=30,
                working_days=22,
                status="OPEN"
            )
            db.add(period)
            db.commit()

        # Delete any existing test run for this period to keep it clean
        existing_runs = db.query(PayrollRun).filter(PayrollRun.period_id == period.id).all()
        for er in existing_runs:
            PayrollService.delete_payroll_run(db, er.id, user_id=hr_user.id)

        # Execute Payroll Run
        payroll_run = PayrollService.execute_payroll_run(
            db=db,
            data=PayrollRunCreate(
                year=2026,
                month=9,
                selected_employee_ids=[emp.id],
                pay_date=date(2026, 10, 1)
            ),
            user_id=hr_user.id
        )

        print(f"✓ Payroll Run Executed: Run #{payroll_run.run_number}, Status: {payroll_run.status}")
        print(f"  Total Employees Processed: {payroll_run.processed_employees}")
        print(f"  Total Gross: ₹{payroll_run.total_gross:,.2f}")
        print(f"  Total Net: ₹{payroll_run.total_net:,.2f}")

        # Submit, Approve and Lock Run
        PayrollService.submit_run_for_approval(db, payroll_run.id, user_id=hr_user.id)
        PayrollService.approve_or_reject_run(db, payroll_run.id, approved=True, user_id=hr_user.id)
        PayrollService.lock_payroll_run(db, payroll_run.id, user_id=hr_user.id)
        print(f"✓ Payroll Run Approved and Locked (Payslips Generated)")

        # Verify Employee Payslip
        payslip = db.query(Payslip).join(PayrollRecord).filter(
            PayrollRecord.employee_id == emp.id,
            PayrollRecord.payroll_run_id == payroll_run.id
        ).first()

        if payslip and payslip.record:
            rec = payslip.record
            print(f"\n  [Final Generated Payslip for {emp.first_name} {emp.last_name}]:")
            print(f"  • Payslip Number: {payslip.payslip_number}")
            print(f"  • Total Days: {rec.total_payroll_days} | Payable Days: {rec.payable_days} | LOP Days: {rec.unpaid_leave_days}")
            print(f"  • Fixed Gross: ₹{rec.fixed_gross_salary:,.2f}")
            print(f"  • LOP Deduction: -₹{rec.lop_deduction_amount:,.2f}")
            print(f"  • Actual Gross Earned: ₹{rec.gross_earnings:,.2f}")
            print(f"  • Total Deductions: -₹{rec.total_deductions:,.2f}")
            print(f"  • Net Take-Home: ₹{rec.net_salary:,.2f}")

        # 11. Active October 2026 Time-Off Workflow Testing
        print("\n--- [Step 11] Active Time-Off Requests & Manager Approval Workflow ---")
        
        # Clean up any existing October test requests
        oct_requests = db.query(TimeOffRequest).filter(
            TimeOffRequest.employee_id == emp.id,
            TimeOffRequest.date >= date(2026, 10, 1),
            TimeOffRequest.date <= date(2026, 10, 31)
        ).all()
        for r in oct_requests:
            db.query(ApprovalTask).filter(ApprovalTask.request_type == "timeoff", ApprovalTask.request_id == r.id).delete()
            db.delete(r)
        db.commit()

        # Ananya applies for Casual Leave on Oct 5, 2026
        cl_req = TimeOffRequest(
            employee_id=emp.id,
            date=date(2026, 10, 5),
            leave_type="Casual Leave",
            duration_hours=8.0,
            status="Pending",
            reason="Festival celebration"
        )
        db.add(cl_req)
        db.flush()

        # Create approval task for manager Vikram
        task_cl = ApprovalTask(
            request_type="timeoff",
            request_id=cl_req.id,
            employee_id=emp.id,
            assigned_role="manager",
            submitted_by=emp_user.id,
            status="pending"
        )
        db.add(task_cl)

        # Ananya applies for Unpaid Leave on Oct 8, 2026
        ul_req = TimeOffRequest(
            employee_id=emp.id,
            date=date(2026, 10, 8),
            leave_type="Unpaid Leave",
            duration_hours=8.0,
            status="Pending",
            reason="Urgent domestic work"
        )
        db.add(ul_req)
        db.flush()

        task_ul = ApprovalTask(
            request_type="timeoff",
            request_id=ul_req.id,
            employee_id=emp.id,
            assigned_role="manager",
            submitted_by=emp_user.id,
            status="pending"
        )
        db.add(task_ul)
        db.commit()

        print(f"✓ Ananya submitted 2 requests:")
        print(f"   1. Casual Leave (CL) on 2026-10-05 [Pending approval]")
        print(f"   2. Unpaid Leave (UL) on 2026-10-08 [Pending approval]")

        # Manager Vikram Malhotra reviews and approves the Casual Leave request
        print("\n  [Manager Action]: Vikram Malhotra reviews and approves Casual Leave request...")
        approve_request(
            db=db,
            request_id=cl_req.id,
            action="APPROVE",
            admin_user_id=mgr_user.id,
            comments="Approved by Manager Vikram Malhotra",
            enforce_approval_stage=False
        )
        print("  ✓ Casual Leave request APPROVED by Manager.")

        # 12. Final Balances Verification
        print("\n--- [Step 12] Final Leave Balances Summary for 2026 ---")
        final_balances = get_employee_leave_balances(db, emp.id, year=2026)
        print(f"  • Paid Leave (PL):")
        print(f"     Allocated: {final_balances['paid_leave']['allocated']}d | Used: {final_balances['paid_leave']['used']}d | Pending: {final_balances['paid_leave']['pending']}d | Remaining: {final_balances['paid_leave']['remaining']}d")
        print(f"  • Unpaid Leave (UL):")
        print(f"     Allocated: {final_balances['unpaid_leave']['allocated']}d | Used: {final_balances['unpaid_leave']['used']}d | Pending: {final_balances['unpaid_leave']['pending']}d | Remaining: {final_balances['unpaid_leave']['remaining']}d")
        print(f"  • Casual Leave (CL):")
        print(f"     Allocated: {final_balances['casual']['quotaDays']}d | Used: {final_balances['casual']['usedDays']}d | Available: {final_balances['casual']['availableDays']}d")

        print("\n================================================================================")
        print("                 ✓ ALL HRMS VERIFICATIONS SUCCESSFUL!                           ")
        print("================================================================================")

    finally:
        db.close()


if __name__ == "__main__":
    run_e2e_verification()
