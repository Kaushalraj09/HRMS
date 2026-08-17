from pydantic import BaseModel
from typing import List, Optional

class DashboardCard(BaseModel):
    icon: str
    label: str
    value: str

class DashboardRecentItem(BaseModel):
    primary: str
    secondary: str
    tertiary: str
    status: str

class DepartmentDistributionItem(BaseModel):
    name: str
    count: int
    percentage: float
    color: str

class MonthlyHiringItem(BaseModel):
    month: str
    count: int

class AttendanceOverviewPoint(BaseModel):
    date: str
    percentage: float
    present: int
    total: int

class RecentJoinerItem(BaseModel):
    id: int
    name: str
    designation: str
    department: str
    doj: str
    avatar: Optional[str] = None
    initials: str

class BirthdayItem(BaseModel):
    id: int
    name: str
    designation: str
    department: str
    dob: str
    avatar: Optional[str] = None
    initials: str
    isToday: bool = False

class PendingApprovalsSummary(BaseModel):
    leaveRequests: int
    timeOffRequests: int
    regularizationRequests: int
    expenseClaims: int

class AdminProfileInfo(BaseModel):
    name: str
    code: str
    role: str
    department: str
    shift: str
    status: str

class AdminDashboardData(BaseModel):
    cards: List[DashboardCard]
    hrUsers: List[DashboardRecentItem]
    employees: List[DashboardRecentItem]
    
    # Enhanced dynamic fields
    totalEmployees: Optional[int] = None
    employeeGrowthCount: Optional[int] = None
    employeeGrowthRate: Optional[float] = None
    attendanceRate: Optional[float] = None
    attendanceGrowthRate: Optional[float] = None
    pendingLeavesCount: Optional[int] = None
    payrollStatus: Optional[str] = None
    payrollPeriod: Optional[str] = None
    
    adminProfile: Optional[AdminProfileInfo] = None
    attendanceOverview: Optional[List[AttendanceOverviewPoint]] = None
    departmentDistribution: Optional[List[DepartmentDistributionItem]] = None
    monthlyHiringTrend: Optional[List[MonthlyHiringItem]] = None
    recentJoiners: Optional[List[RecentJoinerItem]] = None
    todayBirthdays: Optional[List[BirthdayItem]] = None
    pendingApprovals: Optional[PendingApprovalsSummary] = None

class QuickStat(BaseModel):
    total: int
    name: str

class RecentTimeSheet(BaseModel):
    employee: str
    employeeCode: str
    date: str
    punchIn: str
    punchOut: str
    breakTime: str
    overtime: str
    totalHours: str
    status: str
    punchInImage: Optional[str] = None
    punchOutImage: Optional[str] = None

class UpcomingEvent(BaseModel):
    name: str
    note: str
    role: str

class WeeklyAttendanceTrendItem(BaseModel):
    date: str
    present: int
    absent: int
    leave: int
    wfh: int
    total: int
    percentage: float

class HrDashboardData(BaseModel):
    totalEmployees: int
    presentEmployees: int
    checkedInEmployees: int
    checkedOutEmployees: int
    notMarkedEmployees: int
    workModeBreakdown: List[int]
    genderBreakdown: List[int]  
    quickStats: List[QuickStat]
    recentTimeSheets: List[RecentTimeSheet]
    upcomingEvents: List[UpcomingEvent]
    weeklyAttendanceTrend: List[WeeklyAttendanceTrendItem]


