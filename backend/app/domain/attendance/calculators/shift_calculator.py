from datetime import time, date, datetime
from sqlalchemy.orm import Session
from app.models.master_data import Shift, BreakPolicy
import logging

logger = logging.getLogger(__name__)

class ShiftCalculator:
    @staticmethod
    def time_to_minutes(t: time) -> int:
        if not t:
            return 0
        return t.hour * 60 + t.minute

    @staticmethod
    def calculate_overlap_minutes(punch_in: time, punch_out: time, window_start: time, window_end: time) -> int:
        """Calculate overlap duration in minutes between a punch span and a reference window."""
        if not punch_in or not punch_out:
            return 0
        in_mins = ShiftCalculator.time_to_minutes(punch_in)
        out_mins = ShiftCalculator.time_to_minutes(punch_out)
        win_start_mins = ShiftCalculator.time_to_minutes(window_start)
        win_end_mins = ShiftCalculator.time_to_minutes(window_end)
        
        if out_mins <= in_mins:
            return 0
            
        overlap_start = max(in_mins, win_start_mins)
        overlap_end = min(out_mins, win_end_mins)
        
        return max(0, overlap_end - overlap_start)

    @staticmethod
    def calculate_late_minutes(punch_in: time, shift: Shift) -> int:
        """Calculate late minutes based on shift start time and grace period."""
        if not punch_in or not shift.start_time:
            return 0
        in_mins = ShiftCalculator.time_to_minutes(punch_in)
        start_mins = ShiftCalculator.time_to_minutes(shift.start_time)
        grace_mins = shift.grace_minutes or 0
        
        if in_mins <= start_mins + grace_mins:
            return 0
        return in_mins - start_mins

    @staticmethod
    def calculate_early_exit_minutes(punch_out: time, shift: Shift) -> int:
        """Calculate early exit minutes based on shift end time."""
        if not punch_out or not shift.end_time:
            return 0
        out_mins = ShiftCalculator.time_to_minutes(punch_out)
        end_mins = ShiftCalculator.time_to_minutes(shift.end_time)
        
        if out_mins >= end_mins:
            return 0
        return end_mins - out_mins

    @staticmethod
    def get_shift_breaks(db: Session, shift: Shift) -> list[BreakPolicy]:
        """Retrieve breaks associated with a shift, falling back to a default lunch break if none exist."""
        breaks = db.query(BreakPolicy).filter(BreakPolicy.shift_id == shift.id).all()
        if not breaks and shift.id == 0:
            # Fallback for General Shift default configuration: unpaid lunch break 13:00 - 14:00
            return [
                BreakPolicy(
                    id=0,
                    shift_id=0,
                    name="Lunch Break",
                    start_time=time(13, 0),
                    end_time=time(14, 0),
                    paid_break=False,
                    mandatory=True
                )
            ]
        return breaks

    @staticmethod
    def calculate_break_overlaps(db: Session, punch_in: time, punch_out: time, shift: Shift) -> tuple[int, int]:
        """
        Calculate total break minutes and unpaid break minutes that overlap with the punch interval.
        Returns (total_break_minutes, unpaid_break_minutes)
        """
        if not punch_in or not punch_out:
            return 0, 0
            
        breaks = ShiftCalculator.get_shift_breaks(db, shift)
        total_break = 0
        unpaid_break = 0
        
        for bp in breaks:
            overlap = ShiftCalculator.calculate_overlap_minutes(punch_in, punch_out, bp.start_time, bp.end_time)
            if overlap > 0:
                total_break += overlap
                if not bp.paid_break:
                    unpaid_break += overlap
                    
        return total_break, unpaid_break
