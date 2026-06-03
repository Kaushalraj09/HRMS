from datetime import date, time
from app.schemas.attendance import TodayAttendanceState, AttendanceResponse, AttendanceRecord
from app.core.enums import WorkMode

def test_today_attendance_state_colors():
    # Test Working status
    working_state = TodayAttendanceState(
        isWorking=True,
        status="Working",
        totalWorkedSeconds=3600,
        approvedSeconds=3600,
        remainingSeconds=28800,
        shiftTotalSeconds=32400,
        shiftElapsedSeconds=3600,
        shiftStart="09:00",
        shiftEnd="18:00",
        workMode=WorkMode.office
    )
    assert working_state.attendance_status == "working"
    assert working_state.badge_color == "green"

    # Test Present status
    present_state = TodayAttendanceState(
        isWorking=False,
        status="Present",
        totalWorkedSeconds=32400,
        approvedSeconds=32400,
        remainingSeconds=0,
        shiftTotalSeconds=32400,
        shiftElapsedSeconds=32400,
        shiftStart="09:00",
        shiftEnd="18:00",
        workMode=WorkMode.office
    )
    assert present_state.attendance_status == "present"
    assert present_state.badge_color == "gray"

    # Test Not Marked status
    not_marked_state = TodayAttendanceState(
        isWorking=False,
        status="Not Marked",
        totalWorkedSeconds=0,
        approvedSeconds=0,
        remainingSeconds=32400,
        shiftTotalSeconds=32400,
        shiftElapsedSeconds=0,
        shiftStart="09:00",
        shiftEnd="18:00",
        workMode=WorkMode.office
    )
    assert not_marked_state.attendance_status == "not marked"
    assert not_marked_state.badge_color == "gray"

def test_attendance_response_colors():
    # Test Working response
    resp = AttendanceResponse(
        id=1,
        employeeId=101,
        date=date(2026, 6, 3),
        status="Working",
        workMode=WorkMode.office
    )
    assert resp.is_working is True
    assert resp.attendance_status == "working"
    assert resp.badge_color == "green"

    # Test Present response
    resp_present = AttendanceResponse(
        id=1,
        employeeId=101,
        date=date(2026, 6, 3),
        status="Present",
        workMode=WorkMode.office
    )
    assert resp_present.is_working is False
    assert resp_present.attendance_status == "present"
    assert resp_present.badge_color == "gray"

def test_attendance_record_colors():
    # Test Absent record
    rec = AttendanceRecord(
        id=1,
        employeeName="Kaushal Raj",
        employeeCode="EMP-0001",
        department="Engineering",
        date=date(2026, 6, 3),
        status="Absent"
    )
    assert rec.is_working is False
    assert rec.attendance_status == "absent"
    assert rec.badge_color == "gray"
