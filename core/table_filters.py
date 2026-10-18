from datetime import datetime


def normalize_text(value):
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        if len(value) > 1:
            return str(value[1] or "")
        if value:
            return str(value[0] or "")
        return ""
    return str(value)


def normalize_many2one_id(value):
    if isinstance(value, (list, tuple)) and value:
        return str(value[0])
    if value is None:
        return ""
    return str(value)


def contains_text(value, query):
    if not query:
        return True
    return query.lower() in normalize_text(value).lower()


def matches_many2one(value, expected_id):
    if not expected_id:
        return True
    return normalize_many2one_id(value) == str(expected_id)


def matches_exact(value, expected):
    if expected in (None, ""):
        return True
    return str(value or "") == str(expected)


def matches_date_range(value, date_from=None, date_to=None):
    if not value:
        return not date_from and not date_to

    raw = str(value)[:10]
    try:
        current = datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return False

    if date_from:
        start = datetime.strptime(str(date_from), "%Y-%m-%d").date()
        if current < start:
            return False
    if date_to:
        end = datetime.strptime(str(date_to), "%Y-%m-%d").date()
        if current > end:
            return False
    return True
