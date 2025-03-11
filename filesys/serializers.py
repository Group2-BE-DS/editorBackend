from rest_framework import serializers
from .models import Repository, File
from django.conf import settings
import os

class RepositorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Repository
        fields = ['id', 'user', 'name', 'description', 'location', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def validate_name(self, value):
        # Ensure the repository name is unique for the user
        user = self.context['request'].user
        if Repository.objects.filter(user=user, name=value).exists():
            raise serializers.ValidationError("A repository with this name already exists for this user.")
        return value

    def create(self, validated_data):
        # Set the user to the currently authenticated user
        validated_data['user'] = self.context['request'].user
        # Set the location to username/repo-name
        validated_data['location'] = os.path.join(settings.BASE_DIR, 'c3', validated_data['user'].username, validated_data['name'])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Update the location if the name changes
        if 'name' in validated_data:
            validated_data['location'] = os.path.join(settings.BASE_DIR, 'c3', instance.user.username, validated_data['name'])
        return super().update(instance, validated_data)
    

class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = ['id', 'repository', 'path', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'repository', 'created_at', 'updated_at']

    def validate_path(self, value):
        """
        Ensure the file path is unique within the repository and does not contain invalid characters.
        """
        repository = self.context.get('repository')
        if not repository:
            raise serializers.ValidationError("Repository not found in context.")

        # Validate path format
        if any(char in value for char in ['..', '\\', ':']):
            raise serializers.ValidationError("File path contains invalid characters.")

        if File.objects.filter(repository=repository, path=value).exists():
            raise serializers.ValidationError("A file with this path already exists in the repository.")

        return value