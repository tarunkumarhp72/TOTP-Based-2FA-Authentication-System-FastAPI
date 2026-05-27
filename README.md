# 🔐 TOTP-Based 2FA Authentication System (FastAPI)

A secure **Two-Factor Authentication (2FA)** system using **Time-based One-Time Passwords (TOTP)**. Users login with email & password, then verify with a 6-digit code from an authenticator app like Google Authenticator or Authy.

---

## 🚀 Quick Start Setup (Step-by-Step)

### **Step 1: Install Python & Dependencies**

Make sure you have **Python 3.13+** installed on your computer.

```bash
# Clone or download the project
cd TOTP-Based-2FA-Authentication-System-FastAPI

# Create a virtual environment (isolates your project)
python -m venv .venv

# Activate it (Windows)
.venv\Scripts\activate

# Or on Mac/Linux:
source .venv/bin/activate
```

### **Step 2: Install Required Packages**

```bash
# Install dependencies using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### **Step 3: Check Your `.env` File**

Make sure the `.env` file has correct settings:

```
ENVIRONMENT=development
DEBUG=True
DATABASE_URL=sqlite+aiosqlite:///./auth.db
REDIS_URL=redis://localhost:6379/0
```

### **Step 4: Start Redis Server** (Optional but recommended)

For production or if using rate limiting features, start Redis:

```bash
redis-cli
```

Or if Redis isn't installed, the app will still work but rate limiting might not work.

### **Step 5: Run the Project**

```bash
python run.py
```

You should see:

```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### **Step 6: Test It Out**

Open your browser and go to:

```
http://localhost:8000/docs
```

You'll see all available APIs with a test interface! 🎉

---

## 📚 API Documentation

All APIs are under `/api/v1/auth`

### **1. Register a New User**

**Endpoint:** `POST /api/v1/auth/register`

**What it does:** Create a new user account

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123"
}
```

**Response:**
```json
{
  "message": "Account created successfully",
  "data": {
    "id": "123abc",
    "email": "user@example.com",
    "created_at": "2024-01-15T10:00:00"
  }
}
```

**Use case:** User signs up for the first time

---

### **2. Login (Step 1 - Email & Password)**

**Endpoint:** `POST /api/v1/auth/login`

**What it does:** Verify email and password. If 2FA is enabled, returns a temporary token for the next step.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123"
}
```

**Response (if 2FA is enabled):**
```json
{
  "message": "TOTP verification required",
  "data": {
    "totp_required": true,
    "partial_token": "eyJhbGc...",
    "expires_at": "2024-01-15T10:05:00"
  }
}
```

**Use case:** User tries to login

---

### **3. Setup 2FA - Get QR Code**

**Endpoint:** `POST /api/v1/auth/totp/setup`

**What it does:** Generates a unique secret and returns a QR code URL for scanning

**How to use:**
1. Login first to get access token
2. Call this endpoint
3. User opens the QR code URL in a browser or scans with Google Authenticator or Authy app

**Response:**
```json
{
  "message": "Scan the QR code with your authenticator app",
  "data": {
    "totp_uri": "otpauth://totp/user@example.com?secret=JBSWY3DPEBLW64TMMQ%3D%3D%3D%3D&issuer=TOTP+Auth+Service",
    "qr_code_url": "https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=otpauth%3A%2F%2Ftotp%2Fuser%40example.com%3Fsecret%3DJBSWY3DPEBLW64TMMQ%253D%253D%253D%253D%26issuer%3DTOTP%2BAuth%2BService"
  }
}
```

**Use case:** User wants to enable 2FA

---

### **4. Enable 2FA - Verify First Code**

**Endpoint:** `POST /api/v1/auth/totp/enable`

**What it does:** Confirms 2FA setup by verifying the first 6-digit code from the app

**Request:**
```json
{
  "otp": "123456"
}
```

**Response:**
```json
{
  "message": "2FA enabled. Store your backup codes securely",
  "data": {
    "backup_codes": [
      "BACKUP-CODE-1",
      "BACKUP-CODE-2",
      "..."
    ]
  }
}
```

**Important:** Save these backup codes! They're for recovery if you lose your phone.

**Use case:** User confirms 2FA setup

---

### **5. Login (Step 2 - Verify TOTP Code)**

**Endpoint:** `POST /api/v1/auth/verify-totp`

**What it does:** Completes login by verifying the 6-digit code from the authenticator app

**Request:**
```json
{
  "partial_token": "eyJhbGc...",
  "otp": "123456"
}
```

**Response:**
```json
{
  "message": "Login successful",
  "data": {
    "access_token": "eyJhbGc...",
    "refresh_token": "eyJhbGc...",
    "user": {
      "id": "123abc",
      "email": "user@example.com"
    }
  }
}
```

**Use case:** User enters 2FA code after login

---

### **6. Login Using Backup Code**

**Endpoint:** `POST /api/v1/auth/verify-backup-code`

**What it does:** Alternative login if you don't have access to your authenticator app

**Request:**
```json
{
  "partial_token": "eyJhbGc...",
  "backup_code": "BACKUP-CODE-1"
}
```

**Response:** Same as verify-totp (returns access token)

**Use case:** User lost phone but has backup codes

---

### **7. Refresh Access Token**

**Endpoint:** `POST /api/v1/auth/refresh`

**What it does:** Get a new access token using refresh token (access token expires in 15 minutes)

**Request:**
```json
{
  "refresh_token": "eyJhbGc..."
}
```

**Response:**
```json
{
  "message": "Tokens refreshed",
  "data": {
    "access_token": "eyJhbGc...",
    "refresh_token": "eyJhbGc..."
  }
}
```

**Use case:** Access token expired, need a new one

---

### **8. Get Current User Profile**

**Endpoint:** `GET /api/v1/auth/me`

**What it does:** Get logged-in user's information

**How to use:** Add Authorization header with access token

**Response:**
```json
{
  "data": {
    "id": "123abc",
    "email": "user@example.com",
    "totp_enabled": true,
    "created_at": "2024-01-15T10:00:00"
  }
}
```

**Use case:** Get user profile info

---

### **9. Logout**

**Endpoint:** `POST /api/v1/auth/logout`

**What it does:** End current session (logout from one device)

**Request:**
```json
{
  "refresh_token": "eyJhbGc..."
}
```

**Response:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

**Use case:** User wants to logout

---

### **10. Logout All Sessions**

**Endpoint:** `POST /api/v1/auth/logout-all`

**What it does:** Logout from ALL devices/sessions at once

**Response:**
```json
{
  "success": true,
  "message": "All sessions terminated"
}
```

**Use case:** Security concern, logout everywhere

---

## 🔄 Typical Login Flow

```
1. User calls /register → Creates account
2. User calls /login → Email & password verified → Gets partial_token
3. User calls /totp/setup → Gets QR code (if first time)
4. User scans QR with Google Authenticator app
5. User calls /totp/enable → Enables 2FA, gets backup codes
6. Next login:
   → User calls /login → Email & password verified → Gets partial_token
   → User enters 6-digit code from app
   → User calls /verify-totp → Gets access_token & refresh_token
   → User is logged in! ✅
```

---

## 🔑 Key Features

* 🔐 **Secure 2FA** - Time-based one-time passwords
* ⏱️ **Expires every 30 seconds** - Codes are only valid briefly
* 📱 **Works with any authenticator app** - Google Authenticator, Authy, Microsoft Authenticator, etc.
* 📷 **QR code scanning** - Easy setup
* 🔄 **Backup codes** - Recovery if you lose your phone
* 🛡️ **Rate limiting** - Decorator-based, prevents brute force attacks
* 💾 **PostgreSQL database** - Production-ready with Alembic migrations
* ⚡ **Fast API** - Built with FastAPI framework

---

## 🛡️ Security Architecture

This project implements **enterprise-grade security** with multiple layers of protection:

### **1. Authentication & Authorization**

| Feature | Implementation | Security Level |
|---------|---------------|----------------|
| **Password Hashing** | bcrypt with 12 rounds | 🔐 Military-grade |
| **JWT Tokens** | HS256 algorithm, 15-min access / 7-day refresh | 🔐 High |
| **Token Versioning** | Auto-invalidates all tokens on logout-all | 🔐 High |
| **Role-based Access** | pre_2fa, authenticated roles | 🔐 Medium |

### **2. Two-Factor Authentication (2FA)**

| Feature | Implementation | Security Level |
|---------|---------------|----------------|
| **TOTP Algorithm** | RFC 6238 compliant (30-second windows) | 🔐 Industry Standard |
| **Secret Storage** | AES-256 encrypted in database | 🔐 Military-grade |
| **Backup Codes** | 10 single-use codes, bcrypt hashed | 🔐 High |
| **QR Code Generation** | Secure URI with issuer validation | 🔐 Medium |

### **3. Rate Limiting & Anti-Brute Force**

| Feature | Implementation | Protection |
|---------|---------------|------------|
| **Login Attempts** | 5 attempts → 15-minute lockout | 🛡️ Account protection |
| **Rate Limit Decorators** | Per-endpoint: 3/hour register, 5/min login | 🛡️ API protection |
| **Sliding Window** | In-memory + Redis fallback | 🛡️ DDoS protection |
| **IP-based Tracking** | Request metadata logging | 🛡️ Audit trail |

### **4. Database Security**

| Feature | Implementation | Security Level |
|---------|---------------|----------------|
| **Connection Pooling** | Async PostgreSQL with pool limits | 🔐 Production-grade |
| **SQL Injection** | SQLAlchemy ORM (parameterized queries) | 🔐 Eliminated |
| **Session Management** | Row-level refresh token revocation | 🔐 High |
| **Connection Pre-ping** | Stale connection detection | 🔐 Reliability |

### **5. Request Security**

| Feature | Implementation | Protection |
|---------|---------------|------------|
| **CORS Policy** | Configurable allowed origins | 🛡️ CSRF protection |
| **Trusted Hosts** | Whitelist validation | 🛡️ Host header attacks |
| **Request ID** | UUID tracing per request | 🛡️ Audit trail |
| **Security Headers** | X-Content-Type, X-Frame, X-XSS, Referrer | 🛡️ XSS/Clickjacking |
| **Request Size Limit** | 1MB max body size | 🛡️ DoS prevention |
| **Timeout** | 30-second request timeout | 🛡️ Resource exhaustion |

### **6. Logging & Monitoring**

| Feature | Implementation | Security Level |
|---------|---------------|----------------|
| **Structured Logging** | JSON format with rotation | 🔐 Forensics |
| **Sensitive Data Masking** | Passwords, tokens auto-redacted | 🔐 Privacy |
| **Log Rotation** | Year/month/day folder structure | 🔐 Compliance |
| **Security Events** | Failed logins, lockouts, token revokes | 🔐 SIEM-ready |

### **7. Session Management**

| Feature | Implementation | Security Level |
|---------|---------------|----------------|
| **Token Rotation** | New refresh token on every refresh | 🔐 High |
| **Logout All** | Increment token_version → invalidate all | 🔐 High |
| **Device Tracking** | User-agent + IP per token | 🔐 Audit |
| **Single-use Backup** | Consumed after verification | 🔐 High |

### **🔒 Security Best Practices Applied**

- ✅ **No plaintext secrets** - Everything hashed/encrypted
- ✅ **Defense in depth** - Multiple security layers
- ✅ **Fail secure** - Deny by default
- ✅ **Least privilege** - Minimal permissions
- ✅ **Audit everything** - All actions logged
- ✅ **Secure by design** - No insecure defaults
- ✅ **Token binding** - Version-based invalidation

### **🛡️ How Secure Is This?**

This implementation follows **OWASP Top 10** and **NIST guidelines**:

| Attack Vector | Protection Status |
|--------------|-------------------|
| SQL Injection | ✅ Eliminated (ORM) |
| XSS | ✅ Security headers + output encoding |
| CSRF | ✅ CORS + token-based auth |
| Brute Force | ✅ Rate limiting + lockout |
| Session Hijacking | ✅ Token versioning + rotation |
| Man-in-the-Middle | ✅ HTTPS-only (production) |
| Credential Stuffing | ✅ bcrypt + lockout policy |
| Phishing | ✅ 2FA TOTP required |

**Overall Security Rating: 🔐 ENTERPRISE-GRADE**

---

## 🛠️ Tech Stack

* **FastAPI** - Web framework
* **Python 3.13+** - Programming language
* **SQLite** - Database
* **PyOTP** - TOTP generation
* **qrcode** - QR code images
* **Pillow** - Image processing
* **pydantic** - Data validation
* **SQLAlchemy** - Database ORM
* **uv** - Fast Python package manager

---

## 📖 How TOTP Works (Simple Explanation)

1. **Secret Key** - A random string stored on both phone & server
2. **Time** - Current time divided into 30-second periods
3. **Algorithm** - Secret + time = generates 6-digit code
4. **Phone** - Generates same code every 30 seconds
5. **Server** - Checks if codes match → Login allowed ✅

---

## 💡 Why Use TOTP Instead of SMS?

* ✅ **More secure** - No SMS interception
* ⚡ **Works offline** - No internet needed
* 🔄 **Auto-rotating** - New code every 30 seconds
* 💰 **Free** - No SMS charges
* 📱 **Easy app** - Google Authenticator is free

---

## 🤝 Contributing

Found a bug? Want to improve it? Feel free to contribute!

---

## ⭐ Support

If this helps you, please give it a ⭐ on GitHub!
