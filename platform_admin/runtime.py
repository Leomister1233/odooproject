from contextvars import ContextVar


_ACTIVE_CLIENT = ContextVar("active_client", default=None)


def set_active_client(client):
    return _ACTIVE_CLIENT.set(client)


def reset_active_client(token):
    _ACTIVE_CLIENT.reset(token)


def get_active_client():
    return _ACTIVE_CLIENT.get()


