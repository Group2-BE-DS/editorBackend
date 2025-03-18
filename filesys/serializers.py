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
        user = self.context['request'].user
        if Repository.objects.filter(user=user, name=value).exists():
            raise serializers.ValidationError("A repository with this name already exists for this user.")
        return value

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        validated_data['location'] = os.path.join(settings.BASE_DIR, 'c3', validated_data['user'].username, validated_data['name'])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'name' in validated_data:
            validated_data['location'] = os.path.join(settings.BASE_DIR, 'c3', instance.user.username, validated_data['name'])
        return super().update(instance, validated_data)

class FileSerializer(serializers.ModelSerializer):
    language = serializers.CharField(read_only=True)

    class Meta:
        model = File
        fields = ['id', 'repository', 'path', 'content', 'language', 'created_at', 'updated_at']
        read_only_fields = ['id', 'repository', 'language', 'created_at', 'updated_at']
        # Allow partial updates
        extra_kwargs = {'content': {'required': False}}

    def validate_path(self, value):
        repository = self.context.get('repository')
        if not repository:
            raise serializers.ValidationError("Repository not found in context.")
        if any(char in value for char in ['..', '\\', ':']):
            raise serializers.ValidationError("File path contains invalid characters.")
        if self.instance is None and File.objects.filter(repository=repository, path=value).exists():
            raise serializers.ValidationError("A file with this path already exists in the repository.")
        return value

    def create(self, validated_data):
        file_instance = super().create(validated_data)
        file_instance.language = file_instance.detect_language()
        file_instance.save()
        return file_instance

    def update(self, instance, validated_data):
        # Update content and language if content changes
        if 'content' in validated_data:
            instance.content = validated_data['content']
            instance.language = instance.detect_language()
        instance.save()
        return instance