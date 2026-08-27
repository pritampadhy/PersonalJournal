"""
Security Utilities for Personal Journal Application

Provides:
- Password hashing with bcrypt
- Symmetric encryption (AES-256-GCM)
- JWT token generation and validation
- Secure random token generation
- Constant-time comparison

SECURITY NOTES:
- All encryption uses authenticated encryption (GCM mode)
- All hashes use bcrypt with high cost factor
- All tokens are cryptographically random
- No hardcoded keys or secrets
"""

import os
import base64
import logging
from typing import Tuple, Optional, Dict, Any
from datetime import datetime, timedelta
from functools import wraps
from hashlib import sha256

import jwt
import bcrypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend
from flask import request, jsonify, g
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Base security error."""
    pass


class AuthenticationError(SecurityError):
    """Authentication failed."""
    pass


class EncryptionError(SecurityError):
    """Encryption/decryption failed."""
    pass


class PasswordHasher:
    """
    Secure password hashing using bcrypt.
    
    Uses high cost factor to resist brute-force attacks.
    Salt is generated automatically by bcrypt.
    """
    
    def __init__(self, cost_factor: int = 12):
        """
        Initialize password hasher.
        
        Args:
            cost_factor: bcrypt cost factor (10-14 recommended)
                        Higher = more secure but slower
                        12 ≈ 200ms per hash
        """
        if not 10 <= cost_factor <= 14:
            raise ValueError("Cost factor must be between 10 and 14")
        self.cost_factor = cost_factor
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plaintext password
            
        Returns:
            bcrypt hash (includes salt and cost factor)
            
        Raises:
            SecurityError: If hashing fails
        """
        if not password or len(password) < 8:
            raise SecurityError("Password must be at least 8 characters")
        
        try:
            salt = bcrypt.gensalt(rounds=self.cost_factor)
            hashed = bcrypt.hashpw(password.encode(), salt)
            return hashed.decode('utf-8')
        except Exception as e:
            logger.error(f"Password hashing failed: {e}")
            raise SecurityError("Password hashing failed")
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify password against hash (constant-time).
        
        Args:
            password: Plaintext password to verify
            password_hash: Hash to compare against
            
        Returns:
            True if password matches hash
            
        Note:
            Uses constant-time comparison to prevent timing attacks
        """
        if not password or not password_hash:
            return False
        
        try:
            # bcrypt.checkpw is constant-time
            return bcrypt.checkpw(
                password.encode(),
                password_hash.encode()
            )
        except Exception:
            # Never reveal why verification failed
            return False


class SymmetricEncryption:
    """
    AES-256-GCM encryption for sensitive data.
    
    Features:
    - Authenticated encryption (detects tampering)
    - Random nonces per encryption
    - User-specific keys derived from master key
    - Automatic versioning support
    """
    
    ALGORITHM = "AES-256-GCM"
    KEY_LENGTH = 32  # 256 bits
    NONCE_LENGTH = 12  # 96 bits for GCM
    TAG_LENGTH = 16  # 128 bits
    
    def __init__(self, master_key: str):
        """
        Initialize encryption engine.
        
        Args:
            master_key: Base64-encoded master key (32 bytes)
            
        Raises:
            EncryptionError: If master key is invalid
        """
        try:
            self.master_key = base64.b64decode(master_key)
            if len(self.master_key) != self.KEY_LENGTH:
                raise ValueError(f"Master key must be {self.KEY_LENGTH} bytes")
        except Exception as e:
            raise EncryptionError(f"Invalid master key: {e}")
    
    def _derive_key(self, user_id: int, key_version: int = 1) -> bytes:
        """
        Derive user-specific key from master key.
        
        Uses HKDF-SHA256 to derive unique key per user.
        This ensures each user's data is encrypted with different key.
        
        Args:
            user_id: User identifier
            key_version: Key version for rotation support
            
        Returns:
            32-byte derived key
        """
        info = f"journal:encryption:v{key_version}:user:{user_id}".encode()
        
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=self.KEY_LENGTH,
            salt=None,
            info=info,
            backend=default_backend()
        )
        
        return hkdf.derive(self.master_key)
    
    def encrypt(self, plaintext: str, user_id: int) -> str:
        """
        Encrypt plaintext for user.
        
        Format: base64(nonce || ciphertext || auth_tag)
        
        Args:
            plaintext: Data to encrypt
            user_id: User identifier for key derivation
            
        Returns:
            Base64-encoded ciphertext with nonce and tag
            
        Raises:
            EncryptionError: If encryption fails
        """
        if not plaintext:
            raise EncryptionError("Cannot encrypt empty data")
        
        try:
            # Derive user-specific key
            key = self._derive_key(user_id)
            
            # Generate random nonce (IV)
            nonce = os.urandom(self.NONCE_LENGTH)
            
            # Encrypt
            cipher = AESGCM(key)
            ciphertext = cipher.encrypt(
                nonce,
                plaintext.encode('utf-8'),
                None  # No additional authenticated data
            )
            
            # Combine nonce + ciphertext (tag is last 16 bytes of ciphertext)
            combined = nonce + ciphertext
            
            # Return as base64 for storage
            return base64.b64encode(combined).decode('utf-8')
        
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError("Encryption failed")
    
    def decrypt(self, ciphertext: str, user_id: int) -> str:
        """
        Decrypt ciphertext for user.
        
        Args:
            ciphertext: Base64-encoded encrypted data
            user_id: User identifier for key derivation
            
        Returns:
            Decrypted plaintext
            
        Raises:
            EncryptionError: If decryption fails or tag verification fails
        """
        if not ciphertext:
            raise EncryptionError("Cannot decrypt empty data")
        
        try:
            # Derive user-specific key
            key = self._derive_key(user_id)
            
            # Decode from base64
            combined = base64.b64decode(ciphertext)
            
            # Extract nonce and ciphertext
            nonce = combined[:self.NONCE_LENGTH]
            ct = combined[self.NONCE_LENGTH:]
            
            # Decrypt and verify tag
            cipher = AESGCM(key)
            plaintext = cipher.decrypt(nonce, ct, None)
            
            return plaintext.decode('utf-8')
        
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise EncryptionError("Decryption failed or data tampered with")


class TokenManager:
    """
    JWT token generation and validation.
    
    Implements:
    - Access tokens (short-lived, for API auth)
    - Refresh tokens (long-lived, for getting new access tokens)
    - Token rotation to prevent token leakage impact
    - Claims validation
    """
    
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_ttl: timedelta = timedelta(minutes=15),
        refresh_ttl: timedelta = timedelta(days=7)
    ):
        """
        Initialize token manager.
        
        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT algorithm (HS256, RS256, ES256)
            access_ttl: Access token time-to-live
            refresh_ttl: Refresh token time-to-live
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_ttl = access_ttl
        self.refresh_ttl = refresh_ttl
    
    def generate_access_token(self, user_id: int, additional_claims: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate access token for user.
        
        Claims:
        - sub (subject): user_id
        - iat (issued at): timestamp
        - exp (expiry): timestamp
        - type: "access"
        
        Args:
            user_id: User identifier
            additional_claims: Extra claims to include
            
        Returns:
            JWT token
            
        Raises:
            AuthenticationError: If token generation fails
        """
        now = datetime.utcnow()
        claims = {
            "sub": str(user_id),
            "iat": now,
            "exp": now + self.access_ttl,
            "type": "access",
        }
        
        if additional_claims:
            claims.update(additional_claims)
        
        try:
            token = jwt.encode(
                claims,
                self.secret_key,
                algorithm=self.algorithm
            )
            return token
        except Exception as e:
            logger.error(f"Token generation failed: {e}")
            raise AuthenticationError("Token generation failed")
    
    def generate_refresh_token(self, user_id: int) -> str:
        """
        Generate refresh token for user.
        
        Refresh tokens are longer-lived and used to obtain new access tokens.
        They should be stored securely (HttpOnly cookie).
        
        Args:
            user_id: User identifier
            
        Returns:
            JWT refresh token
        """
        now = datetime.utcnow()
        claims = {
            "sub": str(user_id),
            "iat": now,
            "exp": now + self.refresh_ttl,
            "type": "refresh",
            "jti": base64.b64encode(os.urandom(16)).decode(),  # Unique token ID
        }
        
        try:
            token = jwt.encode(
                claims,
                self.secret_key,
                algorithm=self.algorithm
            )
            return token
        except Exception as e:
            logger.error(f"Refresh token generation failed: {e}")
            raise AuthenticationError("Refresh token generation failed")
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Verify and decode JWT token.
        
        Args:
            token: JWT token to verify
            token_type: Expected token type ('access' or 'refresh')
            
        Returns:
            Token claims
            
        Raises:
            AuthenticationError: If token is invalid or expired
        """
        if not token:
            raise AuthenticationError("No token provided")
        
        try:
            # Verify signature and expiry
            claims = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Verify token type
            if claims.get("type") != token_type:
                raise AuthenticationError(
                    f"Invalid token type. Expected '{token_type}', got '{claims.get('type')}'"
                )
            
            return claims
        
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token expired")
        except jwt.InvalidSignatureError:
            raise AuthenticationError("Invalid token signature")
        except jwt.DecodeError:
            raise AuthenticationError("Invalid token format")
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise AuthenticationError("Token verification failed")


# Singleton instances (initialized in app factory)
password_hasher: Optional[PasswordHasher] = None
encryption: Optional[SymmetricEncryption] = None
token_manager: Optional[TokenManager] = None


def init_security(config) -> None:
    """
    Initialize security systems.
    
    Called once at application startup to initialize:
    - Password hasher
    - Encryption engine
    - Token manager
    
    Args:
        config: Application configuration
    """
    global password_hasher, encryption, token_manager
    
    password_hasher = PasswordHasher(cost_factor=config.BCRYPT_LOG_ROUNDS)
    encryption = SymmetricEncryption(config.ENCRYPTION_MASTER_KEY)
    token_manager = TokenManager(
        secret_key=config.JWT_SECRET_KEY,
        algorithm=config.JWT_ALGORITHM,
        access_ttl=config.JWT_ACCESS_TOKEN_EXPIRY,
        refresh_ttl=config.JWT_REFRESH_TOKEN_EXPIRY,
    )
    
    logger.info("✓ Security systems initialized")


def require_auth(f):
    """
    Decorator to require valid JWT authentication.
    
    Extracts token from Authorization header (Bearer scheme),
    verifies it, and stores user_id in flask.g for request context.
    
    Usage:
        @app.route('/entries', methods=['GET'])
        @require_auth
        def get_entries():
            user_id = g.user_id
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Extract token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        try:
            # Verify token
            claims = token_manager.verify_token(token, token_type='access')
            
            # Store user_id in request context
            g.user_id = int(claims['sub'])
            
            return f(*args, **kwargs)
        
        except AuthenticationError as e:
            return jsonify({'error': str(e)}), 401
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return jsonify({'error': 'Authentication failed'}), 401
    
    return decorated_function


def get_current_user_id() -> int:
    """
    Get current user ID from request context.
    
    Must be called within request context of @require_auth decorated function.
    
    Returns:
        User ID
        
    Raises:
        RuntimeError: If not in authenticated request
    """
    if 'user_id' not in g:
        raise RuntimeError("Not in authenticated request context")
    return g.user_id
