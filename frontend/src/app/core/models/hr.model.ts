export type HrStatus = 'Active' | 'Inactive';

export interface HrUser {
  id: string;
  userId: string;
  hrCode: string;
  fullName: string;
  email: string;
  phone: string;
  department: string;
  designation: string;
  status: HrStatus;
  login: 'Enabled' | 'Disabled';
  createdAt: string;
}

export interface CreateHrPayload {
  fullName: string;
  email: string;
  phone: string;
  designation: string;
  department: string;
  temporaryPassword: string;
  status: HrStatus;
}
