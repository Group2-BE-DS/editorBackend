from datetime import datetime, timedelta
from django.core.cache import cache
from django.apps import apps

class TokenStore:
    TOKEN_PREFIX = 'collab_token:'
    REPO_PREFIX = 'repo_info:'
    TOKEN_EXPIRY = 3600  # 1 hour in seconds

    @classmethod
    def add_token(cls, token, repository_slug=None):
        """Store a token with repository information"""
        cache_key = f"{cls.TOKEN_PREFIX}{token}"
        cache_value = {
            'is_valid': True,
            'repository_slug': repository_slug
        }
        cache.set(cache_key, cache_value, cls.TOKEN_EXPIRY)
        
        # Store repository info if provided
        if repository_slug:
            try:
                Repository = apps.get_model('filesys', 'Repository')
                repository = Repository.objects.get(slug=repository_slug)
                repo_info = {
                    'slug': repository.slug,
                    'owner': repository.user.username,
                    'name': repository.name
                }
                repo_key = f"{cls.REPO_PREFIX}{token}"
                cache.set(repo_key, repo_info, cls.TOKEN_EXPIRY)
            except Exception:
                pass

    @classmethod
    def get_repository_info(cls, token):
        """Get repository information associated with token"""
        repo_key = f"{cls.REPO_PREFIX}{token}"
        return cache.get(repo_key)

    @classmethod
    def verify_token(cls, token):
        """Verify if a token exists and is valid"""
        cache_key = f"{cls.TOKEN_PREFIX}{token}"
        value = cache.get(cache_key)
        return value and value.get('is_valid', False)

    @classmethod
    def validate_token(cls, token):
        """Alias for verify_token to maintain compatibility"""
        return cls.verify_token(token)

    @classmethod
    def remove_token(cls, token):
        """Remove a token and its associated repository info"""
        cache_key = f"{cls.TOKEN_PREFIX}{token}"
        repo_key = f"{cls.REPO_PREFIX}{token}"
        cache.delete(cache_key)
        cache.delete(repo_key)

    @classmethod
    def get_expiry_time(cls, token):
        """Get token expiry time"""
        cache_key = f"{cls.TOKEN_PREFIX}{token}"
        return cache.ttl(cache_key)

    @classmethod
    def get_repository_slug(cls, token):
        """Get repository slug associated with token"""
        cache_key = f"{cls.TOKEN_PREFIX}{token}"
        value = cache.get(cache_key)
        return value and value.get('repository_slug')