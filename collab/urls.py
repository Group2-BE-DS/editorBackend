from django.urls import path
from .views import VerificationCodeAPI, VerifyUserAPI, VerifyCodeAPI

urlpatterns = [
    path('generate-code/', VerificationCodeAPI.as_view(), name='generate-code'),
    path('verify-user/<str:username>/', VerifyUserAPI.as_view(), name='verify-user'),
    path('verify-code/<str:code>/', VerifyCodeAPI.as_view(), name='verify-code'),
]