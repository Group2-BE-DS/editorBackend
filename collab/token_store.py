class TokenStore:
    _tokens = set()

    @classmethod
    def add_token(cls, token):
        cls._tokens.add(token)

    @classmethod
    def verify_token(cls, token):
        return token in cls._tokens

    @classmethod
    def remove_token(cls, token):
        cls._tokens.discard(token)