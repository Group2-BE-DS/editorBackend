from datetime import datetime
from django.core.cache import cache
import secrets

class TokenStore:
    TOKEN_PREFIX = 'collab_token_'
    TOKEN_EXPIRY = 3600  # 1 hour

    @classmethod
    def generate_token(cls, repository_slug):
        """Generate a new token for a repository"""
        token = secrets.token_urlsafe(8)
        cache_key = f"{cls.TOKEN_PREFIX}{token}"
        
        # Store token with repository info and empty connections list
        cache.set(cache_key, {
            'repository_slug': repository_slug,
            'connections': [],
            'created_at': True
        }, cls.TOKEN_EXPIRY)
        
        print(f"Successfully stored token {token} for repository {repository_slug}")
        return token

    @classmethod
    def add_token(cls, token, repository_slug):
        """Store token with repository information"""
        if not token or not repository_slug:
            return False
            
        try:
            token = token.strip()
            cache_key = f"{cls.TOKEN_PREFIX}{token}"
            value = {
                'repository_slug': repository_slug,
                'connections': [],
                'created_at': True
            }
            cache.set(cache_key, value, cls.TOKEN_EXPIRY)
            print(f"Successfully added token {token} for repository {repository_slug}")
            return True
        except Exception as e:
            print(f"Error adding token: {str(e)}")
            return False

    @classmethod
    def verify_token(cls, token):
        """Verify if a token exists and is valid"""
        if not token:
            return False
            
        try:
            token = token.strip()
            cache_key = f"{cls.TOKEN_PREFIX}{token}"
            value = cache.get(cache_key)
            
            if value and isinstance(value, dict):
                print(f"Token {token} verified successfully")
                return True
            return False
        except Exception as e:
            print(f"Error verifying token: {str(e)}")
            return False

    @classmethod
    def get_repository_slug(cls, token):
        """Get repository slug associated with a token"""
        if not token:
            return None
            
        try:
            token = token.strip()
            cache_key = f"{cls.TOKEN_PREFIX}{token}"
            value = cache.get(cache_key)
            
            if value and isinstance(value, dict):
                return value.get('repository_slug')
            return None
        except Exception as e:
            print(f"Error getting repository slug: {str(e)}")
            return None

    @classmethod
    def get_connections(cls, token):
        """Get list of user connections for a token"""
        if not token:
            return []
            
        try:
            token = token.strip()
            cache_key = f"{cls.TOKEN_PREFIX}{token}"
            value = cache.get(cache_key)
            
            if value and isinstance(value, dict):
                connections = value.get('connections', [])
                print(f"Retrieved {len(connections)} connections for token {token}")
                print(f"Current users in room: {connections}")
                return connections
            return []
        except Exception as e:
            print(f"Error getting connections: {str(e)}")
            return []

    @classmethod
    def add_connection(cls, token, user_id, username="Anonymous"):
        """Add a user connection to the token"""
        if not token or not user_id:
            return False
            
        try:
            token = token.strip()
            cache_key = f"{cls.TOKEN_PREFIX}{token}"
            value = cache.get(cache_key)
            
            if value and isinstance(value, dict):
                connections = value.get('connections', [])
                if user_id not in [c['id'] for c in connections]:
                    connections.append({
                        'id': user_id,
                        'username': username,
                        'joined_at': datetime.now().isoformat(),
                        'last_activity': datetime.now().isoformat()
                    })
                    value['connections'] = connections
                    cache.set(cache_key, value, cls.TOKEN_EXPIRY)
                    print(f"Added connection {user_id} ({username}) to token {token}")
                    print(f"Total connections: {len(connections)}")
                return True
            return False
        except Exception as e:
            print(f"Error adding connection: {str(e)}")
            return False

    @classmethod
    def remove_connection(cls, token, user_id):
        """Remove a user connection from the token"""
        if not token or not user_id:
            return False
            
        try:
            token = token.strip()
            cache_key = f"{cls.TOKEN_PREFIX}{token}"
            value = cache.get(cache_key)
            
            if value and isinstance(value, dict):
                connections = value.get('connections', [])
                connections = [c for c in connections if c['id'] != user_id]
                value['connections'] = connections
                cache.set(cache_key, value, cls.TOKEN_EXPIRY)
                print(f"Removed connection {user_id} from token {token}")
                print(f"Remaining connections: {len(connections)}")
                return True
            return False
        except Exception as e:
            print(f"Error removing connection: {str(e)}")
            return False