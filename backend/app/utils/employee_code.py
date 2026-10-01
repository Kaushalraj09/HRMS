import re
from typing import Optional

_AIVAN_PATTERN = re.compile(r"^(?:AIVAN)[-_\s]?(\d+)$", re.IGNORECASE)
_GENERIC_CODE_CLEAN = re.compile(r"\s+")


def format_employee_code(num: int, prefix: str = "AIVAN", padding: int = 3) -> str:
    """Format sequential number into company standard employee code.
    
    Examples:
        1   -> AIVAN001
        24  -> AIVAN024
        100 -> AIVAN100
        999 -> AIVAN999
        1000 -> AIVAN1000
    """
    clean_prefix = (prefix or "AIVAN").strip().upper()
    pad = max(1, padding)
    if num < 10**pad:
        return f"{clean_prefix}{num:0{pad}d}"
    return f"{clean_prefix}{num}"


def extract_employee_code_number(code: str, prefix: str = "AIVAN") -> Optional[int]:
    """Extract integer sequence from employee code if matching company prefix."""
    if not code or not isinstance(code, str):
        return None
    s = code.strip()
    pattern = re.compile(rf"^(?:{re.escape(prefix)})[-_\s]?(\d+)$", re.IGNORECASE)
    m = pattern.match(s)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


def is_aivan_code(code: str) -> bool:
    """Check if code follows the AIVAN pattern."""
    return extract_employee_code_number(code, "AIVAN") is not None


def normalize_employee_code(code: str, prefix: str = "AIVAN", padding: int = 3) -> str:
    """Normalize company employee code to canonical display form.
    
    Standardizes:
        aivan024  -> AIVAN024
        Aivan-24  -> AIVAN024
        AIVAN 024 -> AIVAN024
        AIVAN1    -> AIVAN001
        AIVAN1000 -> AIVAN1000
        
    For legacy codes (e.g. OLD-EMP-458, EMP0001, 0004), strips whitespace and returns uppercase
    without destructive modification.
    """
    if not code or not isinstance(code, str):
        return ""
    s = code.strip()
    m = _AIVAN_PATTERN.match(s)
    if m:
        num = int(m.group(1))
        return format_employee_code(num, prefix=prefix, padding=padding)
    
    # Generic normalization for legacy or external codes
    return _GENERIC_CODE_CLEAN.sub(" ", s).upper()
