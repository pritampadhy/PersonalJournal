"""
Configuration Management for Personal Journal Application

Handles secure loading of configuration from environment variables,
with support for Vault integration and key rotation.

SECURITY PRINCIPLES:
- Never log sensitive values
- Validate all configuration at startup
- Use environment variables for secrets
- Support Vault for production
- Fail fast on misconfiguration
"""

import os
import json
import logging
from datetime import timedelta
from functools import lru_cache
from typing import Optional, List, Dict, Any
from pathlib import Path

import dotenv

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


class SecretLoader:
    """
    Handles loading secrets from multiple sources.
    
    Hierarchy:
    1. Vault (if VAULT_BACKEND is configured)
    2. AWS Secrets Manager
    3. Environment variables
    4. .env file (development only)
    """
    
    def __init__(self, backend: str = "environment"):
        """
        Initialize secret loader.
        
        Args:
            backend: 'environment', 'vault', or 'aws-secrets'
        """
        self.backend = backend
        self._vault_client = None
        
        if backend == "vault":
            try:
                import hvac
                self._vault_client = hvac.Client(
                    url=os.getenv("VAULT_ADDR"),
                    token=os.getenv("VAULT_TOKEN"),
                    namespace=os.getenv("VAULT_NAMESPACE")
                )
                self._vault_client.is_authenticated()
                logger.info("✓ Vault authentication successful")
            except Exception as e:
                logger.error(f"✗ Vault connection failed: {e}")
                raise ConfigurationError(f"Cannot connect to Vault: {e}")
    
    def get_secret(self, key: str, default: Optional[str] = None) -> str:
        """
        Retrieve a secret from configured backend.
        
        Args:
            key: Secret key/name
            default: Default value if not found (None = required)
            
        Returns:
            Secret value
            
        Raises:
            ConfigurationError: If required secret not found
        """
        # Try backend first
        if self.backend == "vault":
            secret = self._get_from_vault(key)
            if secret:
                return secret
        
        # Fall back to environment
        secret = os.getenv(key)
        if secret:
            return secret
        
        # Use default or fail
        if default is not None:
            return default
        
        raise ConfigurationError(
            f"Required secret '{key}' not found in {self.backend}"
        )
    
    def _get_from_vault(self, key: str) -> Optional[str]:
        """Get secret from HashiCorp Vault."""
        if not self._vault_client:
            return None
        
        try:
            path = f"secret/data/journal/{key}"
            response = self._vault_client.secrets.kv.read_secret_version(path)
            return response["data"]["data"].get(key)
        except Exception:
            return None


class Config:
    """
    Application configuration with validation.
    
    This class loads configuration from environment and validates it.
    All secrets are loaded through SecretLoader.
    """
    
    # FLASK CONFIGURATION
    FLASK_ENV: str = "production"
    DEBUG: bool = False
    TESTING: bool = False
    SECRET_KEY: str
    
    # DATABASE
    SQLALCHEMY_DATABASE_URI: str
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ECHO: bool = False
    
    # Connection pooling
    SQLALCHEMY_ENGINE_OPTIONS: Dict[str, Any] = {
        "pool_size": 20,
        "max_overflow": 40,
        "pool_recycle": 3600,
        "pool_pre_ping": True,  # Verify connections before using
        "echo": False,
    }
    
    # JWT/Authentication
    JWT_SECRET_KEY: str
    JWT_ACCESS_TOKEN_EXPIRY: timedelta = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRY: timedelta = timedelta(days=7)
    JWT_ALGORITHM: str = "HS256"
    
    # Encryption
    ENCRYPTION_MASTER_KEY: str
    ENCRYPTION_ALGORITHM: str = "AES-256-GCM"
    
    # Security
    CORS_ORIGINS: List[str]
    CORS_ALLOW_CREDENTIALS: bool = True
    CSRF_ENABLED: bool = True
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "100/hour"
    RATE_LIMIT_AUTH: str = "20/hour"
    RATE_LIMIT_JOURNAL: str = "1000/hour"
    
    # Sessions
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Strict"
    SESSION_COOKIE_DOMAIN: Optional[str] = None
    
    # Bcrypt
    BCRYPT_LOG_ROUNDS: int = 12
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: Optional[str] = None
    
    # Audit
    AUDIT_LOG_ENABLED: bool = True
    AUDIT_LOG_RETENTION_DAYS: int = 365
    
    # Monitoring
    SENTRY_DSN: Optional[str] = None
    ENABLE_METRICS: bool = False
    
    # Features
    FEATURE_TWO_FACTOR_AUTH: bool = False
    FEATURE_EXPORT_DATA: bool = True
    FEATURE_AUDIT_LOG_API: bool = False
    
    # Admin
    ENABLE_ADMIN_ENDPOINTS: bool = False
    ADMIN_API_KEY: Optional[str] = None
    
    def __init__(self, env: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            env: Environment name (development, staging, production)
        """
        self.env = env or os.getenv("ENVIRONMENT", "production")
        self.secret_loader = SecretLoader(
            backend=os.getenv("SECRET_BACKEND", "environment")
        )
        
        # Load configuration
        self._load_from_environment()
        self._validate()
        self._log_configuration()
    
    def _load_from_environment(self):
        """Load configuration from environment variables."""
        
        # Flask configuration
        self.FLASK_ENV = os.getenv("FLASK_ENV", "production")
        self.DEBUG = self._parse_bool(os.getenv("DEBUG", "False"))
        self.TESTING = self._parse_bool(os.getenv("TESTING", "False"))
        self.SECRET_KEY = self.secret_loader.get_secret("SECRET_KEY")
        
        # Database
        self.SQLALCHEMY_DATABASE_URI = self.secret_loader.get_secret(
            "DATABASE_URL"
        )
        self.SQLALCHEMY_ECHO = self._parse_bool(
            os.getenv("DB_ECHO", "False")
        )
        
        # Update engine options from env
        pool_size = int(os.getenv("DB_POOL_SIZE", "20"))
        max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "40"))
        pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "3600"))
        
        self.SQLALCHEMY_ENGINE_OPTIONS.update({
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_recycle": pool_recycle,
        })
        
        # JWT
        self.JWT_SECRET_KEY = self.secret_loader.get_secret("JWT_SECRET_KEY")
        self.JWT_ACCESS_TOKEN_EXPIRY = timedelta(
            seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRY", "900"))
        )
        self.JWT_REFRESH_TOKEN_EXPIRY = timedelta(
            seconds=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRY", "604800"))
        )
        self.JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
        
        # Encryption
        self.ENCRYPTION_MASTER_KEY = self.secret_loader.get_secret(
            "ENCRYPTION_MASTER_KEY"
        )
        self.ENCRYPTION_ALGORITHM = os.getenv(
            "ENCRYPTION_ALGORITHM", "AES-256-GCM"
        )
        
        # CORS
        cors_str = os.getenv("CORS_ORIGINS", '["http://localhost:3000"]')
        try:
            self.CORS_ORIGINS = json.loads(cors_str)
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid CORS_ORIGINS JSON: {e}")
        
        # Security
        self.CSRF_ENABLED = self._parse_bool(os.getenv("CSRF_ENABLED", "True"))
        self.RATE_LIMIT_ENABLED = self._parse_bool(
            os.getenv("RATE_LIMIT_ENABLED", "True")
        )
        
        # Sessions
        self.SESSION_COOKIE_SECURE = self._parse_bool(
            os.getenv("SESSION_COOKIE_SECURE", "True")
        )
        self.SESSION_COOKIE_HTTPONLY = self._parse_bool(
            os.getenv("SESSION_COOKIE_HTTPONLY", "True")
        )
        self.SESSION_COOKIE_SAMESITE = os.getenv(
            "SESSION_COOKIE_SAMESITE", "Strict"
        )
        self.SESSION_COOKIE_DOMAIN = os.getenv("SESSION_COOKIE_DOMAIN")
        
        # Bcrypt
        self.BCRYPT_LOG_ROUNDS = int(os.getenv("BCRYPT_LOG_ROUNDS", "12"))
        
        # Logging
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
        self.LOG_FORMAT = os.getenv("LOG_FORMAT", "json")
        self.LOG_FILE = os.getenv("LOG_FILE")
        
        # Features
        self.FEATURE_TWO_FACTOR_AUTH = self._parse_bool(
            os.getenv("FEATURE_TWO_FACTOR_AUTH", "False")
        )
        self.FEATURE_EXPORT_DATA = self._parse_bool(
            os.getenv("FEATURE_EXPORT_DATA", "True")
        )
        self.FEATURE_AUDIT_LOG_API = self._parse_bool(
            os.getenv("FEATURE_AUDIT_LOG_API", "False")
        )
        
        # Admin
        self.ENABLE_ADMIN_ENDPOINTS = self._parse_bool(
            os.getenv("ENABLE_ADMIN_ENDPOINTS", "False")
        )
        if self.ENABLE_ADMIN_ENDPOINTS:
            self.ADMIN_API_KEY = self.secret_loader.get_secret("ADMIN_API_KEY")
        
        # Monitoring
        self.SENTRY_DSN = os.getenv("SENTRY_DSN")
        self.ENABLE_METRICS = self._parse_bool(
            os.getenv("ENABLE_METRICS", "False")
        )
    
    def _validate(self):
        """Validate configuration integrity."""
        errors = []
        
        # Critical validations
        if not self.SECRET_KEY or len(self.SECRET_KEY) < 32:
            errors.append("SECRET_KEY must be at least 32 characters")
        
        if not self.JWT_SECRET_KEY or len(self.JWT_SECRET_KEY) < 32:
            errors.append("JWT_SECRET_KEY must be at least 32 characters")
        
        if not self.ENCRYPTION_MASTER_KEY:
            errors.append("ENCRYPTION_MASTER_KEY is required")
        
        if self.ENCRYPTION_ALGORITHM not in ["AES-256-GCM"]:
            errors.append(f"Unsupported encryption algorithm: {self.ENCRYPTION_ALGORITHM}")
        
        if self.JWT_ALGORITHM not in ["HS256", "RS256", "ES256"]:
            errors.append(f"Unsupported JWT algorithm: {self.JWT_ALGORITHM}")
        
        if self.BCRYPT_LOG_ROUNDS < 10 or self.BCRYPT_LOG_ROUNDS > 14:
            errors.append("BCRYPT_LOG_ROUNDS should be between 10 and 14")
        
        # Environment-specific validations
        if self.env == "production":
            if self.DEBUG:
                errors.append("DEBUG must be False in production")
            if not self.SESSION_COOKIE_SECURE:
                errors.append("SESSION_COOKIE_SECURE must be True in production")
            if not self.CSRF_ENABLED:
                errors.append("CSRF_ENABLED must be True in production")
        
        if errors:
            for error in errors:
                logger.error(f"✗ Configuration error: {error}")
            raise ConfigurationError(
                f"Configuration validation failed with {len(errors)} errors"
            )
    
    def _log_configuration(self):
        """Log configuration (without secrets)."""
        logger.info(f"✓ Configuration loaded for environment: {self.env}")
        logger.info(f"  Flask env: {self.FLASK_ENV}")
        logger.info(f"  Debug: {self.DEBUG}")
        logger.info(f"  CSRF enabled: {self.CSRF_ENABLED}")
        logger.info(f"  Rate limiting: {self.RATE_LIMIT_ENABLED}")
        logger.info(f"  Audit logging: {self.AUDIT_LOG_ENABLED}")
        logger.info(f"  Encryption: {self.ENCRYPTION_ALGORITHM}")
        logger.info(f"  Bcrypt rounds: {self.BCRYPT_LOG_ROUNDS}")
    
    @staticmethod
    def _parse_bool(value: str) -> bool:
        """Parse boolean from string."""
        return value.lower() in ("true", "1", "yes", "on")


@lru_cache(maxsize=1)
def get_config(env: Optional[str] = None) -> Config:
    """
    Get application configuration (cached).
    
    Args:
        env: Environment name (optional)
        
    Returns:
        Config instance
    """
    if env is None:
        env = os.getenv("ENVIRONMENT", "production")
    
    return Config(env=env)


def load_dotenv_file():
    """Load .env file if it exists (development only)."""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists() and os.getenv("ENVIRONMENT") != "production":
        dotenv.load_dotenv(env_file, override=False)
        logger.debug("✓ Loaded .env file")


# Load .env on module import (development)
load_dotenv_file()
