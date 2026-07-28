import re

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User


def build_temporary_testing_password(email: str) -> str:
    """Build the temporary testing password used while SMTP is unavailable."""
    local_part = (email or "").split("@", 1)[0]
    letters = "".join(re.findall(r"[A-Za-z]", local_part))[:5]
    if not letters:
        letters = "User"
    return f"{letters[:1].upper()}{letters[1:].lower()}@1234"


def apply_temporary_testing_password(db: Session, user: User) -> str:
    password = build_temporary_testing_password(user.email)
    user.password_hash = hash_password(password)
    db.add(user)
    db.commit()
    return password
