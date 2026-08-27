# Personal Journal Application - Enterprise Security Architecture

## 1. System Overview

The Personal Journal is a secure, self-contained note storage application with the following characteristics:
- **Per-user data isolation**: Each user's data is cryptographically isolated
- **End-to-end encryption**: All sensitive data encrypted at rest
- **OAuth 2.0 + JWT authentication**: Industry-standard token-based auth
- **RBAC model**: Role-based access control with minimal permissions
- **Audit logging**: Complete audit trail of all operations
- **GDPR/Privacy compliant**: Data minimization and right to deletion

## 2. Threat Model

### Identified Threats & Mitigations

| Threat | Risk Level | Mitigation |
|--------|-----------|-----------|
| SQL Injection | Critical | Parameterized queries, ORM (SQLAlchemy), input validation |
| Unauthorized data access | Critical | JWT tokens, database-level row-level security, encryption at rest |
| Credential compromise | High | bcrypt hashing (cost=12), rate limiting, MFA support |
| Privilege escalation | High | RBAC enforcement at DB and API level |
| Session hijacking | High | Secure cookies, CSRF protection, token rotation |
| XSS attacks | Medium | Input sanitization, output encoding, CSP headers |
| CSRF attacks | Medium | CSRF tokens on state-changing operations |
| DDoS/Brute force | Medium | Rate limiting, account lockout after N failures |
| Data breaches | Critical | Encryption at rest + in transit, secrets rotation |
| Insider threats | Medium | Audit logging, least privilege, separation of duties |

### Attack Surface

```
Internet
   │
   ├─→ API Gateway (rate limit, auth check)
   │      │
   │      ├─→ Authentication Endpoint (login, refresh)
   │      │      │
   │      │      └─→ User DB (password hash only)
   │      │
   │      └─→ Journal Endpoints (protected by JWT)
   │             │
   │             ├─→ User Context (from token)
   │             │
   │             └─→ Journal DB (row-level security)
   │
   └─→ Admin Console (separate auth, IP-restricted)
```

## 3. Data Classification

| Data Type | Classification | Encryption | Storage |
|-----------|----------------|-----------|---------|
| User passwords | Secret | bcrypt + salt | User table |
| JWT tokens | Sensitive | In-memory only, short TTL | Cache/session |
| Journal entries | Private | AES-256-GCM | Journal table |
| User metadata | Personal | Cleartext | User table |
| API logs | Sensitive | Cleartext | Audit table |
| Encryption keys | Secret | Hardware or vault | Key Management Service |

## 4. Database Isolation Strategy

### Database-Level Security

```sql
-- Row-Level Security (RLS)
CREATE POLICY user_journal_isolation ON journal_entries
  USING (user_id = current_user_id)
  WITH CHECK (user_id = current_user_id);

-- Principle of Least Privilege
CREATE ROLE journal_app_api LOGIN;
GRANT SELECT, INSERT, UPDATE ON journals TO journal_app_api;
REVOKE DELETE ON journals FROM journal_app_api;

-- No direct access to passwords
REVOKE SELECT (password_hash) ON users FROM journal_app_api;
```

### Application-Level Isolation

- User ID from JWT token is immutable and verified at API boundary
- Database queries always filtered by authenticated user ID
- Soft deletes (logical deletion) for audit trail
- Immutable audit log table (INSERT ONLY)

## 5. Authentication Flow

```
User Login
   │
   ├─→ POST /auth/login (username, password)
   │      │
   │      ├─→ Hash password with stored salt
   │      ├─→ Compare hash (constant-time)
   │      │
   │      └─→ Generate tokens:
   │             • Access Token (JWT, 15 min TTL)
   │             • Refresh Token (secure cookie, 7 day TTL)
   │
User API Requests
   │
   ├─→ Include Access Token in Authorization header
   │      │
   │      ├─→ Verify JWT signature
   │      ├─→ Check token expiration
   │      ├─→ Extract user_id
   │      │
   │      └─→ Execute operation scoped to user_id
   │
Token Refresh
   │
   ├─→ POST /auth/refresh (using refresh token cookie)
   │      │
   │      ├─→ Validate refresh token
   │      ├─→ Check refresh token rotation
   │      │
   │      └─→ Issue new access token + refresh token
```

## 6. Encryption Strategy

### At-Rest Encryption (Field Level)

```python
# Journal entries encrypted with user-specific key
entry_data = {
    'title': 'My Day',
    'content': 'Sensitive thoughts...',
    'created_at': timestamp
}

# Encrypt with: AES-256-GCM(data, user_key, nonce)
# Store: ciphertext | nonce | auth_tag
```

### In-Transit Encryption

- TLS 1.3+ only
- HSTS headers with long expiry
- Secure cookies (HttpOnly, Secure, SameSite=Strict)
- Certificate pinning (optional, for native apps)

### Key Management

- Master key: stored in external vault (AWS KMS, HashiCorp Vault)
- User keys: derived from master key using HKDF-SHA256
- Key rotation: automatic, with versioning
- No key material in application code or logs

## 7. Secure Coding Standards

### Input Validation
- All inputs validated against schema
- Type checking enforced
- Length limits enforced
- Whitelist approach (allow known good)

### Output Encoding
- JSON responses with correct Content-Type
- HTML sanitization for any rendered content
- No eval() or exec() ever
- No dangerous deserialization

### Error Handling
- Generic error messages to users
- Detailed errors logged server-side
- No stack traces in responses
- No sensitive info in logs

### Dependency Management
- Pinned versions with hashes
- Regular security audits (safety, bandit)
- No dev dependencies in production
- SBOM (software bill of materials) generated

## 8. Secrets Management

### Secret Types & Rotation

| Secret | Rotation | Storage | Access |
|--------|----------|---------|--------|
| DB password | 90 days | Env var / Vault | Application server only |
| JWT signing key | 1 year | Vault + HSM | Signing service only |
| Encryption master key | 1 year | HSM | Key service only |
| API keys | 180 days | Vault | Config at startup |
| Refresh token | Per use | Secure cookie | HTTP only |

### Secrets NOT in Code

```
❌ NEVER commit:
- .env files
- config/*.json with secrets
- Database credentials
- API keys
- Private keys
- Encryption keys

✅ ALWAYS use:
- Environment variables
- Secrets manager (Vault, AWS Secrets Manager)
- HSM for master keys
- Encrypted config files (with separate key storage)
```

## 9. Audit Logging

All sensitive operations logged with:
- Timestamp (UTC)
- User ID
- Action type (LOGIN, CREATE_ENTRY, UPDATE_ENTRY, DELETE_ENTRY)
- Resource ID
- IP address
- User agent
- Result (success/failure)
- Failure reason

Audit logs are:
- Immutable (INSERT only)
- Queryable by admins
- Retained per compliance requirement (suggest: 1 year)
- Not accessible by users
- Backed up separately

## 10. Deployment Security Checklist

### Pre-Production
- [ ] All secrets in vault, not in repository
- [ ] SSL/TLS certificate valid and renewed
- [ ] Database encryption at rest enabled
- [ ] Rate limiting configured
- [ ] CORS policy set to minimum
- [ ] Security headers configured (CSP, HSTS, etc.)
- [ ] WAF rules in place
- [ ] DDoS protection enabled
- [ ] Backup strategy tested (encryption validated)
- [ ] Disaster recovery plan documented

### Ongoing
- [ ] Daily log analysis for anomalies
- [ ] Weekly security audits (bandit, safety)
- [ ] Monthly penetration tests
- [ ] Quarterly threat model review
- [ ] Annual security training
- [ ] Dependency updates and patching
- [ ] Key rotation schedule maintained
- [ ] Access logs reviewed

## 11. Compliance Mapping

### GDPR
- User consent collected and logged
- Right to access: `/users/me/export`
- Right to deletion: soft delete + scheduled hard delete
- Data processing agreement in place
- DPA with cloud provider documented

### OWASP Top 10
1. ✅ Injection - Parameterized queries, input validation
2. ✅ Broken authentication - JWT + bcrypt + MFA-ready
3. ✅ XSS - Input sanitization, output encoding
4. ✅ XXE - Disabled XML parsing
5. ✅ Broken access control - RBAC + RLS
6. ✅ Security misconfiguration - Infrastructure as Code
7. ✅ XSS (Client-side) - CSP headers
8. ✅ CSRF - CSRF tokens + SameSite cookies
9. ✅ Component vulnerabilities - Dependency scanning
10. ✅ Insufficient logging - Comprehensive audit log

## 12. Performance & Security Trade-offs

### bcrypt cost=12
- Security: ✅ Excellent (high computational cost)
- Performance: ⚠️ ~200ms per hash (acceptable for auth)
- Mitigation: Cache successful logins, use redis session store

### AES-256-GCM
- Security: ✅ Excellent (authenticated encryption)
- Performance: ⚠️ CPU overhead for large entries
- Mitigation: Use hardware acceleration, cipher offloading

### Database RLS
- Security: ✅ Defense in depth
- Performance: ⚠️ Query planner overhead (~5%)
- Benefit: Prevents bugs from bypassing app logic

## 13. Incident Response

### Security Incident Response Plan

1. **Detection** → Alert triggered
2. **Triage** → Severity assessment
3. **Containment** → Isolate affected systems
4. **Investigation** → Review audit logs
5. **Eradication** → Remove compromise
6. **Recovery** → Restore from clean backup
7. **Lessons Learned** → Post-mortem + process update

### Contacts & Escalation
- Security team pager: (configured per environment)
- Legal/compliance: (configured per environment)
- Executive escalation: (configured per environment)

## 14. Security Testing

### Required Testing Before Production

```bash
# Static code analysis
bandit -r app/

# Dependency vulnerabilities
safety check
pip-audit

# Secrets scanning
git-secrets --scan

# SAST with multiple tools
semgrep --config=p/security-audit

# Integration tests with auth
pytest -m security

# Load testing (verify rate limits work)
locust -f tests/load_test.py

# Manual penetration testing
# - SQL injection payloads
# - JWT tampering
# - CSRF attacks
# - Session fixation
```

## 15. Documentation & Runbooks

Each deployment includes:
- **Security runbook**: How to respond to common issues
- **Key rotation runbook**: Step-by-step process
- **Disaster recovery runbook**: Backup restoration
- **Forensics playbook**: Incident investigation
- **Architecture decision records (ADRs)**: Why certain choices made

---

**Last Updated**: 2024
**Version**: 1.0
**Review Schedule**: Quarterly
