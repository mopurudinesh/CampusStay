# CampusStay – Smart Hostel Registration & Management System

CampusStay is a modern, full-stack, SaaS-like web application designed for students and administrators to manage hostel registrations, room allocations, payments, complaints, feedback, and announcements.

The system is built on a decoupled architecture using **Django** and **Django REST Framework (DRF)** on the backend, communicating via AJAX with a responsive **HTML5/CSS3/JavaScript/Bootstrap 5** frontend, authenticated securely using **JWT JSON Web Tokens**.

---

## Tech Stack

* **Backend:** Python 3.11+, Django 5.0+, Django REST Framework, SimpleJWT (JWT Auth)
* **Frontend:** HTML5, CSS3 (Custom Glassmorphism and Theme Variables), JavaScript (Fetch AJAX), Bootstrap 5, Chart.js (Analytics Dashboards)
* **Database:** Supabase PostgreSQL (Preferred) / SQLite (Local Fallback)
* **Reports & Utilities:** ReportLab (PDF Receipts), Openpyxl (Excel Reports), Qrcode (QR Resident Badges)

---

## Core System Architecture

```text
Hostel management system/
├── .venv/                  # Python Virtual Environment
├── campusstay/             # Django Project Configuration
│   ├── settings.py         # App settings (SimpleJWT, Supabase Parser, Media)
│   ├── urls.py             # Main router
│   └── ...
├── hostel/                 # Main Hostel Application
│   ├── migrations/         # Database migration histories
│   ├── models.py           # DB Schemas (Rooms, Allocations, Complaints, Payments)
│   ├── serializers.py      # DRF Validation logic and fields
│   ├── views.py            # API Viewsets, AI Recommender, Chatbot, PDF Generators
│   ├── urls.py             # API Endpoint URLs
│   └── tests.py            # Verification suite of 34 test cases
├── static/                 # Static Assets
│   ├── css/style.css       # Custom Glassmorphism UI stylesheet
│   └── js/dashboard.js     # Client side AJAX token handler
├── templates/              # HTML views (extends templates/base.html)
│   ├── base.html           # Main Layout navbar + sidebar + chatbot widget
│   ├── index.html          # Landing Hero View
│   ├── auth/               # Login, Multi-step Signup, Recover & OTP Verification
│   ├── student/            # Dashboard widgets, recommendations, payments, complaints
│   └── admin/              # KPI metrics grid, charts, allocations, resolver board
├── .env                    # Environment configurations
├── db.sqlite3              # Default local database
├── requirements.txt        # Package dependencies
└── README.md               # User guide
```

---

## Installation & Setup Guide

### 1. Prerequisites
Ensure you have Python 3.11+ installed. Verify with:
```bash
python --version
```

### 2. Clone and Setup Environment
Navigate to the root directory and create a virtual environment:
```bash
python -m venv .venv
```

Activate the virtual environment:
* **Windows (PowerShell):**
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
* **macOS/Linux:**
  ```bash
  source .venv/bin/activate
  ```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Setup & Configurations
By default, the application runs on local **SQLite** out-of-the-box. To connect to your **Supabase PostgreSQL** instance:

1. Log into your [Supabase Dashboard](https://supabase.com/).
2. Navigate to **Project Settings** -> **Database**.
3. Copy the **URI connection string** (under Connection Pooling / Transaction mode).
4. Edit the `.env` file in the project root and add your database URL:
   ```env
   SECRET_KEY=your-django-secret-key
   DEBUG=True
   DATABASE_URL=postgresql://postgres.your-project-ref:your-password@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```

### 5. Generate Migrations & Migrate
Run the migrations to create the database tables:
```bash
python manage.py makemigrations hostel
python manage.py migrate
```

### 6. Create Admin Account
Create a hostel administrator account:
```bash
python manage.py createsuperuser
```
*(Make sure to log in and set the `role` field on this CustomUser object to `ADMIN` inside the Django admin panel or using the database console to access the Admin Control Center).*

### 7. Run the Application
Start the Django development server:
```bash
python manage.py runserver
```
Open your browser and navigate to `http://127.0.0.1:8000/`.

---

## Running the Verification Test Suite

The system includes a detailed validation suite covering registrations, password strength boundaries, JWT auth, status transition rules, room capacity limits, payment uniqueness, AI matching, and chatbot keyword intent testing.

To run all 34 test cases:
```bash
python manage.py test
```

---

## Key Advanced Modules

### AI Room Recommendations
Finds vacant rooms and scores compatibility (0% - 100%) by matching student properties such as Gender, Department, and Academic Year of study.

### In-App NLP Chatbot Assistant
A floating widget accessible on all views. Answers queries about hostel fees, room transfer requests, WiFi passwords, mess timings, curfews, and rules.

### QR Code Resident verification
Generates a secure QR code on the student portal linking to a verification endpoint `/api/rooms/verify_qr/?student_id=<id>`. Security wardens can scan this code to verify the student's allocation details, photo, and ID.
