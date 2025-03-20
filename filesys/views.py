import os
import shutil
import subprocess
import logging
from rest_framework import viewsets, permissions, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import Repository, File
from .serializers import RepositorySerializer, FileSerializer

logger = logging.getLogger(__name__)

class RepositoryViewSet(viewsets.ModelViewSet):
    serializer_class = RepositorySerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'slug'
    lookup_value_regex = '[\w-]+/[\w-]+'  # Allows slashes in the slug

    def get_queryset(self):
        return Repository.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        repo_name = serializer.validated_data['name']
        base_path = os.path.join(settings.BASE_DIR, 'c3')
        user_dir = os.path.join(base_path, user.username)
        repo_dir = os.path.join(user_dir, repo_name)

        try:
            os.makedirs(user_dir, exist_ok=True)
            os.makedirs(repo_dir, exist_ok=True)
            
            try:
                git_dir = os.path.join(repo_dir, '.git')
                if os.path.exists(git_dir):
                    shutil.rmtree(git_dir)
                
                result = subprocess.run(['git', 'init'], cwd=repo_dir, check=True,
                                     capture_output=True, text=True)
                logger.info(f"Git init result: {result.stdout}")
                
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
                
                subprocess.run(['git', 'add', '.'], cwd=repo_dir, check=True)
                subprocess.run(['git', 'config', '--local', 'user.email', user.email], 
                             cwd=repo_dir, check=True)
                subprocess.run(['git', 'config', '--local', 'user.name', user.username], 
                             cwd=repo_dir, check=True)
                
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
            
            serializer.save(user=user, location=repo_dir)
            
        except OSError as e:
            logger.error(f"Directory operation failed: {str(e)}")
            raise serializers.ValidationError(
                {'error': f'Directory creation failed: {str(e)}'}
            )

    def perform_destroy(self, instance):
        try:
            if os.path.exists(instance.location):
                shutil.rmtree(instance.location)
            super().perform_destroy(instance)
        except OSError as e:
            raise serializers.ValidationError(
                {'error': f'Directory deletion failed: {str(e)}'}
                )

    @action(detail=True, methods=['get'], url_path='contents')
    def get_contents(self, request, pk=None):
        repository = self.get_object()
        files = File.objects.filter(repository=repository)
        
        db_files = [
            {
                'path': file.path,
                'content': file.content,
                'language': file.language or file.detect_language()
            } for file in files
        ]
        
        fs_files = []
        git_dir = os.path.join(repository.location, '.git')
        for root, _, filenames in os.walk(repository.location):
            if root.startswith(git_dir):
                continue
            for filename in filenames:
                if filename.startswith('.') or filename == 'gitignore':
                    continue
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, repository.location)
                if any(f['path'] == rel_path for f in db_files):
                    continue
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    file_obj = File(repository=repository, path=rel_path, content=content)
                    fs_files.append({
                        'path': rel_path,
                        'content': content,
                        'language': file_obj.detect_language()
                    })
                except (IOError, UnicodeDecodeError) as e:
                    logger.warning(f"Could not read file {file_path}: {str(e)}")
                    continue

        response_data = {
            'repo_id': repository.id,
            'name': repository.name,
            'description': repository.description,
            'files': db_files + fs_files
        }
        return Response(response_data)

    def get_object(self):
        """
        Override to allow looking up by slug
        """
        queryset = self.get_queryset()
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        if 'slug' in self.kwargs:
            filter_kwargs = {'slug': self.kwargs['slug']}
        else:
            filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        return get_object_or_404(queryset, **filter_kwargs)

class FileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        repository = get_object_or_404(
            Repository,
            slug=self.kwargs['repository_slug'],
            user=self.request.user
        )
        return File.objects.filter(repository=repository)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['repository'] = get_object_or_404(
            Repository,
            slug=self.kwargs['repository_slug'],
            user=self.request.user
        )
        return context

    @transaction.atomic
    def perform_create(self, serializer):
        repository = self.get_serializer_context()['repository']
        file_path = os.path.join(repository.location, serializer.validated_data['path'])
        
        if not file_path.startswith(repository.location):
            raise serializers.ValidationError(
                {'error': 'Invalid file path'}
            )

        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(serializer.validated_data.get('content', ''))
            serializer.save(repository=repository)
        except OSError as e:
            raise serializers.ValidationError(
                {'error': f'File operation failed: {str(e)}'}
            )

    @transaction.atomic
    def perform_update(self, serializer):
        """Handle file content updates and sync with filesystem."""
        instance = self.get_object()  # The file being updated
        repository = instance.repository
        file_path = os.path.join(repository.location, instance.path)

        if not file_path.startswith(repository.location):
            raise serializers.ValidationError({'error': 'Invalid file path'})

        # Save updated data to database
        serializer.save()

        # Sync updated content to filesystem
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(serializer.validated_data.get('content', instance.content))
        except OSError as e:
            raise serializers.ValidationError(
                {'error': f'File operation failed: {str(e)}'}
            )