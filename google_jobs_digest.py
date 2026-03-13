#!/usr/bin/env python3
"""
job_fetcher_daily.py
- Opens Google Careers search results using Selenium (headless Chrome).
- Parses job cards from the rendered HTML using BeautifulSoup.
- Deduplicates jobs using SQLite so you only email new ones.
- Sends a daily email digest using SMTP (or SendGrid if configured).
- Reads configuration from environment variables (supports .env).
"""

import os
import time
import sqlite3
from datetime import datetime, timezone
from typing import List, Dict
from email.message import EmailMessage

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import re

load_dotenv()

JOB_KEYWORDS = os.getenv("JOB_KEYWORDS", "software engineer,intern").split(",")
JOB_LOCATION = os.getenv("JOB_LOCATION", "")
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "50"))

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER)
TO_EMAIL = os.getenv("TO_EMAIL", SMTP_USER)

DB_PATH = os.getenv("DB_PATH", "seen_jobs.db")

BASE_SEARCH_URL = "https://careers.google.com/jobs/results/?"


def build_search_url(keywords: List[str], location: str) -> str:
    q = "+".join("+".join(k.strip().split()) for k in keywords if k.strip())
    parts = []
    if q:
        parts.append(f"q={q}")
    if location:
        parts.append(f"location={'+'.join(location.split())}")
    return BASE_SEARCH_URL + "&".join(parts)


def make_headless_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    return driver


def init_db(path: str):
    conn = sqlite3.connect(path)
    cur = conn.cursor()

    # Create table if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS seen (
            url TEXT PRIMARY KEY,
            title TEXT,
            first_seen_at TEXT,
            last_emailed_at TEXT,
            applied INTEGER DEFAULT 0
        )
    """)

    # Safe migrations (ignore if column already exists)
    try:
        cur.execute("ALTER TABLE seen ADD COLUMN title TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE seen ADD COLUMN first_seen_at TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE seen ADD COLUMN last_emailed_at TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE seen ADD COLUMN applied INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    return conn

def is_seen(conn: sqlite3.Connection, url: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM seen WHERE url = ?", (url,))
    return cur.fetchone() is not None


def mark_seen(conn: sqlite3.Connection, url: str, title: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO seen(url, title, first_seen_at, last_emailed_at, applied)
        VALUES(?, ?, ?, ?, 0)
        ON CONFLICT(url) DO UPDATE SET
            title=excluded.title,
            last_emailed_at=excluded.last_emailed_at
    """, (url, title, now, now))
    conn.commit()

def get_unapplied_jobs(conn: sqlite3.Connection, limit: int = 10) -> List[Dict]:
    cur = conn.cursor()
    cur.execute("""
        SELECT title, url
        FROM seen
        WHERE applied = 0
        ORDER BY last_emailed_at DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    return [{"title": r[0] or "Google Job Posting", "url": r[1]} for r in rows]

JOB_DETAIL_RE = re.compile(r"^/jobs/results/\d+")

def parse_jobs_from_html(html: str, max_results: int) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    jobs = []

    for a in soup.select("a[href]"):
        href = a.get("href", "").strip()

        if not JOB_DETAIL_RE.match(href):
            continue

        title = a.get_text(" ", strip=True)
        url = href if href.startswith("http") else "https://careers.google.com" + href
        jobs.append({"title": title, "url": url})

        if len(jobs) >= max_results:
            break

    deduped = []
    seen_urls = set()
    for j in jobs:
        if j["url"] not in seen_urls:
            seen_urls.add(j["url"])
            deduped.append(j)

    return deduped


def send_email_smtp(subject: str, html_body: str, plain_body: str) -> None:
    import smtplib

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL

    msg.set_content(plain_body)

    if html_body.strip():
        msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.ehlo()
        if SMTP_PORT == 587:
            smtp.starttls()
            smtp.ehlo()

        if SMTP_USER and SMTP_PASS:
            smtp.login(SMTP_USER, SMTP_PASS)

        smtp.send_message(msg)


def send_email_sendgrid(subject: str, html_body: str, plain_body: str) -> None:
    url = "https://api.sendgrid.com/v3/mail/send"
    payload = {
        "personalizations": [{"to": [{"email": TO_EMAIL}], "subject": subject}],
        "from": {"email": FROM_EMAIL},
        "content": [
            {"type": "text/plain", "value": plain_body},
            {"type": "text/html", "value": html_body},
        ],
    }
    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json",
    }

    r = requests.post(url, json=payload, headers=headers)
    r.raise_for_status()


def main():
    print("SMTP_USER:", SMTP_USER)
    print("TO_EMAIL:", TO_EMAIL)
    print("Starting at:", datetime.now().isoformat())

    conn = init_db(DB_PATH)

    search_url = build_search_url(JOB_KEYWORDS, JOB_LOCATION)
    print("Search URL:", search_url)

    driver = make_headless_driver()
    try:
        driver.get(search_url)
        time.sleep(3)

        for _ in range(2):
            try:
                button = driver.find_element(
                    By.XPATH, "//button[contains(., 'Load more') or contains(., 'Show more')]"
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", button)
                time.sleep(0.2)
                button.click()
                time.sleep(2)
            except Exception:
                break

        html = driver.page_source
    finally:
        driver.quit()

    candidates = parse_jobs_from_html(html, MAX_RESULTS)
    print("Candidate job cards:", len(candidates))
    for i, job in enumerate(candidates[:10], start=1):
        print(f"{i}. {job['title']} -> {job['url']}")

    keywords_lower = [k.strip().lower() for k in JOB_KEYWORDS if k.strip()]

    new_jobs = []
    for job in candidates:
        text = job["title"].lower()
        if any(k in text for k in keywords_lower):
            if not is_seen(conn, job["url"]):
                new_jobs.append(job)
                mark_seen(conn, job["url"], job["title"])

    print("New jobs:", len(new_jobs))

    if not new_jobs:
        reminders = get_unapplied_jobs(conn, limit=10)

        if not reminders:
            subject = f"No new Google jobs - {datetime.now(timezone.utc).date()}"
            plain_body = (
                "No new job postings today.\n"
                "Also, there are no saved unapplied jobs to remind you about."
            )
            html_body = """
            <html>
                <body>
                    <p>No new job postings today.</p>
                    <p>Also, there are no saved unapplied jobs to remind you about.</p>
                </body>
            </html>
            """
        else:
            subject = f"No new jobs today - reminder list ({datetime.now(timezone.utc).date()})"

            plain_lines = [
                "No new jobs today.",
                "Here are previous jobs you have not marked as applied:",
                ""
            ]
            html_lines = [
                "<html><body>",
                "<p>No new jobs today.</p>",
                "<p>Here are previous jobs you have not marked as applied:</p>",
                "<ul>"
            ]

            for j in reminders:
                plain_lines.append(f"- {j['title']} -> {j['url']}")
                html_lines.append(f"<li><a href='{j['url']}'>{j['title']}</a></li>")

            html_lines.extend(["</ul>", "</body></html>"])
            plain_body = "\n".join(plain_lines)
            html_body = "\n".join(html_lines)
    else:
        subject = f"{len(new_jobs)} new Google jobs - {datetime.now(timezone.utc).date()}"
        lines = ["New job postings:", ""]
        html_lines = ["<html><body><h2>New job postings</h2><ul>"]

        for j in new_jobs:
            lines.append(f"- {j['title']} -> {j['url']}")
            html_lines.append(f"<li><a href='{j['url']}'>{j['title']}</a></li>")

        html_lines.extend(["</ul>", "</body></html>"])
        plain_body = "\n".join(lines)
        html_body = "\n".join(html_lines)

    print("SUBJECT:", subject)
    print("PLAIN BODY:", plain_body)
    print("HTML BODY:", html_body)

    if SENDGRID_API_KEY:
        send_email_sendgrid(subject, html_body, plain_body)
    else:
        send_email_smtp(subject, html_body, plain_body)

    print("Done.")


if __name__ == "__main__":
    main()