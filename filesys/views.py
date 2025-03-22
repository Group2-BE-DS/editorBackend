import os
import shutil
import subprocess
import logging
from django.db.models import Q
from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import Repository, File
from .serializers import RepositorySerializer, FileSerializer
from .permissions import IsOwnerOrCollaborator

User = get_user_model()
logger = logging.getLogger(__name__)

class RepositoryViewSet(viewsets.ModelViewSet):
    serializer_class = RepositorySerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrCollaborator]
    lookup_field = 'slug'
    lookup_value_regex = '[\w-]+/[\w-]+'  # Allows slashes in the slug

    def get_queryset(self):
        # Show repositories where user is owner or collaborator
        return Repository.objects.filter(
            Q(user=self.request.user) | 
            Q(collaborators=self.request.user)
        ).distinct()

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

    @action(detail=False, methods=['get'], url_path='all')
    def list_all_repositories(self, request):
        """
        List all repositories with their full slugs and collaborators
        """
        repositories = Repository.objects.all().select_related('user').prefetch_related('collaborators')
        data = [{
            'slug': repo.slug,
            'name': repo.name,
            'description': repo.description,
            'owner': repo.user.username,
            'created_at': repo.created_at,
            'updated_at': repo.updated_at,
            'collaborators': [
                {
                    'username': user.username,
                    'id': user.id
                } for user in repo.collaborators.all()
            ],
            'is_owner': repo.user == request.user,
            'is_collaborator': request.user in repo.collaborators.all()
        } for repo in repositories]
        
        return Response({
            'count': len(data),
            'repositories': data
        })

    # Add new actions for managing collaborators
    @action(detail=True, methods=['post'], url_path='add-collaborator')
    def add_collaborator(self, request, slug=None):
        repository = self.get_object()
        if repository.user != request.user:
            return Response(
                {'error': 'Only repository owner can add collaborators'},
                status=status.HTTP_403_FORBIDDEN
            )

        user_id = request.data.get('user_id')
        try:
            user = User.objects.get(id=user_id)
            repository.collaborators.add(user)
            return Response({'message': f'Added {user.username} as collaborator'})
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'], url_path='remove-collaborator')
    def remove_collaborator(self, request, slug=None):
        repository = self.get_object()
        if repository.user != request.user:
            return Response(
                {'error': 'Only repository owner can remove collaborators'},
                status=status.HTTP_403_FORBIDDEN
            )

        user_id = request.data.get('user_id')
        try:
            user = User.objects.get(id=user_id)
            repository.collaborators.remove(user)
            return Response({'message': f'Removed {user.username} as collaborator'})
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class FileViewSet(viewsets.ModelViewSet):
    serializer_class = FileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrCollaborator]

    def get_queryset(self):
        try:
            repository = get_object_or_404(
                Repository,
                slug=self.kwargs['repository_slug']
            )
            if not repository.user_has_access(self.request.user):
                return File.objects.none()
            return File.objects.filter(repository=repository)
        except Exception as e:
            logger.error(f"Error in get_queryset: {str(e)}")
            return File.objects.none()

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            
            # Check access permission
            if not instance.user_has_access(request.user):
                return Response(
                    {'error': 'Access denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = self.get_serializer(instance)
            
            # Read actual file content
            file_path = os.path.join(instance.repository.location, instance.path)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    data = serializer.data
                    data['content'] = content
                    return Response(data)
                except UnicodeDecodeError:
                    logger.warning(f"Binary file detected: {file_path}")
                    return Response(
                        {'error': 'Cannot read binary file'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {str(e)}")
                    return Response(
                        {'error': f'Error reading file: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            else:
                return Response(
                    {'error': 'File not found on disk'},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            logger.error(f"Error retrieving file: {str(e)}")
            return Response(
                {'error': f'Error retrieving file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        repository = get_object_or_404(
            Repository.objects.filter(
                Q(user=self.request.user) | 
                Q(collaborators=self.request.user)
            ),
            slug=self.kwargs['repository_slug']
        )
        context['repository'] = repository
        return context

    @transaction.atomic
    def perform_create(self, serializer):
        repository = self.get_serializer_context()['repository']
        file_path = os.path.join(repository.location, serializer.validated_data['path'])
        
        # Ensure file path is within repository
        if not file_path.startswith(repository.location):
            raise serializers.ValidationError({'error': 'Invalid file path'})

        try:
            # Create directories if needed
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write file content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(serializer.validated_data.get('content', ''))
            
            # Save to database
            serializer.save(repository=repository)

            # Git operations
            try:
                subprocess.run(['git', 'add', serializer.validated_data['path']], 
                             cwd=repository.location, check=True)
                subprocess.run(['git', 'commit', '-m', f'Add {serializer.validated_data["path"]}'],
                             cwd=repository.location, check=True)
            except subprocess.CalledProcessError as e:
                logger.warning(f"Git operations failed: {e.stderr}")

        except OSError as e:
            raise serializers.ValidationError({'error': f'File operation failed: {str(e)}'})

    @transaction.atomic
    def perform_update(self, serializer):
        instance = self.get_object()
        repository = instance.repository
        file_path = os.path.join(repository.location, instance.path)

        if not file_path.startswith(repository.location):
            raise serializers.ValidationError({'error': 'Invalid file path'})

        try:
            # Update file content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(serializer.validated_data.get('content', instance.content))
            
            # Save to database
            serializer.save()

            # Git operations
            try:
                subprocess.run(['git', 'add', instance.path], 
                             cwd=repository.location, check=True)
                subprocess.run(['git', 'commit', '-m', f'Update {instance.path}'],
                             cwd=repository.location, check=True)
            except subprocess.CalledProcessError as e:
                logger.warning(f"Git operations failed: {e.stderr}")

        except OSError as e:
            raise serializers.ValidationError({'error': f'File operation failed: {str(e)}'})

    def perform_destroy(self, instance):
        if instance.repository.user != self.request.user:
            raise PermissionDenied('Only repository owner can delete files')

        file_path = os.path.join(instance.repository.location, instance.path)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                
                # Git operations
                try:
                    subprocess.run(['git', 'rm', instance.path], 
                                 cwd=instance.repository.location, check=True)
                    subprocess.run(['git', 'commit', '-m', f'Delete {instance.path}'],
                                 cwd=instance.repository.location, check=True)
                except subprocess.CalledProcessError as e:
                    logger.warning(f"Git operations failed: {e.stderr}")

            super().perform_destroy(instance)
        except OSError as e:
            raise serializers.ValidationError({'error': f'File deletion failed: {str(e)}'})