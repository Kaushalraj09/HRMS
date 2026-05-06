import re

_EMP_HYPHEN = re.compile(r"^EMP-(\d+)$", re.IGNORECASE)
_EMP_PLAIN = re.compile(r"^EMP(\d+)$", re.IGNORECASE)


def normalize_employee_code(code: str) -> str:
    """Return canonical display form EMP-#### for legacy values like EMP003 or EMP-5."""
    if not code or not isinstance(code, str):
        return code
    s = code.strip()
    m = _EMP_HYPHEN.match(s)
    if m:
        return f"EMP-{int(m.group(1)):04d}"
    m = _EMP_PLAIN.match(s)
    if m:
        return f"EMP-{int(m.group(1)):04d}"
    return s
