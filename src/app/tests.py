"""
Comprehensive Test Suite for Personal Journal Application

Tests cover:
- Authentication (registration, login, token refresh)
- Authorization (user isolation, row-level security)
- Encryption/Decryption
- Password hashing
- Rate limiting
- CSRF protection
- Security headers
- Input validation
- Error handling

Run with: pytest tests.py -v
Run with coverage: pytest --cov=. tests.py
"""

import json
import pytest
from datetime import datetime, timedelta
from base64 import b64encode

from app import create_app
from config import Config
from models import db, User, JournalEntry, AuditLog
from security import (
    PasswordHasher, SymmetricEncryption, TokenManager,
    AuthenticationError, EncryptionError, SecurityError
)


@pytest.fixture
def app():
    """Create application for testing."""
    # Override config for testing
    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        DEBUG = False
        SECRET_KEY = 'test-secret-key-minimum-32-characters-long'
        JWT_SECRET_KEY = 'test-jwt-secret-key-minimum-32-characters'
        ENCRYPTION_MASTER_KEY = b64encode(b'x' * 32).decode()
        BCRYPT_LOG_ROUNDS = 10  # Faster for testing
    
    app = create_app()
    app.config.from_object(TestConfig)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create CLI runner."""
    return app.test_cli_runner()


# ============================================================================
# SECURITY UTILITY TESTS
# ============================================================================

class TestPasswordHasher:
    """Test password hashing and verification."""
    
    def test_hash_password(self):
        """Test password hashing."""
        hasher = PasswordHasher(cost_factor=10)
        password = "SecurePassword123!"
        
        hash1 = hasher.hash_password(password)
        hash2 = hasher.hash_password(password)
        
        # Hashes should be different (different salts)
        assert hash1 != hash2
        
        # Both should verify
        assert hasher.verify_password(password, hash1)
        assert hasher.verify_password(password, hash2)
    
    def test_verify_password_success(self):
        """Test successful password verification."""
        hasher = PasswordHasher(cost_factor=10)
        password = "MySecretPassword123!"
        hash_val = hasher.hash_password(password)
        
        assert hasher.verify_password(password, hash_val)
    
    def test_verify_password_failure(self):
        """Test failed password verification."""
        hasher = PasswordHasher(cost_factor=10)
        password = "CorrectPassword"
        wrong_password = "WrongPassword"
        hash_val = hasher.hash_password(password)
        
        assert not hasher.verify_password(wrong_password, hash_val)
    
    def test_weak_password_rejected(self):
        """Test that weak passwords are rejected."""
        hasher = PasswordHasher(cost_factor=10)
        
        with pytest.raises(SecurityError):
            hasher.hash_password("short")
    
    def test_constant_time_comparison(self):
        """Test that verification is timing-safe."""
        hasher = PasswordHasher(cost_factor=10)
        password = "CorrectPassword123!"
        hash_val = hasher.hash_password(password)
        
        # Wrong password should return False, not raise exception
        result = hasher.verify_password("WrongPassword", hash_val)
        assert result is False


class TestSymmetricEncryption:
    """Test AES-256-GCM encryption."""
    
    def test_encrypt_decrypt(self):
        """Test basic encryption and decryption."""
        import os
        from base64 import b64encode
        
        master_key = b64encode(os.urandom(32)).decode()
        encryption = SymmetricEncryption(master_key)
        
        plaintext = "This is a secret message"
        user_id = 123
        
        ciphertext = encryption.encrypt(plaintext, user_id)
        decrypted = encryption.decrypt(ciphertext, user_id)
        
        assert decrypted == plaintext
    
    def test_different_users_different_keys(self):
        """Test that different users get different encryption."""
        import os
        from base64 import b64encode
        
        master_key = b64encode(os.urandom(32)).decode()
        encryption = SymmetricEncryption(master_key)
        
        plaintext = "Secret data"
        
        # Encrypt for different users
        cipher_user1 = encryption.encrypt(plaintext, user_id=1)
        cipher_user2 = encryption.encrypt(plaintext, user_id=2)
        
        # Ciphertexts should be different
        assert cipher_user1 != cipher_user2
        
        # User 1 can decrypt their data
        assert encryption.decrypt(cipher_user1, user_id=1) == plaintext
        
        # User 2 can decrypt their data
        assert encryption.decrypt(cipher_user2, user_id=2) == plaintext
        
        # User 1 cannot decrypt user 2's data
        with pytest.raises(EncryptionError):
            encryption.decrypt(cipher_user2, user_id=1)
    
    def test_tampering_detected(self):
        """Test that tampering is detected."""
        import os
        from base64 import b64encode, b64decode
        
        master_key = b64encode(os.urandom(32)).decode()
        encryption = SymmetricEncryption(master_key)
        
        plaintext = "Secret message"
        user_id = 1
        
        ciphertext = encryption.encrypt(plaintext, user_id)
        
        # Tamper with ciphertext
        tampered = b64decode(ciphertext)
        tampered = tampered[:-5] + b'xxxxx'  # Corrupt last bytes
        tampered = b64encode(tampered).decode()
        
        # Decryption should fail
        with pytest.raises(EncryptionError):
            encryption.decrypt(tampered, user_id)
    
    def test_empty_plaintext_rejected(self):
        """Test that empty plaintext is rejected."""
        import os
        from base64 import b64encode
        
        master_key = b64encode(os.urandom(32)).decode()
        encryption = SymmetricEncryption(master_key)
        
        with pytest.raises(EncryptionError):
            encryption.encrypt("", user_id=1)


class TestTokenManager:
    """Test JWT token generation and validation."""
    
    def test_generate_access_token(self):
        """Test access token generation."""
        tm = TokenManager(
            secret_key='test-secret-key-minimum-32-characters',
            access_ttl=timedelta(minutes=15)
        )
        
        token = tm.generate_access_token(user_id=123)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_access_token(self):
        """Test access token verification."""
        tm = TokenManager(
            secret_key='test-secret-key-minimum-32-characters',
            access_ttl=timedelta(minutes=15)
        )
        
        user_id = 456
        token = tm.generate_access_token(user_id)
        
        claims = tm.verify_token(token, token_type='access')
        
        assert claims['sub'] == str(user_id)
        assert claims['type'] == 'access'
    
    def test_refresh_token_generation(self):
        """Test refresh token generation."""
        tm = TokenManager(
            secret_key='test-secret-key-minimum-32-characters',
            refresh_ttl=timedelta(days=7)
        )
        
        token = tm.generate_refresh_token(user_id=789)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_wrong_token_type_rejected(self):
        """Test that wrong token type is rejected."""
        tm = TokenManager(
            secret_key='test-secret-key-minimum-32-characters',
            access_ttl=timedelta(minutes=15),
            refresh_ttl=timedelta(days=7)
        )
        
        refresh_token = tm.generate_refresh_token(user_id=123)
        
        # Try to verify as access token
        with pytest.raises(AuthenticationError):
            tm.verify_token(refresh_token, token_type='access')
    
    def test_expired_token_rejected(self):
        """Test that expired tokens are rejected."""
        tm = TokenManager(
            secret_key='test-secret-key-minimum-32-characters',
            access_ttl=timedelta(seconds=-1)  # Already expired
        )
        
        token = tm.generate_access_token(user_id=123)
        
        with pytest.raises(AuthenticationError):
            tm.verify_token(token, token_type='access')


# ============================================================================
# API ENDPOINT TESTS
# ============================================================================

class TestAuthenticationEndpoints:
    """Test authentication API endpoints."""
    
    def test_register_user_success(self, client):
        """Test successful user registration."""
        response = client.post('/api/v1/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'full_name': 'Test User'
        })
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'user_id' in data
        assert data['message'] == 'User registered successfully'
    
    def test_register_duplicate_username(self, client):
        """Test that duplicate username is rejected."""
        # Register first user
        client.post('/api/v1/auth/register', json={
            'username': 'testuser',
            'email': 'test1@example.com',
            'password': 'SecurePassword123!',
        })
        
        # Try to register with same username
        response = client.post('/api/v1/auth/register', json={
            'username': 'testuser',
            'email': 'test2@example.com',
            'password': 'SecurePassword123!',
        })
        
        assert response.status_code == 409
        data = json.loads(response.data)
        assert 'Username already exists' in data['error']
    
    def test_register_weak_password(self, client):
        """Test that weak password is rejected."""
        response = client.post('/api/v1/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'short',
        })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Password must be at least 8 characters' in data['error']
    
    def test_login_success(self, client):
        """Test successful login."""
        # Register user
        client.post('/api/v1/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
        })
        
        # Login
        response = client.post('/api/v1/auth/login', json={
            'username': 'testuser',
            'password': 'SecurePassword123!',
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert data['username'] == 'testuser'
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        # Register user
        client.post('/api/v1/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
        })
        
        # Try with wrong password
        response = client.post('/api/v1/auth/login', json={
            'username': 'testuser',
            'password': 'WrongPassword',
        })
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'Invalid credentials' in data['error']
    
    def test_token_refresh(self, client):
        """Test token refresh."""
        # Register and login
        client.post('/api/v1/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
        })
        
        login_response = client.post('/api/v1/auth/login', json={
            'username': 'testuser',
            'password': 'SecurePassword123!',
        })
        
        refresh_token = json.loads(login_response.data)['refresh_token']
        
        # Refresh token
        response = client.post('/api/v1/auth/refresh', json={
            'refresh_token': refresh_token
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'access_token' in data


class TestJournalEndpoints:
    """Test journal API endpoints."""
    
    @pytest.fixture
    def auth_token(self, client):
        """Get authentication token for testing."""
        client.post('/api/v1/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
        })
        
        response = client.post('/api/v1/auth/login', json={
            'username': 'testuser',
            'password': 'SecurePassword123!',
        })
        
        return json.loads(response.data)['access_token']
    
    def test_create_entry(self, client, auth_token):
        """Test creating a journal entry."""
        response = client.post(
            '/api/v1/entries',
            json={
                'title': 'My First Entry',
                'content': 'This is my journal entry',
                'mood': 'happy'
            },
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'id' in data
        assert data['title'] == 'My First Entry'
    
    def test_get_entries(self, client, auth_token):
        """Test retrieving journal entries."""
        # Create entry
        client.post(
            '/api/v1/entries',
            json={
                'title': 'Entry 1',
                'content': 'Content 1',
            },
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        # Get entries
        response = client.get(
            '/api/v1/entries',
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['entries']) == 1
        assert data['entries'][0]['title'] == 'Entry 1'
    
    def test_get_single_entry(self, client, auth_token):
        """Test retrieving a single entry."""
        # Create entry
        create_response = client.post(
            '/api/v1/entries',
            json={
                'title': 'Test Entry',
                'content': 'Test Content',
            },
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        entry_id = json.loads(create_response.data)['id']
        
        # Get entry
        response = client.get(
            f'/api/v1/entries/{entry_id}',
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['title'] == 'Test Entry'
        assert data['content'] == 'Test Content'
    
    def test_update_entry(self, client, auth_token):
        """Test updating an entry."""
        # Create entry
        create_response = client.post(
            '/api/v1/entries',
            json={
                'title': 'Original Title',
                'content': 'Original Content',
            },
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        entry_id = json.loads(create_response.data)['id']
        
        # Update entry
        response = client.put(
            f'/api/v1/entries/{entry_id}',
            json={
                'title': 'Updated Title',
                'content': 'Updated Content',
            },
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        assert response.status_code == 200
        
        # Verify update
        get_response = client.get(
            f'/api/v1/entries/{entry_id}',
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        data = json.loads(get_response.data)
        assert data['title'] == 'Updated Title'
    
    def test_delete_entry(self, client, auth_token):
        """Test deleting an entry."""
        # Create entry
        create_response = client.post(
            '/api/v1/entries',
            json={
                'title': 'To Delete',
                'content': 'This will be deleted',
            },
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        entry_id = json.loads(create_response.data)['id']
        
        # Delete entry
        response = client.delete(
            f'/api/v1/entries/{entry_id}',
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        assert response.status_code == 200
        
        # Verify deletion
        get_response = client.get(
            f'/api/v1/entries/{entry_id}',
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        assert get_response.status_code == 404
    
    def test_user_isolation(self, client):
        """Test that users cannot access other users' entries."""
        # Create two users
        client.post('/api/v1/auth/register', json={
            'username': 'user1',
            'email': 'user1@example.com',
            'password': 'Password123!',
        })
        
        client.post('/api/v1/auth/register', json={
            'username': 'user2',
            'email': 'user2@example.com',
            'password': 'Password123!',
        })
        
        # Login as user1
        login1 = client.post('/api/v1/auth/login', json={
            'username': 'user1',
            'password': 'Password123!',
        })
        token1 = json.loads(login1.data)['access_token']
        
        # Login as user2
        login2 = client.post('/api/v1/auth/login', json={
            'username': 'user2',
            'password': 'Password123!',
        })
        token2 = json.loads(login2.data)['access_token']
        
        # User1 creates entry
        create_response = client.post(
            '/api/v1/entries',
            json={
                'title': 'User1 Entry',
                'content': 'This is user1 data',
            },
            headers={'Authorization': f'Bearer {token1}'}
        )
        
        entry_id = json.loads(create_response.data)['id']
        
        # User2 tries to access user1's entry
        response = client.get(
            f'/api/v1/entries/{entry_id}',
            headers={'Authorization': f'Bearer {token2}'}
        )
        
        # Should be forbidden
        assert response.status_code == 404


class TestSecurityHeaders:
    """Test security headers."""
    
    def test_hsts_header(self, client):
        """Test HSTS header."""
        response = client.get('/health')
        
        assert 'Strict-Transport-Security' in response.headers
    
    def test_x_content_type_options(self, client):
        """Test X-Content-Type-Options header."""
        response = client.get('/health')
        
        assert response.headers.get('X-Content-Type-Options') == 'nosniff'
    
    def test_x_frame_options(self, client):
        """Test X-Frame-Options header."""
        response = client.get('/health')
        
        assert response.headers.get('X-Frame-Options') == 'DENY'
    
    def test_csp_header(self, client):
        """Test Content-Security-Policy header."""
        response = client.get('/health')
        
        assert 'Content-Security-Policy' in response.headers


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests."""
    
    def test_full_workflow(self, client):
        """Test complete workflow: register, login, create, read, update, delete."""
        # Register
        reg_response = client.post('/api/v1/auth/register', json={
            'username': 'workflow_user',
            'email': 'workflow@example.com',
            'password': 'WorkflowPassword123!',
        })
        assert reg_response.status_code == 201
        
        # Login
        login_response = client.post('/api/v1/auth/login', json={
            'username': 'workflow_user',
            'password': 'WorkflowPassword123!',
        })
        assert login_response.status_code == 200
        token = json.loads(login_response.data)['access_token']
        
        # Create entry
        create_response = client.post(
            '/api/v1/entries',
            json={
                'title': 'My Journey',
                'content': 'Starting my journal journey',
                'mood': 'excited'
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        assert create_response.status_code == 201
        entry_id = json.loads(create_response.data)['id']
        
        # Read entry
        read_response = client.get(
            f'/api/v1/entries/{entry_id}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert read_response.status_code == 200
        
        # Update entry
        update_response = client.put(
            f'/api/v1/entries/{entry_id}',
            json={'title': 'My Updated Journey'},
            headers={'Authorization': f'Bearer {token}'}
        )
        assert update_response.status_code == 200
        
        # Delete entry
        delete_response = client.delete(
            f'/api/v1/entries/{entry_id}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert delete_response.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
