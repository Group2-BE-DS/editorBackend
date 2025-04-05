# codegen_app/urls.py
from django.urls import path
from .views import generate_code, GenerateDocsView

urlpatterns = [
    path('generate-code/', generate_code, name='generate-code'),
    path('generate-docs/<path:repo_slug>/', GenerateDocsView.as_view(), name='generate-docs'),
]