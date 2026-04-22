from sqlalchemy.orm import Session
from app.models.user import Role

def seed_roles(db: Session):
    roles = ["Admin", "HR", "Employee"]
    for role_name in roles:
        existing_role = db.query(Role).filter(Role.name == role_name).first()
        if not existing_role:
            new_role = Role(name=role_name)
            db.add(new_role)
            print(f"Added role: {role_name}")
        else:
            print(f"Role {role_name} already exists")
    db.commit()
