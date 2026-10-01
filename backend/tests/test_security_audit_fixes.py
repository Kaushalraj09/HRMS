import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from app.main import app
from app.services.training_service import _validate_training_file


client = TestClient(app)


def test_csp_header_does_not_contain_unsafe_eval():
    """Verify CSP header strictly forbids unsafe-eval to mitigate XSS."""
    response = client.get("/health")
    csp = response.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "'unsafe-eval'" not in csp, "CSP must not contain 'unsafe-eval'"


def test_training_file_validation_rejects_svg():
    """Verify SVG files are explicitly rejected to prevent stored XSS."""
    with pytest.raises(HTTPException) as exc_info:
        _validate_training_file("svg", b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>")
    assert exc_info.value.status_code == 400
    assert "SVG files are not permitted" in exc_info.value.detail


def test_training_file_validation_signature_checks():
    """Verify server-side file signature validation rejects mismatched magic bytes."""
    # Invalid PDF (plain text pretending to be PDF)
    with pytest.raises(HTTPException) as exc_info:
        _validate_training_file("pdf", b"This is not a pdf file")
    assert exc_info.value.status_code == 400
    assert "Missing %PDF- signature" in exc_info.value.detail

    # Valid PDF signature returns canonical mime type
    mime = _validate_training_file("pdf", b"%PDF-1.4\n...")
    assert mime == "application/pdf"

    # Valid PNG signature returns canonical mime type
    mime = _validate_training_file("png", b"\x89PNG\r\n\x1a\n\x00\x00...")
    assert mime == "image/png"

    # Valid JPEG signature returns canonical mime type
    mime = _validate_training_file("jpg", b"\xff\xd8\xff\xe0\x00\x10JFIF...")
    assert mime == "image/jpeg"


def test_training_response_schema_excludes_storage_path():
    """Verify TrainingMaterialResponse schema does not serialize server storage_path."""
    from app.schemas.training import TrainingMaterialResponse
    fields = TrainingMaterialResponse.model_fields.keys()
    assert "storage_path" not in fields, "storage_path must not be exposed in public API response schema"
