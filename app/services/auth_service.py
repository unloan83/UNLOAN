from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import check_password_hash


class AuthService:
    def __init__(self, secret_key: str, admin_username: str, admin_password_hash: str):
        self.serializer = URLSafeTimedSerializer(secret_key=secret_key)
        self.admin_username = admin_username
        self.admin_password_hash = admin_password_hash

    def login(self, username: str, password: str) -> str | None:
        if username != self.admin_username:
            return None
        if not check_password_hash(self.admin_password_hash, password):
            return None
        return self.serializer.dumps({"role": "admin", "username": username})

    def verify_token(self, token: str, max_age: int) -> bool:
        try:
            data = self.serializer.loads(token, max_age=max_age)
            return data.get("role") == "admin"
        except (BadSignature, SignatureExpired):
            return False
