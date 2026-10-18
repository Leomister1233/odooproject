from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import urlencode


PORTAL_CURRENCY_DEFAULT = "EUR"
PORTAL_CURRENCY_CHOICES = {"EUR", "USD", "AOA"}
PORTAL_CURRENCIES = (
    {"code": "EUR", "label": "Euro", "symbol": "€", "short_label": "EUR"},
    {"code": "USD", "label": "US Dollar", "symbol": "$", "short_label": "USD"},
    {"code": "AOA", "label": "Angolan Kwanza", "symbol": "Kz", "short_label": "AOA"},
)
PORTAL_CURRENCY_CACHE_SECONDS = 900

_PORTAL_CURRENCY_MAP = {currency["code"]: currency for currency in PORTAL_CURRENCIES}
_CURRENCY_ALIASES = {
    "€": "EUR",
    "EUR": "EUR",
    "EURO": "EUR",
    "$": "USD",
    "USD": "USD",
    "US DOLLAR": "USD",
    "US DOLLARS": "USD",
    "AOA": "AOA",
    "KZ": "AOA",
    "KWANZA": "AOA",
    "ANGOLAN KWANZA": "AOA",
}
_ACTIVE_PORTAL_CURRENCY = ContextVar("active_portal_currency", default=PORTAL_CURRENCY_DEFAULT)
_ACTIVE_PORTAL_CURRENCY_SNAPSHOT = ContextVar("active_portal_currency_snapshot", default={})


def _now_utc():
    return datetime.now(timezone.utc)


def _snapshot_is_fresh(snapshot):
    refreshed_at = snapshot.get("refreshed_at")
    if not refreshed_at:
        return False

    try:
        refreshed_at_dt = datetime.fromisoformat(str(refreshed_at))
    except ValueError:
        return False

    return refreshed_at_dt >= _now_utc() - timedelta(seconds=PORTAL_CURRENCY_CACHE_SECONDS)


def _safe_decimal(value, default="0"):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def _serialize_decimal(value):
    return format(_safe_decimal(value), "f")


def lookup_portal_currency(currency_code):
    return _PORTAL_CURRENCY_MAP.get(str(currency_code or "").upper())


def get_portal_currency(request=None):
    if request is None:
        return _ACTIVE_PORTAL_CURRENCY.get()

    currency_code = str(request.session.get("portal_currency", PORTAL_CURRENCY_DEFAULT)).upper()
    if currency_code not in PORTAL_CURRENCY_CHOICES:
        return PORTAL_CURRENCY_DEFAULT
    return currency_code


def build_set_currency_url(current_path, currency_code):
    query = urlencode({"next": current_path or "/dashboard"})
    return f"/currency/set/{currency_code}/?{query}"


def _build_currency_snapshot_rows(rows):
    rows_by_code = {}
    for row in rows:
        code = str(row.get("name") or "").upper()
        currency = lookup_portal_currency(code)
        if not currency:
            continue

        rows_by_code[code] = {
            **currency,
            "odoo_id": row.get("id"),
            "active": bool(row.get("active")),
            "rate": _serialize_decimal(row.get("rate", 0)),
        }

    snapshot = {}
    for currency in PORTAL_CURRENCIES:
        current = rows_by_code.get(currency["code"], {})
        snapshot[currency["code"]] = {
            **currency,
            "odoo_id": current.get("odoo_id"),
            "active": current.get("active", False),
            "rate": current.get("rate", "0"),
        }

    return snapshot


def build_fallback_currency_snapshot():
    currencies = {}
    for currency in PORTAL_CURRENCIES:
        currencies[currency["code"]] = {
            **currency,
            "odoo_id": None,
            "active": True,
            "rate": "1" if currency["code"] == PORTAL_CURRENCY_DEFAULT else "0",
        }

    return {
        "currencies": currencies,
        "refreshed_at": _now_utc().isoformat(),
    }


def fetch_portal_currency_snapshot():
    from accounting.services.odoo_accounting import OdooAccountingService

    service = OdooAccountingService()
    rows = service.get_currencies(codes=PORTAL_CURRENCY_CHOICES, include_inactive=True)
    return {
        "currencies": _build_currency_snapshot_rows(rows),
        "refreshed_at": _now_utc().isoformat(),
    }


def get_portal_currency_snapshot(request=None, force_refresh=False):
    if request is None:
        return _ACTIVE_PORTAL_CURRENCY_SNAPSHOT.get()

    snapshot = request.session.get("portal_currency_snapshot") or {}
    currencies = snapshot.get("currencies") or {}
    has_all_portal_currencies = PORTAL_CURRENCY_CHOICES.issubset(set(currencies.keys()))

    if force_refresh or not has_all_portal_currencies or not _snapshot_is_fresh(snapshot):
        try:
            snapshot = fetch_portal_currency_snapshot()
        except Exception:
            snapshot = snapshot if has_all_portal_currencies else build_fallback_currency_snapshot()
        request.session["portal_currency_snapshot"] = snapshot

    return snapshot


def set_active_portal_currency(request=None):
    return _ACTIVE_PORTAL_CURRENCY.set(get_portal_currency(request))


def reset_active_portal_currency(token):
    _ACTIVE_PORTAL_CURRENCY.reset(token)


def set_active_portal_currency_snapshot(snapshot):
    return _ACTIVE_PORTAL_CURRENCY_SNAPSHOT.set(snapshot or {})


def reset_active_portal_currency_snapshot(token):
    _ACTIVE_PORTAL_CURRENCY_SNAPSHOT.reset(token)


def resolve_currency(currency):
    raw_value = ""
    if isinstance(currency, (list, tuple)) and len(currency) > 1:
        raw_value = str(currency[1] or "").strip()
    elif isinstance(currency, dict):
        raw_value = str(currency.get("code") or currency.get("name") or currency.get("symbol") or "").strip()
    elif isinstance(currency, str):
        raw_value = currency.strip()

    if not raw_value:
        return None

    alias = _CURRENCY_ALIASES.get(raw_value.upper())
    if alias:
        return lookup_portal_currency(alias)

    return {
        "code": raw_value.upper(),
        "label": raw_value,
        "symbol": raw_value,
        "short_label": raw_value.upper(),
    }


def convert_currency_amount(amount, source_currency, target_currency_code=None, snapshot=None):
    source = resolve_currency(source_currency)
    target_code = str(target_currency_code or get_portal_currency()).upper()
    target = lookup_portal_currency(target_code)
    snapshot = snapshot or _ACTIVE_PORTAL_CURRENCY_SNAPSHOT.get() or {}
    currency_rows = snapshot.get("currencies") or {}

    if source is None or target is None:
        return _safe_decimal(amount), source or target

    if source["code"] == target["code"]:
        return _safe_decimal(amount), target

    source_row = currency_rows.get(source["code"])
    target_row = currency_rows.get(target["code"])
    if not source_row or not target_row:
        return _safe_decimal(amount), source

    source_rate = _safe_decimal(source_row.get("rate"))
    target_rate = _safe_decimal(target_row.get("rate"))
    if source_rate <= 0 or target_rate <= 0:
        return _safe_decimal(amount), source

    converted = (_safe_decimal(amount) / source_rate) * target_rate
    converted = converted.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return converted, target


class PortalCurrencyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        currency_token = set_active_portal_currency(request)
        snapshot = get_portal_currency_snapshot(request)
        snapshot_token = set_active_portal_currency_snapshot(snapshot)
        try:
            return self.get_response(request)
        finally:
            reset_active_portal_currency_snapshot(snapshot_token)
            reset_active_portal_currency(currency_token)
