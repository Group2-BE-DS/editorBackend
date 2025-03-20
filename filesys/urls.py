from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RepositoryViewSet, FileViewSet

router = DefaultRouter()
router.register(r'', RepositoryViewSet, basename='repository')
router.register(r'(?P<repository_slug>[\w-]+/[\w-]+)/files', FileViewSet, basename='file')

urlpatterns = [
    path('', include(router.urls)),
]