import math
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.employee import Employee
from app.models.master_data import WorkLocation


def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees) in meters.
    """
    R = 6371000.0  # Radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def validate_employee_geofence(
    db: Session,
    employee: Employee,
    current_lat: Optional[float],
    current_lon: Optional[float]
) -> Dict[str, Any]:
    """
    Validates employee's assigned work location and enforces 40-meter geofence
    for office locations. Returns location metadata dictionary if validation passes.
    """
    assigned_location_name = (employee.work_location or "").strip()
    if not assigned_location_name or assigned_location_name.lower() in ["remote", "remote home office", "wfh", "hybrid"]:
        return {
            "is_remote": True,
            "work_location_id": None,
            "work_location_name": assigned_location_name or "Remote",
            "distance_meters": None,
            "allowed_radius_meters": None,
        }

    # 1. Lookup WorkLocation in DB
    work_location = (
        db.query(WorkLocation)
        .filter(WorkLocation.name == assigned_location_name)
        .first()
    )

    if not work_location:
        # Fallback case-insensitive match
        work_location = (
            db.query(WorkLocation)
            .filter(WorkLocation.name.ilike(assigned_location_name))
            .first()
        )

    if not work_location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": f"Assigned work location '{assigned_location_name}' is not configured. Please contact HR.",
                "office": assigned_location_name,
            }
        )

    if (getattr(work_location, "location_type", "office") or "").lower() != "office":
        return {
            "is_remote": True,
            "work_location_id": work_location.id if work_location else None,
            "work_location_name": work_location.name if work_location else assigned_location_name,
            "distance_meters": None,
            "allowed_radius_meters": None,
        }

    if not work_location.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": f"Assigned office '{work_location.name}' is currently inactive. Please contact HR."
            }
        )

    # 3. Office Geofence Validation
    office_lat = getattr(work_location, "latitude", None)
    office_lon = getattr(work_location, "longitude", None)
    allowed_radius = getattr(work_location, "geofence_radius_meters", None) or 40.0

    if office_lat is None or office_lon is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": f"Office coordinates for {work_location.name} are missing in master data. Please contact HR.",
                "office": work_location.name
            }
        )

    if current_lat is None or current_lon is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": f"GPS location access is required to mark attendance for {work_location.name}.",
                "office": work_location.name,
                "allowed_radius_meters": int(allowed_radius)
            }
        )

    # Calculate distance using Haversine formula
    distance_meters = calculate_haversine_distance(
        float(current_lat), float(current_lon),
        float(office_lat), float(office_lon)
    )

    if distance_meters > allowed_radius:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": f"You are outside the assigned office location ({work_location.name}) to mark attendance.",
                "office": work_location.name,
                "distance_meters": round(distance_meters, 1),
                "allowed_radius_meters": int(allowed_radius)
            }
        )

    return {
        "is_remote": False,
        "work_location_id": work_location.id,
        "work_location_name": work_location.name,
        "distance_meters": round(distance_meters, 1),
        "allowed_radius_meters": int(allowed_radius)
    }
