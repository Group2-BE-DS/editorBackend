from django.db import models
from django.conf import settings
import subprocess
import magic  # Works with python-magic-bin on Windows
from django.utils.text import slugify

class Repository(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=500, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    git_initialized = models.BooleanField(default=False)
    last_commit_hash = models.CharField(max_length=40, blank=True)
    collaborators = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='collaborative_repositories',
        blank=True
    )

    class Meta:
        unique_together = ('user', 'name')

    def __str__(self):
        return f"{self.user.username}/{self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = f"{self.user.username}/{slugify(self.name)}"
        super().save(*args, **kwargs)

    def get_git_status(self):
        try:
            result = subprocess.run(['git', 'status'], 
                                   cwd=self.location,
                                   capture_output=True, 
                                   text=True)
            return result.stdout
        except subprocess.CalledProcessError:
            return "Git status unavailable"

    def user_has_access(self, user):
        """Check if user has access (owner or collaborator)"""
        return user == self.user or self.collaborators.filter(id=user.id).exists()

class File(models.Model):
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name='files')
    path = models.CharField(max_length=500)
    content = models.TextField(blank=True, null=True)
    language = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('repository', 'path')

    def __str__(self):
        return f"{self.path} ({self.repository.name})"

    def detect_language(self):
        """Detect the programming language of the file based on its extension or content."""
        if not self.content:
            return None
        
        # Use python-magic-bin compatible detection
        mime_detector = magic.Magic(mime=True)
        file_type = mime_detector.from_buffer(self.content.encode('utf-8'))
        
        # Simple mapping based on extension or MIME type
        extension = self.path.split('.')[-1].lower() if '.' in self.path else ''
        language_map = {
            'py': 'python',
            'js': 'javascript',
            'md': 'markdown',
            'html': 'html',
            'css': 'css',
            'java': 'java',
            'c': 'c',
            'cpp': 'cpp',
            'txt': 'plaintext',
        }
        return language_map.get(extension, 'plaintext')  # Default to plaintext if unknown