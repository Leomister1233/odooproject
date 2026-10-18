from datetime import datetime, timezone

from django import template

from core.currency import (
    PORTAL_CURRENCIES,
    build_set_currency_url,
    convert_currency_amount,
    get_portal_currency,
    get_portal_currency_snapshot,
    resolve_currency,
)
from core.i18n import (
    PORTAL_LANGUAGE_CHOICES,
    PORTAL_LANGUAGE_DEFAULT,
    PORTAL_LANGUAGES,
    build_set_language_url,
    build_toggle_language_url,
    get_portal_language,
    translate_portal_text,
)


register = template.Library()


@register.filter
def attr(value, key):
    if value is None or key is None:
        return ""

    if isinstance(value, dict):
        return value.get(key, "")

    try:
        return getattr(value, key)
    except AttributeError:
        return ""


@register.filter
def portal_t(value, request_or_language=None):
    if hasattr(request_or_language, "session"):
        language = get_portal_language(request_or_language)
    elif isinstance(request_or_language, str) and request_or_language in PORTAL_LANGUAGE_CHOICES:
        language = request_or_language
    else:
        language = PORTAL_LANGUAGE_DEFAULT

    return translate_portal_text(value, language)


@register.filter
def money(value, currency=None):
    converted_amount, resolved_currency = convert_currency_amount(
        amount=value,
        source_currency=currency,
        target_currency_code=get_portal_currency(),
        snapshot=get_portal_currency_snapshot(),
    )
    currency_label = resolved_currency["symbol"] if resolved_currency else ""
    formatted = f"{float(converted_amount):,.2f}"
    return f"{currency_label}\u00a0{formatted}" if currency_label else formatted


@register.simple_tag(takes_context=True)
def portal_lang(context):
    request = context.get("request")
    return get_portal_language(request)


@register.simple_tag(takes_context=True)
def toggle_portal_language_url(context):
    request = context.get("request")
    if request is None:
        return "/language/toggle/"

    return build_toggle_language_url(request.get_full_path())


@register.simple_tag(takes_context=True)
def portal_language_options(context):
    request = context.get("request")
    current_language = get_portal_language(request)
    current_path = request.get_full_path() if request else "/dashboard"

    options = []
    for language in PORTAL_LANGUAGES:
        options.append(
            {
                **language,
                "is_active": language["code"] == current_language,
                "url": build_set_language_url(current_path, language["code"]),
            }
        )
    return options


@register.simple_tag(takes_context=True)
def portal_currency(context):
    request = context.get("request")
    return get_portal_currency(request)


@register.simple_tag(takes_context=True)
def portal_currency_options(context):
    request = context.get("request")
    current_currency = get_portal_currency(request)
    current_path = request.get_full_path() if request else "/dashboard"

    options = []
    for currency in PORTAL_CURRENCIES:
        options.append(
            {
                **currency,
                "is_active": currency["code"] == current_currency,
                "url": build_set_currency_url(current_path, currency["code"]),
            }
        )
    return options


@register.simple_tag(takes_context=True)
def portal_currency_refresh_label(context):
    request = context.get("request")
    snapshot = get_portal_currency_snapshot(request)
    refreshed_at = (snapshot or {}).get("refreshed_at")
    if not refreshed_at:
        return ""

    try:
        refreshed_at_dt = datetime.fromisoformat(str(refreshed_at)).astimezone(timezone.utc)
    except ValueError:
        return ""

    return refreshed_at_dt.strftime("%Y-%m-%d %H:%M UTC")


@register.simple_tag(takes_context=True)
def query_update(context, *args):
    if len(args) % 2 != 0:
        return ""

    request = context.get("request")
    if request is None:
        return ""

    query = request.GET.copy()
    for key, value in zip(args[::2], args[1::2]):
        if value in (None, ""):
            query.pop(str(key), None)
        else:
            query[str(key)] = value

    encoded = query.urlencode()
    return f"?{encoded}" if encoded else ""
