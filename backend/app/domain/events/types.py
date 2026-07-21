from dataclasses import dataclass
from datetime import date, time
from app.domain.events.dispatcher import DomainEvent

@dataclass
class AttendancePunchedIn(DomainEvent):
    employee_id: int
    attendance_id: int
    punch_time: time
    work_mode: str

@dataclass
class AttendancePunchedOut(DomainEvent):
    employee_id: int
    attendance_id: int
    punch_time: time
    work_mode: str

@dataclass
class AttendanceAutoCheckedOut(DomainEvent):
    employee_id: int
    attendance_id: int
    checkout_time: time
    date: date

@dataclass
class ShiftEndingSoon(DomainEvent):
    employee_id: int
    attendance_id: int
    minutes_remaining: int

@dataclass
class OvertimeStarted(DomainEvent):
    employee_id: int
    attendance_id: int
    start_time: time

@dataclass
class OvertimeApproved(DomainEvent):
    employee_id: int
    overtime_request_id: int

@dataclass
class LeaveRequested(DomainEvent):
    employee_id: int
    leave_request_id: int
    date: date
    leave_type: str

@dataclass
class LeaveApproved(DomainEvent):
    employee_id: int
    leave_request_id: int
    date: date
    leave_type: str

@dataclass
class LeaveRejected(DomainEvent):
    employee_id: int
    leave_request_id: int
    date: date

@dataclass
class LeaveCancelled(DomainEvent):
    employee_id: int
    leave_request_id: int
    date: date

@dataclass
class AttendanceRegularizationRequested(DomainEvent):
    employee_id: int
    regularization_request_id: int
    date: date

@dataclass
class AttendanceRegularizationApproved(DomainEvent):
    employee_id: int
    regularization_request_id: int
    date: date
