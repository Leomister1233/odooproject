from django.contrib import admin

from .models import AGTSubmission, FiscalConfiguration, FiscalDocument, FiscalEvent, FiscalSeries, OutboxEvent, SubmissionAttempt

admin.site.register((FiscalConfiguration, FiscalSeries, FiscalDocument, AGTSubmission, SubmissionAttempt, OutboxEvent, FiscalEvent))
