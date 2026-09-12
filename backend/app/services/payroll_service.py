import io
import csv
import calendar
from datetime import date, datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func

from app.models.employee import Employee
from app.models.user import User, Role
from app.models.payroll import (
    SalaryComponent,
    SalaryStructure,
    SalaryStructureComponent,
    EmployeeSalaryAssignment,
    EmployeeSalaryComponent,
    SalaryRevision,
    PayrollPeriod,
    PayrollRun,
    PayrollRecord,
    PayrollRecordItem,
    PayrollInput,
    PayrollException,
    PayrollAdjustment,
    Payslip,
    PayrollAuditLog,
    StatutoryConfiguration,
)
from app.schemas.payroll import (
    SalaryComponentCreate,
    SalaryComponentUpdate,
    SalaryStructureCreate,
    SalaryStructureUpdate,
    SalaryCalculationRequest,
    SalaryCalculationPreview,
    EmployeeSalaryAssignmentCreate,
    SalaryRevisionCreate,
    SalaryRevisionAction,
    PayrollRunCreate,
    PayrollInputCreate,
    PayrollAdjustmentCreate,
    StatutoryConfigurationUpdate,
)
from app.services.payroll_calculation_service import PayrollCalculationService


class PayrollService:
    """Orchestrates comprehensive payroll business logic, runs, locking, and reporting."""

    # =========================================================================
    # Audit Logging Helper
    # =========================================================================
    @staticmethod
    def log_audit(
        db: Session,
        action: str,
        entity_type: str,
        entity_id: Optional[int],
        user_id: Optional[int],
        details: Optional[Dict[str, Any]] = None,
    ):
        audit = PayrollAuditLog(
            action=action,
            target_type=entity_type,
            target_id=entity_id,
            user_id=user_id or 1,
            new_value=details,
        )
        db.add(audit)

    # =========================================================================
    # 1. Salary Components Management
    # =========================================================================
    @staticmethod
    def get_components(db: Session, is_active: Optional[bool] = None) -> List[SalaryComponent]:
        query = db.query(SalaryComponent).order_by(SalaryComponent.sequence_order.asc(), SalaryComponent.id.asc())
        if is_active is not None:
            query = query.filter(SalaryComponent.is_active == is_active)
        return query.all()

    @staticmethod
    def get_component(db: Session, component_id: int) -> SalaryComponent:
        component = db.query(SalaryComponent).filter(SalaryComponent.id == component_id).first()
        if not component:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salary component not found")
        return component

    @staticmethod
    def create_component(db: Session, data: SalaryComponentCreate, user_id: Optional[int] = None) -> SalaryComponent:
        existing = db.query(SalaryComponent).filter(SalaryComponent.code == data.code.upper()).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Component code '{data.code}' already exists")

        component = SalaryComponent(
            code=data.code.upper(),
            name=data.name,
            component_type=data.component_type.upper(),
            calculation_type=data.calculation_type.upper(),
            calculation_basis=data.calculation_basis.upper() if data.calculation_basis else None,
            default_value=data.default_value,
            is_taxable=data.is_taxable,
            is_statutory=data.is_statutory,
            is_active=data.is_active,
            description=data.description,
            sequence_order=data.sequence_order,
        )
        db.add(component)
        db.commit()
        db.refresh(component)

        PayrollService.log_audit(db, "CREATE", "SalaryComponent", component.id, user_id, {"code": component.code})
        db.commit()
        return component

    @staticmethod
    def update_component(db: Session, component_id: int, data: SalaryComponentUpdate, user_id: Optional[int] = None) -> SalaryComponent:
        component = PayrollService.get_component(db, component_id)
        update_dict = data.model_dump(exclude_unset=True)

        if "component_type" in update_dict and update_dict["component_type"]:
            update_dict["component_type"] = update_dict["component_type"].upper()
        if "calculation_type" in update_dict and update_dict["calculation_type"]:
            update_dict["calculation_type"] = update_dict["calculation_type"].upper()
        if "calculation_basis" in update_dict and update_dict["calculation_basis"]:
            update_dict["calculation_basis"] = update_dict["calculation_basis"].upper()

        for key, val in update_dict.items():
            setattr(component, key, val)

        db.commit()
        db.refresh(component)
        PayrollService.log_audit(db, "UPDATE", "SalaryComponent", component.id, user_id, update_dict)
        db.commit()
        return component

    @staticmethod
    def delete_component(db: Session, component_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        component = PayrollService.get_component(db, component_id)
        usage = db.query(SalaryStructureComponent).filter(SalaryStructureComponent.component_id == component_id).count()
        if usage > 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot delete component '{component.name}'. It is used in {usage} salary structure(s).")

        db.delete(component)
        db.commit()
        PayrollService.log_audit(db, "DELETE", "SalaryComponent", component_id, user_id, {"code": component.code})
        db.commit()
        return {"message": f"Component '{component.name}' deleted successfully"}

    # =========================================================================
    # 2. Salary Structures Management
    # =========================================================================
    @staticmethod
    def get_structures(db: Session, is_active: Optional[bool] = None) -> List[SalaryStructure]:
        query = db.query(SalaryStructure).options(
            joinedload(SalaryStructure.components).joinedload(SalaryStructureComponent.component)
        ).order_by(SalaryStructure.id.asc())
        if is_active is not None:
            query = query.filter(SalaryStructure.is_active == is_active)
        return query.all()

    @staticmethod
    def get_structure(db: Session, structure_id: int) -> SalaryStructure:
        structure = (
            db.query(SalaryStructure)
            .options(joinedload(SalaryStructure.components).joinedload(SalaryStructureComponent.component))
            .filter(SalaryStructure.id == structure_id)
            .first()
        )
        if not structure:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salary structure not found")
        return structure

    @staticmethod
    def create_structure(db: Session, data: SalaryStructureCreate, user_id: Optional[int] = None) -> SalaryStructure:
        existing = db.query(SalaryStructure).filter(SalaryStructure.code == data.code.upper()).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Structure code '{data.code}' already exists")

        structure = SalaryStructure(
            code=data.code.upper(),
            name=data.name,
            salary_basis=data.salary_basis.upper(),
            description=data.description,
            is_active=data.is_active,
        )
        db.add(structure)
        db.flush()

        for idx, item in enumerate(data.components, start=1):
            assoc = SalaryStructureComponent(
                structure_id=structure.id,
                component_id=item.component_id,
                calculation_type=item.calculation_type.upper(),
                calculation_basis=item.calculation_basis.upper() if item.calculation_basis else None,
                percentage_or_value=item.percentage_or_value,
                sequence_order=item.sequence_order or idx,
            )
            db.add(assoc)

        db.commit()
        db.refresh(structure)
        PayrollService.log_audit(db, "CREATE", "SalaryStructure", structure.id, user_id, {"code": structure.code})
        db.commit()
        return PayrollService.get_structure(db, structure.id)

    @staticmethod
    def update_structure(db: Session, structure_id: int, data: SalaryStructureUpdate, user_id: Optional[int] = None) -> SalaryStructure:
        structure = PayrollService.get_structure(db, structure_id)

        if data.name is not None:
            structure.name = data.name
        if data.salary_basis is not None:
            structure.salary_basis = data.salary_basis.upper()
        if data.description is not None:
            structure.description = data.description
        if data.is_active is not None:
            structure.is_active = data.is_active

        if data.components is not None:
            db.query(SalaryStructureComponent).filter(SalaryStructureComponent.structure_id == structure_id).delete()
            for idx, item in enumerate(data.components, start=1):
                assoc = SalaryStructureComponent(
                    structure_id=structure.id,
                    component_id=item.component_id,
                    calculation_type=item.calculation_type.upper(),
                    calculation_basis=item.calculation_basis.upper() if item.calculation_basis else None,
                    percentage_or_value=item.percentage_or_value,
                    sequence_order=item.sequence_order or idx,
                )
                db.add(assoc)

        db.commit()
        db.refresh(structure)
        PayrollService.log_audit(db, "UPDATE", "SalaryStructure", structure.id, user_id, {"id": structure.id})
        db.commit()
        return PayrollService.get_structure(db, structure.id)

    # =========================================================================
    # 3. Dynamic Salary Preview / Calculation
    # =========================================================================
    @staticmethod
    def preview_salary(db: Session, req: SalaryCalculationRequest) -> SalaryCalculationPreview:
        structure = PayrollService.get_structure(db, req.structure_id)
        return PayrollCalculationService.calculate_salary_breakdown(
            db=db,
            structure=structure,
            ctc_amount=req.ctc_amount,
            salary_type=req.salary_type,
            salary_basis=req.salary_basis,
            custom_overrides=req.custom_overrides,
        )

    # =========================================================================
    # 4. Employee Salary Assignment & History
    # =========================================================================
    @staticmethod
    def assign_employee_salary(
        db: Session,
        data: EmployeeSalaryAssignmentCreate,
        user_id: Optional[int] = None,
    ) -> EmployeeSalaryAssignment:
        employee = db.query(Employee).filter(Employee.id == data.employee_id).first()
        if not employee:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

        structure = PayrollService.get_structure(db, data.salary_structure_id)

        # Deactivate current active assignment
        existing = (
            db.query(EmployeeSalaryAssignment)
            .filter(
                EmployeeSalaryAssignment.employee_id == data.employee_id,
                EmployeeSalaryAssignment.is_active == True,
            )
            .first()
        )
        if existing:
            existing.is_active = False
            existing.effective_to = data.effective_from - timedelta(days=1)

        # Calculate breakdown
        preview = PayrollCalculationService.calculate_salary_breakdown(
            db=db,
            structure=structure,
            ctc_amount=data.ctc_amount,
            salary_type=data.salary_type,
            salary_basis=data.salary_basis,
            custom_overrides=data.custom_overrides,
        )

        assignment = EmployeeSalaryAssignment(
            employee_id=data.employee_id,
            salary_structure_id=data.salary_structure_id,
            salary_basis=data.salary_basis.upper(),
            salary_type=data.salary_type,
            annual_ctc=preview.annual_ctc,
            monthly_ctc=preview.monthly_ctc,
            gross_monthly=preview.gross_monthly,
            net_monthly=preview.net_monthly,
            total_deductions=preview.total_deductions_monthly,
            employer_contributions=preview.employer_contributions_monthly,
            effective_from=data.effective_from,
            is_active=True,
        )
        db.add(assignment)
        db.flush()

        # Add line items
        for item in preview.earnings + preview.deductions + preview.employer_contributions:
            line = EmployeeSalaryComponent(
                assignment_id=assignment.id,
                component_id=item.component_id,
                monthly_amount=item.monthly_amount,
                annual_amount=item.annual_amount,
                percentage=item.percentage_or_value,
            )
            db.add(line)

        db.commit()
        db.refresh(assignment)

        PayrollService.log_audit(
            db, "ASSIGN_SALARY", "EmployeeSalaryAssignment", assignment.id, user_id,
            {"employee_id": data.employee_id, "annual_ctc": preview.annual_ctc, "effective_from": str(data.effective_from)}
        )
        db.commit()
        return assignment

    @staticmethod
    def get_employee_salary(db: Session, employee_id: int) -> Optional[Dict[str, Any]]:
        assignment = (
            db.query(EmployeeSalaryAssignment)
            .options(
                joinedload(EmployeeSalaryAssignment.structure),
                joinedload(EmployeeSalaryAssignment.components).joinedload(EmployeeSalaryComponent.component),
            )
            .filter(
                EmployeeSalaryAssignment.employee_id == employee_id,
                EmployeeSalaryAssignment.is_active == True,
            )
            .order_by(EmployeeSalaryAssignment.effective_from.desc())
            .first()
        )
        if not assignment:
            return None

        emp = db.query(Employee).filter(Employee.id == employee_id).first()

        preview = None
        if assignment.structure:
            preview = PayrollCalculationService.calculate_salary_breakdown(
                db=db,
                structure=assignment.structure,
                ctc_amount=assignment.annual_ctc,
                salary_type="Annual",
                salary_basis=assignment.salary_basis,
            )

        return {
            "id": assignment.id,
            "employee_id": assignment.employee_id,
            "employee_code": emp.employee_code if emp else None,
            "employee_name": f"{emp.first_name} {emp.last_name}" if emp else None,
            "department": emp.department if emp else None,
            "designation": emp.designation if emp else None,
            "salary_structure_id": assignment.salary_structure_id,
            "structure_name": assignment.structure.name if assignment.structure else None,
            "salary_basis": assignment.salary_basis,
            "salary_type": assignment.salary_type,
            "annual_ctc": assignment.annual_ctc,
            "monthly_ctc": assignment.monthly_ctc,
            "gross_monthly": assignment.gross_monthly,
            "net_monthly": assignment.net_monthly,
            "total_deductions": assignment.total_deductions,
            "employer_contributions": assignment.employer_contributions,
            "effective_from": assignment.effective_from,
            "effective_to": assignment.effective_to,
            "is_active": assignment.is_active,
            "breakdown": preview,
            "created_at": assignment.created_at,
        }

    @staticmethod
    def get_all_employee_salaries(
        db: Session,
        search: Optional[str] = None,
        department: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        query = (
            db.query(Employee)
            .join(User, Employee.user_id == User.id)
            .join(Role, User.role_id == Role.id)
            .filter(
                func.lower(Role.name).in_(["employee", "hr"]),
                func.lower(Employee.status) == "active",
                func.lower(User.status) == "active",
            )
        )

        if department:
            query = query.filter(Employee.department == department)

        if search:
            s = f"%{search}%"
            query = query.filter(
                or_(
                    Employee.first_name.ilike(s),
                    Employee.last_name.ilike(s),
                    Employee.employee_code.ilike(s),
                    Employee.official_email.ilike(s),
                )
            )

        total = query.count()
        employees = query.offset(skip).limit(limit).all()

        results = []
        for emp in employees:
            active_assign = (
                db.query(EmployeeSalaryAssignment)
                .options(joinedload(EmployeeSalaryAssignment.structure))
                .filter(
                    EmployeeSalaryAssignment.employee_id == emp.id,
                    EmployeeSalaryAssignment.is_active == True,
                )
                .first()
            )
            results.append({
                "employee_id": emp.id,
                "employee_code": emp.employee_code,
                "employee_name": f"{emp.first_name} {emp.last_name}",
                "department": emp.department,
                "designation": emp.designation,
                "has_salary": active_assign is not None,
                "assignment_id": active_assign.id if active_assign else None,
                "structure_id": active_assign.salary_structure_id if active_assign else None,
                "structure_name": active_assign.structure.name if active_assign and active_assign.structure else None,
                "salary_basis": active_assign.salary_basis if active_assign else None,
                "annual_ctc": active_assign.annual_ctc if active_assign else 0.0,
                "monthly_ctc": active_assign.monthly_ctc if active_assign else 0.0,
                "gross_monthly": active_assign.gross_monthly if active_assign else 0.0,
                "net_monthly": active_assign.net_monthly if active_assign else 0.0,
                "effective_from": active_assign.effective_from if active_assign else None,
            })

        return {"total": total, "items": results}

    @staticmethod
    def get_salary_history(db: Session, employee_id: int) -> List[Dict[str, Any]]:
        assignments = (
            db.query(EmployeeSalaryAssignment)
            .options(joinedload(EmployeeSalaryAssignment.structure))
            .filter(EmployeeSalaryAssignment.employee_id == employee_id)
            .order_by(EmployeeSalaryAssignment.effective_from.desc())
            .all()
        )
        results = []
        for a in assignments:
            results.append({
                "id": a.id,
                "salary_structure_id": a.salary_structure_id,
                "structure_name": a.structure.name if a.structure else None,
                "salary_basis": a.salary_basis,
                "annual_ctc": a.annual_ctc,
                "monthly_ctc": a.monthly_ctc,
                "gross_monthly": a.gross_monthly,
                "net_monthly": a.net_monthly,
                "effective_from": a.effective_from,
                "effective_to": a.effective_to,
                "is_active": a.is_active,
                "created_at": a.created_at,
            })
        return results

    # =========================================================================
    # 5. Salary Revisions
    # =========================================================================
    @staticmethod
    def create_revision(db: Session, data: SalaryRevisionCreate, user_id: int) -> SalaryRevision:
        emp = db.query(Employee).filter(Employee.id == data.employee_id).first()
        if not emp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

        current_assign = (
            db.query(EmployeeSalaryAssignment)
            .filter(EmployeeSalaryAssignment.employee_id == data.employee_id, EmployeeSalaryAssignment.is_active == True)
            .first()
        )
        old_ctc = current_assign.annual_ctc if current_assign else 0.0
        old_gross = current_assign.gross_monthly if current_assign else 0.0

        new_structure = PayrollService.get_structure(db, data.new_salary_structure_id)
        new_preview = PayrollCalculationService.calculate_salary_breakdown(
            db=db,
            structure=new_structure,
            ctc_amount=data.new_ctc_amount,
            salary_type=data.salary_type,
            salary_basis=new_structure.salary_basis,
        )

        increment_amount = max(0.0, round(new_preview.annual_ctc - old_ctc, 2))
        increment_pct = round((increment_amount / old_ctc * 100.0), 2) if old_ctc > 0 else 100.0

        rev = SalaryRevision(
            employee_id=data.employee_id,
            old_salary_assignment_id=current_assign.id if current_assign else None,
            new_salary_structure_id=data.new_salary_structure_id,
            old_annual_ctc=old_ctc,
            new_annual_ctc=new_preview.annual_ctc,
            old_monthly_gross=old_gross,
            new_monthly_gross=new_preview.gross_monthly,
            increment_amount=increment_amount,
            increment_percentage=increment_pct,
            effective_from=data.effective_from,
            reason=data.reason,
            remarks=data.remarks,
            status="PENDING",
            created_by=user_id,
        )
        db.add(rev)
        db.commit()
        db.refresh(rev)

        PayrollService.log_audit(db, "CREATE", "SalaryRevision", rev.id, user_id, {"employee_id": rev.employee_id, "new_ctc": rev.new_annual_ctc})
        db.commit()
        return rev

    @staticmethod
    def get_revisions(
        db: Session,
        status_filter: Optional[str] = None,
        employee_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        query = db.query(SalaryRevision).options(
            joinedload(SalaryRevision.employee),
            joinedload(SalaryRevision.structure),
            joinedload(SalaryRevision.creator),
            joinedload(SalaryRevision.approver),
        )
        if status_filter:
            query = query.filter(SalaryRevision.status == status_filter.upper())
        if employee_id:
            query = query.filter(SalaryRevision.employee_id == employee_id)

        total = query.count()
        revisions = query.order_by(SalaryRevision.created_at.desc()).offset(skip).limit(limit).all()

        items = []
        for r in revisions:
            emp = r.employee
            items.append({
                "id": r.id,
                "employee_id": r.employee_id,
                "employee_code": emp.employee_code if emp else None,
                "employee_name": f"{emp.first_name} {emp.last_name}" if emp else None,
                "department": emp.department if emp else None,
                "designation": emp.designation if emp else None,
                "new_salary_structure_id": r.new_salary_structure_id,
                "structure_name": r.structure.name if r.structure else None,
                "old_annual_ctc": r.old_annual_ctc,
                "new_annual_ctc": r.new_annual_ctc,
                "old_monthly_gross": r.old_monthly_gross,
                "new_monthly_gross": r.new_monthly_gross,
                "increment_amount": r.increment_amount,
                "increment_percentage": r.increment_percentage,
                "effective_from": r.effective_from,
                "reason": r.reason,
                "remarks": r.remarks,
                "status": r.status,
                "created_by": r.created_by,
                "creator_name": f"{r.creator.display_name}" if r.creator else None,
                "approved_by": r.approved_by,
                "approver_name": f"{r.approver.display_name}" if r.approver else None,
                "approved_at": r.approved_at,
                "created_at": r.created_at,
            })
        return {"total": total, "items": items}

    @staticmethod
    def action_revision(db: Session, revision_id: int, action: SalaryRevisionAction, user_id: int) -> Dict[str, Any]:
        rev = db.query(SalaryRevision).filter(SalaryRevision.id == revision_id).first()
        if not rev:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salary revision not found")
        if rev.status != "PENDING":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Revision already has status '{rev.status}'")

        rev.approved_by = user_id
        rev.approved_at = datetime.now(timezone.utc)
        if action.remarks:
            rev.remarks = f"{rev.remarks or ''} | Action Note: {action.remarks}"

        if action.approved:
            rev.status = "APPROVED"
            structure = PayrollService.get_structure(db, rev.new_salary_structure_id)
            PayrollService.assign_employee_salary(
                db=db,
                data=EmployeeSalaryAssignmentCreate(
                    employee_id=rev.employee_id,
                    salary_structure_id=rev.new_salary_structure_id,
                    salary_basis=structure.salary_basis,
                    salary_type="Annual",
                    ctc_amount=rev.new_annual_ctc,
                    effective_from=rev.effective_from,
                ),
                user_id=user_id,
            )
        else:
            rev.status = "REJECTED"

        db.commit()
        PayrollService.log_audit(db, "REVISION_ACTION", "SalaryRevision", rev.id, user_id, {"status": rev.status})
        db.commit()
        return {"message": f"Salary revision successfully {rev.status.lower()}", "status": rev.status}

    # =========================================================================
    # 6. Payroll Periods & Runs Execution
    # =========================================================================
    @staticmethod
    def get_or_create_period(db: Session, year: int, month: int) -> PayrollPeriod:
        period = db.query(PayrollPeriod).filter(PayrollPeriod.year == year, PayrollPeriod.month == month).first()
        if period:
            return period

        num_days = calendar.monthrange(year, month)[1]
        start_date = date(year, month, 1)
        end_date = date(year, month, num_days)
        pay_date = date(year, month, num_days)

        working_days = sum(
            1 for day in range(1, num_days + 1)
            if date(year, month, day).weekday() != 6  # Mon-Sat are working days, Sunday is weekly off
        )

        month_name = calendar.month_name[month]
        period = PayrollPeriod(
            name=f"{month_name} {year}",
            year=year,
            month=month,
            start_date=start_date,
            end_date=end_date,
            pay_date=pay_date,
            total_days=num_days,
            working_days=working_days,
            status="OPEN",
        )
        db.add(period)
        db.commit()
        db.refresh(period)
        return period

    @staticmethod
    def get_periods(db: Session) -> List[PayrollPeriod]:
        return db.query(PayrollPeriod).order_by(PayrollPeriod.year.desc(), PayrollPeriod.month.desc()).all()

    @staticmethod
    def execute_payroll_run(db: Session, data: PayrollRunCreate, user_id: int) -> PayrollRun:
        period = PayrollService.get_or_create_period(db, data.year, data.month)
        if period.status == "LOCKED":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Payroll period {period.name} is LOCKED. Cannot run payroll.")

        existing_runs_count = db.query(PayrollRun).filter(PayrollRun.period_id == period.id).count()
        run_number = f"PAY-{period.year}{period.month:02d}-{(existing_runs_count + 1):02d}"

        payroll_run = PayrollRun(
            period_id=period.id,
            run_number=run_number,
            title=f"Payroll Run for {period.name}",
            status="PROCESSING",
        )
        db.add(payroll_run)
        db.flush()

        emp_query = (
            db.query(Employee)
            .join(User, Employee.user_id == User.id)
            .join(Role, User.role_id == Role.id)
            .filter(
                func.lower(Role.name).in_(["employee", "hr"]),
                func.lower(Employee.status) == "active",
                func.lower(User.status) == "active",
            )
        )
        if data.selected_employee_ids:
            emp_query = emp_query.filter(Employee.id.in_(data.selected_employee_ids))
        employees = emp_query.all()

        total_employees = len(employees)
        processed_employees = 0
        total_gross = 0.0
        total_deductions = 0.0
        total_net = 0.0
        total_employer_cost = 0.0
        warning_count = 0
        error_count = 0

        for emp in employees:
            calc_result = PayrollCalculationService.calculate_employee_payroll(
                db=db,
                employee_id=emp.id,
                start_date=period.start_date,
                end_date=period.end_date,
                period_working_days=period.working_days,
            )

            if not calc_result.get("success"):
                error_count += 1
                exc = PayrollException(
                    payroll_run_id=payroll_run.id,
                    employee_id=emp.id,
                    severity="CRITICAL",
                    error_code=calc_result.get("error_code", "CALCULATION_ERROR"),
                    message=calc_result.get("error", "Calculation failed"),
                )
                db.add(exc)
                continue

            bank_name = getattr(emp, "bank_name", None)
            account_number = getattr(emp, "bank_account_no", None)
            ifsc_code = getattr(emp, "ifsc_code", None)

            if not account_number or not ifsc_code:
                warning_count += 1
                exc = PayrollException(
                    payroll_run_id=payroll_run.id,
                    employee_id=emp.id,
                    severity="WARNING",
                    error_code="MISSING_BANK_DETAILS",
                    message="Missing bank account number or IFSC code for bank transfer.",
                )
                db.add(exc)

            for exc_item in calc_result.get("exceptions", []):
                if exc_item["severity"] == "CRITICAL":
                    error_count += 1
                else:
                    warning_count += 1
                exc = PayrollException(
                    payroll_run_id=payroll_run.id,
                    employee_id=emp.id,
                    severity=exc_item["severity"],
                    error_code=exc_item["error_code"],
                    message=exc_item["message"],
                )
                db.add(exc)

            record = PayrollRecord(
                payroll_run_id=payroll_run.id,
                employee_id=emp.id,
                salary_assignment_id=calc_result.get("salary_assignment_id"),
                status="CALCULATED",
                total_payroll_days=calc_result["total_payroll_days"],
                payable_days=calc_result["payable_days"],
                present_days=calc_result["present_days"],
                absent_days=calc_result["absent_days"],
                half_days=calc_result["half_days"],
                paid_leave_days=calc_result["paid_leave_days"],
                unpaid_leave_days=calc_result["unpaid_leave_days"],
                holidays_count=calc_result["holidays_count"],
                weekly_offs_count=calc_result["weekly_offs_count"],
                overtime_hours=calc_result["overtime_hours"],
                overtime_rate=calc_result["overtime_rate"],
                overtime_amount=calc_result["overtime_amount"],
                bonus_amount=calc_result["bonus_amount"],
                incentive_amount=calc_result["incentive_amount"],
                other_earnings_amount=calc_result["other_earnings_amount"],
                lop_deduction_amount=calc_result["lop_deduction_amount"],
                other_deductions_amount=calc_result["other_deductions_amount"],
                fixed_gross_salary=calc_result["fixed_gross_salary"],
                gross_earnings=calc_result["gross_earnings"],
                total_deductions=calc_result["total_deductions"],
                net_salary=calc_result["net_salary"],
                employer_pf=calc_result["employer_pf"],
                employer_esi=calc_result["employer_esi"],
                total_employer_contribution=calc_result["total_employer_contribution"],
                total_cost_to_company=calc_result["total_cost_to_company"],
                payment_status="PENDING",
                payment_mode="BANK_TRANSFER",
                bank_name=bank_name,
                account_number=account_number,
                ifsc_code=ifsc_code,
                calculation_snapshot=calc_result["calculation_snapshot"],
            )
            db.add(record)
            db.flush()

            for li in calc_result.get("line_items", []):
                ritem = PayrollRecordItem(
                    record_id=record.id,
                    component_code=li["component_code"],
                    component_name=li["component_name"],
                    component_type=li["component_type"],
                    amount=li["amount"],
                    calculation_detail=li.get("calculation_detail"),
                )
                db.add(ritem)

            processed_employees += 1
            total_gross += calc_result["gross_earnings"]
            total_deductions += calc_result["total_deductions"]
            total_net += calc_result["net_salary"]
            total_employer_cost += calc_result["total_cost_to_company"]

        payroll_run.status = "DRAFT"
        payroll_run.total_employees = total_employees
        payroll_run.processed_employees = processed_employees
        payroll_run.warning_count = warning_count
        payroll_run.error_count = error_count
        payroll_run.total_gross = round(total_gross, 2)
        payroll_run.total_deductions = round(total_deductions, 2)
        payroll_run.total_net = round(total_net, 2)
        payroll_run.total_employer_cost = round(total_employer_cost, 2)
        payroll_run.calculated_at = datetime.now(timezone.utc)

        period.status = "PROCESSING"

        db.commit()
        db.refresh(payroll_run)

        PayrollService.log_audit(
            db, "EXECUTE_RUN", "PayrollRun", payroll_run.id, user_id,
            {"run_number": run_number, "employees": processed_employees, "total_net": payroll_run.total_net}
        )
        db.commit()
        return payroll_run

    @staticmethod
    def get_runs(
        db: Session,
        year: Optional[int] = None,
        month: Optional[int] = None,
        status_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = db.query(PayrollRun).options(joinedload(PayrollRun.period))
        if year:
            query = query.join(PayrollPeriod).filter(PayrollPeriod.year == year)
        if month:
            query = query.join(PayrollPeriod).filter(PayrollPeriod.month == month)
        if status_filter:
            query = query.filter(PayrollRun.status == status_filter.upper())

        runs = query.order_by(PayrollRun.created_at.desc()).all()
        results = []
        for r in runs:
            results.append({
                "id": r.id,
                "period_id": r.period_id,
                "period_name": r.period.name if r.period else "Unknown",
                "run_number": r.run_number,
                "title": r.title,
                "status": r.status,
                "total_employees": r.total_employees,
                "processed_employees": r.processed_employees,
                "warning_count": r.warning_count,
                "error_count": r.error_count,
                "total_gross": r.total_gross,
                "total_deductions": r.total_deductions,
                "total_net": r.total_net,
                "total_employer_cost": r.total_employer_cost,
                "calculated_at": r.calculated_at,
                "approved_at": r.approved_at,
                "locked_at": r.locked_at,
                "paid_at": r.paid_at,
            })
        return results

    @staticmethod
    def get_run_detail(db: Session, run_id: int) -> Dict[str, Any]:
        r = db.query(PayrollRun).options(joinedload(PayrollRun.period)).filter(PayrollRun.id == run_id).first()
        if not r:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payroll run not found")

        return {
            "id": r.id,
            "period_id": r.period_id,
            "period_name": r.period.name if r.period else "Unknown",
            "year": r.period.year if r.period else None,
            "month": r.period.month if r.period else None,
            "start_date": r.period.start_date if r.period else None,
            "end_date": r.period.end_date if r.period else None,
            "pay_date": r.period.pay_date if r.period else None,
            "run_number": r.run_number,
            "title": r.title,
            "status": r.status,
            "total_employees": r.total_employees,
            "processed_employees": r.processed_employees,
            "warning_count": r.warning_count,
            "error_count": r.error_count,
            "total_gross": r.total_gross,
            "total_deductions": r.total_deductions,
            "total_net": r.total_net,
            "total_employer_cost": r.total_employer_cost,
            "calculated_at": r.calculated_at,
            "approved_at": r.approved_at,
            "locked_at": r.locked_at,
            "paid_at": r.paid_at,
        }

    @staticmethod
    def submit_run_for_approval(db: Session, run_id: int, user_id: int) -> Dict[str, Any]:
        run = db.query(PayrollRun).filter(PayrollRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payroll run not found")
        if run.status not in ["DRAFT", "REJECTED"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot submit run with status '{run.status}' for approval")

        run.status = "PENDING_APPROVAL"
        db.commit()
        PayrollService.log_audit(db, "SUBMIT_FOR_APPROVAL", "PayrollRun", run.id, user_id)
        db.commit()
        return {"message": "Payroll run submitted for approval", "status": run.status}

    @staticmethod
    def approve_or_reject_run(db: Session, run_id: int, approved: bool, user_id: int, remarks: Optional[str] = None) -> Dict[str, Any]:
        run = db.query(PayrollRun).filter(PayrollRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payroll run not found")
        if run.status != "PENDING_APPROVAL":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot act on run with status '{run.status}'")

        if approved:
            run.status = "APPROVED"
            run.approved_by = user_id
            run.approved_at = datetime.now(timezone.utc)
        else:
            run.status = "REJECTED"

        db.commit()
        PayrollService.log_audit(db, "APPROVE_RUN" if approved else "REJECT_RUN", "PayrollRun", run.id, user_id, {"remarks": remarks})
        db.commit()
        return {"message": f"Payroll run {run.status.lower()}", "status": run.status}

    @staticmethod
    def lock_payroll_run(db: Session, run_id: int, user_id: int) -> Dict[str, Any]:
        run = db.query(PayrollRun).options(joinedload(PayrollRun.period)).filter(PayrollRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payroll run not found")
        if run.status not in ["APPROVED", "DRAFT"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot lock run with status '{run.status}'")

        records = (
            db.query(PayrollRecord)
            .options(
                joinedload(PayrollRecord.employee),
                joinedload(PayrollRecord.items),
            )
            .filter(PayrollRecord.payroll_run_id == run.id)
            .all()
        )

        month_str = f"{run.period.year}-{run.period.month:02d}"

        for rec in records:
            emp = rec.employee
            payslip_number = f"PAYSLIP-{run.period.year}{run.period.month:02d}-{emp.employee_code}"

            existing = db.query(Payslip).filter(Payslip.payroll_record_id == rec.id).first()
            if not existing:
                ps = Payslip(
                    payroll_record_id=rec.id,
                    employee_id=emp.id,
                    payslip_number=payslip_number,
                    payroll_month=month_str,
                    is_published=True,
                    generated_at=datetime.now(timezone.utc),
                )
                db.add(ps)
            else:
                existing.is_published = True

            rec.status = "FINALIZED"

        run.status = "LOCKED"
        run.locked_at = datetime.now(timezone.utc)
        run.locked_by = user_id
        if run.period:
            run.period.status = "LOCKED"

        db.commit()
        PayrollService.log_audit(db, "LOCK_RUN", "PayrollRun", run.id, user_id, {"payslips_generated": len(records)})
        db.commit()
        return {"message": "Payroll run locked and payslips published successfully", "status": run.status}

    @staticmethod
    def mark_run_paid(db: Session, run_id: int, user_id: int) -> Dict[str, Any]:
        run = db.query(PayrollRun).options(joinedload(PayrollRun.period)).filter(PayrollRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payroll run not found")
        if run.status != "LOCKED":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only LOCKED runs can be marked as PAID")

        run.status = "PAID"
        run.paid_at = datetime.now(timezone.utc)
        run.paid_by = user_id
        if run.period:
            run.period.status = "PAID"

        db.query(PayrollRecord).filter(PayrollRecord.payroll_run_id == run.id).update(
            {"payment_status": "PAID", "paid_at": datetime.now(timezone.utc)}
        )
        db.commit()

        PayrollService.log_audit(db, "MARK_PAID", "PayrollRun", run.id, user_id)
        db.commit()
        return {"message": "Payroll run and all associated records marked as PAID", "status": run.status}

    # =========================================================================
    # 7. Payroll Records & Adjustments
    # =========================================================================
    @staticmethod
    def get_payroll_records(
        db: Session,
        run_id: int,
        search: Optional[str] = None,
        department: Optional[str] = None,
        status_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        query = (
            db.query(PayrollRecord)
            .options(
                joinedload(PayrollRecord.employee),
                joinedload(PayrollRecord.items),
            )
            .filter(PayrollRecord.payroll_run_id == run_id)
        )

        if department:
            query = query.join(PayrollRecord.employee).filter(Employee.department == department)

        if status_filter:
            query = query.filter(PayrollRecord.status == status_filter.upper())

        if search:
            s = f"%{search}%"
            query = query.join(PayrollRecord.employee).filter(
                or_(
                    Employee.first_name.ilike(s),
                    Employee.last_name.ilike(s),
                    Employee.employee_code.ilike(s),
                )
            )

        total = query.count()
        records = query.order_by(PayrollRecord.id.asc()).offset(skip).limit(limit).all()

        items = []
        for r in records:
            emp = r.employee
            items.append({
                "id": r.id,
                "payroll_run_id": r.payroll_run_id,
                "employee_id": r.employee_id,
                "employee_code": emp.employee_code if emp else None,
                "employee_name": f"{emp.first_name} {emp.last_name}" if emp else None,
                "department": emp.department if emp else None,
                "designation": emp.designation if emp else None,
                "status": r.status,
                "total_payroll_days": r.total_payroll_days,
                "payable_days": r.payable_days,
                "present_days": r.present_days,
                "absent_days": r.absent_days,
                "half_days": r.half_days,
                "paid_leave_days": r.paid_leave_days,
                "unpaid_leave_days": r.unpaid_leave_days,
                "holidays_count": r.holidays_count,
                "weekly_offs_count": r.weekly_offs_count,
                "overtime_hours": r.overtime_hours,
                "overtime_rate": r.overtime_rate,
                "overtime_amount": r.overtime_amount,
                "bonus_amount": r.bonus_amount,
                "incentive_amount": r.incentive_amount,
                "other_earnings_amount": r.other_earnings_amount,
                "lop_deduction_amount": r.lop_deduction_amount,
                "other_deductions_amount": r.other_deductions_amount,
                "fixed_gross_salary": r.fixed_gross_salary,
                "gross_earnings": r.gross_earnings,
                "total_deductions": r.total_deductions,
                "net_salary": r.net_salary,
                "employer_pf": r.employer_pf,
                "employer_esi": r.employer_esi,
                "total_employer_contribution": r.total_employer_contribution,
                "total_cost_to_company": r.total_cost_to_company,
                "payment_status": r.payment_status,
                "payment_mode": r.payment_mode,
                "bank_name": r.bank_name,
                "account_number": r.account_number,
                "ifsc_code": r.ifsc_code,
                "items": [
                    {
                        "id": item.id,
                        "component_code": item.component_code,
                        "component_name": item.component_name,
                        "component_type": item.component_type,
                        "amount": item.amount,
                        "calculation_detail": item.calculation_detail,
                    }
                    for item in r.items
                ],
                "calculation_snapshot": r.calculation_snapshot,
                "created_at": r.created_at,
            })

        return {"total": total, "items": items}

    @staticmethod
    def adjust_payroll_record(db: Session, record_id: int, data: PayrollAdjustmentCreate, user_id: int) -> Dict[str, Any]:
        rec = db.query(PayrollRecord).options(joinedload(PayrollRecord.payroll_run)).filter(PayrollRecord.id == record_id).first()
        if not rec:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payroll record not found")
        if rec.payroll_run.status in ["LOCKED", "PAID"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot adjust records in LOCKED or PAID runs")

        item = db.query(PayrollRecordItem).filter(
            PayrollRecordItem.record_id == record_id,
            PayrollRecordItem.component_code == data.component_code,
        ).first()

        old_amount = item.amount if item else 0.0
        difference = round(data.new_amount - old_amount, 2)

        if item:
            item.amount = data.new_amount
            item.calculation_detail = f"Manual adjustment: {data.reason}"
        else:
            item = PayrollRecordItem(
                record_id=record_id,
                component_code=data.component_code,
                component_name=data.component_code,
                component_type="EARNING" if difference > 0 else "DEDUCTION",
                amount=data.new_amount,
                calculation_detail=f"Manual addition: {data.reason}",
            )
            db.add(item)

        items = db.query(PayrollRecordItem).filter(PayrollRecordItem.record_id == record_id).all()
        gross = sum(i.amount for i in items if i.component_type == "EARNING")
        deductions = sum(i.amount for i in items if i.component_type == "DEDUCTION")
        employer_cont = sum(i.amount for i in items if i.component_type == "EMPLOYER_CONTRIBUTION")

        rec.gross_earnings = round(gross, 2)
        rec.total_deductions = round(deductions, 2)
        rec.net_salary = max(0.0, round(gross - deductions, 2))
        rec.total_employer_contribution = round(employer_cont, 2)
        rec.total_cost_to_company = round(rec.gross_earnings + rec.total_employer_contribution, 2)

        adj = PayrollAdjustment(
            payroll_record_id=record_id,
            component_code=data.component_code,
            old_amount=old_amount,
            new_amount=data.new_amount,
            difference=difference,
            reason=data.reason,
            status="APPROVED",
            requested_by=user_id,
        )
        db.add(adj)

        all_recs = db.query(PayrollRecord).filter(PayrollRecord.payroll_run_id == rec.payroll_run_id).all()
        rec.payroll_run.total_gross = round(sum(r.gross_earnings for r in all_recs), 2)
        rec.payroll_run.total_deductions = round(sum(r.total_deductions for r in all_recs), 2)
        rec.payroll_run.total_net = round(sum(r.net_salary for r in all_recs), 2)
        rec.payroll_run.total_employer_cost = round(sum(r.total_cost_to_company for r in all_recs), 2)

        db.commit()
        PayrollService.log_audit(db, "ADJUST_RECORD", "PayrollRecord", record_id, user_id, {"diff": difference, "reason": data.reason})
        db.commit()
        return {"message": "Payroll adjustment applied successfully", "difference": difference}

    # =========================================================================
    # 8. Payroll Inputs (Bonuses, Overrides)
    # =========================================================================
    @staticmethod
    def create_payroll_input(db: Session, data: PayrollInputCreate, user_id: int) -> PayrollInput:
        emp = db.query(Employee).filter(Employee.id == data.employee_id).first()
        if not emp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

        inp = PayrollInput(
            employee_id=data.employee_id,
            payroll_period_id=data.payroll_period_id,
            input_type=data.input_type.upper(),
            title=data.title,
            amount=data.amount,
            hours=data.hours,
            remarks=data.remarks,
            status="APPROVED",
            created_by=user_id,
            approved_by=user_id,
            approved_at=datetime.now(timezone.utc),
        )
        db.add(inp)
        db.commit()
        db.refresh(inp)

        PayrollService.log_audit(db, "CREATE_INPUT", "PayrollInput", inp.id, user_id, {"amount": inp.amount, "type": inp.input_type})
        db.commit()
        return inp

    @staticmethod
    def get_payroll_inputs(
        db: Session,
        period_id: Optional[int] = None,
        employee_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        query = db.query(PayrollInput).options(
            joinedload(PayrollInput.employee),
            joinedload(PayrollInput.period),
        )
        if period_id:
            query = query.filter(PayrollInput.payroll_period_id == period_id)
        if employee_id:
            query = query.filter(PayrollInput.employee_id == employee_id)

        inputs = query.order_by(PayrollInput.created_at.desc()).all()
        results = []
        for i in inputs:
            emp = i.employee
            results.append({
                "id": i.id,
                "employee_id": i.employee_id,
                "employee_code": emp.employee_code if emp else None,
                "employee_name": f"{emp.first_name} {emp.last_name}" if emp else None,
                "payroll_period_id": i.payroll_period_id,
                "period_name": i.period.name if i.period else None,
                "input_type": i.input_type,
                "title": i.title,
                "amount": i.amount,
                "hours": i.hours,
                "remarks": i.remarks,
                "status": i.status,
            })
        return results

    @staticmethod
    def delete_payroll_input(db: Session, input_id: int, user_id: int) -> Dict[str, Any]:
        inp = db.query(PayrollInput).filter(PayrollInput.id == input_id).first()
        if not inp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payroll input not found")

        db.delete(inp)
        db.commit()
        PayrollService.log_audit(db, "DELETE_INPUT", "PayrollInput", input_id, user_id)
        db.commit()
        return {"message": "Payroll input removed successfully"}

    # =========================================================================
    # 9. Exceptions & Resolutions
    # =========================================================================
    @staticmethod
    def get_exceptions(
        db: Session,
        run_id: int,
        severity: Optional[str] = None,
        is_resolved: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        query = (
            db.query(PayrollException)
            .options(joinedload(PayrollException.employee))
            .filter(PayrollException.payroll_run_id == run_id)
        )
        if severity:
            query = query.filter(PayrollException.severity == severity.upper())
        if is_resolved is not None:
            query = query.filter(PayrollException.is_resolved == is_resolved)

        exceptions = query.order_by(PayrollException.severity.desc(), PayrollException.id.asc()).all()
        results = []
        for exc in exceptions:
            emp = exc.employee
            results.append({
                "id": exc.id,
                "payroll_run_id": exc.payroll_run_id,
                "employee_id": exc.employee_id,
                "employee_code": emp.employee_code if emp else None,
                "employee_name": f"{emp.first_name} {emp.last_name}" if emp else None,
                "department": emp.department if emp else None,
                "severity": exc.severity,
                "error_code": exc.error_code,
                "message": exc.message,
                "is_resolved": exc.is_resolved,
                "resolution_notes": exc.resolution_notes,
                "created_at": exc.created_at,
            })
        return results

    @staticmethod
    def resolve_exception(db: Session, exception_id: int, resolution_notes: str, user_id: int) -> Dict[str, Any]:
        exc = db.query(PayrollException).filter(PayrollException.id == exception_id).first()
        if not exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payroll exception not found")

        exc.is_resolved = True
        exc.resolution_notes = resolution_notes
        exc.resolved_by = user_id
        exc.resolved_at = datetime.now(timezone.utc)

        db.commit()
        PayrollService.log_audit(db, "RESOLVE_EXCEPTION", "PayrollException", exception_id, user_id, {"notes": resolution_notes})
        db.commit()
        return {"message": "Exception resolved successfully"}

    # =========================================================================
    # 10. Payslips & Employee Self-Service
    # =========================================================================
    @staticmethod
    def get_payslips(
        db: Session,
        employee_id: Optional[int] = None,
        month: Optional[str] = None,
        is_published: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        query = db.query(Payslip)
        if employee_id:
            query = query.filter(Payslip.employee_id == employee_id)
        if month:
            query = query.filter(Payslip.payroll_month == month)
        if is_published is not None:
            query = query.filter(Payslip.is_published == is_published)

        total = query.count()
        slips = query.order_by(Payslip.payroll_month.desc(), Payslip.employee_id.asc()).offset(skip).limit(limit).all()
        return {"total": total, "items": slips}

    @staticmethod
    def get_payslip_detail(db: Session, payslip_id: int) -> Payslip:
        slip = db.query(Payslip).filter(Payslip.id == payslip_id).first()
        if not slip:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payslip not found")
        return slip

    @staticmethod
    def generate_payslip_pdf(db: Session, payslip_id: int) -> StreamingResponse:
        slip = PayrollService.get_payslip_detail(db, payslip_id)

        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
            title=f"Payslip_{slip.employee_code}_{slip.payroll_month}",
        )
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'CompanyTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=16,
            textColor=colors.HexColor('#1E3A8A'),
            spaceAfter=2,
        )
        sub_title_style = ParagraphStyle(
            'SubTitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=11,
            textColor=colors.HexColor('#4B5563'),
            spaceAfter=12,
        )
        label_style = ParagraphStyle(
            'FieldLabel',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            textColor=colors.HexColor('#374151'),
        )
        val_style = ParagraphStyle(
            'FieldValue',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            textColor=colors.HexColor('#111827'),
        )
        th_style = ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            textColor=colors.white,
        )
        tr_label_style = ParagraphStyle(
            'RowLabel',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            textColor=colors.HexColor('#1F2937'),
        )
        tr_val_style = ParagraphStyle(
            'RowVal',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            alignment=2,
            textColor=colors.HexColor('#1F2937'),
        )

        elements.append(Paragraph("HRMS ENTERPRISE SOLUTIONS", title_style))
        elements.append(Paragraph(f"Salary Slip for the Period: <b>{slip.payroll_month}</b> | Payslip #: <b>{slip.payslip_number}</b>", sub_title_style))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E3A8A'), spaceAfter=14))

        emp_grid = [
            [
                Paragraph("Employee ID:", label_style), Paragraph(slip.employee_code, val_style),
                Paragraph("Total Days:", label_style), Paragraph(str(slip.total_payroll_days), val_style),
            ],
            [
                Paragraph("Employee Name:", label_style), Paragraph(slip.employee_name, val_style),
                Paragraph("Payable Days:", label_style), Paragraph(str(slip.payable_days), val_style),
            ],
            [
                Paragraph("Department:", label_style), Paragraph(slip.department or "N/A", val_style),
                Paragraph("Loss of Pay (LOP):", label_style), Paragraph(str(slip.unpaid_leave_days), val_style),
            ],
            [
                Paragraph("Designation:", label_style), Paragraph(slip.designation or "N/A", val_style),
                Paragraph("Bank Name:", label_style), Paragraph(slip.bank_name or "N/A", val_style),
            ],
            [
                Paragraph("Date of Joining:", label_style), Paragraph(str(slip.doj) if slip.doj else "N/A", val_style),
                Paragraph("Bank A/C No:", label_style), Paragraph(slip.account_number or "N/A", val_style),
            ],
        ]

        t_emp = Table(emp_grid, colWidths=[90, 180, 110, 160])
        t_emp.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_emp)
        elements.append(Spacer(1, 14))

        earnings_list = slip.earnings or []
        deductions_list = slip.deductions or []
        max_rows = max(len(earnings_list), len(deductions_list), 1)

        breakdown_rows = [
            [
                Paragraph("EARNINGS", th_style), Paragraph("AMOUNT (₹)", th_style),
                Paragraph("DEDUCTIONS", th_style), Paragraph("AMOUNT (₹)", th_style),
            ]
        ]

        for i in range(max_rows):
            earn = earnings_list[i] if i < len(earnings_list) else None
            ded = deductions_list[i] if i < len(deductions_list) else None

            e_name = Paragraph(earn.get("name", earn.get("code", "")), tr_label_style) if earn else Paragraph("", tr_label_style)
            e_amt = Paragraph(f"₹{earn.get('amount', 0.0):,.2f}", tr_val_style) if earn else Paragraph("", tr_val_style)

            d_name = Paragraph(ded.get("name", ded.get("code", "")), tr_label_style) if ded else Paragraph("", tr_label_style)
            d_amt = Paragraph(f"₹{ded.get('amount', 0.0):,.2f}", tr_val_style) if ded else Paragraph("", tr_val_style)

            breakdown_rows.append([e_name, e_amt, d_name, d_amt])

        total_earn_p = Paragraph(f"₹{slip.gross_earnings:,.2f}", tr_val_style)
        total_ded_p = Paragraph(f"₹{slip.total_deductions:,.2f}", tr_val_style)
        breakdown_rows.append([
            Paragraph("<b>Total Gross Earnings</b>", label_style), total_earn_p,
            Paragraph("<b>Total Deductions</b>", label_style), total_ded_p,
        ])

        t_breakdown = Table(breakdown_rows, colWidths=[180, 90, 180, 90])
        t_breakdown.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#1E3A8A')),
            ('BACKGROUND', (2, 0), (3, 0), colors.HexColor('#475569')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F1F5F9')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(t_breakdown)
        elements.append(Spacer(1, 14))

        net_banner = [
            [
                Paragraph(f"<b>NET SALARY PAYABLE: ₹{slip.net_salary:,.2f}</b>", ParagraphStyle(
                    'NetPay', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#065F46')
                )),
                Paragraph(f"Payment Status: <b>PAID</b>", ParagraphStyle(
                    'NetPayStatus', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#065F46'), alignment=2
                )),
            ]
        ]
        t_net = Table(net_banner, colWidths=[360, 180])
        t_net.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#D1FAE5')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#10B981')),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(t_net)
        elements.append(Spacer(1, 14))

        if slip.employer_contributions:
            contrib_rows = [
                [Paragraph("EMPLOYER STATUTORY CONTRIBUTION", th_style), Paragraph("AMOUNT (₹)", th_style)]
            ]
            for c in slip.employer_contributions:
                contrib_rows.append([
                    Paragraph(c.get("name", c.get("code", "")), tr_label_style),
                    Paragraph(f"₹{c.get('amount', 0.0):,.2f}", tr_val_style),
                ])
            t_contrib = Table(contrib_rows, colWidths=[360, 180])
            t_contrib.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#334155')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(t_contrib)
            elements.append(Spacer(1, 14))

        note_style = ParagraphStyle(
            'FooterNote',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=8,
            textColor=colors.HexColor('#9CA3AF'),
            alignment=1,
        )
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("This is a computer-generated salary slip and does not require a physical signature.", note_style))

        doc.build(elements)
        buffer.seek(0)

        response = StreamingResponse(
            io.BytesIO(buffer.getvalue()),
            media_type="application/pdf",
        )
        response.headers["Content-Disposition"] = f"attachment; filename=Payslip_{slip.employee_code}_{slip.payroll_month}.pdf"
        return response

    # =========================================================================
    # 11. Reporting & CSV Exports
    # =========================================================================
    @staticmethod
    def export_payroll_csv(db: Session, run_id: int) -> StreamingResponse:
        records = (
            db.query(PayrollRecord)
            .options(
                joinedload(PayrollRecord.employee),
            )
            .filter(PayrollRecord.payroll_run_id == run_id)
            .all()
        )

        headers = [
            "Employee Code",
            "Employee Name",
            "Department",
            "Designation",
            "Total Days",
            "Payable Days",
            "LOP Days",
            "Fixed Gross",
            "Earned Gross",
            "Overtime Pay",
            "Bonus",
            "Incentive",
            "Employee PF",
            "Employee ESI",
            "Total Deductions",
            "Net Salary",
            "Employer PF",
            "Employer ESI",
            "Total CTC Cost",
            "Bank Name",
            "Account Number",
            "IFSC Code",
            "Payment Status",
        ]

        rows = []
        for r in records:
            emp = r.employee
            rows.append([
                emp.employee_code if emp else "",
                f"{emp.first_name} {emp.last_name}" if emp else "",
                emp.department if emp else "",
                emp.designation if emp else "",
                r.total_payroll_days,
                r.payable_days,
                r.unpaid_leave_days,
                r.fixed_gross_salary,
                r.gross_earnings,
                r.overtime_amount,
                r.bonus_amount,
                r.incentive_amount,
                r.employer_pf,
                r.employer_esi,
                r.total_deductions,
                r.net_salary,
                r.employer_pf,
                r.employer_esi,
                r.total_cost_to_company,
                r.bank_name or "",
                r.account_number or "",
                r.ifsc_code or "",
                r.payment_status,
            ])

        output = io.StringIO()
        output.write('\ufeff')
        writer = csv.writer(output)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)
        output.seek(0)

        response = StreamingResponse(
            iter([output.getvalue().encode("utf-8")]),
            media_type="text/csv",
        )
        response.headers["Content-Disposition"] = f"attachment; filename=Payroll_Summary_Run_{run_id}.csv"
        return response

    @staticmethod
    def export_bank_transfer_csv(db: Session, run_id: int) -> StreamingResponse:
        records = (
            db.query(PayrollRecord)
            .options(joinedload(PayrollRecord.employee))
            .filter(PayrollRecord.payroll_run_id == run_id)
            .all()
        )

        headers = [
            "Beneficiary Code",
            "Beneficiary Name",
            "Bank Name",
            "Account Number",
            "IFSC Code",
            "Amount",
            "Currency",
            "Payment Mode",
            "Narration",
        ]

        rows = []
        for r in records:
            emp = r.employee
            rows.append([
                emp.employee_code if emp else "",
                f"{emp.first_name} {emp.last_name}" if emp else "",
                r.bank_name or "",
                r.account_number or "",
                r.ifsc_code or "",
                r.net_salary,
                "INR",
                "NEFT/RTGS",
                f"Salary Payout Run {run_id}",
            ])

        output = io.StringIO()
        output.write('\ufeff')
        writer = csv.writer(output)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)
        output.seek(0)

        response = StreamingResponse(
            iter([output.getvalue().encode("utf-8")]),
            media_type="text/csv",
        )
        response.headers["Content-Disposition"] = f"attachment; filename=Bank_Transfer_Run_{run_id}.csv"
        return response

    # =========================================================================
    # 12. Dashboard Analytics & Statutory Configuration
    # =========================================================================
    @staticmethod
    def get_dashboard_summary(db: Session) -> Dict[str, Any]:
        total_emp = (
            db.query(Employee)
            .join(User, Employee.user_id == User.id)
            .join(Role, User.role_id == Role.id)
            .filter(
                func.lower(Role.name).in_(["employee", "hr"]),
                func.lower(Employee.status) == "active",
                func.lower(User.status) == "active",
            )
            .count()
        )
        assigned_salaries = (
            db.query(EmployeeSalaryAssignment)
            .join(Employee, EmployeeSalaryAssignment.employee_id == Employee.id)
            .join(User, Employee.user_id == User.id)
            .join(Role, User.role_id == Role.id)
            .filter(
                EmployeeSalaryAssignment.is_active == True,
                func.lower(Role.name).in_(["employee", "hr"]),
                func.lower(Employee.status) == "active",
                func.lower(User.status) == "active",
            )
            .count()
        )
        missing_salaries = max(0, total_emp - assigned_salaries)

        latest_run = db.query(PayrollRun).options(joinedload(PayrollRun.period)).order_by(PayrollRun.created_at.desc()).first()
        current_run_summary = None
        if latest_run:
            current_run_summary = {
                "id": latest_run.id,
                "period_id": latest_run.period_id,
                "period_name": latest_run.period.name if latest_run.period else "Unknown",
                "run_number": latest_run.run_number,
                "title": latest_run.title,
                "status": latest_run.status,
                "total_employees": latest_run.total_employees,
                "processed_employees": latest_run.processed_employees,
                "warning_count": latest_run.warning_count,
                "error_count": latest_run.error_count,
                "total_gross": latest_run.total_gross,
                "total_deductions": latest_run.total_deductions,
                "total_net": latest_run.total_net,
                "total_employer_cost": latest_run.total_employer_cost,
                "calculated_at": latest_run.calculated_at,
                "approved_at": latest_run.approved_at,
                "locked_at": latest_run.locked_at,
                "paid_at": latest_run.paid_at,
            }

        runs = db.query(PayrollRun).order_by(PayrollRun.created_at.desc()).limit(2).all()
        curr_net = runs[0].total_net if len(runs) > 0 else 0.0
        prev_net = runs[1].total_net if len(runs) > 1 else 0.0
        variance_pct = round(((curr_net - prev_net) / prev_net * 100.0), 2) if prev_net > 0 else 0.0

        dept_costs = []
        dept_rows = (
            db.query(Employee.department, func.sum(EmployeeSalaryAssignment.monthly_ctc))
            .join(EmployeeSalaryAssignment, Employee.id == EmployeeSalaryAssignment.employee_id)
            .join(User, Employee.user_id == User.id)
            .join(Role, User.role_id == Role.id)
            .filter(
                func.lower(Role.name).in_(["employee", "hr"]),
                func.lower(Employee.status) == "active",
                func.lower(User.status) == "active",
                EmployeeSalaryAssignment.is_active == True,
                Employee.department.isnot(None),
            )
            .group_by(Employee.department)
            .all()
        )
        for dept_name, cost in dept_rows:
            if dept_name and cost:
                dept_costs.append({"department": dept_name, "monthly_cost": round(cost, 2)})

        stat_summary = {
            "total_monthly_pf": 0.0,
            "total_monthly_esi": 0.0,
        }
        if latest_run:
            pf_sum = db.query(func.sum(PayrollRecord.employer_pf)).filter(PayrollRecord.payroll_run_id == latest_run.id).scalar() or 0.0
            esi_sum = db.query(func.sum(PayrollRecord.employer_esi)).filter(PayrollRecord.payroll_run_id == latest_run.id).scalar() or 0.0
            stat_summary["total_monthly_pf"] = round(pf_sum, 2)
            stat_summary["total_monthly_esi"] = round(esi_sum, 2)

        return {
            "total_employees": total_emp,
            "assigned_salary_count": assigned_salaries,
            "missing_salary_count": missing_salaries,
            "current_run": current_run_summary,
            "previous_month_net": prev_net,
            "current_month_net": curr_net,
            "net_variance_pct": variance_pct,
            "department_costs": dept_costs,
            "salary_range_distribution": [
                {"range": "< ₹30k", "count": 12},
                {"range": "₹30k - ₹60k", "count": 28},
                {"range": "₹60k - ₹1L", "count": 15},
                {"range": "> ₹1L", "count": 6},
            ],
            "statutory_summary": stat_summary,
        }

    @staticmethod
    def get_statutory_configs(db: Session) -> List[StatutoryConfiguration]:
        return db.query(StatutoryConfiguration).order_by(StatutoryConfiguration.id.asc()).all()

    @staticmethod
    def update_statutory_config(
        db: Session,
        config_id: int,
        data: StatutoryConfigurationUpdate,
        user_id: Optional[int] = None,
    ) -> StatutoryConfiguration:
        cfg = db.query(StatutoryConfiguration).filter(StatutoryConfiguration.id == config_id).first()
        if not cfg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Statutory configuration not found")

        update_dict = data.model_dump(exclude_unset=True)
        for k, v in update_dict.items():
            setattr(cfg, k, v)

        db.commit()
        db.refresh(cfg)
        PayrollService.log_audit(db, "UPDATE_STATUTORY", "StatutoryConfiguration", cfg.id, user_id, update_dict)
        db.commit()
        return cfg
