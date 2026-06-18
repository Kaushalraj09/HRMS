from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app import models  # noqa: F401 - ensure all tables are registered
from app.models.employee import Employee
from app.models.hr_user import HrUser
from app.models.user import User
from app.seeds.seed_demo_users import seed_users
from app.seeds.seed_master_data import seed_roles


def test_seed_users_bootstraps_fresh_database():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = testing_session_local()

    seed_roles(db)
    seed_users(db)

    assert db.query(User).count() == 3
    assert db.query(Employee).count() == 2
    assert db.query(HrUser).count() == 1

    db.close()
