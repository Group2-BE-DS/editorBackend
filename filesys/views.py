import os
import shutil
from rest_framework import viewsets, permissions, serializers
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import Repository, File
from .serializers import RepositorySerializer, FileSerializer


class RepositoryViewSet(viewsets.ModelViewSet):
    queryset = Repository.objects.all()
    serializer_class = RepositorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return repositories for the authenticated user."""
        return Repository.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Create repository with proper directory structure."""
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
            
            # Save repository with the correct path
            serializer.save(user=user, location=repo_dir)
        except OSError as e:
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