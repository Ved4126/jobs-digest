# Google Jobs Email Digest

![Jobs Digest](https://github.com/Ved4126/jobs-digest/actions/workflows/jobs-digest.yml/badge.svg)

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Automation](https://img.shields.io/badge/Automation-GitHub%20Actions-green)
![License](https://img.shields.io/badge/License-MIT-orange)

Automatically scrape Google Careers job listings and send a daily email digest with new opportunities.

This project uses Python, Selenium, and GitHub Actions to run automatically every day and notify you of new job postings.

---

# Overview

This system performs three steps:

1. Scrapes job listings from Google Careers
2. Filters relevant job postings
3. Sends an email digest with clickable job links

The workflow runs automatically every day at 9:00 AM using GitHub Actions.

---

# Architecture

GitHub Actions (Daily 9 AM)
        │
        ▼
scrape_google_jobs.py
        │
        ▼
jobs_raw.json
        │
        ▼
filter_jobs.py
        │
        ▼
jobs_filtered.json
        │
        ▼
send_jobs_email.py
        │
        ▼
Email with clickable job links
        │
        ▼
seen_jobs.db updated

---

# Example Email Output

Example email sent by the system:

New Google job postings

Software Engineer Infrastructure Quantum AI  
Job ID: 97144402941485766  
https://careers.google.com/jobs/results/97144402941485766-software-engineer-infrastructure-quantum-ai  

Software Engineer Compute Infrastructure Admission Control  
Job ID: 101126917809152710  
https://careers.google.com/jobs/results/101126917809152710-software-engineer-compute-infrastructure-admission-control  

Each job includes a clickable link to the official Google Careers page.

---

# Features

- Scrapes Google Careers automatically
- Supports multiple job keywords (AI, ML, SWE, etc.)
- Removes duplicate job listings
- Sends formatted email notifications
- Fully automated with GitHub Actions
- Persistent database prevents repeated emails

---

# Project Structure

jobs_digest/

scrape_google_jobs.py  
filter_jobs.py  
send_jobs_email.py  

jobs_raw.json  
jobs_filtered.json  
seen_jobs.db  

.env  
.gitignore  

.github/workflows/jobs-digest.yml  

---

# Environment Configuration

Create a `.env` file locally.

Example:

JOB_KEYWORDS=software engineer,ai,machine learning,data scientist  
JOB_LOCATION=United States  
MAX_RESULTS=50  

SMTP_HOST=smtp.gmail.com  
SMTP_PORT=587  
SMTP_USER=your_email@gmail.com  
SMTP_PASS=your_app_password  
FROM_EMAIL=your_email@gmail.com  
TO_EMAIL=recipient_email@gmail.com  

DB_PATH=seen_jobs.db

---

# Installation

Clone the repository

git clone https://github.com/YOUR_USERNAME/google-jobs-digest.git  
cd google-jobs-digest  

Create virtual environment

python3 -m venv venv  
source venv/bin/activate  

Install dependencies

pip install selenium webdriver-manager beautifulsoup4 python-dotenv requests  

---

# Running Locally

Run the pipeline manually:

python scrape_google_jobs.py  
python filter_jobs.py  
python send_jobs_email.py  

---

# GitHub Automation

The workflow runs automatically every day using:

.github/workflows/jobs-digest.yml

Example schedule:

cron: "0 16 * * *"

This corresponds to 9:00 AM Pacific Time.

---

# Future Improvements

Possible future upgrades:

- Add job location extraction
- Include job description summaries
- Categorize jobs by keyword
- Support multiple job boards
- Add web dashboard

---

# Author

Ved Dabhi  
Software Engineering Student
