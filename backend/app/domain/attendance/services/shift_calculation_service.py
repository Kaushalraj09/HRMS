from datetime import time, datetime, date, timedelta
from typing import Optional, Tuple
from zoneinfo import ZoneInfo
from app.models.master_data import Shift

APP_TIMEZONE = ZoneInfo("Asia/Kolkata")

class ShiftCalculationService:
    @staticmethod
    def time_to_minutes(t: time) -> int:
        if not t:
            return 0
        return t.hour * 60 + t.minute

    @staticmethod
    def minutes_to_time(mins: int) -> time:
        mins = mins % (24 * 60)
        return time(mins // 60, mins % 60)

    @staticmethod
    def get_effective_shift(shift: Optional[Shift]) -> Shift:
        """Fallback to standard default Shift if None provided."""
        if shift:
            return shift
        return Shift(
            id=0,
            name="General Shift",
            code="GEN_SHIFT",
            start_time=time(9, 0),
            end_time=time(18, 0),
            working_hours=8.0,
            required_work_minutes=480,
            grace_minutes=15,
            lunch_duration_minutes=60,
            lunch_start_time=None,
            lunch_end_time=None,
            half_day_hours=4.0,
            minimum_half_day_minutes=240,
            present_hours=8.0,
            minimum_present_minutes=480,
            overtime_start_time=None,
            late_mark_after_minutes=15,
            early_exit_before_minutes=0,
            is_night_shift=False,
            is_active=True
        )

    @classmethod
    def calculate_lunch_window(cls, shift: Shift) -> Tuple[time, time]:
        """
        Calculates lunch start and end times.
        If admin manually specified lunch_start_time and lunch_end_time, returns those.
        Otherwise, Lunch Start = Shift Start + (Half Working Hours),
        Lunch End = Lunch Start + lunch_duration_minutes.
        """
        shift = cls.get_effective_shift(shift)
        if shift.lunch_start_time and shift.lunch_end_time:
            return shift.lunch_start_time, shift.lunch_end_time

        start_mins = cls.time_to_minutes(shift.start_time or time(9, 0))
        req_mins = shift.required_work_minutes or int((float(shift.working_hours or 8.0)) * 60)
        half_working_mins = req_mins // 2

        lunch_start_mins = start_mins + half_working_mins
        lunch_duration = shift.lunch_duration_minutes if shift.lunch_duration_minutes is not None else 60
        lunch_end_mins = lunch_start_mins + lunch_duration

        return cls.minutes_to_time(lunch_start_mins), cls.minutes_to_time(lunch_end_mins)

    @classmethod
    def calculate_punch_in_status(cls, punch_in: Optional[time], shift: Optional[Shift]) -> str:
        """
        Determines Punch In status based on shift start and grace period:
        - On Time: Punch In <= Shift Start
        - Within Grace: Shift Start < Punch In <= Shift Start + Grace
        - Late: Punch In > Shift Start + Grace
        """
        if not punch_in:
            return "Not Marked"

        shift = cls.get_effective_shift(shift)
        start_mins = cls.time_to_minutes(shift.start_time or time(9, 0))
        grace_mins = shift.grace_minutes if shift.grace_minutes is not None else 30
        in_mins = cls.time_to_minutes(punch_in)

        # Handle night shift cross midnight if punch in happens very early/late
        if shift.is_night_shift and in_mins < start_mins - 720:
            in_mins += 1440

        if in_mins <= start_mins:
            return "On Time"
        elif in_mins <= start_mins + grace_mins:
            return "Within Grace"
        else:
            return "Late"

    @classmethod
    def calculate_late_minutes(cls, punch_in: Optional[time], shift: Optional[Shift]) -> int:
        """Calculate late minutes beyond grace period."""
        if not punch_in:
            return 0
        shift = cls.get_effective_shift(shift)
        start_mins = cls.time_to_minutes(shift.start_time or time(9, 0))
        grace_mins = shift.grace_minutes if shift.grace_minutes is not None else 30
        in_mins = cls.time_to_minutes(punch_in)

        if shift.is_night_shift and in_mins < start_mins - 720:
            in_mins += 1440

        if in_mins <= start_mins + grace_mins:
            return 0
        return max(0, in_mins - start_mins)

    @classmethod
    def calculate_early_exit_minutes(cls, punch_out: Optional[time], shift: Optional[Shift]) -> int:
        """Calculate early exit minutes before shift end."""
        if not punch_out:
            return 0
        shift = cls.get_effective_shift(shift)
        end_mins = cls.time_to_minutes(shift.end_time or time(18, 0))
        out_mins = cls.time_to_minutes(punch_out)
        start_mins = cls.time_to_minutes(shift.start_time or time(9, 0))

        if (shift.is_night_shift or end_mins < start_mins) and out_mins < start_mins:
            out_mins += 1440
            if end_mins < start_mins:
                end_mins += 1440

        early_threshold = shift.early_exit_before_minutes or 0
        target_end_mins = end_mins - early_threshold

        if out_mins >= target_end_mins:
            return 0
        return max(0, end_mins - out_mins)

    @classmethod
    def calculate_overtime_minutes(
        cls,
        punch_in: Optional[time],
        punch_out: Optional[time],
        shift: Optional[Shift],
        net_working_minutes: int = 0
    ) -> int:
        """
        Calculates dynamic overtime minutes based entirely on assigned Shift configuration:
        - If overtime_allowed is False, returns 0.
        - Checks overtime_start_time (or shift end_time).
        - Handles night shifts and max_overtime_minutes limit.
        """
        shift = cls.get_effective_shift(shift)
        if shift.overtime_allowed is False:
            return 0

        max_ot = shift.max_overtime_minutes if shift.max_overtime_minutes is not None else 120
        if max_ot <= 0:
            return 0

        if punch_in and punch_out:
            in_mins = cls.time_to_minutes(punch_in)
            out_mins = cls.time_to_minutes(punch_out)
            start_mins = cls.time_to_minutes(shift.start_time or time(9, 0))
            
            ot_start_time = shift.overtime_start_time or shift.end_time or time(18, 0)
            ot_start_mins = cls.time_to_minutes(ot_start_time)

            if (shift.is_night_shift or cls.time_to_minutes(shift.end_time or time(18, 0)) < start_mins):
                if out_mins < start_mins:
                    out_mins += 1440
                if ot_start_mins < start_mins:
                    ot_start_mins += 1440

            if out_mins > ot_start_mins:
                potential_ot = out_mins - ot_start_mins
                return min(max_ot, max(0, potential_ot))

        req_mins = shift.required_work_minutes or int((float(shift.working_hours or 8.0)) * 60)
        if net_working_minutes > req_mins:
            potential_ot = net_working_minutes - req_mins
            return min(max_ot, max(0, potential_ot))

        return 0

    @classmethod
    def calculate_lunch_overlap(cls, punch_in: time, punch_out: time, shift: Optional[Shift]) -> int:
        """Calculate overlap duration in minutes between punch span and lunch window."""
        if not punch_in or not punch_out:
            return 0
        shift = cls.get_effective_shift(shift)
        lunch_start, lunch_end = cls.calculate_lunch_window(shift)

        in_mins = cls.time_to_minutes(punch_in)
        out_mins = cls.time_to_minutes(punch_out)
        win_start_mins = cls.time_to_minutes(lunch_start)
        win_end_mins = cls.time_to_minutes(lunch_end)

        start_mins = cls.time_to_minutes(shift.start_time or time(9, 0))
        end_mins = cls.time_to_minutes(shift.end_time or time(18, 0))

        if shift.is_night_shift or end_mins < start_mins:
            if out_mins < in_mins:
                out_mins += 1440
            if win_start_mins < start_mins:
                win_start_mins += 1440
            if win_end_mins < start_mins:
                win_end_mins += 1440

        if out_mins <= in_mins:
            return 0

        overlap_start = max(in_mins, win_start_mins)
        overlap_end = min(out_mins, win_end_mins)

        return max(0, overlap_end - overlap_start)

    @classmethod
    def get_attendance_status(
        cls,
        punch_in: Optional[time],
        punch_out: Optional[time],
        record_date: date,
        shift: Optional[Shift] = None,
        current_dt: Optional[datetime] = None,
        timeoff_duration_hours: float = 0.0,
    ) -> str:
        """
        Determines dynamic attendance status using Shift configuration.
        """
        shift = cls.get_effective_shift(shift)

        # Full day approved leave / time off
        req_hours = float(shift.working_hours or 8.0)
        if timeoff_duration_hours >= req_hours:
            return "LEAVE"

        if punch_in is not None and punch_out is None:
            return "WORKING"

        if punch_in is not None and punch_out is not None:
            in_mins = cls.time_to_minutes(punch_in)
            out_mins = cls.time_to_minutes(punch_out)
            start_mins = cls.time_to_minutes(shift.start_time or time(9, 0))
            end_mins = cls.time_to_minutes(shift.end_time or time(18, 0))

            if (shift.is_night_shift or end_mins < start_mins) and out_mins < in_mins:
                out_mins += 1440

            gross_mins = max(0, out_mins - in_mins)
            lunch_mins = cls.calculate_lunch_overlap(punch_in, punch_out, shift)
            net_mins = max(0, gross_mins - lunch_mins)

            timeoff_mins = int(timeoff_duration_hours * 60)
            credited_mins = net_mins + timeoff_mins

            present_mins = shift.minimum_present_minutes or int((float(shift.present_hours or 8.0)) * 60)
            half_day_mins = shift.minimum_half_day_minutes or int((float(shift.half_day_hours or 4.0)) * 60)

            grace_mins = shift.grace_minutes if shift.grace_minutes is not None else 15
            grace_tolerance = grace_mins if (in_mins > start_mins and in_mins <= start_mins + grace_mins) else 0

            if credited_mins + grace_tolerance >= present_mins:
                return "PRESENT"
            elif credited_mins >= half_day_mins:
                return "HALF_DAY"
            else:
                return "ABSENT"

        # Punch In is None
        timeoff_mins = int(timeoff_duration_hours * 60)
        present_mins = shift.minimum_present_minutes or int((float(shift.present_hours or 8.0)) * 60)
        half_day_mins = shift.minimum_half_day_minutes or int((float(shift.half_day_hours or 4.0)) * 60)

        if timeoff_mins >= present_mins:
            return "LEAVE"
        elif timeoff_mins >= half_day_mins:
            return "HALF_DAY"

        if current_dt is None:
            current_dt = datetime.now(APP_TIMEZONE)

        today = current_dt.date()
        if record_date < today:
            return "ABSENT"

        # Today cutoff: 2 hours after shift start or mid day
        start_mins = cls.time_to_minutes(shift.start_time or time(9, 0))
        cutoff_mins = start_mins + (shift.minimum_half_day_minutes or 240) + 90
        cutoff_time = cls.minutes_to_time(cutoff_mins)

        if current_dt.time() > cutoff_time and not shift.is_night_shift:
            return "ABSENT"

        return "NOT_MARKED"
