from datetime import datetime, timedelta

class TokenStore:
    _tokens = {}  # Store token -> room_info mapping

    @classmethod
    def add_token(cls, token, creator_id=None):
        cls._tokens[token] = {
            'created_at': datetime.now(),
            'creator_id': creator_id,
            'expires_at': datetime.now() + timedelta(hours=24)
        }

    @classmethod
    def verify_token(cls, token):
        if token not in cls._tokens:
            return False
        
        room_info = cls._tokens[token]
        if room_info['expires_at'] < datetime.now():
            cls.remove_token(token)
            return False
            
        return True

    @classmethod
    def remove_token(cls, token):
        cls._tokens.pop(token, None)

    @classmethod
    def cleanup_expired(cls):
        now = datetime.now()
        expired = [token for token, info in cls._tokens.items() 
                  if info['expires_at'] < now]
        for token in expired:
            cls.remove_token(token)