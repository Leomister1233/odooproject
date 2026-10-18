from .runtime import reset_active_client, set_active_client
from .services import get_client_by_domain, get_client_feature_map, get_current_client


class CurrentClientMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        hostname = request.get_host().split(":")[0].lower()
        is_authenticated = bool(request.session.get("portal_authenticated"))
        session_slug = request.session.get("active_client_slug") if is_authenticated else None
        client = get_current_client(session_slug=session_slug) if session_slug else get_client_by_domain(hostname)
        client_token = set_active_client(client)

        try:
            request.current_client = client
            request.client_features = get_client_feature_map(client)

            if client:
                request.session.setdefault("portal_language", client.default_language)
                request.session.setdefault("portal_currency", client.default_currency)

            return self.get_response(request)
        finally:
            reset_active_client(client_token)
