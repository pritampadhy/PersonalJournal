# Security Policy (WIP)

## Supported Versions

Custom Instructions that bake in enterprise-grade production directives — threat modeling, secure coding standards, database isolation rules, and proper secret management.

| Version | Supported  (WIP)        |
| ------- | ------------------ |
| 5.1.x   | :white_check_mark: |
| 5.0.x   | :x:                |
| 4.0.x   | :white_check_mark: |
| < 4.0   | :x:                |

## Reporting a Vulnerability

Use this section to tell people how to report a vulnerability.

Tell them where to go, how often they can expect to get an update on a
reported vulnerability, what to expect if the vulnerability is accepted or
declined, etc.

**User Authentication**
---->Sign-in via Database 

**Multi-turn AI Interaction**
---->Real conversations with the  API for brainstorming/journaling

**Isolated Data Storage**
---->Each user's summaries/logs persist to Cloud DB — with zero cross-user leakage

**Secure Key Management**
---->API keys retrieved via Cloud Secret Manager, never hardcoded

        Guidelines 
**Authentication**●
Use Argon2id password hashing.
●
Require passwords of at least 12 characters.
●
Implement login rate limiting.
●
Use MFA for administrators.
●
Use short-lived access tokens.
●
Implement refresh-token rotation if refresh tokens are used.
●
Revoke sessions after password changes.
**Application security**

Never log passwords.
Never log journal content.
Never expose stack traces to users.
Validate all API input.
Enforce maximum request sizes.
Use dependency vulnerability scanning.
Run SAST in CI/CD.

**Database**

Separate database accounts for migrations and runtime.
Runtime account should not own tables.
Enable TLS between application and database.
Enable encrypted backups.
Test restoration procedures.
Use row-level security where appropriate.

**Infrastructure**

HTTPS only
HSTS enabled.
Restrict CORS to known origins.
Put database in a private network.
Use WAF/rate limiting.
Use centralized security monitoring.

**Core security decisions**

Passwords are hashed, never encrypted.
Journal entries are encrypted before storage.
Encryption keys are managed through a KMS/HSM or cloud secret
manager in production.
Every database query is scoped to the authenticated user.
UUIDs are used instead of predictable IDs.
Secrets never appear in source code.
TLS is required in production.
Authentication tokens are short-lived.
Security events are logged without logging journal content.
Database access uses least-privilege accounts.

### Authentication & Authorization
- ✅ OAuth 2.0 + JWT token-based authentication
- ✅ bcrypt password hashing (cost factor 12, ~200ms per hash)
- ✅ Account lockout protection (5 failed attempts → 30 min lockout)
- ✅ Token rotation on refresh
- ✅ CSRF protection on state-changing operations
- ✅ Role-based access control (RBAC)

### Encryption
- ✅ AES-256-GCM encryption at rest for all journal entries
- ✅ User-specific keys derived from master key using HKDF-SHA256
- ✅ Authenticated encryption (detects tampering)
- ✅ TLS 1.3+ for all network communication
- ✅ HTTPS-only cookies with Secure, HttpOnly, SameSite flags

### Database Security
- ✅ Row-level security (RLS) enforced at database level
- ✅ User data isolation - queries always filtered by user ID
- ✅ Parameterized queries (SQLAlchemy ORM)
- ✅ No direct password access at database level
- ✅ Soft deletes for GDPR compliance
- ✅ Immutable audit log (INSERT ONLY)

### Threat Model
Covers 14 identified threats including:
- SQL injection (Severity: Critical)
- Unauthorized data access (Critical)
- Credential compromise (High)
- Privilege escalation (High)
- Session hijacking (High)
- DDoS/Brute force (Medium)

### Isolation Strategy
```
┌─────────────────────────────────────┐
│          API Layer                  │
│  (User ID verified from token)      │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Application Layer              │
│  (Query filtered by user_id)        │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Database Layer (PostgreSQL)    │
│  (Row-Level Security enforced)      │
│  (Encryption at field level)        │
└─────────────────────────────────────┘
```


## 🔒 Security Checklist

Pre-Production:
- [ ] All secrets in Vault (not in code)
- [ ] SSL/TLS certificate installed
- [ ] Database encryption enabled
- [ ] Rate limiting configured
- [ ] Security headers configured
- [ ] CORS policy set to minimum
- [ ] Audit logging enabled
- [ ] Backups encrypted and tested
- [ ] Security team onboarded

Ongoing:
- [ ] Daily log analysis
- [ ] Weekly security audits
- [ ] Monthly penetration tests
- [ ] Quarterly threat model review
- [ ] Key rotation scheduled

## 📊 Audit Logging

All sensitive operations logged:
- User login/logout
- Registration
- Failed authentication
- Journal entry CRUD
- User deletion
- Account lockout

Audit logs:
- Immutable (INSERT ONLY, no updates/deletes)
- Include timestamp, user, action, resource, IP, user agent
- Retained for 1 year (configurable)

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
