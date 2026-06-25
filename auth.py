# password fucntion
def hash_password(password: str):
    return f"HASHED_{password}"


def verify_password(plain_password: str, hashed_password: str):
    return hashed_password == f"HASHED_{plain_password}"

# JWT fucntions
from jose import jwt

SECRET_KEY = "super-secret-dev-key"
ALGORITHM = "HS256"


def create_access_token(email: str):
    data = {"sub": email}
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    