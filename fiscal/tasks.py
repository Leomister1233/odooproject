from django.db import transaction
from django.utils import timezone

from fiscal.agt.config import AGTSettings
from fiscal.agt.errors import AGTConfigurationError
from fiscal.models import OutboxEvent


def process_outbox_event(event_id):
    AGTSettings.load().validate_for_submission()
    with transaction.atomic():
        event = OutboxEvent.objects.select_for_update().get(pk=event_id)
        if event.state == "complete":
            return event
        event.state = "processing"
        event.locked_at = timezone.now()
        event.attempts += 1
        event.save(update_fields=("state", "locked_at", "attempts", "updated_at"))
    raise AGTConfigurationError("A producer-key resolver must be configured before processing AGT submissions.")

