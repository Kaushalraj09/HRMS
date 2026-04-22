from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date

class PersonalDetails(BaseModel):
    firstName: str
    lastName: str
    gender: Optional[str] = None
    dateOfBirth: Optional[date] = None
    maritalStatus: Optional[str] = None
    bloodGroup: Optional[str] = None

class ContactDetails(BaseModel):
    officialEmail: EmailStr
    personalEmail: Optional[EmailStr] = None
    mobileNumber: str
    alternateMobile: Optional[str] = None
    location: Optional[str] = None

class EmployeeProfile(BaseModel):
    id: int
    employeeId: str
    firstName: str
    lastName: str
    initials: str
    role: str
    department: str
    shift: str
    status: str
    personalDetails: PersonalDetails
    contactDetails: ContactDetails

class ProfileUpdate(BaseModel):
    personalDetails: Optional[PersonalDetails] = None
    contactDetails: Optional[ContactDetails] = None
