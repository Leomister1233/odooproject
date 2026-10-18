from django.db import transaction
from django.utils import timezone

from fiscal.models import FiscalEvent, FiscalState


@transaction.atomic
def record_submission_result(*, submission, state, response_payload, request_id=""):
    if state not in FiscalState.values:
        raise ValueError("Unsupported fiscal state.")
    previous_state = submission.state
    submission.state = state
    submission.response_payload = response_payload or {}
    submission.request_id = request_id
    submission.save(update_fields=("state", "response_payload", "request_id", "updated_at"))
    document = submission.document
    document.state = state
    document.agt_request_id = request_id
    if state in {FiscalState.SUBMITTED, FiscalState.PROCESSING, FiscalState.ACCEPTED} and not document.submitted_at:
        document.submitted_at = timezone.now()
    document.save(update_fields=("state", "agt_request_id", "submitted_at", "updated_at"))
    FiscalEvent.objects.create(company=submission.company, document=document, action="submission_result", previous_state=previous_state, new_state=state)

