import urllib.request
import json

# Login as admin using JSON
login_url = "http://localhost:8000/api/v1/auth/login"
login_data = json.dumps({
    "email": "admin@hrms.com",
    "password": "admin123"
}).encode("utf-8")

req = urllib.request.Request(
    login_url, 
    data=login_data, 
    headers={"Content-Type": "application/json"}
)
try:
    with urllib.request.urlopen(req) as res:
        response_data = json.loads(res.read().decode())
        print("Login Success!")
        token = response_data["accessToken"]
except Exception as e:
    print("Login Failed:", e)
    token = None

if token:
    # Query reports endpoint
    reports_url = "http://localhost:8000/api/v1/reports/admin/hr-workload"
    req_reports = urllib.request.Request(
        reports_url, 
        headers={"Authorization": f"Bearer {token}"}
    )
    try:
        with urllib.request.urlopen(req_reports) as res:
            print("Reports API Success!")
            print(json.loads(res.read().decode()))
    except Exception as e:
        print("Reports API Failed:", e)
        if hasattr(e, 'read'):
            print(e.read().decode())
