import os
import shutil
import subprocess
import logging
from rest_framework import viewsets, permissions, serializers
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import Repository, File
from .serializers import RepositorySerializer, FileSerializer

logger = logging.getLogger(__name__)

class RepositoryViewSet(viewsets.ModelViewSet):
    queryset = Repository.objects.all()
    serializer_class = RepositorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return repositories for the authenticated user."""
        return Repository.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Create repository with proper directory structure and initialize Git."""
        user = self.request.user
        repo_name = serializer.validated_data['name']
        
        # Create path: BASE_DIR/c3/username/repository-name
        base_path = os.path.join(settings.BASE_DIR, 'c3')
        user_dir = os.path.join(base_path, user.username)
        repo_dir = os.path.join(user_dir, repo_name)

        try:
            # Create all necessary directories
            os.makedirs(user_dir, exist_ok=True)
            os.makedirs(repo_dir, exist_ok=True)
            
            # Initialize Git repository
            try:
                # Remove any existing .git directory to ensure clean initialization
                git_dir = os.path.join(repo_dir, '.git')
                if os.path.exists(git_dir):
                    shutil.rmtree(git_dir)
                
                # Initialize new Git repository
                result = subprocess.run(['git', 'init'], cwd=repo_dir, check=True,
                                     capture_output=True, text=True)
                logger.info(f"Git init result: {result.stdout}")
                
                # Create .gitignore file
                gitignore_path = os.path.join(repo_dir, '.gitignore')
                with open(gitignore_path, 'w') as f:
                    f.write("""# Python
__pycache__/
*.py[cod]
*.so
.env
.venv/
venv/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
""")
                
                # Initial commit
                subprocess.run(['git', 'add', '.'], cwd=repo_dir, check=True)
                subprocess.run(['git', 'config', '--local', 'user.email', user.email], 
                             cwd=repo_dir, check=True)
                subprocess.run(['git', 'config', '--local', 'user.name', user.username], 
                             cwd=repo_dir, check=True)
                
                # Check if there are files to commit
                status = subprocess.run(['git', 'status', '--porcelain'], 
                                     cwd=repo_dir, capture_output=True, text=True)
                if status.stdout.strip():
                    subprocess.run(['git', 'commit', '-m', 'Initial commit'], 
                                 cwd=repo_dir, check=True)
                    logger.info(f"Created initial commit for repository: {repo_name}")
                
            except subprocess.CalledProcessError as e:
                logger.error(f"Git initialization failed: {e.stderr}")
                raise serializers.ValidationError(
                    {'error': f'Git initialization failed: {e.stderr}'}
                )
            
            # Save repository with the correct path
            serializer.save(user=user, location=repo_dir)
            
        except OSError as e:
            logger.error(f"Directory operation failed: {str(e)}")
            raise serializers.ValidationError(
                {'error': f'Directory creation failed: {str(e)}'}
            )

    def perform_destroy(self, instance):
        """Delete repository directory atomically."""
        try:
            if os.path.exists(instance.location):
                shutil.rmtree(instance.location)
            super().perform_destroy(instance)
        except OSError as e:
            raise serializers.ValidationError(
                {'error': f'Directory deletion failed: {str(e)}'}
                )


class FileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Get files for current repository."""
        repository = get_object_or_404(
            Repository,
            id=self.kwargs['repository_id'],
            user=self.request.user
        )
        return File.objects.filter(repository=repository)

    def get_serializer_context(self):
        """Add repository to serializer context."""
        context = super().get_serializer_context()
        context['repository'] = get_object_or_404(
            Repository,
            id=self.kwargs['repository_id'],
            user=self.request.user
        )
        return context

    @transaction.atomic
    def perform_create(self, serializer):
        """Create file with proper path validation."""
        repository = self.get_serializer_context()['repository']
        file_path = os.path.join(repository.location, serializer.validated_data['path'])
        
        # Security check: Prevent directory traversal
        if not file_path.startswith(repository.location):
            raise serializers.ValidationError(
                {'error': 'Invalid file path'}
            )

        try:
            # Create parent directories if needed
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Create or overwrite file
            with open(file_path, 'w') as f:
                f.write(serializer.validated_data.get('content', ''))
            
            # Save file record
            serializer.save(repository=repository)
        except OSError as e:
            raise serializers.ValidationError(
                {'error': f'File operation failed: {str(e)}'}
                )