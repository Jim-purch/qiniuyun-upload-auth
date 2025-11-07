import os


class Settings:
    app_name: str = os.getenv("APP_NAME", "Qiniu Upload Auth Service")
    environment: str = os.getenv("ENV", "development")

    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data.db")

    # JWT
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    # Qiniu
    qiniu_access_key: str = os.getenv("QINIU_ACCESS_KEY", "")
    qiniu_secret_key: str = os.getenv("QINIU_SECRET_KEY", "")
    qiniu_bucket: str = os.getenv("QINIU_BUCKET", "")

    # Admin bootstrap
    bootstrap_admin_email: str = os.getenv("ADMIN_EMAIL", "admin@example.com")
    bootstrap_admin_password: str = os.getenv("ADMIN_PASSWORD", "admin123")


settings = Settings()