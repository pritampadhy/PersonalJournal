# PersonalJournal (ToBeModified)
Personal Journal — an authenticated web app where users sign in, brainstorm or journal with LLM, and have their conversations automatically summarized and saved. 

# Personal Journal Application - Enterprise Security Edition

A production-grade, secure journal application built with industry best practices for encryption, authentication, and data protection.

## 🔐 Security Features
# Production security directives

## Threat model
- Assets: credentials, journal plaintext, tokens, LLM prompts/responses, provider keys, audit records.
- Trust boundaries: browser/API, API/database, API/LLM provider, agent/tools/social APIs, operators/CI.
- Threats: account takeover, IDOR/cross-tenant reads, SQL injection, XSS, CSRF, prompt injection, data leakage to model providers, tool misuse, supply-chain compromise, abuse/cost exhaustion, backups/logs exposing plaintext.
- Mitigations: Argon2id, short-lived tokens with rotation/revocation, TLS, strict owner predicates, encrypted fields, parameterized ORM, validation, rate limits, redacted logs, least-privilege service accounts, approval gates for write tools, egress allowlists, monitoring and incident response.

## Database isolation
Every query for tenant-owned data MUST constrain by authenticated `owner_id`; never accept owner IDs from clients. For enterprise multi-tenant deployments, use PostgreSQL Row-Level Security with a transaction-local tenant claim, separate encryption keys per tenant, separate schemas or databases for high-sensitivity tenants, and tested backup/restore isolation.

## Secrets
Use a cloud secret manager/Vault in production. Inject secrets at runtime; never commit `.env`, keys, tokens, prompts containing secrets, or production dumps. Rotate provider keys and JWT/encryption keys with a key-ID scheme and planned re-encryption. Keep encryption keys separate from database backups. Add secret scanning to CI.

## Authentication and application security
Use HTTPS/HSTS, secure HttpOnly SameSite cookies if moving from bearer tokens, MFA/passkeys for enterprise, email verification, password-reset tokens that are single-use and hashed at rest, login throttling, generic auth errors, CSRF protection for cookie auth, CSP, dependency/SAST/DAST scanning, migrations reviewed and reversible, and immutable audit logs. Disable interactive API docs in production.

## LLM and agent policy
Default to read-only journaling tools. Treat journal text and retrieved content as untrusted prompt data. Use allowlisted tools with typed schemas, per-user authorization inside every tool, timeouts, budgets, rate limits, output validation, PII/redaction controls, provider data-retention review, and human confirmation for publishing, messaging, deleting, or financial actions. Do not grant an agent unrestricted shell, browser, database, or social-media access. Record tool decisions without recording sensitive plaintext.

## Release gates
Threat model updated; tests cover auth/IDOR/isolation; dependency and secret scans pass; SBOM generated; backups encrypted and restore-tested; key rotation tested; incident runbook and data-deletion/export workflow approved; red-team prompt-injection and exfiltration tests pass; DPA/consent and regional data-retention requirements reviewed.



### Compliance
- ✅ GDPR-compliant (right to access, right to deletion)
- ✅ OWASP Top 10 protections
- ✅ Comprehensive audit trail
- ✅ Data minimization principles
- ✅ User consent tracking

### API Security
- ✅ Rate limiting (100/hour default, configurable per endpoint)
- ✅ Security headers (HSTS, CSP, X-Frame-Options, etc.)
- ✅ Input validation and sanitization
- ✅ CORS with whitelist
- ✅ Request ID tracing
- ✅ Comprehensive error logging

## 📁 Project Structure

```
.
├── README.md                    # This file
├── ARCHITECTURE.md              # System design & threat model
├── DEPLOYMENT.md                # Production deployment guide
├── QUICKSTART.md                # Quick start guide
├── API.md                       # API reference documentation
│
├── Core Application
├── app.py                       # Flask application factory
├── config.py                    # Configuration management
├── security.py                  # Security utilities (encryption, auth, hashing)
├── models.py                    # Database models (User, JournalEntry, AuditLog)
│
├── Configuration
├── .env.example                 # Environment variables template
├── requirements.txt             # Python dependencies
│
├── Testing
├── tests.py                     # Comprehensive test suite (50+ tests)
│
├── Docker
└── Dockerfile                   # Container image definition
└── docker-compose.yml           # Multi-container setup
```

## 🚀 Quick Start

### Development (2 minutes)
```bash
# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env

# Initialize database
python app.py init-db

# Run application
flask run
```

Visit `http://localhost:5000/health` to verify

### Production (see DEPLOYMENT.md)
- Uses PostgreSQL with encryption at rest
- Gunicorn + gevent workers
- Load balancer with TLS termination
- Automated backups with encryption
- Monitoring and alerting

## 🔑 Key Technologies

### Security
- **Hashing**: bcrypt with cost factor 12
- **Encryption**: AES-256-GCM (NIST-approved)
- **Key Derivation**: HKDF-SHA256
- **Tokens**: JWT (HS256, RS256, ES256 supported)
- **TLS**: 1.3+ with strong cipher suites

### Backend
- **Framework**: Flask 3.0
- **Database**: PostgreSQL 13+ (SQLite for dev)
- **ORM**: SQLAlchemy 2.0
- **Validation**: Pydantic
- **Logging**: Structured JSON logging

### DevOps (only For Reference)
- **Containerization**: Docker
- **Orchestration**: Kubernetes (example configs provided)
- **Secrets**: Vault /  Secrets Manager
- **Monitoring**: Prometheus + Grafana ready
- **CI/CD**: GitHub Actions ready

## 📊 Architecture Highlights


### Data Flow
```
User Input → Validation → Authentication → Encryption → Database
                                              ↓
                                          Audit Log
```



## 🧪 Testing

### Test Coverage
- **Security tests**: 15+ tests
- **Authentication tests**: 8+ tests
- **API tests**: 20+ tests
- **Integration tests**: 5+ tests
- **Total**: 50+ comprehensive tests

### Run Tests
```bash
# All tests
pytest tests.py -v

# With coverage
pytest --cov=. tests.py

# Security tests only
pytest tests.py::TestPasswordHasher -v
pytest tests.py::TestSymmetricEncryption -v
pytest tests.py::TestTokenManager -v
```

### Security Validation
```bash
# Static analysis
bandit -r .           # Security issues
safety check          # Dependency vulnerabilities
flake8 .             # Code quality
mypy .               # Type checking
```

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| **ARCHITECTURE.md** | System design, threat model, security architecture (15 sections) |
| **DEPLOYMENT.md** | Production deployment, Docker, Kubernetes (25+ sections) |
| **API.md** | Complete API reference with examples (20+ endpoints) |
| **QUICKSTART.md** | Quick start, development setup, troubleshooting |
| **README.md** (this file) | Overview and project structure |



## 📋 API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - User login
- `POST /auth/refresh` - Refresh access token

### Journal Entries
- `GET /entries` - List entries (paginated)
- `GET /entries/{id}` - Get single entry
- `POST /entries` - Create entry (content auto-encrypted)
- `PUT /entries/{id}` - Update entry
- `DELETE /entries/{id}` - Delete entry (soft delete)

### Health
- `GET /health` - Application health check
- `GET /info` - Application info

See [API.md](API.md) for complete reference with examples.

## 🔐 Password Hashing

```python
from security import password_hasher

# Hash password (returns bcrypt hash with salt)
hash = password_hasher.hash_password("SecurePassword123!")
# ~200ms per hash (cost factor 12)

# Verify password (constant-time comparison)
is_valid = password_hasher.verify_password("SecurePassword123!", hash)
# Returns False for wrong password, never raises exception
```

## 🔐 Encryption

```python
from security import encryption

# Encrypt user data
ciphertext = encryption.encrypt("Sensitive data", user_id=123)
# Uses user-specific key derived from master key

# Decrypt user data
plaintext = encryption.decrypt(ciphertext, user_id=123)
# Only works with correct user_id (different key)

# Tampering detected
try:
    encryption.decrypt(corrupted_ciphertext, user_id=123)
except EncryptionError:
    print("Data tampered with")
```

## 🔐 Token Management

```python
from security import token_manager

# Generate access token (15 min TTL)
access_token = token_manager.generate_access_token(user_id=123)

# Generate refresh token (7 day TTL)
refresh_token = token_manager.generate_refresh_token(user_id=123)

# Verify token
claims = token_manager.verify_token(access_token, token_type='access')
# Returns: {'sub': '123', 'iat': ..., 'exp': ..., 'type': 'access'}

# Invalid or expired tokens raise AuthenticationError
```

## 🚦 Rate Limiting

Default limits:
- **General**: 100 requests/hour
- **Authentication**: 20 requests/hour  
- **Journal**: 1000 requests/hour

Account lockout:
- 5 failed login attempts → 30 minute lockout
- Lockout tracked and logged

## 🌍 Deployment Options

### Docker
```bash
docker build -t journal-app:latest .
docker run -p 5000:5000 journal-app:latest
```

### Kubernetes
Full example manifests provided:
- Deployment with rolling updates
- Service for load balancing
- HPA for auto-scaling
- Security contexts enforced
- Liveness/readiness probes

### Traditional VM
- Gunicorn + gevent workers
- Supervisor for process management
- Nginx reverse proxy + TLS termination
- PostgreSQL with WAL archiving
- Redis for caching/rate limiting

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed guides.

## 🔄 Configuration Management

Configuration hierarchy:
1. Vault / Secrets Manager (production)
2. Environment variables
3. `.env` file (development only)
4. Defaults in config.py

Never commit:
- `.env` with real secrets
- Private keys or certificates
- Database credentials
- API keys

## 📈 Monitoring

Ready for:
- **Logs**: JSON structured logging → ELK Stack
- **Metrics**: Prometheus-compatible metrics
- **Tracing**: Distributed tracing (Jaeger/Zipkin)
- **Alerts**: PagerDuty / Slack integration

Example metrics:
- Request latency (p50, p95, p99)
- Error rates by endpoint
- Authentication failures
- Database pool usage
- Encryption/decryption performance

## 📖 Learning Path

1. **Start here**: [QUICKSTART.md](QUICKSTART.md) - Get running in 5 minutes
2. **Understand design**: [ARCHITECTURE.md](ARCHITECTURE.md) - System design & threat model
3. **Review security**: [security.py](security.py) - Implementation details
4. **Test thoroughly**: [tests.py](tests.py) - 50+ test examples
5. **Deploy confidently**: [DEPLOYMENT.md](DEPLOYMENT.md) - Production setup

## 🤝 Contributing

Security-focused changes welcome:
1. All code must pass security checks (bandit, safety)
2. All endpoints require authentication where appropriate
3. Add tests for new features
4. Update documentation

## 📄 License

This is a reference implementation. Use and modify as needed for your use case.

## 🔗 Resources

- **OWASP Top 10**: https://owasp.org/Top10/
- **JWT**: https://jwt.io/
- **Cryptography**: https://cryptography.io/
- **SQLAlchemy**: https://www.sqlalchemy.org/
- **Flask**: https://flask.palletsprojects.com/

## 📞 Support

For questions or issues:
- Check [QUICKSTART.md](QUICKSTART.md) troubleshooting section
- Review error messages in application logs
- Check security audit logs via database

---

## Summary

**Personal Journal Application** is a complete, production-ready reference implementation demonstrating:

✅ **Enterprise-grade security** with encryption, authentication, and authorization  
✅ **Comprehensive threat modeling** covering 14+ identified threats  
✅ **Database isolation** at multiple levels (API, application, database)  
✅ **Complete audit trail** for compliance and forensics  
✅ **50+ security tests** ensuring protection against common attacks  
✅ **Full documentation** for developers and operators  
✅ **Multiple deployment options** from Docker to Kubernetes  
✅ **Production-ready code** following industry best practices  

**Created**: 2024-01-15  
**Version**: 1.0.0  
**Status**: Production Ready ✅

