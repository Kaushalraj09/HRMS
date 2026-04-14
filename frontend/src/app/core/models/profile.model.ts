export interface PersonalDetails {
  firstName: string;
  lastName: string;
  gender: string;
  dateOfBirth: string;
  maritalStatus?: string;
  bloodGroup?: string;
}

export interface ContactDetails {
  officialEmail: string;
  personalEmail?: string;
  mobileNumber: string;
  alternateMobile?: string;
  location: string;
}

export interface EmployeeProfile {
  id: string;
  employeeId: string;
  firstName: string;
  lastName: string;
  initials: string;
  role: string;
  department: string;
  shift: string;
  status: 'Active' | 'Inactive';
  personalDetails: PersonalDetails;
  contactDetails: ContactDetails;
}
