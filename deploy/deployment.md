CI/CD security gate

Your deployment pipeline should effectively be:
Developer Commit
│
▼
Unit Tests
│
▼
Authorization / Isolation Tests
│
▼
Static Security Analysis
│
▼
Dependency Vulnerability Scan
│
▼
Secret Scan
│
▼
Container Scan
│
▼
Deploy to Staging
│
▼
Security Tests
│
▼
Production
A deployment should fail automatically if secrets, critical dependency
vulnerabilities, or authorization failures are detected.


Deployment Options
Docker
docker build -t journal-app:latest .
docker run -p 5000:5000 journal-app:latest
Kubernetes
Full example manifests provided:

Deployment with rolling updates
Service for load balancing
HPA for auto-scaling
Security contexts enforced
Liveness/readiness probes
Traditional VM
Gunicorn + gevent workers
Supervisor for process management
Nginx reverse proxy + TLS termination
PostgreSQL with WAL archiving
Redis for caching/rate limiting
See DEPLOYMENT.md for detailed guides.

🔄 Configuration Management
Configuration hierarchy:

Vault / Secrets Manager (production)
Environment variables
.env file (development only)
Defaults in config.py
Never commit:

.env with real secrets
Private keys or certificates
Database credentials
API keys
