from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / '.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'CampusPulse'
    app_env: Literal['development', 'test', 'production'] = 'development'
    debug: bool = Field(default=False, validation_alias='APP_DEBUG')
    database_url: str = 'postgresql+psycopg://campuspulse:change-me@localhost:5432/campuspulse'
    frontend_url: str = 'http://localhost:3000'
    cors_origins: list[str] = ['http://localhost:3000']
    trusted_hosts: list[str] = ['localhost', '127.0.0.1', 'testserver', 'backend']
    secret_key: str = 'development-only-replace-with-a-random-secret'
    session_cookie_name: str = 'campuspulse_session'
    session_expire_hours: int = Field(default=24, ge=1, le=720)
    cookie_secure: bool = False
    cookie_domain: str | None = None
    storage_path: Path = BACKEND_DIR / 'storage'
    max_upload_size_mb: int = Field(default=20, ge=1, le=100)
    smtp_enabled: bool = True
    smtp_host: str = 'localhost'
    smtp_port: int = Field(default=1025, ge=1, le=65535)
    smtp_username: str = ''
    smtp_password: str = ''
    smtp_starttls: bool = False
    smtp_ssl: bool = False
    smtp_allow_insecure: bool = False
    smtp_from_email: str = 'noreply@campuspulse.test'
    smtp_from_name: str = 'CampusPulse'
    smtp_timeout_seconds: int = Field(default=10, ge=1, le=60)
    mail_max_attempts: int = Field(default=5, ge=1, le=20)
    mail_poll_seconds: int = Field(default=5, ge=1, le=60)
    password_reset_expire_minutes: int = Field(default=30, ge=5, le=1440)
    invitation_expire_hours: int = Field(default=48, ge=1, le=168)
    public_registration_enabled: bool = True
    otp_secret_key: str = ''
    otp_ttl_minutes: int = Field(default=10, ge=1, le=30)
    otp_max_attempts: int = Field(default=5, ge=1, le=10)
    otp_resend_cooldown_seconds: int = Field(default=60, ge=30, le=300)

    @model_validator(mode='after')
    def validate_settings(self):
        if self.smtp_ssl and self.smtp_starttls:
            raise ValueError('Choisir SMTP_SSL ou SMTP_STARTTLS, jamais les deux.')
        if self.cookie_domain == '':
            self.cookie_domain = None
        if self.database_url.startswith('postgresql://'):
            self.database_url = self.database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
        self.frontend_url = self.frontend_url.rstrip('/')
        if not self.storage_path.is_absolute():
            self.storage_path = (BACKEND_DIR / self.storage_path).resolve()
        if self.app_env == 'production':
            if self.otp_secret_key and len(self.otp_secret_key) < 32:
                raise ValueError('OTP_SECRET_KEY doit contenir au moins 32 caractères ou rester vide pour utiliser SECRET_KEY.')
            if len(self.secret_key) < 32 or any(word in self.secret_key.lower() for word in ('change', 'replace', 'development')):
                raise ValueError('SECRET_KEY de production doit être aléatoire et contenir au moins 32 caractères.')
            if not self.cookie_secure or not self.frontend_url.startswith('https://'):
                raise ValueError('La production exige COOKIE_SECURE=true et FRONTEND_URL en HTTPS.')
            if self.debug or '*' in self.cors_origins or '*' in self.trusted_hosts:
                raise ValueError('DEBUG et les origines/hôtes génériques sont interdits en production.')
            if self.smtp_enabled and not (self.smtp_ssl or self.smtp_starttls or self.smtp_allow_insecure):
                raise ValueError('Configurer TLS pour SMTP ou autoriser explicitement un relais privé.')
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
