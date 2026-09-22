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

        if data.code is not None and data.code.strip():
            new_code = data.code.strip().upper()
            existing = db.query(SalaryStructure).filter(
                SalaryStructure.code == new_code,
                SalaryStructure.id != structure_id
            ).first()
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Structure code '{new_code}' already exists")
            structure.code = new_code

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
        PayrollService.log_audit(db, "UPDATE", "SalaryStructure", structure.id, user_id, {"id": structure.id, "code": structure.code})
        db.commit()
        return PayrollService.get_structure(db, structure.id)

    @staticmethod
    def delete_structure(db: Session, structure_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        structure = PayrollService.get_structure(db, structure_id)

        # Check if structure is in use by any employee salary assignments
        assignment_count = db.query(EmployeeSalaryAssignment).filter(
            EmployeeSalaryAssignment.salary_structure_id == structure_id
        ).count()
        if assignment_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete structure '{structure.name}'. It is currently assigned to {assignment_count} employee(s). Consider deactivating it instead."
            )

        # Check if structure is in use by any salary revisions
        revision_count = db.query(SalaryRevision).filter(
            SalaryRevision.new_salary_structure_id == structure_id
        ).count()
        if revision_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete structure '{structure.name}'. It is referenced in {revision_count} salary revision(s)."
            )

        db.delete(structure)
        db.commit()
        PayrollService.log_audit(db, "DELETE", "SalaryStructure", structure_id, user_id, {"code": structure.code, "name": structure.name})
        db.commit()
        return {"message": f"Salary structure '{structure.name}' deleted successfully", "id": structure_id}


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

            snapshot_data = calc_result.get("calculation_snapshot") or {}
            if isinstance(snapshot_data, dict):
                snapshot_data.setdefault("pan", getattr(emp, "pan_number", None) or getattr(emp, "pan", None))
                snapshot_data.setdefault("pf_uan", getattr(emp, "uan_number", None) or getattr(emp, "uan", None))
                snapshot_data.setdefault("pf_no", getattr(emp, "pf_number", None) or getattr(emp, "pf_no", None))
                snapshot_data.setdefault("bank_micr", getattr(emp, "micr_code", None))
                snapshot_data.setdefault("gender", getattr(emp, "gender", None))
                snapshot_data.setdefault("dob", emp.dob.isoformat() if getattr(emp, "dob", None) else None)
                snapshot_data.setdefault("doj", emp.doj.isoformat() if getattr(emp, "doj", None) else None)
                snapshot_data.setdefault("work_location", getattr(emp, "work_location", None))

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
                calculation_snapshot=snapshot_data,
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
            {"payment_status": "PAID"}
        )
        db.commit()

        PayrollService.log_audit(db, "MARK_PAID", "PayrollRun", run.id, user_id)
        db.commit()
        return {"message": "Payroll run and all associated records marked as PAID", "status": run.status}

    @staticmethod
    def delete_payroll_run(db: Session, run_id: int, user_id: int) -> Dict[str, Any]:
        run = db.query(PayrollRun).options(joinedload(PayrollRun.period)).filter(PayrollRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payroll run not found")
        if run.status == "PAID":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete a PAID payroll run. Processed disbursements must be retained for compliance."
            )

        period = run.period
        period_id = run.period_id
        run_number = run.run_number

        # 1. Gather all record IDs for this run
        records = db.query(PayrollRecord).filter(PayrollRecord.payroll_run_id == run.id).all()
        record_ids = [rec.id for rec in records]

        if record_ids:
            # Delete payslips associated with these records
            db.query(Payslip).filter(Payslip.payroll_record_id.in_(record_ids)).delete(synchronize_session=False)
            # Delete adjustments
            db.query(PayrollAdjustment).filter(PayrollAdjustment.payroll_record_id.in_(record_ids)).delete(synchronize_session=False)
            # Delete record line items
            db.query(PayrollRecordItem).filter(PayrollRecordItem.record_id.in_(record_ids)).delete(synchronize_session=False)
            # Delete payroll records
            db.query(PayrollRecord).filter(PayrollRecord.id.in_(record_ids)).delete(synchronize_session=False)

        # Delete exceptions
        db.query(PayrollException).filter(PayrollException.payroll_run_id == run.id).delete(synchronize_session=False)

        # Delete the run itself
        db.delete(run)
        db.commit()

        # Update period status if applicable
        if period:
            remaining_runs = db.query(PayrollRun).filter(PayrollRun.period_id == period_id).all()
            if not remaining_runs:
                period.status = "OPEN"
            elif any(r.status == "PAID" for r in remaining_runs):
                period.status = "PAID"
            elif any(r.status == "LOCKED" for r in remaining_runs):
                period.status = "LOCKED"
            elif any(r.status in ["PROCESSING", "APPROVED", "UNDER_REVIEW"] for r in remaining_runs):
                period.status = "PROCESSING"
            else:
                period.status = "OPEN"
            db.commit()

        PayrollService.log_audit(db, "DELETE_RUN", "PayrollRun", run_id, user_id, {"run_number": run_number})
        db.commit()

        return {"message": f"Payroll run #{run_number} deleted successfully", "run_number": run_number}

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

    @staticmethod
    def resolve_all_exceptions(db: Session, run_id: int, resolution_notes: str, user_id: int) -> Dict[str, Any]:
        unresolved = (
            db.query(PayrollException)
            .filter(
                PayrollException.payroll_run_id == run_id,
                PayrollException.is_resolved == False,
            )
            .all()
        )
        count = len(unresolved)
        for exc in unresolved:
            exc.is_resolved = True
            exc.resolution_notes = resolution_notes
            exc.resolved_by = user_id

        db.commit()
        PayrollService.log_audit(db, "RESOLVE_ALL_EXCEPTIONS", "PayrollRun", run_id, user_id, {"count": count, "notes": resolution_notes})
        db.commit()
        return {"message": f"Successfully resolved {count} exceptions", "resolved_count": count}

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
    def _get_logo_path():
        import os
        candidates = [
            os.path.join(os.path.dirname(__file__), "..", "assets", "Logo.png"),
            os.path.abspath("backend/app/assets/Logo.png"),
            os.path.abspath("frontend/src/assets/Logo.png"),
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend", "src", "assets", "Logo.png"),
        ]
        for c in candidates:
            if os.path.exists(c):
                return os.path.abspath(c)
        return None

    @staticmethod
    def _get_tight_logo_path() -> Optional[str]:
        """Returns path to tightly-cropped logo (without surrounding blank padding)."""
        import os
        logo_path = PayrollService._get_logo_path()
        if not logo_path or not os.path.exists(logo_path):
            return None
        tight_path = os.path.join(os.path.dirname(logo_path), "Logo_tight.png")
        try:
            if not os.path.exists(tight_path) or os.path.getmtime(logo_path) > os.path.getmtime(tight_path):
                from PIL import Image as PILImage
                with PILImage.open(logo_path) as im:
                    im_rgba = im.convert("RGBA")
                    bbox = im_rgba.getbbox()
                    cropped = im_rgba.crop(bbox) if bbox else im_rgba
                    cropped.save(tight_path, "PNG")
            return tight_path
        except Exception:
            return logo_path

    @staticmethod
    def _get_watermark_path() -> Optional[str]:
        """
        Returns path to a color-calibrated watermark image with authentic company blue
        colors and 16% opacity baked into its alpha channel for perfect reproduction.
        """
        import os
        logo_path = PayrollService._get_logo_path()
        if not logo_path or not os.path.exists(logo_path):
            return None
        wm_path = os.path.join(os.path.dirname(logo_path), "Logo_watermark.png")
        try:
            if not os.path.exists(wm_path) or os.path.getmtime(logo_path) > os.path.getmtime(wm_path):
                from PIL import Image as PILImage
                with PILImage.open(logo_path) as im:
                    im_rgba = im.convert("RGBA")
                    bbox = im_rgba.getbbox()
                    cropped = im_rgba.crop(bbox) if bbox else im_rgba
                    r, g, b, a = cropped.split()
                    # 16% alpha preserves perfect corporate blue color while staying elegant in background
                    new_a = a.point(lambda p: int(p * 0.16))
                    wm_img = PILImage.merge("RGBA", (r, g, b, new_a))
                    wm_img.save(wm_path, "PNG")
            return wm_path
        except Exception:
            return logo_path

    @staticmethod
    def _get_company_logo(max_width=95, max_height=48, width=None, height=None):
        import os
        from reportlab.platypus import Image, Paragraph
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib import colors

        logo_path = PayrollService._get_tight_logo_path() or PayrollService._get_logo_path()
        if logo_path:
            try:
                from PIL import Image as PILImage
                with PILImage.open(logo_path) as pil_img:
                    orig_w, orig_h = pil_img.size
                aspect = orig_w / float(orig_h)

                target_h = height or max_height
                target_w = target_h * aspect
                if target_w > (width or max_width):
                    target_w = width or max_width
                    target_h = target_w / aspect

                img = Image(logo_path, width=target_w, height=target_h)
                img.hAlign = 'LEFT'
                return img
            except Exception:
                try:
                    img = Image(logo_path, width=68, height=48)
                    img.hAlign = 'LEFT'
                    return img
                except Exception:
                    pass
        return Paragraph("<b>AIVAN 360</b><br/><font size=7 color='#64748B'>SOLUTIONS</font>", ParagraphStyle('LogoFallback', fontSize=12, leading=14, textColor=colors.HexColor('#1E3A8A')))

    @staticmethod
    def _number_to_words_indian(num: float | int) -> str:
        n = int(round(num))
        if n == 0:
            return "zero only"

        ones = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
                "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
                "seventeen", "eighteen", "nineteen"]
        tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

        def two_digits(num_val: int) -> str:
            if num_val < 20:
                return ones[num_val]
            else:
                t = tens[num_val // 10]
                o = ones[num_val % 10]
                return f"{t}-{o}".strip("-") if o else t

        def three_digits(num_val: int) -> str:
            h = num_val // 100
            rem = num_val % 100
            parts = []
            if h > 0:
                parts.append(f"{ones[h]} hundred")
            if rem > 0:
                if parts:
                    parts.append("and")
                parts.append(two_digits(rem))
            return " ".join(parts)

        parts = []
        crore = n // 10000000
        n %= 10000000
        lakh = n // 100000
        n %= 100000
        thousand = n // 1000
        n %= 1000
        remainder = n

        if crore > 0:
            parts.append(f"{two_digits(crore)} crore")
        if lakh > 0:
            parts.append(f"{two_digits(lakh)} lakh")
        if thousand > 0:
            parts.append(f"{two_digits(thousand)} thousand")
        if remainder > 0:
            parts.append(three_digits(remainder))

        words = " ".join(parts).strip()
        if not words:
            return "Zero only"
        return words[0].upper() + words[1:] + " only"

    @staticmethod
    def generate_payslip_pdf(db: Session, payslip_id: int) -> StreamingResponse:
        slip = PayrollService.get_payslip_detail(db, payslip_id)

        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=35,
            leftMargin=35,
            topMargin=32,
            bottomMargin=32,
            title=f"Payslip_{slip.employee_code}_{slip.payroll_month}",
        )
        elements = []
        styles = getSampleStyleSheet()

        # Styles matching official corporate template
        label_style = ParagraphStyle(
            'FieldLabel',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#0F172A'),
        )
        val_style = ParagraphStyle(
            'FieldValue',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#1E293B'),
        )
        center_bold_style = ParagraphStyle(
            'CenterBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8.5,
            leading=11,
            alignment=1,
            textColor=colors.HexColor('#0F172A'),
        )
        left_bold_style = ParagraphStyle(
            'LeftBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#0F172A'),
        )
        right_bold_style = ParagraphStyle(
            'RightBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            alignment=2,
            textColor=colors.HexColor('#0F172A'),
        )
        cell_left_style = ParagraphStyle(
            'CellLeft',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#1E293B'),
        )
        cell_right_style = ParagraphStyle(
            'CellRight',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            alignment=2,
            textColor=colors.HexColor('#1E293B'),
        )

        # 1. Corporate Header with Proportional Logo & Centered Company Details
        logo_flowable = PayrollService._get_company_logo(max_width=85, max_height=52)

        # Format payroll month to human-readable month name & year (e.g. "2026-11" -> "November 2026")
        month_display = str(slip.payroll_month or "—")
        if slip.payroll_month:
            try:
                from datetime import datetime as dt
                m_str = str(slip.payroll_month).strip()
                if len(m_str) == 7 and "-" in m_str:
                    month_display = dt.strptime(m_str, "%Y-%m").strftime("%B %Y")
                elif len(m_str) >= 10 and "-" in m_str:
                    month_display = dt.strptime(m_str[:10], "%Y-%m-%d").strftime("%B %Y")
            except Exception:
                month_display = str(slip.payroll_month)

        if (not month_display or month_display == "—" or ("-" in month_display and len(month_display) <= 7)) and slip.record and slip.record.payroll_run and slip.record.payroll_run.period:
            try:
                import calendar
                p = slip.record.payroll_run.period
                month_display = f"{calendar.month_name[p.month]} {p.year}"
            except Exception:
                pass

        header_text = (
            "<para align='center' leading='13'>"
            "<font size=13 fontName='Helvetica-Bold' color='#475569'><b>AIVAN 360 SOLUTIONS PRIVATE LIMITED</b></font><br/>"
            "<font size=8 fontName='Helvetica' color='#64748B'>2863, Devtal Road, Near Rani Durgawati Ward, Garha,Jabalpur- 482003</font><br/>"
            "<font size=8 fontName='Helvetica-Bold' color='#64748B'>MADHYA PRADESH</font><br/><br/>"
            f"<font size=9.5 fontName='Helvetica-Bold' color='#374151'>Pay Slip for the month of {month_display}</font><br/>"
            "<font size=8.5 fontName='Helvetica-Bold' color='#4B5563'>All amounts are in INR</font>"
            "</para>"
        )
        t_header = Table(
            [[logo_flowable, Paragraph(header_text, styles['Normal']), ""]],
            colWidths=[85, 355, 85]
        )
        t_header.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_header)
        elements.append(Spacer(1, 10))

        # 2. Employee Metadata Box (2-column info grid matching the user template)
        emp = slip.employee
        rec = slip.record

        emp_code = slip.employee_code or "—"
        emp_name = slip.employee_name or "—"
        department = slip.department or "—"
        designation = slip.designation or "—"
        snapshot = rec.calculation_snapshot if (rec and isinstance(rec.calculation_snapshot, dict)) else {}

        gender = (emp.gender if (emp and emp.gender) else (snapshot.get("gender") or "—"))
        if emp and emp.dob:
            dob_str = emp.dob.strftime("%d %B %Y")
        elif snapshot.get("dob"):
            try:
                from datetime import datetime as dt
                dob_str = dt.strptime(str(snapshot["dob"])[:10], "%Y-%m-%d").strftime("%d %B %Y")
            except Exception:
                dob_str = str(snapshot["dob"])
        else:
            dob_str = "—"

        if emp and emp.doj:
            doj_str = emp.doj.strftime("%d %B %Y")
        elif slip.doj:
            doj_str = slip.doj.strftime("%d %B %Y")
        elif snapshot.get("doj"):
            try:
                from datetime import datetime as dt
                doj_str = dt.strptime(str(snapshot["doj"])[:10], "%Y-%m-%d").strftime("%d %B %Y")
            except Exception:
                doj_str = str(snapshot["doj"])
        else:
            doj_str = "—"

        payable_days_str = f"{slip.payable_days:.2f}"
        lop_str = f"{slip.unpaid_leave_days:.2f}"

        location_str = (emp.work_location if (emp and emp.work_location) else (snapshot.get("work_location") or "Main Office"))
        b_name = slip.bank_name or (emp.bank_name if emp else None)
        b_acc = slip.account_number or (emp.bank_account_no if emp else None)
        bank_acc_str = f"{b_acc} ({b_name})" if (b_acc and b_name) else (b_acc or b_name or "—")

        pan_str = snapshot.get("pan") or getattr(emp, "pan_number", None) or getattr(emp, "pan_card_number", None) or getattr(emp, "pan", None) or "—"
        pf_uan_str = snapshot.get("pf_uan") or getattr(emp, "uan_number", None) or getattr(emp, "uan", None) or "—"
        pf_no_str = snapshot.get("pf_no") or getattr(emp, "pf_number", None) or getattr(emp, "pf_no", None) or "—"
        bank_micr_str = snapshot.get("bank_micr") or getattr(emp, "micr_code", None) or "—"

        emp_info_data = [
            [Paragraph("<b>Emp Code</b>", label_style), ":", Paragraph(emp_code, val_style),
             Paragraph("<b>Location</b>", label_style), ":", Paragraph(location_str, val_style)],
            [Paragraph("<b>Emp Name</b>", label_style), ":", Paragraph(emp_name, val_style),
             Paragraph("<b>Bank/MICR</b>", label_style), ":", Paragraph(bank_micr_str, val_style)],
            [Paragraph("<b>Department</b>", label_style), ":", Paragraph(department, val_style),
             Paragraph("<b>Bank A/c No.</b>", label_style), ":", Paragraph(bank_acc_str, val_style)],
            [Paragraph("<b>Designation</b>", label_style), ":", Paragraph(designation, val_style),
             "", "", ""],
            [Paragraph("<b>Gender</b>", label_style), ":", Paragraph(gender, val_style),
             Paragraph("<b>PAN</b>", label_style), ":", Paragraph(pan_str, val_style)],
            [Paragraph("<b>DOB</b>", label_style), ":", Paragraph(dob_str, val_style),
             Paragraph("<b>PF No.</b>", label_style), ":", Paragraph(pf_no_str, val_style)],
            [Paragraph("<b>DOJ</b>", label_style), ":", Paragraph(doj_str, val_style),
             Paragraph("<b>PF UAN.</b>", label_style), ":", Paragraph(pf_uan_str, val_style)],
            [Paragraph("<b>Payable Days</b>", label_style), ":", Paragraph(payable_days_str, val_style),
             "", "", ""],
            [Paragraph("<b>L.O. P</b>", label_style), ":", Paragraph(lop_str, val_style),
             "", "", ""],
        ]

        t_emp_info = Table(emp_info_data, colWidths=[80, 12, 170.5, 80, 12, 170.5])
        t_emp_info.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#334155')),
            ('LINEBEFORE', (3, 0), (3, -1), 0.75, colors.HexColor('#334155')),
            ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#CBD5E1')),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('ALIGN', (4, 0), (4, -1), 'CENTER'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ('FONTNAME', (4, 0), (4, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (1, 0), (1, -1), 8),
            ('FONTSIZE', (4, 0), (4, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(t_emp_info)

        # 3. Earnings & Deductions Table
        earnings_list = slip.earnings or []
        deductions_list = slip.deductions or []

        if not earnings_list and snapshot.get("items"):
            earnings_list = [it for it in snapshot["items"] if it.get("component_type") == "EARNING"]
            deductions_list = [it for it in snapshot["items"] if it.get("component_type") == "DEDUCTION"]

        def fmt_amt(val: float | None) -> str:
            if val is None or val == 0:
                return ""
            if abs(val - round(val)) < 0.001:
                return f"{int(round(val))}"
            return f"{val:,.2f}"

        max_rows = max(len(earnings_list), len(deductions_list), 3)

        table_data = [
            # Header Row 1
            [
                Paragraph("<b>Earnings</b>", center_bold_style), "",
                Paragraph("<b>Deductions</b>", center_bold_style), ""
            ],
            # Header Row 2
            [
                Paragraph("<b>Description</b>", left_bold_style),
                Paragraph("<b>Amount (Monthly)</b>", right_bold_style),
                Paragraph("<b>Description</b>", left_bold_style),
                Paragraph("<b>Amount</b>", right_bold_style),
            ]
        ]

        for i in range(max_rows):
            earn = earnings_list[i] if i < len(earnings_list) else None
            ded = deductions_list[i] if i < len(deductions_list) else None

            e_name = Paragraph(earn.get("name", earn.get("code", "")), cell_left_style) if earn else Paragraph("", cell_left_style)
            e_amt = Paragraph(fmt_amt(earn.get("amount", 0.0)), cell_right_style) if earn else Paragraph("", cell_right_style)

            d_name = Paragraph(ded.get("name", ded.get("code", "")), cell_left_style) if ded else Paragraph("", cell_left_style)
            d_amt = Paragraph(fmt_amt(ded.get("amount", 0.0)), cell_right_style) if ded else Paragraph("", cell_right_style)

            table_data.append([e_name, e_amt, d_name, d_amt])

        # Blank padding separator row
        table_data.append([Paragraph("", cell_left_style), Paragraph("", cell_right_style), Paragraph("", cell_left_style), Paragraph("", cell_right_style)])

        # Totals Row
        gross_earn_str = fmt_amt(slip.gross_earnings)
        gross_ded_str = fmt_amt(slip.total_deductions)
        table_data.append([
            Paragraph("<b>GROSS EARNINGS</b>", left_bold_style),
            Paragraph(f"<b>{gross_earn_str}</b>", right_bold_style),
            Paragraph("<b>GROSS DEDUCTIONS</b>", left_bold_style),
            Paragraph(f"<b>{gross_ded_str}</b>", right_bold_style),
        ])

        # Net Pay Row (spanned across all 4 cols)
        net_amt_str = fmt_amt(slip.net_salary)
        net_words = PayrollService._number_to_words_indian(slip.net_salary)
        net_text = f"<b>Net Pay: {net_amt_str} ({net_words})</b>"
        table_data.append([Paragraph(net_text, center_bold_style), "", "", ""])

        t_breakdown = Table(table_data, colWidths=[182.5, 80, 182.5, 80])
        t_breakdown.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#1E293B')),
            ('SPAN', (0, 0), (1, 0)),
            ('SPAN', (2, 0), (3, 0)),
            ('SPAN', (0, -1), (3, -1)),
            ('LINEBELOW', (0, 0), (-1, 0), 0.75, colors.HexColor('#1E293B')),
            ('LINEBELOW', (0, 1), (-1, 1), 0.75, colors.HexColor('#1E293B')),
            ('LINEAFTER', (1, 0), (1, -2), 0.75, colors.HexColor('#1E293B')),
            ('LINEBEFORE', (1, 1), (1, -2), 0.4, colors.HexColor('#CBD5E1')),
            ('LINEBEFORE', (3, 1), (3, -2), 0.4, colors.HexColor('#CBD5E1')),
            ('LINEABOVE', (0, -2), (-1, -2), 0.75, colors.HexColor('#1E293B')),
            ('LINEABOVE', (0, -1), (-1, -1), 0.75, colors.HexColor('#1E293B')),
            ('TOPPADDING', (0, 0), (-1, -1), 2.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(t_breakdown)
        elements.append(Spacer(1, 12))

        # 4. Official System Disclaimer
        disc_style = ParagraphStyle(
            'Disclaimer',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            textColor=colors.HexColor('#111827'),
        )
        elements.append(Paragraph("<b>Disclaimer: This is a system generated payslip, does not require any signature.</b>", disc_style))

        def draw_watermark(canvas, document):
            import os
            wm_path = PayrollService._get_watermark_path()
            if not wm_path or not os.path.exists(wm_path):
                return
            canvas.saveState()
            try:
                page_w, page_h = document.pagesize
                aspect_ratio = 1.4327
                try:
                    from PIL import Image as PILImage
                    with PILImage.open(wm_path) as img:
                        orig_w, orig_h = img.size
                        if orig_h > 0:
                            aspect_ratio = orig_w / float(orig_h)
                except Exception:
                    pass

                # Large, vibrant watermark spanning virtually the full page width
                wm_width = min(page_w - 24.0, 565.0)
                wm_height = wm_width / aspect_ratio
                if wm_height > page_h * 0.85:
                    wm_height = page_h * 0.85
                    wm_width = wm_height * aspect_ratio

                x = (page_w - wm_width) / 2.0
                y = (page_h - wm_height) / 2.0
                canvas.drawImage(
                    wm_path,
                    x, y,
                    width=wm_width,
                    height=wm_height,
                    mask='auto',
                    preserveAspectRatio=True
                )
            except Exception:
                pass
            finally:
                canvas.restoreState()

        doc.build(elements, onFirstPage=draw_watermark, onLaterPages=draw_watermark)
        buffer.seek(0)

        response = StreamingResponse(
            io.BytesIO(buffer.getvalue()),
            media_type="application/pdf",
        )
        response.headers["Content-Disposition"] = f"attachment; filename=Payslip_{slip.employee_code}_{slip.payroll_month}.pdf"
        return response

    # =========================================================================
    # 11. Reporting & PDF Exports
    # =========================================================================
    @staticmethod
    def export_payroll_pdf(db: Session, run_id: int) -> StreamingResponse:
        run = db.query(PayrollRun).options(joinedload(PayrollRun.period)).filter(PayrollRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payroll run not found")

        records = (
            db.query(PayrollRecord)
            .options(joinedload(PayrollRecord.employee))
            .filter(PayrollRecord.payroll_run_id == run_id)
            .all()
        )

        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
            title=f"Payroll_Summary_{run.run_number}",
        )
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=16,
            textColor=colors.HexColor('#1E3A8A'),
            spaceAfter=2,
        )
        sub_title_style = ParagraphStyle(
            'ReportSubTitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9.5,
            textColor=colors.HexColor('#4B5563'),
            spaceAfter=10,
        )
        card_label_style = ParagraphStyle(
            'CardLabel',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            textColor=colors.HexColor('#64748B'),
            alignment=1,
        )
        card_val_style = ParagraphStyle(
            'CardVal',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            textColor=colors.HexColor('#0F172A'),
            alignment=1,
        )
        th_style = ParagraphStyle(
            'ReportTH',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7.5,
            textColor=colors.white,
            alignment=1,
        )
        td_style = ParagraphStyle(
            'ReportTD',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7.5,
            textColor=colors.HexColor('#1E293B'),
        )
        td_num_style = ParagraphStyle(
            'ReportTDNum',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7.5,
            textColor=colors.HexColor('#1E293B'),
            alignment=2,
        )
        td_bold_num_style = ParagraphStyle(
            'ReportTDBoldNum',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7.5,
            textColor=colors.HexColor('#0F172A'),
            alignment=2,
        )
        td_center_style = ParagraphStyle(
            'ReportTDCenter',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7.5,
            textColor=colors.HexColor('#1E293B'),
            alignment=1,
        )

        logo_flowable = PayrollService._get_company_logo(width=120, height=48)
        period_name = run.period.name if run.period else "N/A"
        header_text = (
            "<para align='center' leading='13'>"
            "<font size=13 fontName='Helvetica-Bold' color='#475569'><b>AIVAN 360 SOLUTIONS PRIVATE LIMITED</b></font><br/>"
            "<font size=8 fontName='Helvetica' color='#64748B'>2863, Devtal Road, Near Rani Durgawati Ward, Garha,Jabalpur- 482003</font><br/>"
            "<font size=8 fontName='Helvetica-Bold' color='#64748B'>MADHYA PRADESH</font><br/><br/>"
            f"<font size=10 fontName='Helvetica-Bold' color='#1E3A8A'>PAYROLL SUMMARY REPORT — {period_name}</font><br/>"
            f"<font size=8 fontName='Helvetica' color='#4B5563'>Payroll Run: <b>#{run.run_number}</b> | Status: <b>{run.status}</b> | Generated: <b>{datetime.now().strftime('%d-%b-%Y %H:%M')}</b></font><br/>"
            "<font size=8 fontName='Helvetica-Bold' color='#4B5563'>All amounts are in INR</font>"
            "</para>"
        )
        t_header = Table(
            [[logo_flowable, Paragraph(header_text, styles['Normal']), ""]],
            colWidths=[120, 480, 120]
        )
        t_header.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_header)
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E3A8A'), spaceAfter=10))

        # KPI Summary Table
        kpi_data = [
            [
                Paragraph("TOTAL EMPLOYEES", card_label_style),
                Paragraph("GROSS PAYOUT", card_label_style),
                Paragraph("TOTAL DEDUCTIONS", card_label_style),
                Paragraph("NET DISBURSEMENT", card_label_style),
                Paragraph("TOTAL CTC EXPENSE", card_label_style),
            ],
            [
                Paragraph(str(run.total_employees), card_val_style),
                Paragraph(f"Rs. {run.total_gross:,.2f}", card_val_style),
                Paragraph(f"Rs. {run.total_deductions:,.2f}", card_val_style),
                Paragraph(f"Rs. {run.total_net:,.2f}", card_val_style),
                Paragraph(f"Rs. {run.total_employer_cost:,.2f}", card_val_style),
            ]
        ]
        t_kpi = Table(kpi_data, colWidths=[144, 144, 144, 144, 144])
        t_kpi.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t_kpi)
        elements.append(Spacer(1, 12))

        # Table Header
        table_data = [
            [
                Paragraph("Emp Code", th_style),
                Paragraph("Employee Name", th_style),
                Paragraph("Department", th_style),
                Paragraph("Payable / Total Days", th_style),
                Paragraph("Fixed Gross (INR)", th_style),
                Paragraph("Earned Gross (INR)", th_style),
                Paragraph("Deductions (INR)", th_style),
                Paragraph("Net Pay (INR)", th_style),
                Paragraph("Status", th_style),
            ]
        ]

        sum_fixed = 0.0
        sum_earned = 0.0
        sum_deductions = 0.0
        sum_net = 0.0

        for r in records:
            emp = r.employee
            sum_fixed += (r.fixed_gross_salary or 0.0)
            sum_earned += (r.gross_earnings or 0.0)
            sum_deductions += (r.total_deductions or 0.0)
            sum_net += (r.net_salary or 0.0)

            emp_name = f"{emp.first_name} {emp.last_name}" if emp else "Unknown"
            table_data.append([
                Paragraph(emp.employee_code if emp else "—", td_style),
                Paragraph(emp_name, td_style),
                Paragraph(emp.department or "—" if emp else "—", td_style),
                Paragraph(f"{r.payable_days} / {r.total_payroll_days}", td_center_style),
                Paragraph(f"Rs. {(r.fixed_gross_salary or 0.0):,.2f}", td_num_style),
                Paragraph(f"Rs. {(r.gross_earnings or 0.0):,.2f}", td_num_style),
                Paragraph(f"Rs. {(r.total_deductions or 0.0):,.2f}", td_num_style),
                Paragraph(f"Rs. {(r.net_salary or 0.0):,.2f}", td_bold_num_style),
                Paragraph(r.payment_status or "PENDING", td_center_style),
            ])

        # Summary Row
        table_data.append([
            Paragraph("TOTAL", th_style),
            Paragraph(f"{len(records)} Employees", th_style),
            Paragraph("", th_style),
            Paragraph("", th_style),
            Paragraph(f"Rs. {sum_fixed:,.2f}", th_style),
            Paragraph(f"Rs. {sum_earned:,.2f}", th_style),
            Paragraph(f"Rs. {sum_deductions:,.2f}", th_style),
            Paragraph(f"Rs. {sum_net:,.2f}", th_style),
            Paragraph("", th_style),
        ])

        col_widths = [65, 120, 85, 80, 80, 80, 75, 85, 50]  # total = 720
        t_records = Table(table_data, colWidths=col_widths, repeatRows=1)
        t_records_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 3.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#334155')),
        ]
        for row_idx in range(1, len(table_data) - 1):
            if row_idx % 2 == 0:
                t_records_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor('#F8FAFC')))
        t_records.setStyle(TableStyle(t_records_style))
        elements.append(t_records)
        elements.append(Spacer(1, 14))

        # Sign-off block
        signoff_data = [
            [
                Paragraph("Prepared By: ___________________", td_style),
                Paragraph("Verified By (HR Head): ___________________", td_style),
                Paragraph("Approved By (Finance Director): ___________________", td_style),
            ]
        ]
        t_sign = Table(signoff_data, colWidths=[240, 240, 240])
        t_sign.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_sign)

        doc.build(elements)
        pdf_bytes = buffer.getvalue()

        response = StreamingResponse(iter([pdf_bytes]), media_type="application/pdf")
        response.headers["Content-Disposition"] = f"attachment; filename=Payroll_Run_{run.run_number}.pdf"
        return response

    @staticmethod
    def export_payroll_csv(db: Session, run_id: int) -> StreamingResponse:
        # Default all exports to PDF per system requirement
        return PayrollService.export_payroll_pdf(db, run_id)

    @staticmethod
    def export_bank_transfer_pdf(db: Session, run_id: int) -> StreamingResponse:
        run = db.query(PayrollRun).options(joinedload(PayrollRun.period)).filter(PayrollRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payroll run not found")

        records = (
            db.query(PayrollRecord)
            .options(joinedload(PayrollRecord.employee))
            .filter(PayrollRecord.payroll_run_id == run_id)
            .all()
        )

        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
            title=f"Bank_Disbursement_{run.run_number}",
        )
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'BankTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=16,
            textColor=colors.HexColor('#0F766E'),
            spaceAfter=2,
        )
        sub_title_style = ParagraphStyle(
            'BankSubTitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9.5,
            textColor=colors.HexColor('#4B5563'),
            spaceAfter=10,
        )
        card_label_style = ParagraphStyle(
            'CardLabel',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            textColor=colors.HexColor('#64748B'),
            alignment=1,
        )
        card_val_style = ParagraphStyle(
            'CardVal',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            textColor=colors.HexColor('#0F172A'),
            alignment=1,
        )
        th_style = ParagraphStyle(
            'ReportTH',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            textColor=colors.white,
            alignment=1,
        )
        td_style = ParagraphStyle(
            'ReportTD',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            textColor=colors.HexColor('#1E293B'),
        )
        td_num_style = ParagraphStyle(
            'ReportTDNum',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            textColor=colors.HexColor('#0F172A'),
            alignment=2,
        )
        td_center_style = ParagraphStyle(
            'ReportTDCenter',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            textColor=colors.HexColor('#1E293B'),
            alignment=1,
        )

        logo_flowable = PayrollService._get_company_logo(width=120, height=48)
        period_name = run.period.name if run.period else "N/A"
        header_text = (
            "<para align='center' leading='13'>"
            "<font size=13 fontName='Helvetica-Bold' color='#475569'><b>AIVAN 360 SOLUTIONS PRIVATE LIMITED</b></font><br/>"
            "<font size=8 fontName='Helvetica' color='#64748B'>2863, Devtal Road, Near Rani Durgawati Ward, Garha,Jabalpur- 482003</font><br/>"
            "<font size=8 fontName='Helvetica-Bold' color='#64748B'>MADHYA PRADESH</font><br/><br/>"
            f"<font size=10 fontName='Helvetica-Bold' color='#0F766E'>BANK SALARY DISBURSEMENT ADVICE — {period_name}</font><br/>"
            f"<font size=8 fontName='Helvetica' color='#4B5563'>Corporate Transfer Mandate | Direct NEFT / RTGS | Run: <b>#{run.run_number}</b></font><br/>"
            "<font size=8 fontName='Helvetica-Bold' color='#4B5563'>All amounts are in INR</font>"
            "</para>"
        )
        t_header = Table(
            [[logo_flowable, Paragraph(header_text, styles['Normal']), ""]],
            colWidths=[120, 480, 120]
        )
        t_header.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_header)
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0F766E'), spaceAfter=10))

        # KPI Box
        kpi_data = [
            [
                Paragraph("TOTAL BENEFICIARIES", card_label_style),
                Paragraph("TOTAL DISBURSEMENT AMOUNT", card_label_style),
                Paragraph("CURRENCY", card_label_style),
                Paragraph("TRANSFER TYPE", card_label_style),
            ],
            [
                Paragraph(str(len(records)), card_val_style),
                Paragraph(f"Rs. {run.total_net:,.2f}", card_val_style),
                Paragraph("INR (Indian Rupee)", card_val_style),
                Paragraph("NEFT / RTGS Batch Transfer", card_val_style),
            ]
        ]
        t_kpi = Table(kpi_data, colWidths=[180, 180, 180, 180])
        t_kpi.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F0FDFA')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#99F6E4')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t_kpi)
        elements.append(Spacer(1, 12))

        # Table
        table_data = [
            [
                Paragraph("#", th_style),
                Paragraph("Employee ID", th_style),
                Paragraph("Beneficiary Name", th_style),
                Paragraph("Bank Name", th_style),
                Paragraph("Account Number", th_style),
                Paragraph("IFSC Code", th_style),
                Paragraph("Net Amount (INR)", th_style),
                Paragraph("Mode", th_style),
            ]
        ]

        total_amount = 0.0
        for idx, r in enumerate(records, start=1):
            emp = r.employee
            total_amount += (r.net_salary or 0.0)
            emp_name = f"{emp.first_name} {emp.last_name}" if emp else "Unknown"
            table_data.append([
                Paragraph(str(idx), td_center_style),
                Paragraph(emp.employee_code if emp else "—", td_style),
                Paragraph(emp_name, td_style),
                Paragraph(r.bank_name or "N/A", td_style),
                Paragraph(r.account_number or "N/A", td_style),
                Paragraph(r.ifsc_code or "N/A", td_center_style),
                Paragraph(f"Rs. {(r.net_salary or 0.0):,.2f}", td_num_style),
                Paragraph(r.payment_mode or "NEFT", td_center_style),
            ])

        table_data.append([
            Paragraph("TOTAL", th_style),
            Paragraph("", th_style),
            Paragraph(f"{len(records)} Beneficiaries", th_style),
            Paragraph("", th_style),
            Paragraph("", th_style),
            Paragraph("", th_style),
            Paragraph(f"Rs. {total_amount:,.2f}", th_style),
            Paragraph("", th_style),
        ])

        col_widths = [30, 75, 140, 115, 120, 80, 95, 65]  # total = 720
        t_bank = Table(table_data, colWidths=col_widths, repeatRows=1)
        t_bank_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F766E')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCFBF1')),
            ('TOPPADDING', (0, 0), (-1, -1), 3.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#115E59')),
        ]
        for row_idx in range(1, len(table_data) - 1):
            if row_idx % 2 == 0:
                t_bank_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor('#F0FDFA')))
        t_bank.setStyle(TableStyle(t_bank_style))
        elements.append(t_bank)
        elements.append(Spacer(1, 14))

        # Authorization instruction block
        auth_p = Paragraph(
            "<b>Corporate Authorization Instruction:</b> Please debit our company primary operating account "
            f"for the sum of <b>Rs. {total_amount:,.2f}</b> (INR) and disburse credits to the beneficiary bank accounts listed above.",
            td_style
        )
        elements.append(auth_p)
        elements.append(Spacer(1, 12))

        signoff_data = [
            [
                Paragraph("Authorised Signatory 1: ___________________", td_style),
                Paragraph("Authorised Signatory 2: ___________________", td_style),
                Paragraph("Company Seal: [                      ]", td_style),
            ]
        ]
        t_sign = Table(signoff_data, colWidths=[240, 240, 240])
        t_sign.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_sign)

        doc.build(elements)
        pdf_bytes = buffer.getvalue()

        response = StreamingResponse(iter([pdf_bytes]), media_type="application/pdf")
        response.headers["Content-Disposition"] = f"attachment; filename=Bank_Payout_{run.run_number}.pdf"
        return response

    @staticmethod
    def export_bank_transfer_csv(db: Session, run_id: int) -> StreamingResponse:
        # Default all exports to PDF per system requirement
        return PayrollService.export_bank_transfer_pdf(db, run_id)

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
