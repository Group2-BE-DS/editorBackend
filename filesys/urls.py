from django.urls import path
from .views import CreateRepository

urlpatterns = [
    path('create-repository/', CreateRepository, name='create-repository'),

]
