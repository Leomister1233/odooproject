from django.urls import path

from . import views

urlpatterns = [
    path("fiscal/documents", views.document_list, name="fiscal_documents"),
    path("fiscal/documents/<int:document_id>", views.document_detail, name="fiscal_document_detail"),
    path("fiscal/submissions", views.submission_list, name="fiscal_submissions"),
    path("fiscal/settings", views.configuration, name="fiscal_configuration"),
]

