from django.urls import path, re_path
from . import views

urlpatterns = [
    re_path(r'^(?P<repository_slug>[\w-]+/[\w-]+)/commit-main/$',
         views.commit_to_main_branch, 
         name='commit-to-main'),
]