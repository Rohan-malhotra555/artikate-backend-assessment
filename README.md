# Artikate Backend Engineering Assessment

> Backend engineering assessment focusing on **database optimization**, **asynchronous job processing**, **rate limiting**, and **multi-tenant data isolation**.

---

## Loom Walkthrough (Optional)

If you recorded a walkthrough, add the link here:

**Loom:** `https://drive.google.com/drive/folders/1Rnu6Ijsqi1zeAb5KB_Xro-BRDesyFkxI?usp=sharing`

---

# Project Overview

This repository contains my completed solution for the Artikate Backend Engineering Assessment.

The implementation covers:

- Database query optimization (N+1 elimination)
- Background job processing using Celery
- Rate limiting with retry and exponential backoff
- Multi-tenant data isolation using `contextvars`
- Automated test suite validating all major requirements

---

# Deliverables

## 1. Written Answers

**File:** `ANSWERS.md`

Contains:

- Section 1 – N+1 Incident Log
- Section 3 – Async ContextVars explanation
- Section 4 – Architecture Review

---

## 2. Job Queue Design

**File:** `DESIGN.md`

Includes:

- Architectural decisions
- Design trade-offs
- Failure mode analysis
- Queue design rationale
- Rate limiter implementation details

---

## 3. Profiler Evidence

Located inside:

```
evidence/
├── evidence_before.png
└── evidence_after.png
```

These screenshots demonstrate the reduction in database queries after optimizing the N+1 issue.

---

## 4. Test Suite

Location:

```
assessment/tests.py
```

The tests validate:

- Rate limiting
- Retry behavior with exponential backoff
- Multi-tenant isolation
- Tenant-scoped query behavior

---

# Local Setup

These steps will get the project running from a clean environment.

## Prerequisites

- Python 3.9+
- Redis Server (running locally on port `6379`)

---

## 1. Clone Repository

```bash
git clone <your-repository-url>
cd <your-repository-folder>
```

---

## 2. Create Virtual Environment

### macOS / Linux

```bash
python -m venv venv
source venv/bin/activate
```

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Database Setup

Generate and apply migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

SQLite is used for local development and testing.

---

# Running the Application

To test the complete asynchronous workflow, run the following services in separate terminal windows.

## Terminal 1 — Redis

Start Redis:

```bash
redis-server
```

---

## Terminal 2 — Celery Worker

Start the worker:

```bash
celery -A core worker -l INFO
```

---

## Terminal 3 — Django Development Server

(Optional)

```bash
python manage.py runserver
```

---

# Running the Test Suite

Execute all assessment tests:

```bash
python manage.py test assessment
```

---

# Test Coverage

The test suite validates the following scenarios.

## Rate Limiter

Simulates **500 simultaneous task submissions** and verifies:

- 200 tasks are accepted
- 300 tasks are rejected

---

## Retry Logic

Verifies that intentional rate-limit failures trigger Celery's retry mechanism with exponential backoff.

---

## Multi-Tenant Isolation

Confirms that:

- Lazy `.all()` queries are automatically scoped to the active tenant using `contextvars`
- Attempts to access another tenant's data return zero results
- Tenant isolation is enforced consistently

---

# Project Structure

```
.
├── ANSWERS.md
├── DESIGN.md
├── evidence/
│   ├── evidence_before.png
│   └── evidence_after.png
├── assessment/
│   └── tests.py
├── requirements.txt
└── README.md
```

---

# Technologies Used

- Python 3.9+
- Django
- Celery
- Redis
- SQLite
- ContextVars

---

# Summary

This submission demonstrates:

- Database optimization by eliminating N+1 queries
- Asynchronous task execution with Celery
- Rate limiting with retry and exponential backoff
- Tenant-safe data isolation using `contextvars`
- Automated tests verifying correctness and isolation