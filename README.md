# 🔐 TOTP-Based 2FA Authentication System (FastAPI)

This repository implements a secure **Time-based One-Time Password (TOTP)** authentication system using **FastAPI**. It enables **Two-Factor Authentication (2FA)** by generating and verifying temporary numeric codes that refresh every 30–60 seconds.

## 🚀 Overview

**TOTP (RFC 6238)** is a widely used authentication mechanism that enhances security by requiring users to verify their identity using a time-sensitive code generated on their device.

This project demonstrates how to:

* Generate a unique **secret key** for each user
* Create a **QR code** for easy setup with authenticator apps
* Verify **TOTP codes** during login or sensitive actions
* Integrate secure 2FA into a FastAPI backend

---

## 🔑 Key Features

* 🔐 **Secure 2FA (Two-Factor Authentication)**
* ⏱️ Time-based OTP (valid for ~30 seconds)
* 📱 Compatible with apps like **Google Authenticator** & **Authy**
* 📷 QR code generation for easy onboarding
* ⚡ Fast and lightweight implementation using FastAPI
* ❌ No dependency on SMS (works offline)

---

## ⚙️ How It Works

1. **Secret Generation**
   A unique secret key is generated for each user.

2. **QR Code Setup**
   The secret is encoded into a QR code and scanned using an authenticator app.

3. **Code Generation (User Side)**
   The app generates a new OTP every 30 seconds.

4. **Verification (Server Side)**
   The server validates the OTP using the same secret and current time.

---

## 🛠️ Tech Stack

* **FastAPI** (Backend Framework)
* **PyOTP** (TOTP generation & verification)
* **qrcode** (QR code generation)
* **Python 3.x**

---

## 📌 Use Cases

* Secure login systems (2FA)
* Admin panel protection
* Financial or sensitive operations verification
* SaaS applications & enterprise systems

---

## 🧠 Why TOTP?

* ✅ More secure than SMS OTP (no interception risk)
* ⚡ Works offline (no network dependency)
* 🔄 Automatically rotating codes
* 📉 Cost-effective (no SMS charges)

---

## 📖 Standard

This implementation follows **RFC 6238**, based on the **HMAC-based One-Time Password (HOTP)** algorithm.

---

## 🤝 Contribution

Feel free to fork, improve, and contribute to this project!

---

## ⭐ Support

If you find this useful, give it a ⭐ on GitHub!
