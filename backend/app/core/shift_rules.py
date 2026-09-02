SHIFT_RULE_DEFAULTS = {
    "allow_early_punch_in": False,
    "early_coming_minutes": 60,
    "punch_in_grace_minutes": 10,
    "shift_grace_minutes": 15,
}


def normalize_shift_rule_values(values: dict) -> dict:
    """Replace explicit NULL shift-rule inputs with their documented defaults."""
    normalized = dict(values)
    for field, default in SHIFT_RULE_DEFAULTS.items():
        if field in normalized and normalized[field] is None:
            normalized[field] = default
    return normalized


def get_shift_rule_value(source, field: str):
    """Read a shift rule safely when legacy rows contain NULL values."""
    value = getattr(source, field, None)
    return SHIFT_RULE_DEFAULTS[field] if value is None else value
