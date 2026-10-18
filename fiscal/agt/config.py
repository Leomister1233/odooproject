from dataclasses import dataclass

from django.conf import settings

from .errors import AGTConfigurationError


@dataclass(frozen=True)
class AGTSettings:
    environment: str
    base_url: str
    username: str
    password: str
    connect_timeout: int
    read_timeout: int
    submissions_enabled: bool

    @classmethod
    def load(cls):
        return cls(
            environment=settings.AGT_ENVIRONMENT,
            base_url=settings.AGT_BASE_URL.rstrip("/"),
            username=settings.AGT_USERNAME,
            password=settings.AGT_PASSWORD,
            connect_timeout=settings.AGT_CONNECT_TIMEOUT_SECONDS,
            read_timeout=settings.AGT_READ_TIMEOUT_SECONDS,
            submissions_enabled=settings.AGT_SUBMISSIONS_ENABLED,
        )

    def validate_for_submission(self):
        if not self.submissions_enabled:
            raise AGTConfigurationError("AGT submissions are disabled.")
        if self.environment != "homologation" and not settings.AGT_ALLOW_PRODUCTION:
            raise AGTConfigurationError("Production AGT submissions require AGT_ALLOW_PRODUCTION=true.")
        if not all((self.base_url, self.username, self.password)):
            raise AGTConfigurationError("AGT endpoint credentials are incomplete.")
