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
        
        # Determine threshold bounds using policy if active, otherwise using shift configuration
        required_mins = policy.required_minutes if policy.id != 0 else (shift.required_work_minutes or 480)
        half_day_mins = policy.minimum_half_day_minutes if policy.id != 0 else (shift.minimum_half_day_minutes or 120)
        
        if credited_minutes >= required_mins:
            if late_minutes > 0 and early_exit_minutes > 0:
                return "Late + Early Exit"
            elif late_minutes > 0:
                return "Late Present"
            elif early_exit_minutes > 0:
                return "Present With Early Exit"
            else:
                return "Present"
        elif credited_minutes >= half_day_mins:
            return "Half Day"
        else:
            return "Absent"
