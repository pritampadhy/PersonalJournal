# Personal Journal Application - Quick Start Guide

## Prerequisites

- Python 3.11+
- PostgreSQL 13+ (or SQLite for development)
- pip (Python package manager)
- Git

## Development Setup (5 minutes)

### 1. Clone and Install
```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file for development
cp .env.example .env

# Edit .env with local values
# For development, you can use simple values:
# SECRET_KEY=your-dev-secret-key-minimum-32-chars-long-here
# JWT_SECRET_KEY=your-jwt-secret-key-minimum-32-chars-long-here
# ENCRYPTION_MASTER_KEY=<output from: python -c "import secrets; print(__import__('base64').b64encode(secrets.token_bytes(32)).decode())">
```

### 2. Database Setup
```bash
# Option A: Use SQLite (easiest for development)
# In .env, set:
# DATABASE_URL=sqlite:///journal.db

# Option B: Use PostgreSQL
# Create database:
psql -U postgres -c "CREATE DATABASE journal_db;"
psql -U postgres -c "CREATE USER journal_user WITH PASSWORD 'dev_password';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE journal_db TO journal_user;"

# In .env, set:
# DATABASE_URL=postgresql://journal_user:dev_password@localhost:5432/journal_db
```

### 3. Initialize Application
```bash
# Create tables
python app.py init-db

# Verify initialization
python app.py shell
>>> from models import db, User
>>> db.session.execute('SELECT 1')
```

### 4. Run Application
```bash
# Development server (with auto-reload)
flask run

# Or with Gunicorn (production-like)
gunicorn --workers=4 --bind=0.0.0.0:5000 "app:create_app()"
```

Application runs on `http://localhost:5000`

### 5. Health Check
```bash
# Check if running
curl http://localhost:5000/health
# Expected response:
# {"status":"healthy","database":"healthy",...}
```

## API Testing

### Register User
```bash
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "SecurePassword123!",
    "full_name": "John Doe"
  }'
```

### Login
```bash
RESPONSE=$(curl -s -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "SecurePassword123!"
  }')

# Extract token
TOKEN=$(echo $RESPONSE | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
echo "Token: $TOKEN"
```

### Create Journal Entry
```bash
curl -X POST http://localhost:5000/api/v1/entries \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "title": "My First Entry",
    "content": "This is my first journal entry!",
    "mood": "happy"
  }'
```

### Get Entries
```bash
curl -X GET http://localhost:5000/api/v1/entries \
  -H "Authorization: Bearer $TOKEN"
```

## Running Tests

### All Tests
```bash
pytest tests.py -v

# With coverage
pytest --cov=. tests.py -v

# Only security tests
pytest tests.py::TestPasswordHasher -v
pytest tests.py::TestSymmetricEncryption -v
pytest tests.py::TestTokenManager -v
```

### Specific Test
```bash
# Test login
pytest tests.py::TestAuthenticationEndpoints::test_login_success -v

# Test user isolation
pytest tests.py::TestJournalEndpoints::test_user_isolation -v
```

## Security Verification

### Static Code Analysis
```bash
# Check for security issues
bandit -r app.py config.py security.py models.py

# Check dependencies for vulnerabilities
safety check
pip-audit

# Code style and quality
flake8 app.py config.py security.py models.py
mypy app.py config.py security.py models.py
```

### Manual Security Testing

#### Test SQL Injection
```bash
# Try SQL injection in username
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin\" OR \"1\"=\"1",
    "password": "test"
  }'
# Should reject with validation error or 401
```

#### Test Cross-User Access
```bash
# User1 tries to access User2's entry (should fail)
curl -X GET http://localhost:5000/api/v1/entries/999 \
  -H "Authorization: Bearer $USER1_TOKEN"
# Should return 404
```

#### Test Token Manipulation
```bash
# Try modified token
MODIFIED_TOKEN="$TOKEN"xyz
curl -X GET http://localhost:5000/api/v1/entries \
  -H "Authorization: Bearer $MODIFIED_TOKEN"
# Should return 401 (invalid signature)
```

## Development Workflows

### Adding New Endpoint
```python
# In app.py
@app.route('/api/v1/new-endpoint', methods=['POST'])
@require_auth
def new_endpoint():
    """
    Endpoint description.
    """
    try:
        user_id = get_current_user_id()
        data = request.get_json()
        
        # Validate input
        if not all(k in data for k in ['required_field']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Process
        result = "success"
        
        # Audit log
        create_audit_log(
            event_type='ACTION_PERFORMED',
            user_id=user_id,
            ip_address=g.ip_address,
            user_agent=g.user_agent,
            success=True
        )
        
        db.session.commit()
        return jsonify({'result': result}), 200
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error: {e}", exc_info=True)
        return jsonify({'error': 'Operation failed'}), 500
```

### Adding Migration
```bash
# Create migration
flask db migrate -m "Description of changes"

# Review migration
cat migrations/versions/xxxx_description.py

# Apply migration
flask db upgrade

# Rollback if needed
flask db downgrade
```

### Adding Test
```python
# In tests.py
def test_new_feature(self, client, auth_token):
    """Test description."""
    response = client.post(
        '/api/v1/new-endpoint',
        json={'required_field': 'value'},
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['result'] == 'success'
```

## Docker Development

### Build Image
```bash
docker build -t journal-app:latest .
```

### Run Container
```bash
docker run -p 5000:5000 \
  -e DATABASE_URL=sqlite:///journal.db \
  -e SECRET_KEY=dev-secret-key-min-32-chars-here \
  -e JWT_SECRET_KEY=dev-jwt-secret-key-min-32-chars-here \
  -e ENCRYPTION_MASTER_KEY=... \
  journal-app:latest
```

### Docker Compose
```bash
# Start stack
docker-compose up

# View logs
docker-compose logs -f app

# Stop stack
docker-compose down
```

## Environment Variables Reference

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| FLASK_ENV | Yes | production | Flask environment |
| DATABASE_URL | Yes | - | Database connection string |
| SECRET_KEY | Yes | - | Flask session secret |
| JWT_SECRET_KEY | Yes | - | JWT signing key |
| ENCRYPTION_MASTER_KEY | Yes | - | Master encryption key |
| DEBUG | No | False | Debug mode |
| LOG_LEVEL | No | INFO | Logging level |
| BCRYPT_LOG_ROUNDS | No | 12 | Password hash cost |
| CORS_ORIGINS | No | localhost | Allowed CORS origins |

## Troubleshooting

### ImportError: No module named 'flask'
```bash
# Install dependencies
pip install -r requirements.txt
```

### Database connection failed
```bash
# Check DATABASE_URL in .env
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Or for SQLite
sqlite3 journal.db "SELECT 1"
```

### Encryption master key invalid
```bash
# Regenerate master key
python -c "import secrets; print(__import__('base64').b64encode(secrets.token_bytes(32)).decode())"

# Update in .env
# ENCRYPTION_MASTER_KEY=<new-key>
```

### Password hashing too slow
```bash
# Reduce BCRYPT_LOG_ROUNDS in .env for development
BCRYPT_LOG_ROUNDS=10  # Was 12

# Note: Use 12+ in production
```

### Rate limiting errors in tests
```bash
# Disable rate limiting for tests in config.py
RATE_LIMIT_ENABLED = False
```

## Next Steps

1. **Read Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md)
2. **Review Security**: See [SECURITY.md](SECURITY.md)
3. **Deploy**: See [DEPLOYMENT.md](DEPLOYMENT.md)
4. **API Docs**: See [API.md](API.md)
5. **Production Setup**: Follow pre-deployment checklist

## Common Commands

```bash
# Start dev server
flask run

# Run tests
pytest tests.py -v

# Security checks
bandit -r . && safety check

# Initialize database
python app.py init-db

# Drop database (dev only)
python app.py drop-db

# Interactive shell
python app.py shell

# Check code style
flake8 .

# Format code
black .

# Build for production
docker build -t journal-app:1.0.0 .
```

## Support

- **Issues**: Check existing issues or create new one
- **Security**: Report to security@example.com
- **Docs**: https://docs.example.com
- **Community**: #journal-app on Slack

---

**Last Updated**: 2024-01-15
**Version**: 1.0.0
