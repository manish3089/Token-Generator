# 🔐 Sharekhan API Token Generator (FastAPI)

A simple FastAPI web application to generate an access token from Sharekhan's API using `app_id`, `secret_id`, and `authorization_code`.

## 🚀 Features

- 📄 HTML form-based input using Jinja2 templates
- 🔐 Access token generation via Sharekhan API
- ✅ Success & error handling with user-friendly output
- ⚡ Clean and modular FastAPI structure

---

## ⚙️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/Token-Generator.git
cd Token-Generator
```

---

## 🛠️ Create and Activate Virtual Environment

```bash
# Linux/macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate

```
---

##  Install Dependencies
```bash
 pip install fastapi uvicorn jinja2 requests python-multipart
```

---

## Run the Application
```bash
uvicorn app:app --reload
```

