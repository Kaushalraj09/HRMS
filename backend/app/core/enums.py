from enum import Enum


class WorkMode(str, Enum):
    """Valid work modes for attendance tracking."""
    office = "Office"
    remote = "Remote"
    hybrid = "Hybrid"

    def __str__(self):
        return self.value


class AttendanceStatus(str, Enum):
    """Valid attendance statuses."""
    present = "Present"
    late = "Late"
    half_day = "Half-Day"
    leave = "Leave"
    absent = "Absent"
    not_marked = "Not Marked"
    working = "Working"
    not_working = "Not Working"

    def __str__(self):
        return self.value
