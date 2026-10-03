import calendar
import math
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.employee import Employee
from app.models.master_data import Shift, Holiday
from app.models.attendance import Attendance
from app.models.timeoff import TimeOffRequest
from app.models.payroll import (
    SalaryComponent,
    SalaryStructure,
    SalaryStructureComponent,
    EmployeeSalaryAssignment,
    StatutoryConfiguration,
    PayrollInput,
)
from app.schemas.payroll import (
    SalaryCalculationPreview,
    CalculatedComponentItem,
)


class PayrollCalculationService:
    """Core mathematical and rule-based payroll engine."""

    @staticmethod
    def calculate_salary_breakdown(
        db: Session,
        structure: SalaryStructure,
        ctc_amount: float,
        salary_type: str = "Annual",
        salary_basis: str = "CTC",
        custom_overrides: Optional[Dict[str, float]] = None,
    ) -> SalaryCalculationPreview:
        """
        Calculates monthly and annual earnings, deductions, and employer contributions
        based on SalaryStructure components and salary basis mode (CTC or GROSS).
        """
        if custom_overrides is None:
            custom_overrides = {}

        # 1. Normalize annual vs monthly input
        if salary_type.lower() == "annual":
            annual_input = float(ctc_amount)
            monthly_input = annual_input / 12.0
        else:
            monthly_input = float(ctc_amount)
            annual_input = monthly_input * 12.0

        monthly_input = round(monthly_input, 2)
        annual_input = round(annual_input, 2)

        # 2. Fetch statutory configurations
        statutory_rules = {
            s.code: s for s in db.query(StatutoryConfiguration).filter(StatutoryConfiguration.is_enabled == True).all()
        }

        # 3. Fetch components assigned to structure
        struct_components = (
            db.query(SalaryStructureComponent, SalaryComponent)
            .join(SalaryComponent, SalaryStructureComponent.component_id == SalaryComponent.id)
            .filter(SalaryStructureComponent.structure_id == structure.id)
            .order_by(SalaryStructureComponent.sequence_order)
            .all()
        )

        earnings_list: List[CalculatedComponentItem] = []
        deductions_list: List[CalculatedComponentItem] = []
        employer_contributions_list: List[CalculatedComponentItem] = []

        # Maps for intermediate formula resolution
        calculated_monthly: Dict[str, float] = {}
        balance_item: Optional[Tuple[SalaryStructureComponent, SalaryComponent]] = None

        # Mode calculation basis
        is_ctc_mode = (salary_basis.upper() == "CTC")

        # PASS 1: Calculate fixed & percentage-based earnings and employer contributions (except balance)
        for sc_link, comp in struct_components:
            code = comp.code.upper()
            pct_val = custom_overrides.get(code, sc_link.percentage_or_value)
            calc_type = sc_link.calculation_type.upper()
            calc_basis = (sc_link.calculation_basis or "CTC").upper()

            if calc_type in ["BALANCE", "FORMULA"] or (code in ["SPECIAL_ALLOWANCE", "SPECIAL_ALLOWANCES"] and calc_type not in ["FIXED", "PERCENTAGE"]):
                balance_item = (sc_link, comp)
                continue

            monthly_val = 0.0
            if calc_type == "FIXED":
                monthly_val = float(pct_val)
            elif calc_type == "PERCENTAGE":
                if calc_basis in ["CTC", "ANNUAL_CTC"]:
                    base_amount = monthly_input
                elif calc_basis in ["BASIC", "BASIC_SALARY"]:
                    base_amount = calculated_monthly.get("BASIC", 0.0)
                elif calc_basis in ["GROSS", "GROSS_SALARY"]:
                    # In Gross mode or preliminary gross (CTC input is equivalent to target gross prior to statutory employer deductions)
                    base_amount = monthly_input
                else:
                    base_amount = monthly_input

                monthly_val = round((base_amount * (pct_val / 100.0)), 2)

            calculated_monthly[code] = monthly_val

        # PASS 2: Employer statutory contributions estimation & CTC Resolution
        # In CTC mode: Gross = Monthly CTC - Employer PF - Employer ESI
        # Special Allowance = Gross - Basic - HRA - other fixed earnings
        basic_monthly = calculated_monthly.get("BASIC", 0.0)

        other_earnings_sum = 0.0
        for sc_link, comp in struct_components:
            code = comp.code.upper()
            if comp.component_type.upper() == "EARNING" and (balance_item is None or comp.id != balance_item[1].id):
                other_earnings_sum += calculated_monthly.get(code, 0.0)
        other_earnings_sum = round(other_earnings_sum, 2)

        # 1. Employer PF
        has_pf_employer = any(comp.code.upper() in ["PF_EMPLOYER", "EMPLOYER_PF"] for _, comp in struct_components)
        pf_emplr_amt = 0.0
        pf_emp_amt = 0.0
        if has_pf_employer or any(comp.code.upper() in ["PF_EMP", "EMPLOYEE_PF", "PF"] for _, comp in struct_components):
            pf_override = custom_overrides.get("PF_EMPLOYER", custom_overrides.get("EMPLOYER_PF"))
            pf_rule = statutory_rules.get("PF")
            if pf_override is not None:
                pf_emplr_amt = round(float(pf_override), 2)
                pf_emp_amt = round(float(custom_overrides.get("PF_EMP", custom_overrides.get("EMPLOYEE_PF", pf_override))), 2)
            elif pf_rule and pf_rule.is_enabled:
                wage_ceiling = pf_rule.wage_ceiling or 15000.0
                pf_wage = min(basic_monthly, wage_ceiling) if wage_ceiling else basic_monthly
                pf_emplr_amt = round(pf_wage * (pf_rule.employer_rate_pct / 100.0), 2)
                pf_emp_amt = round(pf_wage * (pf_rule.employee_rate_pct / 100.0), 2)
            else:
                pf_emplr_amt = round(basic_monthly * 0.12, 2)
                pf_emp_amt = round(basic_monthly * 0.12, 2)

            if not has_pf_employer:
                pf_emplr_amt = 0.0

        # 2. Employer ESI
        has_esi_employer = any(comp.code.upper() in ["ESI_EMPLOYER", "EMPLOYER_ESI"] for _, comp in struct_components)
        esi_emplr_amt = 0.0
        esi_rule = statutory_rules.get("ESI")
        esi_override = custom_overrides.get("ESI_EMPLOYER", custom_overrides.get("EMPLOYER_ESI"))

        if is_ctc_mode:
            # In CTC mode: Gross = Monthly CTC - Employer PF - Employer ESI
            # Special Allowance = Gross - Basic - HRA - Other Fixed Earnings
            #                   = Monthly CTC - Basic - HRA - Other Fixed Earnings - Employer PF - Employer ESI
            # Circular dependency resolution:
            # Let W = Monthly CTC - Employer PF.
            # Since Gross + Employer ESI = W, and Employer ESI = Gross * esi_employer_rate:
            # Gross * (1 + esi_employer_rate) = W => Gross = W / (1 + esi_employer_rate)
            W = round(monthly_input - pf_emplr_amt, 2)
            if has_esi_employer:
                if esi_override is not None:
                    esi_emplr_amt = round(float(esi_override), 2)
                elif esi_rule and esi_rule.is_enabled:
                    esi_rate = esi_rule.employer_rate_pct / 100.0
                    ceiling = esi_rule.wage_ceiling or 21000.0
                    if W <= (ceiling * (1.0 + esi_rate)):
                        preliminary_gross = round(W / (1.0 + esi_rate), 2)
                        esi_emplr_amt = round(W - preliminary_gross, 2)
                    else:
                        esi_emplr_amt = 0.0
                else:
                    esi_emplr_amt = 0.0
            else:
                esi_emplr_amt = 0.0

            total_employer_temp = round(pf_emplr_amt + esi_emplr_amt, 2)
            # Gross Salary = Monthly CTC - Employer PF - Employer ESI
            target_gross = round(monthly_input - total_employer_temp, 2)

            # Special Allowance = Gross Salary - Basic - HRA - Other Fixed Earnings
            if balance_item:
                b_sc_link, b_comp = balance_item
                b_code = b_comp.code.upper()
                balance_amount = max(0.0, round(target_gross - other_earnings_sum, 2))
                calculated_monthly[b_code] = balance_amount
        else:
            # Gross mode: Gross Salary = monthly_input
            target_gross = monthly_input
            if balance_item:
                b_sc_link, b_comp = balance_item
                b_code = b_comp.code.upper()
                balance_amount = max(0.0, round(target_gross - other_earnings_sum, 2))
                calculated_monthly[b_code] = balance_amount

            # ESI in Gross mode
            if has_esi_employer:
                if esi_override is not None:
                    esi_emplr_amt = round(float(esi_override), 2)
                elif esi_rule and esi_rule.is_enabled:
                    ceiling = esi_rule.wage_ceiling or 21000.0
                    if target_gross <= ceiling:
                        esi_emplr_amt = round(target_gross * (esi_rule.employer_rate_pct / 100.0), 2)
                    else:
                        esi_emplr_amt = 0.0
                else:
                    esi_emplr_amt = 0.0

        # PASS 3: Construct Full Earnings List & Finalize Gross
        gross_monthly = 0.0
        for sc_link, comp in struct_components:
            code = comp.code.upper()
            if comp.component_type.upper() == "EARNING":
                amt = calculated_monthly.get(code, 0.0)
                gross_monthly += amt
                earnings_list.append(
                    CalculatedComponentItem(
                        component_id=comp.id,
                        code=code,
                        name=comp.name,
                        component_type="EARNING",
                        calculation_type=sc_link.calculation_type,
                        percentage_or_value=custom_overrides.get(code, sc_link.percentage_or_value),
                        monthly_amount=amt,
                        annual_amount=round(amt * 12.0, 2),
                        is_statutory=comp.is_statutory,
                    )
                )

        gross_monthly = round(gross_monthly, 2)

        # PASS 4: Deductions (Employee PF, ESI, PT, TDS)
        total_deductions_monthly = 0.0

        # ESI calculation check (Gross threshold e.g. <= 21,000)
        esi_eligible = False
        esi_emp_amt = 0.0
        if esi_rule and esi_rule.is_enabled:
            ceiling = esi_rule.wage_ceiling or 21000.0
            if gross_monthly <= ceiling:
                esi_eligible = True
                esi_emp_override = custom_overrides.get("ESI_EMP", custom_overrides.get("EMPLOYEE_ESI"))
                if esi_emp_override is not None:
                    esi_emp_amt = round(float(esi_emp_override), 2)
                else:
                    esi_emp_amt = round(gross_monthly * (esi_rule.employee_rate_pct / 100.0), 2)

        for sc_link, comp in struct_components:
            code = comp.code.upper()
            if comp.component_type.upper() == "DEDUCTION":
                if code in ["PF_EMP", "EMPLOYEE_PF", "PF"]:
                    amt = pf_emp_amt
                elif code in ["ESI_EMP", "EMPLOYEE_ESI", "ESI"]:
                    amt = esi_emp_amt if esi_eligible else 0.0
                elif code in ["PT", "PROFESSIONAL_TAX"]:
                    pt_rule = statutory_rules.get("PT")
                    # If PT is not enabled in Statutory Configuration, PT is not applicable in this company
                    if not pt_rule or not pt_rule.is_enabled:
                        amt = 0.0
                    else:
                        calc_type = sc_link.calculation_type.upper()
                        val = float(custom_overrides.get(code, sc_link.percentage_or_value) or 0.0)
                        c_basis = (sc_link.calculation_basis or "GROSS").upper()
                        
                        # Determine base amount dynamically based on structure definition
                        base_amt = gross_monthly if "GROSS" in c_basis else (basic_monthly if "BASIC" in c_basis else monthly_input)
                        
                        min_threshold = (pt_rule.min_wage_threshold or 0.0)
                        if base_amt < min_threshold or base_amt <= 0.0:
                            amt = 0.0
                        elif calc_type == "PERCENTAGE":
                            amt = round(base_amt * (val / 100.0), 2)
                        else:
                            amt = val
                else:
                    amt = calculated_monthly.get(code, 0.0)

                amt = round(amt, 2)
                # If PT is disabled / not applicable for the company or zero, exclude from deductions list
                if code in ["PT", "PROFESSIONAL_TAX"] and (not pt_rule or not pt_rule.is_enabled or amt <= 0.0):
                    continue
                total_deductions_monthly += amt
                deductions_list.append(
                    CalculatedComponentItem(
                        component_id=comp.id,
                        code=code,
                        name=comp.name,
                        component_type="DEDUCTION",
                        calculation_type=sc_link.calculation_type,
                        percentage_or_value=custom_overrides.get(code, sc_link.percentage_or_value),
                        monthly_amount=amt,
                        annual_amount=round(amt * 12.0, 2),
                        is_statutory=comp.is_statutory,
                    )
                )

        total_deductions_monthly = round(total_deductions_monthly, 2)

        # PASS 5: Employer Contributions
        total_employer_contributions_monthly = 0.0
        for sc_link, comp in struct_components:
            code = comp.code.upper()
            if comp.component_type.upper() in ["STATUTORY_EMPLOYER", "EMPLOYER_CONTRIBUTION"]:
                if code in ["PF_EMPLOYER", "EMPLOYER_PF"]:
                    amt = pf_emplr_amt
                elif code in ["ESI_EMPLOYER", "EMPLOYER_ESI"]:
                    amt = esi_emplr_amt
                else:
                    amt = calculated_monthly.get(code, 0.0)

                amt = round(amt, 2)
                total_employer_contributions_monthly += amt
                employer_contributions_list.append(
                    CalculatedComponentItem(
                        component_id=comp.id,
                        code=code,
                        name=comp.name,
                        component_type="STATUTORY_EMPLOYER",
                        calculation_type=sc_link.calculation_type,
                        percentage_or_value=custom_overrides.get(code, sc_link.percentage_or_value),
                        monthly_amount=amt,
                        annual_amount=round(amt * 12.0, 2),
                        is_statutory=comp.is_statutory,
                    )
                )

        total_employer_contributions_monthly = round(total_employer_contributions_monthly, 2)

        # PASS 6: Net Take-Home & CTC Reconciliation Validation
        net_monthly = max(0.0, round(gross_monthly - total_deductions_monthly, 2))

        # Total Employer Cost
        if is_ctc_mode:
            final_monthly_ctc = monthly_input
            final_annual_ctc = annual_input
        else:
            final_monthly_ctc = round(gross_monthly + total_employer_contributions_monthly, 2)
            final_annual_ctc = round(final_monthly_ctc * 12.0, 2)

        # Total CTC validation: Total CTC = Gross Salary + Employer PF + Employer ESI
        calculated_monthly_ctc = round(gross_monthly + total_employer_contributions_monthly, 2)
        diff = round(abs(calculated_monthly_ctc - final_monthly_ctc), 2)
        validation_warning = None
        if diff > 0.01:
            validation_warning = (
                f"Reconciliation Warning: Calculated Monthly CTC (₹{calculated_monthly_ctc:,.2f}) "
                f"does not match Monthly CTC (₹{final_monthly_ctc:,.2f}). "
                f"Gross: ₹{gross_monthly:,.2f}, Employer Contributions: ₹{total_employer_contributions_monthly:,.2f}."
            )

        return SalaryCalculationPreview(
            salary_basis=salary_basis.upper(),
            annual_ctc=final_annual_ctc,
            monthly_ctc=final_monthly_ctc,
            gross_monthly=gross_monthly,
            gross_annual=round(gross_monthly * 12.0, 2),
            total_deductions_monthly=total_deductions_monthly,
            total_deductions_annual=round(total_deductions_monthly * 12.0, 2),
            net_monthly=net_monthly,
            net_annual=round(net_monthly * 12.0, 2),
            employer_contributions_monthly=total_employer_contributions_monthly,
            employer_contributions_annual=round(total_employer_contributions_monthly * 12.0, 2),
            total_employer_cost_monthly=final_monthly_ctc,
            validation_warning=validation_warning,
            earnings=earnings_list,
            deductions=deductions_list,
            employer_contributions=employer_contributions_list,
        )

    @staticmethod
    def get_attendance_and_leave_metrics(
        db: Session,
        employee_id: int,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        """
        Integrates with Attendance and TimeOffRequest tables to extract finalized
        attendance, leave, overtime, and unpaid days (LOP).
        """
        total_days = (end_date - start_date).days + 1

        # 1. Fetch employee and shift
        emp = db.query(Employee).filter(Employee.id == employee_id).first()
        shift = emp.shift if emp else None
        daily_shift_hours = float(shift.working_hours) if shift and shift.working_hours else 8.0

        # 2. Fetch approved time-off requests first to prevent double deductions
        timeoff_records = (
            db.query(TimeOffRequest)
            .filter(
                TimeOffRequest.employee_id == employee_id,
                TimeOffRequest.date >= start_date,
                TimeOffRequest.date <= end_date,
                TimeOffRequest.status.in_(["Approved", "Active", "Completed"]),
            )
            .all()
        )

        timeoff_dates = {to.date for to in timeoff_records}
        paid_leave_days = 0.0
        unpaid_leave_days = 0.0

        from app.services.leave_balance_service import LeaveBalanceService
        for to in timeoff_records:
            lt = (to.leave_type or "").strip().lower()
            lt_obj = LeaveBalanceService.resolve_leave_type(db, to.leave_type)
            if lt_obj and lt_obj.counts_as_leave is False:
                continue

            duration = to.duration_hours or 0.0
            # If duration is full-day (>= daily_shift_hours) count 1.0, half-day count 0.5
            day_fraction = 1.0 if duration >= (daily_shift_hours * 0.8) else (0.5 if duration >= 2.0 else duration / daily_shift_hours)
            if day_fraction <= 0:
                day_fraction = 1.0

            # Determine whether leave is paid or unpaid:
            # 1. lt_obj.is_paid attribute
            # 2. explicit unpaid/ul/lop names
            is_unpaid = False
            if lt_obj and getattr(lt_obj, "is_paid", None) is not None:
                is_unpaid = not lt_obj.is_paid
            elif "unpaid" in lt or "loss of pay" in lt or "lop" in lt or lt == "ul":
                is_unpaid = True

            if is_unpaid:
                unpaid_leave_days += day_fraction
            else:
                paid_leave_days += day_fraction

        # 3. Fetch attendance records in period
        attendance_records = (
            db.query(Attendance)
            .filter(
                Attendance.employee_id == employee_id,
                Attendance.date >= start_date,
                Attendance.date <= end_date,
            )
            .all()
        )

        present_days = 0.0
        half_days = 0.0
        absent_days = 0.0
        approved_ot_minutes = 0

        attendance_dates = set()
        for att in attendance_records:
            attendance_dates.add(att.date)
            # CRITICAL: Prevent double deduction!
            # If an approved time-off request exists on this date, skip attendance absence deduction.
            if att.date in timeoff_dates:
                continue

            st = (att.status or "").strip().upper()
            if st in ["PRESENT", "WORKING", "PUNCHED_OUT"]:
                present_days += 1.0
            elif st in ["HALF_DAY", "HALF-DAY"]:
                half_days += 1.0
            elif st in ["ABSENT"]:
                absent_days += 1.0

            # Only approved overtime flows into payroll
            if att.overtime_approved and att.overtime_minutes and att.overtime_minutes > 0:
                approved_ot_minutes += att.overtime_minutes

        # 4. Fetch holidays in period
        holidays_count = float(
            db.query(Holiday)
            .filter(
                Holiday.holiday_date >= start_date,
                Holiday.holiday_date <= end_date,
                Holiday.is_active == True,
            )
            .count()
        )

        # 5. Weekly offs count (Sundays in period)
        curr = start_date
        weekly_offs = 0.0
        while curr <= end_date:
            if curr.weekday() == 6:  # Sunday
                weekly_offs += 1.0
            curr += timedelta(days=1)

        # 6. Unpaid Days (LOP) Calculation
        # LOP Days = Approved Unpaid Leaves + Unexcused Absences (+ half-day fractions)
        unexcused_absent_days = round(absent_days + (half_days * 0.5), 2)
        unpaid_days_total = round(unpaid_leave_days + unexcused_absent_days, 2)
        
        # Payable Days = total_days - unpaid_days_total
        payable_days = max(0.0, round(total_days - unpaid_days_total, 2))

        return {
            "total_days": total_days,
            "present_days": present_days,
            "half_days": half_days,
            "absent_days": absent_days,
            "unexcused_absent_days": unexcused_absent_days,
            "paid_leave_days": paid_leave_days,
            "approved_unpaid_leave_days": unpaid_leave_days,
            "unpaid_leave_days": unpaid_days_total,
            "lop_days": unpaid_days_total,
            "holidays_count": holidays_count,
            "weekly_offs_count": weekly_offs,
            "payable_days": payable_days,
            "approved_ot_minutes": approved_ot_minutes,
            "approved_ot_hours": round(approved_ot_minutes / 60.0, 2),
            "daily_shift_hours": daily_shift_hours,
        }

    @staticmethod
    def calculate_employee_payroll(
        db: Session,
        employee_id: int,
        start_date: date,
        end_date: date,
        period_working_days: int = 26,
        lop_divisor_mode: str = "CALENDAR_DAYS",  # CALENDAR_DAYS, FIXED_30, WORKING_DAYS
    ) -> Dict[str, Any]:
        """
        Executes end-to-end payroll calculation for a single employee for the given date range.
        Produces full line items, frozen calculation snapshot, and financial totals.
        """
        # 1. Fetch active salary assignment effective for this period
        assignment = (
            db.query(EmployeeSalaryAssignment)
            .filter(
                EmployeeSalaryAssignment.employee_id == employee_id,
                EmployeeSalaryAssignment.is_active == True,
                EmployeeSalaryAssignment.effective_from <= end_date,
                or_(
                    EmployeeSalaryAssignment.effective_to == None,
                    EmployeeSalaryAssignment.effective_to >= start_date,
                ),
            )
            .order_by(EmployeeSalaryAssignment.effective_from.desc())
            .first()
        )

        exceptions = []

        if not assignment:
            return {
                "success": False,
                "error": f"No active salary assignment found for employee ID {employee_id}.",
                "error_code": "MISSING_SALARY_ASSIGNMENT",
            }

        structure = assignment.structure
        if not structure:
            return {
                "success": False,
                "error": f"Salary structure missing for assignment ID {assignment.id}.",
                "error_code": "MISSING_STRUCTURE",
            }

        # 2. Compute base salary breakdown
        base_preview = PayrollCalculationService.calculate_salary_breakdown(
            db=db,
            structure=structure,
            ctc_amount=assignment.annual_ctc,
            salary_type="Annual",
            salary_basis=assignment.salary_basis,
        )

        # 3. Pull attendance, leave, and approved overtime
        att_metrics = PayrollCalculationService.get_attendance_and_leave_metrics(
            db=db,
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date,
        )

        total_days = att_metrics["total_days"]
        unpaid_days = att_metrics["unpaid_leave_days"]
        payable_days = att_metrics["payable_days"]
        fixed_gross = base_preview.gross_monthly

        # 4. LOP Calculation (Loss of Pay)
        divisor = float(total_days)
        if lop_divisor_mode == "FIXED_30":
            divisor = 30.0
        elif lop_divisor_mode == "WORKING_DAYS":
            divisor = float(period_working_days) if period_working_days > 0 else 26.0

        lop_amount = 0.0
        if unpaid_days > 0 and divisor > 0:
            lop_amount = round((fixed_gross / divisor) * unpaid_days, 2)
            lop_amount = min(lop_amount, fixed_gross)  # Cannot deduct more than fixed gross

        # 5. Overtime Calculation (using approved overtime only)
        ot_hours = att_metrics["approved_ot_hours"]
        daily_shift_hours = att_metrics["daily_shift_hours"]
        # Hourly rate based on working days * shift hours
        hourly_rate = round(fixed_gross / (period_working_days * daily_shift_hours), 2) if (period_working_days > 0 and daily_shift_hours > 0) else 150.0
        ot_rate = round(hourly_rate * 1.5, 2)  # Standard 1.5x rate multiplier
        ot_amount = round(ot_hours * ot_rate, 2)

        # 6. Fetch approved monthly payroll inputs (Bonuses, incentives, ad-hoc deductions)
        inputs = (
            db.query(PayrollInput)
            .filter(
                PayrollInput.employee_id == employee_id,
                PayrollInput.status == "APPROVED",
            )
            .all()
        )

        bonus_amount = 0.0
        incentive_amount = 0.0
        other_earnings = 0.0
        other_deductions = 0.0

        for inp in inputs:
            itype = (inp.input_type or "").upper()
            amt = inp.amount or 0.0
            if itype == "BONUS":
                bonus_amount += amt
            elif itype == "INCENTIVE":
                incentive_amount += amt
            elif itype == "OVERTIME_OVERRIDE":
                ot_amount = amt  # Override if explicitly specified
            elif itype in ["OTHER_DEDUCTION", "LOAN_ADVANCE"]:
                other_deductions += amt
            else:
                other_earnings += amt

        # 7. Calculate Actual Gross Earnings for Month
        # Gross Earnings = Fixed Gross - LOP + OT + Bonus + Incentive + Other Earnings
        actual_gross = max(0.0, round(fixed_gross - lop_amount + ot_amount + bonus_amount + incentive_amount + other_earnings, 2))

        # 8. Prorate / Recalculate Deductions on actual earned gross
        # Scale Basic proportionally if LOP applies
        lop_ratio = max(0.0, (fixed_gross - lop_amount) / fixed_gross) if fixed_gross > 0 else 1.0
        actual_basic = round((base_preview.earnings[0].monthly_amount if base_preview.earnings else fixed_gross * 0.5) * lop_ratio, 2)

        statutory_rules = {
            s.code: s for s in db.query(StatutoryConfiguration).filter(StatutoryConfiguration.is_enabled == True).all()
        }

        # PF
        pf_rule = statutory_rules.get("PF")
        if pf_rule and pf_rule.is_enabled:
            pf_wage = min(actual_basic, pf_rule.wage_ceiling) if pf_rule.wage_ceiling else actual_basic
            emp_pf = round(pf_wage * (pf_rule.employee_rate_pct / 100.0), 2)
            employer_pf = round(pf_wage * (pf_rule.employer_rate_pct / 100.0), 2)
        else:
            emp_pf = round(actual_basic * 0.12, 2)
            employer_pf = round(actual_basic * 0.12, 2)

        # ESI
        esi_rule = statutory_rules.get("ESI")
        emp_esi = 0.0
        employer_esi = 0.0
        if esi_rule and esi_rule.is_enabled:
            if not esi_rule.wage_ceiling or actual_gross <= esi_rule.wage_ceiling:
                emp_esi = round(actual_gross * (esi_rule.employee_rate_pct / 100.0), 2)
                employer_esi = round(actual_gross * (esi_rule.employer_rate_pct / 100.0), 2)

        # Professional Tax: Dynamically evaluated from Salary Structure against actual earned salary
        pt_rule = statutory_rules.get("PT")
        pt = 0.0
        pt_detail = "Not Applicable (Company Exempt)"
        if pt_rule and pt_rule.is_enabled and actual_gross > 0:
            pt_item = next((d for d in base_preview.deductions if d.code in ["PT", "PROFESSIONAL_TAX"]), None)
            if pt_item:
                calc_type = (pt_item.calculation_type or "FIXED").upper()
                val = float(pt_item.percentage_or_value or 0.0)
                sc_match = next((sc for sc in structure.components if sc.component and sc.component.code.upper() in ["PT", "PROFESSIONAL_TAX"]), None)
                c_basis = (sc_match.calculation_basis or "GROSS").upper() if sc_match else "GROSS"
                eval_base = actual_basic if "BASIC" in c_basis else actual_gross

                min_threshold = (pt_rule.min_wage_threshold or 0.0)

                if eval_base >= min_threshold and eval_base > 0:
                    if calc_type == "PERCENTAGE":
                        pt = round(eval_base * (val / 100.0), 2)
                        pt_detail = f"{val}% on {c_basis.capitalize()} (₹{eval_base:,.2f})"
                    else:
                        pt = round(val, 2)
                        pt_detail = f"₹{pt:,.2f} as defined in Salary Structure"
                else:
                    pt = 0.0
                    pt_detail = f"Exempt (Base ₹{eval_base:,.2f} < Min Threshold ₹{min_threshold:,.2f})"

        total_deductions = round(emp_pf + emp_esi + pt + other_deductions, 2)
        net_salary = max(0.0, round(actual_gross - total_deductions, 2))
        total_employer_contributions = round(employer_pf + employer_esi, 2)
        total_cost_to_company = round(actual_gross + total_employer_contributions, 2)

        # 9. Build Detailed Breakdown Line Items
        line_items = []
        for earn in base_preview.earnings:
            # Scale prorated components
            prorated_amt = round(earn.monthly_amount * lop_ratio, 2)
            line_items.append({
                "component_code": earn.code,
                "component_name": earn.name,
                "component_type": "EARNING",
                "amount": prorated_amt,
                "calculation_detail": f"{earn.percentage_or_value}% (Prorated for {payable_days}/{total_days} days)",
            })

        if ot_amount > 0:
            line_items.append({
                "component_code": "OVERTIME",
                "component_name": "Overtime Pay",
                "component_type": "EARNING",
                "amount": ot_amount,
                "calculation_detail": f"{ot_hours} hrs @ ₹{ot_rate}/hr",
            })

        if bonus_amount > 0:
            line_items.append({
                "component_code": "BONUS",
                "component_name": "Bonus",
                "component_type": "EARNING",
                "amount": bonus_amount,
                "calculation_detail": "Approved Monthly Bonus",
            })

        if incentive_amount > 0:
            line_items.append({
                "component_code": "INCENTIVE",
                "component_name": "Performance Incentive",
                "component_type": "EARNING",
                "amount": incentive_amount,
                "calculation_detail": "Approved Variable Incentive",
            })

        if lop_amount > 0:
            line_items.append({
                "component_code": "LOP",
                "component_name": "Loss of Pay (LOP)",
                "component_type": "DEDUCTION",
                "amount": lop_amount,
                "calculation_detail": f"{unpaid_days} unpaid days deducted",
            })

        if emp_pf > 0:
            line_items.append({
                "component_code": "PF_EMP",
                "component_name": "Employee PF (12%)",
                "component_type": "DEDUCTION",
                "amount": emp_pf,
                "calculation_detail": f"12% on Basic ₹{actual_basic}",
            })

        if emp_esi > 0:
            line_items.append({
                "component_code": "ESI_EMP",
                "component_name": "Employee ESI (0.75%)",
                "component_type": "DEDUCTION",
                "amount": emp_esi,
                "calculation_detail": f"0.75% on Gross ₹{actual_gross}",
            })

        if pt > 0:
            line_items.append({
                "component_code": "PT",
                "component_name": "Professional Tax",
                "component_type": "DEDUCTION",
                "amount": pt,
                "calculation_detail": pt_detail,
            })

        if other_deductions > 0:
            line_items.append({
                "component_code": "OTHER_DED",
                "component_name": "Other Deductions / Advances",
                "component_type": "DEDUCTION",
                "amount": other_deductions,
                "calculation_detail": "Monthly Advance / Adjustments",
            })

        if employer_pf > 0:
            line_items.append({
                "component_code": "PF_EMPLOYER",
                "component_name": "Employer PF Contribution (12%)",
                "component_type": "EMPLOYER_CONTRIBUTION",
                "amount": employer_pf,
                "calculation_detail": f"12% on Basic ₹{actual_basic}",
            })

        if employer_esi > 0:
            line_items.append({
                "component_code": "ESI_EMPLOYER",
                "component_name": "Employer ESI Contribution (3.25%)",
                "component_type": "EMPLOYER_CONTRIBUTION",
                "amount": employer_esi,
                "calculation_detail": f"3.25% on Gross ₹{actual_gross}",
            })

        # 10. Compliance Checks / Automatic Exceptions
        if net_salary <= 0:
            exceptions.append({
                "severity": "CRITICAL",
                "error_code": "NEGATIVE_OR_ZERO_NET",
                "message": f"Net Salary evaluated to ₹{net_salary}, which is zero or negative.",
            })

        if ot_hours > 60:
            exceptions.append({
                "severity": "WARNING",
                "error_code": "HIGH_OVERTIME",
                "message": f"High overtime recorded: {ot_hours} hours. Please verify.",
            })

        if unpaid_days >= 15:
            exceptions.append({
                "severity": "WARNING",
                "error_code": "HIGH_LOP",
                "message": f"High LOP: {unpaid_days} unpaid days out of {total_days} days.",
            })

        # 11. Freeze snapshot JSON
        calculation_snapshot = {
            "calculation_timestamp": datetime.utcnow().isoformat(),
            "salary_basis": assignment.salary_basis,
            "structure_code": structure.code,
            "structure_name": structure.name,
            "fixed_annual_ctc": assignment.annual_ctc,
            "fixed_monthly_gross": fixed_gross,
            "total_days": total_days,
            "payable_days": payable_days,
            "unpaid_days": unpaid_days,
            "present_days": att_metrics["present_days"],
            "half_days": att_metrics["half_days"],
            "absent_days": att_metrics["absent_days"],
            "overtime_hours": ot_hours,
            "overtime_rate": ot_rate,
            "overtime_amount": ot_amount,
            "lop_amount": lop_amount,
            "bonus_amount": bonus_amount,
            "incentive_amount": incentive_amount,
            "gross_earnings": actual_gross,
            "total_deductions": total_deductions,
            "net_salary": net_salary,
            "employer_pf": employer_pf,
            "employer_esi": employer_esi,
            "total_cost_to_company": total_cost_to_company,
            "items": line_items,
        }

        return {
            "success": True,
            "salary_assignment_id": assignment.id,
            "salary_structure_id": structure.id,
            "total_payroll_days": total_days,
            "payable_days": payable_days,
            "present_days": att_metrics["present_days"],
            "absent_days": att_metrics["absent_days"],
            "half_days": att_metrics["half_days"],
            "paid_leave_days": att_metrics["paid_leave_days"],
            "unpaid_leave_days": unpaid_days,
            "holidays_count": att_metrics["holidays_count"],
            "weekly_offs_count": att_metrics["weekly_offs_count"],
            "overtime_hours": ot_hours,
            "overtime_rate": ot_rate,
            "overtime_amount": ot_amount,
            "bonus_amount": bonus_amount,
            "incentive_amount": incentive_amount,
            "other_earnings_amount": other_earnings,
            "lop_deduction_amount": lop_amount,
            "other_deductions_amount": other_deductions,
            "fixed_gross_salary": fixed_gross,
            "gross_earnings": actual_gross,
            "total_deductions": total_deductions,
            "net_salary": net_salary,
            "employer_pf": employer_pf,
            "employer_esi": employer_esi,
            "total_employer_contribution": total_employer_contributions,
            "total_cost_to_company": total_cost_to_company,
            "line_items": line_items,
            "calculation_snapshot": calculation_snapshot,
            "exceptions": exceptions,
        }
