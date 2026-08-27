# Personal Journal API - Complete Reference

## Base URL
```
https://api.example.com/api/v1
```

## Authentication

All endpoints except `/auth/register`, `/auth/login`, and `/health` require authentication.

### Authorization Header
```
Authorization: Bearer <access_token>
```

### Token Lifecycle
- **Access Token**: Valid for 15 minutes
- **Refresh Token**: Valid for 7 days
- Refresh tokens are automatically rotated on use

## Error Handling

All errors follow this format:
```json
{
  "error": "Error message",
  "request_id": "unique-request-id"
}
```

### Error Codes
| Code | Meaning |
|------|---------|
| 400 | Bad request (invalid input) |
| 401 | Unauthorized (missing or invalid token) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Not found |
| 409 | Conflict (resource already exists) |
| 429 | Rate limited |
| 500 | Internal server error |

## Endpoints

### Authentication

#### Register User
**POST** `/auth/register`

Create a new user account.

**Request Body**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePassword123!",
  "full_name": "John Doe"
}
```

**Requirements**
- `username`: 3-100 alphanumeric characters (no spaces)
- `email`: Valid email format, unique
- `password`: Minimum 8 characters
- `full_name`: Optional

**Response (201 Created)**
```json
{
  "message": "User registered successfully",
  "user_id": 1
}
```

**Errors**
- 400: Missing fields or validation failed
- 409: Username or email already exists

**Example**
```bash
curl -X POST https://api.example.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "SecurePassword123!",
    "full_name": "John Doe"
  }'
```

---

#### Login
**POST** `/auth/login`

Authenticate and receive access and refresh tokens.

**Request Body**
```json
{
  "username": "john_doe",
  "password": "SecurePassword123!"
}
```

**Response (200 OK)**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user_id": 1,
  "username": "john_doe"
}
```

**Security Features**
- Account lockout after 5 failed attempts (30 minute duration)
- Failed attempts logged to audit trail
- Passwords hashed with bcrypt (cost factor 12)
- Constant-time password comparison

**Errors**
- 401: Invalid credentials
- 429: Account temporarily locked

**Example**
```bash
curl -X POST https://api.example.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "SecurePassword123!"
  }'
```

---

#### Refresh Token
**POST** `/auth/refresh`

Get a new access token using a refresh token.

**Request Body**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response (200 OK)**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Security Features**
- Refresh tokens rotate on use
- Old tokens become invalid
- Tokens include unique JTI (JWT ID)

**Errors**
- 401: Invalid or expired refresh token

**Example**
```bash
curl -X POST https://api.example.com/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }'
```

---

### Journal Entries

#### Create Entry
**POST** `/entries`

Create a new journal entry.

**Authentication Required**: Yes (Bearer token)

**Request Body**
```json
{
  "title": "My Day",
  "content": "Today was amazing...",
  "mood": "happy"
}
```

**Requirements**
- `title`: 1-500 characters, required
- `content`: At least 1 character, max 1MB, required
- `mood`: Optional, predefined values

**Response (201 Created)**
```json
{
  "id": 1,
  "title": "My Day",
  "created_at": "2024-01-15T10:30:00+00:00"
}
```

**Security Features**
- Content automatically encrypted with AES-256-GCM
- User isolation enforced at database level
- Audit logged

**Errors**
- 400: Validation failed
- 401: Missing or invalid token

**Example**
```bash
curl -X POST https://api.example.com/api/v1/entries \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "title": "My Day",
    "content": "Today was amazing...",
    "mood": "happy"
  }'
```

---

#### Get All Entries
**GET** `/entries`

Retrieve all journal entries for authenticated user.

**Authentication Required**: Yes

**Query Parameters**
| Parameter | Type | Default | Max |
|-----------|------|---------|-----|
| limit | integer | 20 | 100 |
| offset | integer | 0 | - |
| sort | string | created_at_desc | - |

**Sort Options**
- `created_at_desc`: Newest first (default)
- `created_at_asc`: Oldest first
- `updated_at_desc`: Recently modified first

**Response (200 OK)**
```json
{
  "entries": [
    {
      "id": 1,
      "title": "My Day",
      "content": "Today was amazing...",
      "mood": "happy",
      "is_favorite": false,
      "created_at": "2024-01-15T10:30:00+00:00",
      "updated_at": "2024-01-15T10:30:00+00:00"
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

**Security Features**
- Only user's own entries returned
- Content decrypted transparently
- Soft-deleted entries excluded

**Errors**
- 401: Missing or invalid token

**Example**
```bash
curl -X GET "https://api.example.com/api/v1/entries?limit=20&offset=0&sort=created_at_desc" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

---

#### Get Single Entry
**GET** `/entries/{entry_id}`

Retrieve a specific journal entry.

**Authentication Required**: Yes

**Path Parameters**
- `entry_id`: Entry ID (integer)

**Response (200 OK)**
```json
{
  "id": 1,
  "title": "My Day",
  "content": "Today was amazing...",
  "mood": "happy",
  "is_favorite": false,
  "created_at": "2024-01-15T10:30:00+00:00",
  "updated_at": "2024-01-15T10:30:00+00:00"
}
```

**Security Features**
- User ownership verified
- Content decrypted transparently
- Deleted entries return 404

**Errors**
- 401: Missing or invalid token
- 404: Entry not found or doesn't belong to user

**Example**
```bash
curl -X GET https://api.example.com/api/v1/entries/1 \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

---

#### Update Entry
**PUT** `/entries/{entry_id}`

Update an existing journal entry.

**Authentication Required**: Yes

**Path Parameters**
- `entry_id`: Entry ID (integer)

**Request Body**
```json
{
  "title": "Updated Title",
  "content": "Updated content...",
  "mood": "calm",
  "is_favorite": true
}
```

**All Fields Optional**
- Only provided fields are updated
- Updated entries re-encrypted with current key version

**Response (200 OK)**
```json
{
  "id": 1,
  "title": "Updated Title",
  "updated_at": "2024-01-15T11:00:00+00:00"
}
```

**Security Features**
- Only content owner can update
- Content re-encrypted on each update
- Audit logged with timestamp

**Errors**
- 400: Validation failed
- 401: Missing or invalid token
- 404: Entry not found

**Example**
```bash
curl -X PUT https://api.example.com/api/v1/entries/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "title": "Updated Title",
    "mood": "calm"
  }'
```

---

#### Delete Entry
**DELETE** `/entries/{entry_id}`

Delete (soft-delete) a journal entry.

**Authentication Required**: Yes

**Path Parameters**
- `entry_id`: Entry ID (integer)

**Response (200 OK)**
```json
{
  "message": "Entry deleted"
}
```

**Security Features**
- Soft delete (data preserved for GDPR compliance)
- Audit logged with timestamp
- Cannot be undone via API (admin intervention required)

**Errors**
- 401: Missing or invalid token
- 404: Entry not found

**Example**
```bash
curl -X DELETE https://api.example.com/api/v1/entries/1 \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

---

### Health & Status

#### Health Check
**GET** `/health`

Check application and database health.

**Authentication Required**: No

**Response (200 OK)**
```json
{
  "status": "healthy",
  "database": "healthy",
  "timestamp": "2024-01-15T10:30:00+00:00"
}
```

**Response (503 Service Unavailable)**
```json
{
  "status": "unhealthy",
  "database": "unhealthy",
  "timestamp": "2024-01-15T10:30:00+00:00"
}
```

**Use Case**
- Load balancer health checks
- Monitoring and alerting
- Deployment verification

**Example**
```bash
curl https://api.example.com/health
```

---

#### Application Info
**GET** `/api/v1/info`

Get application version and environment information.

**Authentication Required**: No

**Response (200 OK)**
```json
{
  "name": "Personal Journal API",
  "version": "1.0.0",
  "environment": "production",
  "timestamp": "2024-01-15T10:30:00+00:00"
}
```

**Example**
```bash
curl https://api.example.com/api/v1/info
```

---

## Rate Limiting

### Limits
| Endpoint | Limit |
|----------|-------|
| General | 100 requests/hour |
| Auth | 20 requests/hour |
| Journal | 1000 requests/hour |

### Rate Limit Headers
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1705318200
```

### Exceeding Limits
**Response (429 Too Many Requests)**
```json
{
  "error": "Too many requests",
  "request_id": "unique-request-id"
}
```

---

## Security Best Practices

### For Clients
1. **Store tokens securely**
   - Use HttpOnly cookies for web apps (not localStorage)
   - Use Keychain for mobile apps
   - Never log tokens

2. **Token refresh**
   - Refresh before expiry (set a 5-minute buffer)
   - Handle 401 by refreshing and retrying

3. **HTTPS only**
   - Always use HTTPS in production
   - Verify certificate validity

4. **Input validation**
   - Validate all inputs before sending
   - Use strong passwords (12+ characters)

5. **Data handling**
   - Never cache sensitive data
   - Clear data on logout
   - Handle encryption transparently

### For Servers
```python
# Example: Secure token storage
def setup_token_refresh(access_token, refresh_token):
    # Store refresh token in HttpOnly secure cookie
    response.set_cookie(
        'refresh_token',
        refresh_token,
        httponly=True,
        secure=True,
        samesite='Strict',
        max_age=7*24*3600  # 7 days
    )
    
    # Return access token in response body
    return {'access_token': access_token}
```

---

## Testing the API

### Using cURL
```bash
# Register
curl -X POST https://api.example.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@example.com","password":"Test123!"}'

# Login
RESPONSE=$(curl -s -X POST https://api.example.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"Test123!"}')

TOKEN=$(echo $RESPONSE | jq -r '.access_token')

# Create entry
curl -X POST https://api.example.com/api/v1/entries \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"title":"Test","content":"Testing the API"}'
```

### Using Python Requests
```python
import requests

BASE_URL = "https://api.example.com/api/v1"
SESSION = requests.Session()

# Register
r = SESSION.post(f"{BASE_URL}/auth/register", json={
    "username": "test",
    "email": "test@example.com",
    "password": "Test123!"
})
print(r.json())

# Login
r = SESSION.post(f"{BASE_URL}/auth/login", json={
    "username": "test",
    "password": "Test123!"
})
token = r.json()['access_token']

# Create entry
headers = {'Authorization': f'Bearer {token}'}
r = SESSION.post(f"{BASE_URL}/entries", 
    json={"title": "Test", "content": "Testing"},
    headers=headers)
print(r.json())
```

### Using JavaScript/Fetch
```javascript
const BASE_URL = "https://api.example.com/api/v1";

// Register
const registerResponse = await fetch(`${BASE_URL}/auth/register`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'test',
    email: 'test@example.com',
    password: 'Test123!'
  })
});

// Login
const loginResponse = await fetch(`${BASE_URL}/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'test',
    password: 'Test123!'
  })
});

const { access_token } = await loginResponse.json();

// Create entry
const entryResponse = await fetch(`${BASE_URL}/entries`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${access_token}`
  },
  body: JSON.stringify({
    title: 'Test',
    content: 'Testing the API'
  })
});

console.log(await entryResponse.json());
```

---

## Changelog

### Version 1.0.0 (2024-01-15)
- Initial release
- User registration and authentication
- Journal entry CRUD operations
- AES-256-GCM encryption at rest
- Rate limiting
- Comprehensive audit logging
- Security headers
- GDPR-compliant soft deletes

---

## Support

For API support:
- Email: support@example.com
- Docs: https://docs.example.com
- Status: https://status.example.com
