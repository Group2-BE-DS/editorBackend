from django.urls import path
from .views import VerificationCodeAPI

urlpatterns = [
    path('generate-code/', VerificationCodeAPI.as_view(), name='generate-code'),
]