"""
Personal Journal Application - Flask Application Factory

Initializes Flask app with:
- Security middleware (CORS, CSRF, rate limiting, headers)
- Database connection with RLS
- Error handling with security-conscious responses
- Authentication routes
- Journal API routes
- Audit logging integration
- Monitoring and health checks

SECURITY FEATURES:
- HSTS + CSP headers
- CSRF protection on state-changing operations
- Rate limiting per endpoint
- Request/response logging
- Security context for each request
- Graceful error handling
"""

import logging
import logging.config
import json
from datetime import datetime
from typing import Dict, Any, Tuple

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from werkzeug.exceptions import HTTPException
from werkzeug.security import generate_password_hash
import structlog

from config import get_config, load_dotenv_file
from models import db, User, JournalEntry, AuditLog, create_audit_log
from security import (
    init_security, password_hasher, token_manager, encryption,
    AuthenticationError, SecurityError, get_current_user_id, require_auth
)

# Load environment first
load_dotenv_file()

# Configure structured logging
def configure_logging(config):
    """Configure JSON logging for production."""
    
    if config.LOG_FORMAT == "json":
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    # Standard logging config
    log_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
            'json': {
                '()': structlog.stdlib.ProcessorFormatter,
                'processor': structlog.processors.JSONRenderer(),
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'json' if config.LOG_FORMAT == 'json' else 'standard',
                'stream': 'ext://sys.stdout',
            },
        },
        'loggers': {
            '': {
                'handlers': ['console'],
                'level': config.LOG_LEVEL,
            },
            'werkzeug': {'level': 'INFO'},
            'sqlalchemy': {'level': 'WARNING'},
        }
    }
    
    if config.LOG_FILE:
        log_config['handlers']['file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'json' if config.LOG_FORMAT == 'json' else 'standard',
            'filename': config.LOG_FILE,
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
        }
        log_config['loggers']['']['handlers'].append('file')
    
    logging.config.dictConfig(log_config)


def create_app(config_env: str = None) -> Flask:
    """
    Application factory.
    
    Creates and configures Flask application with all security middleware.
    
    Args:
        config_env: Environment name (development, staging, production)
        
    Returns:
        Configured Flask application
    """
    
    # Load configuration
    config = get_config(config_env)
    
    # Configure logging
    configure_logging(config)
    logger = logging.getLogger(__name__)
    logger.info("🚀 Initializing Personal Journal Application")
    
    # Create Flask app
    app = Flask(__name__)
    app.config.from_object(config)
    
    # Initialize database
    db.init_app(app)
    logger.info("✓ Database initialized")
    
    # Initialize security systems
    init_security(config)
    logger.info("✓ Security systems initialized")
    
    # =========================================================================
    # SECURITY MIDDLEWARE
    # =========================================================================
    
    # CORS Protection
    CORS(
        app,
        resources={r"/api/*": {
            "origins": config.CORS_ORIGINS,
            "allow_headers": ["Content-Type", "Authorization"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "supports_credentials": config.CORS_ALLOW_CREDENTIALS,
            "max_age": 3600,
        }},
        expose_headers=["Content-Type"],
    )
    logger.info(f"✓ CORS configured for origins: {config.CORS_ORIGINS}")
    
    # Security Headers (Talisman)
    Talisman(
        app,
        force_https=config.FLASK_ENV == "production",
        strict_transport_security=True,
        strict_transport_security_max_age=config.HSTS_MAX_AGE,
        strict_transport_security_include_subdomains=config.HSTS_INCLUDE_SUBDOMAINS,
        content_security_policy={
            "default-src": "'self'",
            "script-src": "'self'",
            "style-src": "'self'",
            "img-src": "'self' data: https:",
            "font-src": "'self'",
            "connect-src": "'self'",
            "frame-ancestors": "'none'",
            "base-uri": "'self'",
            "form-action": "'self'",
        },
        content_security_policy_nonce_in=["script-src"],
        referrer_policy="strict-origin-when-cross-origin",
        feature_policy={},
        session_cookie_secure=config.SESSION_COOKIE_SECURE,
        session_cookie_http_only=config.SESSION_COOKIE_HTTPONLY,
        session_cookie_samesite=config.SESSION_COOKIE_SAMESITE,
    )
    logger.info("✓ Security headers configured")
    
    # Rate Limiting
    if config.RATE_LIMIT_ENABLED:
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=[config.RATE_LIMIT_DEFAULT],
            storage_uri=config.RATE_LIMIT_STORAGE_URL if hasattr(config, 'RATE_LIMIT_STORAGE_URL') else None,
        )
        app.limiter = limiter
        logger.info("✓ Rate limiting enabled")
    
    # =========================================================================
    # REQUEST/RESPONSE MIDDLEWARE
    # =========================================================================
    
    @app.before_request
    def setup_request_context():
        """Set up request context for security logging."""
        g.request_id = request.headers.get('X-Request-ID', 'unknown')
        g.start_time = datetime.utcnow()
        g.ip_address = request.remote_addr
        g.user_agent = request.headers.get('User-Agent', 'unknown')
        g.user_id = None
    
    @app.after_request
    def add_security_headers(response):
        """Add additional security headers."""
        # Prevent MIME sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Disable XSS filtering (browser has this by default)
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        
        # Request ID for tracing
        response.headers['X-Request-ID'] = g.request_id
        
        # Remove server info
        response.headers.pop('Server', None)
        
        return response
    
    # =========================================================================
    # ERROR HANDLING
    # =========================================================================
    
    @app.errorhandler(400)
    def bad_request(error):
        """Handle bad request."""
        logger.warning(f"Bad request: {error}")
        return jsonify({
            'error': 'Bad request',
            'request_id': g.request_id
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        """Handle unauthorized."""
        return jsonify({
            'error': 'Unauthorized',
            'request_id': g.request_id
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        """Handle forbidden."""
        logger.warning(f"Forbidden access attempt from {g.ip_address}")
        return jsonify({
            'error': 'Forbidden',
            'request_id': g.request_id
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle not found."""
        return jsonify({
            'error': 'Not found',
            'request_id': g.request_id
        }), 404
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        """Handle rate limit exceeded."""
        logger.warning(f"Rate limit exceeded for {g.ip_address}")
        return jsonify({
            'error': 'Too many requests',
            'request_id': g.request_id
        }), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle internal server error."""
        logger.error(f"Internal server error: {error}", exc_info=True)
        return jsonify({
            'error': 'Internal server error',
            'request_id': g.request_id
        }), 500
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle other HTTP exceptions."""
        logger.warning(f"HTTP error {error.code}: {error.description}")
        return jsonify({
            'error': error.description or 'An error occurred',
            'request_id': g.request_id
        }), error.code or 500
    
    # =========================================================================
    # HEALTH CHECK & MONITORING
    # =========================================================================
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint (no auth required)."""
        try:
            # Check database connectivity
            db.session.execute('SELECT 1')
            db_status = "healthy"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            db_status = "unhealthy"
            return jsonify({
                'status': 'unhealthy',
                'database': db_status,
                'timestamp': datetime.utcnow().isoformat()
            }), 503
        
        return jsonify({
            'status': 'healthy',
            'database': db_status,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    @app.route('/api/v1/info', methods=['GET'])
    def app_info():
        """Application info (for debugging)."""
        return jsonify({
            'name': 'Personal Journal API',
            'version': '1.0.0',
            'environment': config.FLASK_ENV,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    # =========================================================================
    # AUTHENTICATION ROUTES
    # =========================================================================
    
    @app.route('/api/v1/auth/register', methods=['POST'])
    def register():
        """
        Register new user.
        
        Request body:
        {
            "username": "john_doe",
            "email": "john@example.com",
            "password": "securepassword123",
            "full_name": "John Doe"
        }
        """
        try:
            data = request.get_json()
            
            # Validate input
            if not all(k in data for k in ['username', 'email', 'password']):
                return jsonify({'error': 'Missing required fields'}), 400
            
            username = data['username']
            email = data['email']
            password = data['password']
            full_name = data.get('full_name', '')
            
            # Check if user exists
            if User.query.filter_by(username=username).first():
                return jsonify({'error': 'Username already exists'}), 409
            
            if User.query.filter_by(email=email).first():
                return jsonify({'error': 'Email already registered'}), 409
            
            # Validate password strength
            if len(password) < 8:
                return jsonify({'error': 'Password must be at least 8 characters'}), 400
            
            # Hash password
            password_hash = password_hasher.hash_password(password)
            
            # Create user
            user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                full_name=full_name,
                is_active=True,
            )
            
            db.session.add(user)
            db.session.flush()  # Get user ID
            
            # Audit log
            create_audit_log(
                event_type='USER_CREATED',
                user_id=user.id,
                resource_type='User',
                resource_id=user.id,
                ip_address=g.ip_address,
                user_agent=g.user_agent,
                success=True
            )
            
            db.session.commit()
            
            logger.info(f"✓ New user registered: {username}")
            
            return jsonify({
                'message': 'User registered successfully',
                'user_id': user.id
            }), 201
        
        except ValueError as e:
            db.session.rollback()
            logger.warning(f"Registration validation error: {e}")
            return jsonify({'error': str(e)}), 400
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration failed: {e}", exc_info=True)
            return jsonify({'error': 'Registration failed'}), 500
    
    @app.route('/api/v1/auth/login', methods=['POST'])
    def login():
        """
        User login.
        
        Request body:
        {
            "username": "john_doe",
            "password": "securepassword123"
        }
        
        Response:
        {
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
            "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
            "user_id": 1,
            "username": "john_doe"
        }
        """
        try:
            data = request.get_json()
            
            if not all(k in data for k in ['username', 'password']):
                create_audit_log(
                    event_type='USER_LOGIN_FAILED',
                    ip_address=g.ip_address,
                    user_agent=g.user_agent,
                    success=False,
                    error_message='Missing credentials'
                )
                db.session.commit()
                return jsonify({'error': 'Missing credentials'}), 400
            
            username = data['username']
            password = data['password']
            
            # Find user
            user = User.query.filter_by(username=username).first()
            
            if not user or not password_hasher.verify_password(password, user.password_hash):
                # Log failed attempt
                if user:
                    user.failed_login_attempts += 1
                    # Lock account after 5 failed attempts
                    if user.failed_login_attempts >= 5:
                        user.locked_until = datetime.utcnow() + timedelta(minutes=30)
                
                create_audit_log(
                    event_type='USER_LOGIN_FAILED',
                    user_id=user.id if user else None,
                    ip_address=g.ip_address,
                    user_agent=g.user_agent,
                    success=False,
                    error_message='Invalid credentials'
                )
                
                db.session.commit()
                logger.warning(f"Failed login attempt for {username}")
                return jsonify({'error': 'Invalid credentials'}), 401
            
            # Check if account is locked
            if user.locked_until and user.locked_until > datetime.utcnow():
                create_audit_log(
                    event_type='USER_LOGIN_FAILED',
                    user_id=user.id,
                    ip_address=g.ip_address,
                    user_agent=g.user_agent,
                    success=False,
                    error_message='Account locked'
                )
                db.session.commit()
                return jsonify({'error': 'Account temporarily locked'}), 429
            
            # Check if account is active
            if not user.is_active:
                create_audit_log(
                    event_type='USER_LOGIN_FAILED',
                    user_id=user.id,
                    ip_address=g.ip_address,
                    user_agent=g.user_agent,
                    success=False,
                    error_message='Account inactive'
                )
                db.session.commit()
                return jsonify({'error': 'Account is inactive'}), 401
            
            # Reset failed attempts on successful login
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_login_at = datetime.utcnow()
            user.last_login_ip = g.ip_address
            
            # Generate tokens
            access_token = token_manager.generate_access_token(user.id)
            refresh_token = token_manager.generate_refresh_token(user.id)
            
            # Audit log
            create_audit_log(
                event_type='USER_LOGIN',
                user_id=user.id,
                ip_address=g.ip_address,
                user_agent=g.user_agent,
                success=True
            )
            
            db.session.commit()
            
            logger.info(f"✓ User logged in: {username}")
            
            return jsonify({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user_id': user.id,
                'username': user.username
            }), 200
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Login failed: {e}", exc_info=True)
            return jsonify({'error': 'Login failed'}), 500
    
    @app.route('/api/v1/auth/refresh', methods=['POST'])
    def refresh_token():
        """
        Refresh access token using refresh token.
        
        Request body:
        {
            "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
        }
        """
        try:
            data = request.get_json()
            
            if 'refresh_token' not in data:
                return jsonify({'error': 'Missing refresh token'}), 400
            
            refresh_token_str = data['refresh_token']
            
            # Verify refresh token
            claims = token_manager.verify_token(refresh_token_str, token_type='refresh')
            user_id = int(claims['sub'])
            
            # Generate new access token
            access_token = token_manager.generate_access_token(user_id)
            
            logger.debug(f"✓ Token refreshed for user {user_id}")
            
            return jsonify({
                'access_token': access_token,
            }), 200
        
        except AuthenticationError as e:
            return jsonify({'error': str(e)}), 401
        except Exception as e:
            logger.error(f"Token refresh failed: {e}", exc_info=True)
            return jsonify({'error': 'Token refresh failed'}), 500
    
    # =========================================================================
    # JOURNAL API ROUTES
    # =========================================================================
    
    @app.route('/api/v1/entries', methods=['GET'])
    @require_auth
    def get_entries():
        """
        Get user's journal entries.
        
        Query parameters:
        - limit: Number of entries (default 20, max 100)
        - offset: Pagination offset (default 0)
        - sort: Sort order (created_at_desc, created_at_asc, updated_at_desc)
        """
        try:
            user_id = get_current_user_id()
            
            limit = min(int(request.args.get('limit', 20)), 100)
            offset = int(request.args.get('offset', 0))
            sort = request.args.get('sort', 'created_at_desc')
            
            # Build query
            query = JournalEntry.query.filter_by(
                user_id=user_id
            ).filter(
                JournalEntry.deleted_at.is_(None)
            )
            
            # Sort
            if sort == 'created_at_asc':
                query = query.order_by(JournalEntry.created_at.asc())
            elif sort == 'updated_at_desc':
                query = query.order_by(JournalEntry.updated_at.desc())
            else:  # created_at_desc (default)
                query = query.order_by(JournalEntry.created_at.desc())
            
            # Count total
            total = query.count()
            
            # Paginate
            entries = query.limit(limit).offset(offset).all()
            
            # Decrypt content
            entries_data = []
            for entry in entries:
                try:
                    decrypted_content = encryption.decrypt(entry.content, user_id)
                    entries_data.append({
                        'id': entry.id,
                        'title': entry.title,
                        'content': decrypted_content,
                        'mood': entry.mood,
                        'is_favorite': entry.is_favorite,
                        'created_at': entry.created_at.isoformat(),
                        'updated_at': entry.updated_at.isoformat(),
                    })
                except Exception as e:
                    logger.error(f"Failed to decrypt entry {entry.id}: {e}")
                    # Skip corrupted entries
                    continue
            
            return jsonify({
                'entries': entries_data,
                'total': total,
                'limit': limit,
                'offset': offset,
            }), 200
        
        except Exception as e:
            logger.error(f"Failed to get entries: {e}", exc_info=True)
            return jsonify({'error': 'Failed to retrieve entries'}), 500
    
    @app.route('/api/v1/entries', methods=['POST'])
    @require_auth
    def create_entry():
        """
        Create new journal entry.
        
        Request body:
        {
            "title": "My Day",
            "content": "Today was amazing...",
            "mood": "happy"
        }
        """
        try:
            user_id = get_current_user_id()
            data = request.get_json()
            
            if not all(k in data for k in ['title', 'content']):
                return jsonify({'error': 'Missing required fields'}), 400
            
            title = data['title']
            content = data['content']
            mood = data.get('mood')
            
            # Encrypt content
            encrypted_content = encryption.encrypt(content, user_id)
            
            # Create entry
            entry = JournalEntry(
                user_id=user_id,
                title=title,
                content=encrypted_content,
                mood=mood,
            )
            
            db.session.add(entry)
            db.session.flush()
            
            # Audit log (automatic via event listener)
            
            db.session.commit()
            
            logger.info(f"✓ Entry created: {entry.id} for user {user_id}")
            
            return jsonify({
                'id': entry.id,
                'title': entry.title,
                'created_at': entry.created_at.isoformat(),
            }), 201
        
        except ValueError as e:
            db.session.rollback()
            logger.warning(f"Entry validation error: {e}")
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create entry: {e}", exc_info=True)
            return jsonify({'error': 'Failed to create entry'}), 500
    
    @app.route('/api/v1/entries/<int:entry_id>', methods=['GET'])
    @require_auth
    def get_entry(entry_id: int):
        """Get specific journal entry."""
        try:
            user_id = get_current_user_id()
            
            entry = JournalEntry.query.filter_by(
                id=entry_id,
                user_id=user_id
            ).filter(
                JournalEntry.deleted_at.is_(None)
            ).first()
            
            if not entry:
                return jsonify({'error': 'Entry not found'}), 404
            
            # Decrypt content
            decrypted_content = encryption.decrypt(entry.content, user_id)
            
            return jsonify({
                'id': entry.id,
                'title': entry.title,
                'content': decrypted_content,
                'mood': entry.mood,
                'is_favorite': entry.is_favorite,
                'created_at': entry.created_at.isoformat(),
                'updated_at': entry.updated_at.isoformat(),
            }), 200
        
        except Exception as e:
            logger.error(f"Failed to get entry: {e}", exc_info=True)
            return jsonify({'error': 'Failed to retrieve entry'}), 500
    
    @app.route('/api/v1/entries/<int:entry_id>', methods=['PUT'])
    @require_auth
    def update_entry(entry_id: int):
        """Update journal entry."""
        try:
            user_id = get_current_user_id()
            data = request.get_json()
            
            entry = JournalEntry.query.filter_by(
                id=entry_id,
                user_id=user_id
            ).filter(
                JournalEntry.deleted_at.is_(None)
            ).first()
            
            if not entry:
                return jsonify({'error': 'Entry not found'}), 404
            
            # Update fields
            if 'title' in data:
                entry.title = data['title']
            
            if 'content' in data:
                # Encrypt new content
                entry.content = encryption.encrypt(data['content'], user_id)
            
            if 'mood' in data:
                entry.mood = data['mood']
            
            if 'is_favorite' in data:
                entry.is_favorite = data['is_favorite']
            
            db.session.commit()
            
            logger.info(f"✓ Entry updated: {entry_id} by user {user_id}")
            
            return jsonify({
                'id': entry.id,
                'title': entry.title,
                'updated_at': entry.updated_at.isoformat(),
            }), 200
        
        except ValueError as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update entry: {e}", exc_info=True)
            return jsonify({'error': 'Failed to update entry'}), 500
    
    @app.route('/api/v1/entries/<int:entry_id>', methods=['DELETE'])
    @require_auth
    def delete_entry(entry_id: int):
        """Soft-delete journal entry (GDPR compliant)."""
        try:
            user_id = get_current_user_id()
            
            entry = JournalEntry.query.filter_by(
                id=entry_id,
                user_id=user_id
            ).filter(
                JournalEntry.deleted_at.is_(None)
            ).first()
            
            if not entry:
                return jsonify({'error': 'Entry not found'}), 404
            
            # Soft delete
            entry.soft_delete()
            
            create_audit_log(
                event_type='ENTRY_DELETED',
                user_id=user_id,
                resource_type='JournalEntry',
                resource_id=entry_id,
                ip_address=g.ip_address,
                user_agent=g.user_agent,
                success=True
            )
            
            db.session.commit()
            
            logger.info(f"✓ Entry deleted: {entry_id} by user {user_id}")
            
            return jsonify({'message': 'Entry deleted'}), 200
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to delete entry: {e}", exc_info=True)
            return jsonify({'error': 'Failed to delete entry'}), 500
    
    # =========================================================================
    # DATABASE INITIALIZATION
    # =========================================================================
    
    @app.shell_context_processor
    def make_shell_context():
        """Make models available in flask shell."""
        return {
            'db': db,
            'User': User,
            'JournalEntry': JournalEntry,
            'AuditLog': AuditLog,
        }
    
    @app.cli.command()
    def init_db():
        """Initialize database with schema."""
        db.create_all()
        logger.info("✓ Database schema initialized")
    
    @app.cli.command()
    def drop_db():
        """Drop all database tables (USE WITH CAUTION)."""
        if config.FLASK_ENV == 'production':
            logger.error("Cannot drop database in production")
            return
        
        db.drop_all()
        logger.warning("✓ Database dropped")
    
    logger.info("✓ Application initialized successfully")
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=False, host='0.0.0.0', port=5000)
