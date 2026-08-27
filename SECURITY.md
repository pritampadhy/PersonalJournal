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


