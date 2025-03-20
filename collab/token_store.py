from datetime import datetime, timedelta
from django.core.cache import cache

class TokenStore:
    TOKEN_PREFIX = 'collab_token:'
    TOKEN_EXPIRY = 3600  # 1 hour in seconds

    @classmethod
    def add_token(cls, token):
        """Store a token with expiration time"""
        cache_key = f"{cls.TOKEN_PREFIX}{token}"
        cache.set(cache_key, True, cls.TOKEN_EXPIRY)

    @classmethod
    def verify_token(cls, token):
        """Verify if a token exists and is valid"""
        cache_key = f"{cls.TOKEN_PREFIX}{token}"
        return cache.get(cache_key, False)

    @classmethod
    def validate_token(cls, token):
        """Alias for verify_token to maintain compatibility"""
        return cls.verify_token(token)

    @classmethod
    def remove_token(cls, token):
        """Remove a token"""
        cache_key = f"{cls.TOKEN_PREFIX}{token}"
        cache.delete(cache_key)

    @classmethod
    def get_expiry_time(cls, token):
        """Get token expiry time"""
        cache_key = f"{cls.TOKEN_PREFIX}{token}"
        return cache.ttl(cache_key)