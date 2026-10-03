from sqlalchemy import inspect, text
from app.core.database import engine

def run():
    inspector = inspect(engine)
    col_names = [col["name"] for col in inspector.get_columns("employees")]
    print("Existing employee columns:", col_names)
    with engine.connect() as conn:
        if "employee_code_source" not in col_names:
            conn.execute(text("ALTER TABLE employees ADD COLUMN employee_code_source VARCHAR(30) DEFAULT 'AIVAN_GENERATED'"))
            print("Added employee_code_source column")
        if "employee_code_status" not in col_names:
            conn.execute(text("ALTER TABLE employees ADD COLUMN employee_code_status VARCHAR(20) DEFAULT 'ACTIVE'"))
            print("Added employee_code_status column")
        conn.commit()
    print("Database migration for employee code columns complete.")

if __name__ == "__main__":
    run()
