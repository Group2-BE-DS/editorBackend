import os
import aiofiles
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.conf import settings
from .models import Repository, File
from .serializers import RepositorySerializer, FileSerializer

class RepositoryViewSet(viewsets.ModelViewSet):
    queryset = Repository.objects.all()
    serializer_class = RepositorySerializer
    permission_classes = [permissions.IsAuthenticated]  # Ensure only authenticated users can access

    def get_queryset(self):
        """
        Override the default queryset to return repositories for the authenticated user.
        """
        user = self.request.user
        return Repository.objects.filter(user=user)

    def perform_create(self, serializer):
        """
        Automatically set the user to the authenticated user when creating a repository.
        Also, create a folder for the repository.
        """
        user = self.request.user
        repo_name = serializer.validated_data['name']
        location = os.path.join(settings.BASE_DIR, 'c3', user.username, repo_name)

        # Create the folder
        os.makedirs(location, exist_ok=True)

        # Save the repository with the location
        serializer.save(user=user, location=location)

    def create(self, request, *args, **kwargs):
        """
        Handle repository creation.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_destroy(self, instance):
        """
        Delete the repository folder when the repository is deleted.
        """
        if os.path.exists(instance.location):
            # Delete the folder and its contents
            os.rmdir(instance.location)  # Use shutil.rmtree for non-empty directories
        super().perform_destroy(instance)

    def destroy(self, request, *args, **kwargs):
        """
        Handle deleting a repository.
        """
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class FileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Return files for the authenticated user's repository.
        """
        user = self.request.user
        repository_id = self.kwargs.get('repository_id')
        return File.objects.filter(repository__user=user, repository_id=repository_id)

    async def perform_create(self, serializer):
        """
        Create a file and write its content to the filesystem.
        """
        repository = serializer.validated_data['repository']
        file_path = os.path.join(repository.location, serializer.validated_data['path'])

        # Create the file on the filesystem
        async with aiofiles.open(file_path, 'w') as f:
            await f.write(serializer.validated_data.get('content', ''))

        # Save the file in the database
        serializer.save()

    async def perform_update(self, serializer):
        """
        Update the file content on the filesystem.
        """
        instance = serializer.instance
        file_path = os.path.join(instance.repository.location, instance.path)

        # Update the file on the filesystem
        async with aiofiles.open(file_path, 'w') as f:
            await f.write(serializer.validated_data.get('content', ''))

        # Save the updated file in the database
        serializer.save()

    async def perform_destroy(self, instance):
        """
        Delete the file from the filesystem and the database.
        """
        file_path = os.path.join(instance.repository.location, instance.path)

        # Delete the file from the filesystem
        if os.path.exists(file_path):
            os.remove(file_path)

        # Delete the file from the database
        await super().perform_destroy(instance)