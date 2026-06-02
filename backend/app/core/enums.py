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
    working = "Working"
    present = "Present"
    absent = "Absent"
    not_marked = "Not Marked"

    def __str__(self):
        return self.value
