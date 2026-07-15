# Artikate Backend Assessment

**Loom Walkthrough (Optional):** [Insert your Loom link here, or delete this line if you didn't record one]

This repository contains the completed Artikate backend engineering assessment, focusing on database optimization, asynchronous job queues, and multi-tenant data isolation.

## Deliverables Mapping
To make the review process as seamless as possible, here is where you can find the required deliverables:

* **`ANSWERS.md`:** Contains all written explanations for Section 1 (N+1 Incident Log), Section 3 (Async ContextVars), and Section 4 (Architecture Review).
* **`DESIGN.md`:** Contains the architectural reasoning, trade-offs, and failure mode analysis specifically for Section 2 (Job Queue & Rate Limiter).
* **Profiler Evidence:** Profiler evidence proving the query count reduction is attached in the /evidence directory as evidence_before.png and evidence_after.png.
* **Test Suite:** Located in `assessment/tests.py`, covering the rate limiter, intentional failures (exponential backoff), and multi-tenant isolation proofs.

---

## Local Setup Instructions

These instructions will get the environment running from a clean slate in under 5 minutes.

### Prerequisites
* Python 3.9+
* Redis Server (Running locally on the default port `6379`)

### 1. Environment Setup
Clone the repository and set up an isolated virtual environment:
```bash
git clone <your-repository-url>
cd <your-repository-folder>

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt