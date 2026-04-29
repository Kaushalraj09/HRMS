from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.hr import HrCreate, HrResponse
from app.services import hr_service

router = APIRouter(prefix="/hr-users", tags=["hr-management"])

@router.post("", response_model=HrResponse)
def create_hr_user(request: HrCreate, db: Session = Depends(get_db)):
    # You should add a check here later to make sure ONLY admins can do this!
    try:
        return hr_service.create_hr(db, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.get("", response_model=List[HrResponse])
def get_hr_users(db: Session = Depends(get_db)):
    return hr_service.list_hrs(db)
