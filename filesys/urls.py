from django.urls import path
from . import views

urlpatterns = [
    path('create-repository/', views.CreateRepository, name='create-repository'),
    path('update-repository/<int:pk>/', views.UpdateRepository, name='update-repository'),
        path('delete-repository/<int:pk>/', views.DeleteRepository, name='delete-repository'),



]
