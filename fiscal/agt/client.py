import base64
import json
import urllib.error
import urllib.request

from .config import AGTSettings
from .errors import AGTTransportError


class AGTClient:
    def __init__(self, config=None, opener=None):
        self.config = config or AGTSettings.load()
        self.opener = opener or urllib.request.urlopen

    def submit_invoice(self, signed_payload):
        self.config.validate_for_submission()
        credentials = base64.b64encode(f"{self.config.username}:{self.config.password}".encode()).decode()
        request = urllib.request.Request(
            f"{self.config.base_url}/invoices",
            data=json.dumps({"signedPayload": signed_payload}).encode("utf-8"),
            headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with self.opener(request, timeout=self.config.read_timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise AGTTransportError("The AGT service could not confirm the submission outcome.") from exc

