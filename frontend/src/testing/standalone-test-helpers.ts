import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { BehaviorSubject, delay, of } from 'rxjs';

import { AuthService } from '../app/core/services/auth.service';
import { AttendanceService } from '../app/core/services/attendance.service';
import { DashboardService } from '../app/core/services/dashboard.service';
import { EmployeeService } from '../app/core/services/employee.service';
import { HrService } from '../app/core/services/hr.service';
import { LoginActivityService } from '../app/core/services/login-activity.service';
import { NotificationService } from '../app/core/services/notification.service';
import { MyProfileService } from '../app/core/services/profile.service';

const mockCurrentUser = {
  id: '1',
  email: 'admin@aivan.com',
  displayName: 'Test User',
  role: 'admin' as const,
  status: 'Active' as const,
  accessibleDashboards: ['MASTER'],
  activeDashboard: 'MASTER' as const,
  profileImage: null
};

const mockAdminDashboard = {
  cards: [],
  hrUsers: [],
  employees: []
};

const mockHrDashboard = {
  totalEmployees: 0,
  presentEmployees: 0,
  checkedInEmployees: 0,
  checkedOutEmployees: 0,
  notMarkedEmployees: 0,
  absentEmployees: 0,
  workModeBreakdown: [0, 0],
  genderBreakdown: [0, 0],
  quickStats: [],
  recentTimeSheets: [],
  upcomingEvents: []
};

const mockTodayState = {
  isWorking: false,
  status: 'Not Marked',
  totalWorkedSeconds: 0,
  approvedSeconds: 0,
  remainingSeconds: 0,
  shiftTotalSeconds: 0,
  shiftElapsedSeconds: 0,
  shiftStart: '09:00 AM',
  shiftEnd: '06:00 PM',
  workMode: 'Office' as const,
  punchIn: null,
  punchOut: null
};

const mockProfile = {
  id: '1',
  employeeId: '1',
  firstName: 'Test',
  lastName: 'User',
  initials: 'TU',
  role: 'Employee',
  department: 'Engineering',
  shift: 'General Shift',
  status: 'Active' as const,
  personalDetails: {
    firstName: 'Test',
    lastName: 'User',
    gender: 'Male',
    dateOfBirth: '1998-01-01',
    maritalStatus: 'Single',
    bloodGroup: 'O+'
  },
  contactDetails: {
    officialEmail: 'test@aivan.com',
    personalEmail: 'test.personal@aivan.com',
    mobileNumber: '9999999999',
    alternateMobile: '',
    location: 'Pune'
  }
};

const notifications$ = new BehaviorSubject<any[]>([]);
const unreadCount$ = new BehaviorSubject<number>(0);
const wsMessage$ = new BehaviorSubject<any>(null);

export function provideStandaloneComponentTestProviders(): any[] {
  return [
    provideRouter([]),
    provideHttpClient(),
    provideHttpClientTesting(),
    {
      provide: AuthService,
      useValue: {
        currentUser$: of(mockCurrentUser),
        login: () => of({ me: mockCurrentUser }),
        logout: () => undefined,
        isLoggedIn: () => true,
        getCurrentUser: () => mockCurrentUser,
        getLandingRoute: () => '/master-dashboard',
        getDisplayName: () => mockCurrentUser.displayName,
        updateProfileImage: () => undefined,
        forgotPassword: () => of({ success: true, message: 'Reset link generated.' }),
        resetPassword: () => of({ success: true, message: 'Password reset successfully.' })
      }
    },
    {
      provide: DashboardService,
      useValue: {
        getAdminDashboard: () => of(mockAdminDashboard),
        getHrDashboard: () => of(mockHrDashboard)
      }
    },
    {
      provide: AttendanceService,
      useValue: {
        wsMessage$: wsMessage$.asObservable(),
        timeoffUpdate$: of(null),
        connectWebSocket: () => undefined,
        disconnectWebSocket: () => undefined,
        getTodayAttendanceState: () => of(mockTodayState),
        getMyTimesheets: () => of([]),
        getMyAttendanceSummary: () => of([]),
        getAttendanceLogs: () => of({ data: [], total: 0, metrics: { present: 0, working: 0, absent: 0, notMarked: 0 } }),
        getPendingTimeOffRequests: () => of([]),
        getProcessedTimeOffRequests: () => of([]),
        approveTimeOffRequest: () => of({}),
        applyTimeOffInline: () => of({}),
        requestTimeOff: () => of({}),
        getMyTimeOffRequests: () => of([]),
        getIpLocation: () => of({}),
        reverseGeocode: () => of({ display_name: '' }),
        punchIn: () => of(mockTodayState),
        punchOut: () => of(mockTodayState),
        updateWorkMode: () => of(mockTodayState),
        addSchedule: () => of(void 0)
      }
    },
    {
      provide: NotificationService,
      useValue: {
        notifications$: notifications$.asObservable(),
        unreadCount$: unreadCount$.asObservable(),
        fetchNotifications: () => of([]),
        fetchUnreadCount: () => of({ unread_count: 0 }),
        markAsRead: () => of({}),
        markAllAsRead: () => of({ unread_count: 0 })
      }
    },
    {
      provide: EmployeeService,
      useValue: {
        getEmployees: () => of({ data: [], total: 0 }).pipe(delay(0)),
        getEmployeeById: () => of(null),
        getEmployeeCredentials: () => of(null),
        createEmployee: () => of({ success: true, message: 'Employee created.' }),
        updateEmployee: () => of({ success: true, message: 'Employee updated.' })
      }
    },
    {
      provide: HrService,
      useValue: {
        getHrUsers: () => of({ data: [], total: 0 }),
        createHr: () => of({ success: true, message: 'HR created.' })
      }
    },
    {
      provide: MyProfileService,
      useValue: {
        getProfile: () => of(mockProfile),
        updateProfile: () => of({ success: true, message: 'Profile updated.' })
      }
    },
    {
      provide: LoginActivityService,
      useValue: {
        getHistory: () => of([]),
        getDetail: () => of(null)
      }
    }
  ];
}
