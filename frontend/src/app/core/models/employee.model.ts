export interface Employee {
  id: string;
  employeeCode: string;
  name: string;
  department: string;
  designation: string;
  employeeType: string;
  status: 'Active' | 'Inactive';
  login: 'Enabled' | 'Disabled';
}

export interface PaginatedResult<T> {
  data: T[];
  total: number;
}

export interface EmployeePayload {
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
