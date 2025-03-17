from django.db import models
from django.conf import settings
import subprocess

class Repository(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=500, blank=True, null=True)  # Change to CharField for folder path
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # Automatically updates on save
    git_initialized = models.BooleanField(default=False)
    last_commit_hash = models.CharField(max_length=40, blank=True)

    class Meta:
        unique_together = ('user', 'name')  # Ensure unique repository names per user

    def __str__(self):
        return f"{self.name} ({self.user.username})"
    
    def get_git_status(self):
        """Get Git repository status."""
        try:
            result = subprocess.run(['git', 'status'], 
                                 cwd=self.location,
                                 capture_output=True, 
                                 text=True)
            return result.stdout
        except subprocess.CalledProcessError:
            return "Git status unavailable"
    
class File(models.Model):
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name='files')
    path = models.CharField(max_length=500)  # Relative path inside the repository
    content = models.TextField(blank=True, null=True)  # File content
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('repository', 'path')

    def __str__(self):
        return f"{self.path} ({self.repository.name})"
