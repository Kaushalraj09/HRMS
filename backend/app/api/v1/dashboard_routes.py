from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/admin")
def get_admin_dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {"message": "Admin Dashboard implementation coming soon"}
