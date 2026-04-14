export type EmployeeStatus = 'Active' | 'Inactive';
export type LoginStatus = 'Enabled' | 'Disabled';

export interface Employee {
  id: string;
  userId: string;
  employeeCode: string;
  name: string;
  firstName: string;
  lastName: string;
  department: string;
  designation: string;
  employeeType: string;
  status: EmployeeStatus;
  login: LoginStatus;
  officialEmail: string;
  personalEmail: string;
  mobile: string;
  alternateMobile: string;
  emergencyContactName: string;
  emergencyContactNumber: string;
  gender: string;
  dob: string;
  maritalStatus: string;
  bloodGroup: string;
  workLocation: string;
  shiftType: string;
  doj: string;
}

export interface PaginatedResult<T> {
  data: T[];
  total: number;
}

export interface EmployeePayload {
  accountAccess?: {
    loginEmail?: string;
    temporaryPassword?: string;
    role?: 'employee';
  };
  personalInfo: {
    firstName: string;
    lastName: string;
    gender: string;
    dob: string;
    maritalStatus: string;
    bloodGroup: string;
  };
  employmentInfo: {
    employeeType: string;
    department: string;
    designation: string;
    workLocation: string;
    shiftType: string;
    doj: string;
    employeeCode?: string;
  };
  contactInfo: {
    officialEmail: string;
    personalEmail: string;
    mobile: string;
    alternateMobile: string;
    emergencyContactName: string;
    emergencyContactNumber: string;
  };
}

export interface EmployeeDetailView {
  employee: Employee;
  managerName: string;
  loginEmail: string;
  temporaryPasswordHint: string;
}
