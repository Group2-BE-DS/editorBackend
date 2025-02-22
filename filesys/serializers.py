from rest_framework import serializers
from .models import Repository, File

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
        validated_data['location'] = f"{validated_data['user'].username}/{validated_data['name']}"
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Update the location if the name changes
        if 'name' in validated_data:
            validated_data['location'] = f"{instance.user.username}/{validated_data['name']}"
        return super().update(instance, validated_data)

class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = ['id', 'repository', 'path', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'repository', 'created_at', 'updated_at']

    def validate_path(self, value):
        """
        Ensure the file path is unique within the repository.
        """
        repository = self.context['request'].repository
        if File.objects.filter(repository=repository, path=value).exists():
            raise serializers.ValidationError("A file with this path already exists in the repository.")
        return value