#!/usr/bin/env python3

import json
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict
from email.message import EmailMessage
import smtplib

from dotenv import load_dotenv

load_dotenv()

FILTERED_FILE = Path("jobs_filtered.json")
DB_PATH = Path("seen_jobs.db")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "")
TO_EMAIL = os.getenv("TO_EMAIL", "")

def load_filtered_jobs() -> List[Dict]:
    if not FILTERED_FILE.exists():
        print("jobs_filtered.json not found")
        return[]
    
    with FILTERED_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)
    
def init_db(path: str) -> sqlite3.Connection:

    conn = sqlite3.connect(path)

    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS seen_jobs (
            url TEXT PRIMARY KEY,
            job_id TEXT,
            title TEXT,
            first_seen_at TEXT
        )
    """)

    conn.commit()
    return conn

def is_seen(conn: sqlite3.Connection, url: str) -> bool:

    cur = conn.cursor()

    cur.execute("SELECT 1 FROM seen_jobs WHERE url = ?", (url,))

    return cur.fetchone() is not None

def mark_seen(conn: sqlite3.Connection, job: Dict) -> None:

    cur = conn.cursor()

    cur.execute(
        """
        INSERT OR IGNORE INTO seen_jobs (url, job_id, title, first_seen_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            job.get("url", ""),
            job.get("job_id", ""),
            job.get("title", ""),
            datetime.now(timezone.utc).isoformat(),
        ),
    )

    conn.commit()

def get_new_jobs(conn: sqlite3.Connection, jobs: List[Dict]) -> List[Dict]:
    new_jobs = []
    
    for job in jobs:
        url = job.get("url", "").strip()
        if not url:
            continue

        if not is_seen(conn, url):
            new_jobs.append(job)

    return new_jobs

def build_email_content(new_jobs: List[Dict]) -> tuple[str, str, str]:

    today = datetime.now(timezone.utc).date()

    if not new_jobs:
        subject = f"No new Google jobs - {today}"
        plain_body = "No new job postings today."
        html_body = """
        <html>
        <body>
            <p>No new job postings today.</p>
        </body>
        </html>
        """

        return subject, plain_body, html_body
    

    subject = f"{len(new_jobs)} new Google jobs - {today}"

    plain_lines = ["New Google job postings:", ""]
    html_lines = [
        "<html>",
        "<body>",
        "<h2>New Google job postings</h2>",
        "<ul>"
    ]

    for job in new_jobs:
        title = job.get("title", "Google Job Posting")
        url = job.get("url", "")
        job_id = job.get("job_id", "")

        plain_lines.append(f"- {title}")
        plain_lines.append(f"  Job ID: {job_id}")
        plain_lines.append(f"  Link: {url}")
        plain_lines.append("")

        html_lines.append(
            f"<li><strong>{title}</strong><br>"
            f"Job ID: {job_id}<br>"
            f"<a href='{url}'>{url}</a></li><br>"
        )

    html_lines.extend(["</ul>", "</body>", "</html>"])

    plain_body = "\n".join(plain_lines)
    html_body = "\n".join(html_lines)

    return subject, plain_body, html_body

def send_email(subject: str, plain_body: str, html_body: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL

    msg.set_content(plain_body)
    msg.add_alternative(html_body, subtype="html")


    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.ehlo()
        if SMTP_PORT == 587:
            smtp.starttls()
            smtp.ehlo()

        if SMTP_USER and SMTP_PASS:
            smtp.login(SMTP_USER, SMTP_PASS)

        smtp.send_message(msg)

def main() -> None:
    print("Loading filtered jobs...")
    jobs = load_filtered_jobs()
    print("Total filtered jobs:", len(jobs))

    conn = init_db(DB_PATH)
    print("DB_PATH:", DB_PATH)  

    new_jobs = get_new_jobs(conn, jobs)
    print("New jobs to send:", len(new_jobs))

    print("SMTP_HOST:", SMTP_HOST)
    print("SMTP_PORT:", SMTP_PORT)
    print("SMTP_USER:", SMTP_USER)
    print("FROM_EMAIL:", FROM_EMAIL)
    print("TO_EMAIL:", TO_EMAIL)

    subject, plain_body, html_body = build_email_content(new_jobs)

    print("SUBJECT:", subject)
    print("PLAIN BODY:")
    print(plain_body)

    send_email(subject, plain_body, html_body)

    for job in new_jobs:
        mark_seen(conn, job)

    print("Email sent successfully.")


if __name__ == "__main__":
    main()












    
    
