from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RepositoryViewSet, FileViewSet

router = DefaultRouter()
router.register(r'repositories', RepositoryViewSet)
router.register(r'repositories/(?P<repository_id>\d+)/files', FileViewSet, basename='file')

urlpatterns = [
    path('', include(router.urls)),
]