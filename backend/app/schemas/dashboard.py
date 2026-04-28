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

class AdminDashboardData(BaseModel):
    cards: List[DashboardCard]
    hrUsers: List[DashboardRecentItem]
    employees: List[DashboardRecentItem]

class QuickStat(BaseModel):
    total: int
    name: str

class RecentTimeSheet(BaseModel):
    employee: str
    date: str
    punchIn: str
    punchOut: str
    breakTime: str
    overtime: str
    totalHours: str
    status: str

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

