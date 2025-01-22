# filesys/serializers.py

from rest_framework import serializers
from .models import Repository

class RepositorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Repository
        fields = ['name', 'description', 'location', 'user']
