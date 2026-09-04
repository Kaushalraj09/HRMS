from sqlalchemy.orm import Session
from app.models.master_data import Shift, AttendancePolicy
from datetime import time
import logging

logger = logging.getLogger(__name__)

class AttendancePolicyEvaluator:
    @staticmethod
    def get_active_policy(db: Session) -> AttendancePolicy:
        """Fetch the active attendance policy or fallback to a default configuration."""
        policy = db.query(AttendancePolicy).filter(AttendancePolicy.is_active == True).first()
        if not policy:
            policy = AttendancePolicy(
                id=0,
                name="Default Global Policy",
                required_minutes=480,
                minimum_half_day_minutes=120,
                grace_minutes=15,
                is_active=True
            )
        return policy

    @staticmethod
    def evaluate_status(
        db: Session,
        shift: Shift,
        credited_minutes: int,
        late_minutes: int,
        early_exit_minutes: int,
        requires_regularization: bool = False
    ) -> str:
        """
        Evaluate and return the appropriate attendance status string based on the active policy rules.
        """
        if requires_regularization:
            return "Regularization Pending"

        policy = AttendancePolicyEvaluator.get_active_policy(db)
        
        # Dynamically determine thresholds from the employee's assigned Shift configuration
        if shift and shift.required_work_minutes:
            required_mins = shift.required_work_minutes
        elif shift and shift.working_hours:
            required_mins = int(float(shift.working_hours) * 60)
        elif policy and policy.id != 0 and policy.required_minutes:
            required_mins = policy.required_minutes
        else:
            required_mins = 480

        if shift and shift.minimum_half_day_minutes:
            half_day_mins = shift.minimum_half_day_minutes
        elif shift and shift.half_day_hours:
            half_day_mins = int(float(shift.half_day_hours) * 60)
        elif policy and policy.id != 0 and policy.minimum_half_day_minutes:
            half_day_mins = policy.minimum_half_day_minutes
        else:
            half_day_mins = required_mins // 2

        shift_grace = getattr(shift, "shift_grace_minutes", None)
        if shift_grace is None:
            shift_grace = getattr(shift, "grace_minutes", 15) or 15
        effective_required_mins = max(0, required_mins - shift_grace)
        
        if credited_minutes >= effective_required_mins:
            if late_minutes > 0:
                return "Late Present"
            return "Present"
        elif credited_minutes >= half_day_mins:
            return "Half Day"
        else:
            return "Absent"
