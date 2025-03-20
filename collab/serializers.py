from rest_framework import serializers
from filesys.models import Repository
import re

class VerificationCodeSerializer(serializers.Serializer):
    emails = serializers.ListField(
        child=serializers.EmailField(),
        allow_empty=False,
        error_messages={'empty': 'No email addresses provided'}
    )
    repoSlug = serializers.CharField(max_length=500)

    def validate_repoSlug(self, value):
        # Custom validation for username/repo-name format
        if not re.match(r'^[\w-]+/[\w-]+$', value):
            raise serializers.ValidationError(
                "Invalid slug format. Must be 'username/repo-name' using only letters, numbers, underscores or hyphens."
            )
        try:
            repository = Repository.objects.get(slug=value)
            return value
        except Repository.DoesNotExist:
            raise serializers.ValidationError("Repository not found")