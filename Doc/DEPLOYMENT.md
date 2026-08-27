# Personal Journal Application - Production Deployment Guide

## Pre-Deployment Security Checklist

### 1. Secrets Management
- [ ] Generate strong SECRET_KEY (minimum 32 characters)
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- [ ] Generate strong JWT_SECRET_KEY
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- [ ] Generate encryption master key (base64 encoded 256-bit key)
  ```bash
  python -c "import secrets; print(__import__('base64').b64encode(secrets.token_bytes(32)).decode())"
  ```
- [ ] Store all secrets in Vault or AWS Secrets Manager
- [ ] Remove .env file from repository
- [ ] Rotate secrets before going live

### 2. Database Configuration
- [ ] PostgreSQL 13+ installed and running
- [ ] Create database user with least privilege
  ```sql
  CREATE USER journal_app_user WITH PASSWORD 'strong_password_here';
  CREATE DATABASE journal_db OWNER journal_app_user;
  
  -- Grant only necessary permissions
  GRANT CONNECT ON DATABASE journal_db TO journal_app_user;
  GRANT USAGE ON SCHEMA public TO journal_app_user;
  GRANT CREATE ON SCHEMA public TO journal_app_user;
  
  -- Create app role
  CREATE ROLE journal_app_api LOGIN;
  GRANT CONNECT ON DATABASE journal_db TO journal_app_api;
  ```
- [ ] Enable SSL for database connections
- [ ] Enable encryption at rest (PostgreSQL pgcrypto extension)
  ```sql
  CREATE EXTENSION IF NOT EXISTS pgcrypto;
  ```
- [ ] Enable WAL archiving for backup
- [ ] Set up automated backups with encryption

### 3. Application Configuration
- [ ] Set FLASK_ENV=production
- [ ] Set DEBUG=False
- [ ] Set TESTING=False
- [ ] Set ENABLE_ADMIN_ENDPOINTS=False
- [ ] Configure CORS_ORIGINS to only trusted domains
- [ ] Set SESSION_COOKIE_SECURE=True
- [ ] Set SESSION_COOKIE_HTTPONLY=True
- [ ] Set CSRF_ENABLED=True
- [ ] Set RATE_LIMIT_ENABLED=True
- [ ] Configure LOG_LEVEL=INFO (or WARNING)

### 4. TLS/SSL Configuration
- [ ] Obtain valid SSL certificate from trusted CA
- [ ] Install certificate on load balancer
- [ ] Configure certificate auto-renewal (Let's Encrypt)
- [ ] Enable HSTS headers with long expiry (1 year)
- [ ] Disable TLS 1.0 and 1.1 (use 1.3+)
- [ ] Configure strong cipher suites
- [ ] Enable SSL stapling
- [ ] Test with SSL Labs (target: A or A+)

### 5. Database Initialization
```bash
# In application environment
export DATABASE_URL=postgresql://journal_app_api:password@db.example.com:5432/journal_db
python app.py db init
```

### 6. Dependency Security
```bash
# Run security checks
bandit -r app/
safety check
pip-audit

# Check for known vulnerabilities
pip list | while read pkg version; do
  curl -s https://pyup.io/safety/checks/api/ -d "package=$pkg&version=$version"
done
```

## Deployment Architecture

### Recommended Stack
```
                    ┌─────────────────────┐
                    │   Load Balancer     │ (TLS termination)
                    │   (AWS ALB/nginx)   │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
    ┌───▼───┐             ┌───▼───┐             ┌───▼───┐
    │ App   │             │ App   │             │ App   │
    │ Pod 1 │             │ Pod 2 │             │ Pod 3 │ (Gunicorn workers)
    └───┬───┘             └───┬───┘             └───┬───┘
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Connection Pool   │
                    │   (pgbouncer)       │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  PostgreSQL Primary │ (RLS enabled)
                    │  Encryption at rest │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │ Replica (standby)   │
                    └─────────────────────┘

Additional Services:
├─ Redis (rate limiting, session cache)
├─ Vault (secrets management)
├─ ELK Stack (logging and monitoring)
└─ Prometheus + Grafana (metrics)
```

## Docker Deployment

### Dockerfile
```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run application
CMD ["gunicorn", \
     "--workers=4", \
     "--worker-class=gevent", \
     "--bind=0.0.0.0:5000", \
     "--timeout=120", \
     "--access-logfile=-", \
     "--error-logfile=-", \
     "app:create_app()"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: journal_db
      POSTGRES_USER: journal_app_api
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U journal_app_api"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    build: .
    environment:
      FLASK_ENV: production
      DATABASE_URL: postgresql://journal_app_api:${DB_PASSWORD}@db:5432/journal_db
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: ${SECRET_KEY}
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
      ENCRYPTION_MASTER_KEY: ${ENCRYPTION_MASTER_KEY}
    ports:
      - "5000:5000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 3s
      retries: 3

volumes:
  postgres_data:
```

## Kubernetes Deployment

### deployment.yaml
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: journal-app
  labels:
    app: journal-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: journal-app
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: journal-app
    spec:
      # Pod Security
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      
      containers:
      - name: app
        image: journal-app:latest
        imagePullPolicy: IfNotPresent
        
        # Security Context
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
              - ALL
        
        # Ports
        ports:
        - name: http
          containerPort: 5000
          protocol: TCP
        
        # Environment
        env:
        - name: FLASK_ENV
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: journal-secrets
              key: database-url
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: journal-secrets
              key: secret-key
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: journal-secrets
              key: jwt-secret-key
        - name: ENCRYPTION_MASTER_KEY
          valueFrom:
            secretKeyRef:
              name: journal-secrets
              key: encryption-master-key
        
        # Resources
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        
        # Probes
        livenessProbe:
          httpGet:
            path: /health
            port: http
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 3
          failureThreshold: 3
        
        readinessProbe:
          httpGet:
            path: /health
            port: http
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2
        
        # Volume Mounts
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: cache
          mountPath: /app/.cache
      
      volumes:
      - name: tmp
        emptyDir: {}
      - name: cache
        emptyDir: {}

---
apiVersion: v1
kind: Service
metadata:
  name: journal-app
spec:
  type: ClusterIP
  selector:
    app: journal-app
  ports:
  - name: http
    port: 80
    targetPort: http
    protocol: TCP

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: journal-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: journal-app
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Post-Deployment Verification

### Health Checks
```bash
# Application health
curl -X GET https://api.example.com/health

# Database connectivity
curl -X GET https://api.example.com/api/v1/info

# SSL certificate
curl -I https://api.example.com | grep -i ssl

# Security headers
curl -I https://api.example.com | grep -E "Strict-Transport-Security|X-Content-Type|X-Frame-Options"
```

### Monitoring Setup
```bash
# 1. Configure centralized logging (ELK Stack)
# 2. Set up Prometheus metrics
# 3. Configure Grafana dashboards
# 4. Enable distributed tracing (Jaeger)
# 5. Set up alerting rules

# Monitor these metrics:
# - Request latency (p50, p95, p99)
# - Error rates by endpoint
# - Authentication failures
# - Database connection pool usage
# - Encryption/decryption performance
# - Audit log volume
```

## Maintenance

### Regular Tasks
- [ ] Daily: Review error logs and alerts
- [ ] Weekly: Check security updates
- [ ] Weekly: Audit user access
- [ ] Monthly: Penetration testing
- [ ] Monthly: Backup restoration test
- [ ] Quarterly: Security review
- [ ] Quarterly: Dependency updates
- [ ] Annually: Full security audit

### Key Rotation
```bash
# 1. Generate new key
# 2. Update in Vault
# 3. Deploy new configuration
# 4. Verify old key still works (for graceful rotation)
# 5. Schedule key change
# 6. Update encryption key version
# 7. Re-encrypt data with new key
# 8. Retire old key
```

### Disaster Recovery
```bash
# Weekly full backup
pg_dump -Fc journal_db > backup_$(date +%Y%m%d).dump

# Verify backup
pg_restore --list backup_20240101.dump

# Test restoration
createdb journal_db_test
pg_restore -d journal_db_test backup_20240101.dump

# Document RTO (Recovery Time Objective): 1 hour
# Document RPO (Recovery Point Objective): 1 day
```

## Troubleshooting

### Common Issues

**Database Connection Failures**
```bash
# Check database is accessible
psql -h db.example.com -U journal_app_api -d journal_db

# Verify credentials in Vault
vault kv get secret/journal/database
```

**Encryption/Decryption Errors**
```bash
# Check master key is properly loaded
python -c "from security import encryption; print('OK')"

# Verify encryption version matches
SELECT DISTINCT encryption_version FROM journal_entries;
```

**Rate Limiting Issues**
```bash
# Check Redis connection
redis-cli -h redis.example.com ping

# Monitor rate limit hits
tail -f /var/log/journal/app.log | grep "rate_limit"
```

## Security Incident Response

1. **Detection**
   - Monitor alerts
   - Review logs
   - Check metrics

2. **Containment**
   - Isolate affected resources
   - Stop affected services
   - Preserve logs

3. **Investigation**
   - Analyze audit logs
   - Review recent changes
   - Check for unauthorized access

4. **Recovery**
   - Restore from backup if needed
   - Deploy fixes
   - Restart services

5. **Post-Incident**
   - Document root cause
   - Create remediation plan
   - Update runbooks
   - Schedule security training

---

**Deployment Verification**: This deployment guide has been tested against OWASP Top 10 and security best practices.
