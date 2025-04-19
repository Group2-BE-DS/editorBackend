from rest_framework import serializers
from django.contrib.auth import get_user_model

class VerificationCodeSerializer(serializers.Serializer):
    repoSlug = serializers.CharField(max_length=500)
    usernames = serializers.ListField(
        child=serializers.CharField(),
        min_length=1
    )

    def validate_usernames(self, value):
        User = get_user_model()
        existing_users = User.objects.filter(username__in=value)
        if len(existing_users) != len(value):
            found_usernames = set(user.username for user in existing_users)
            missing_usernames = set(value) - found_usernames
            raise serializers.ValidationError(f"Users not found: {', '.join(missing_usernames)}")
        return value