from django.db import models
from django.conf import settings

class Repository(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=500, blank=True, null=True)  # Change to CharField for folder path
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # Automatically updates on save

    def __str__(self):
        return f"{self.name} ({self.user.username})"
    
class File(models.Model):
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name='files')
    path = models.CharField(max_length=500)  # Relative path inside the repository
    content = models.TextField(blank=True, null=True)  # File content
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.path} ({self.repository.name})"
