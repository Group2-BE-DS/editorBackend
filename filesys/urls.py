from django.urls import path
from .views import FileSystemView

urlpatterns = [
    path('api/files/', FileSystemView.as_view(), name='filesystem'),
    path('api/files/<path:path>/', FileSystemView.as_view(), name='filesystem_path'),
]
