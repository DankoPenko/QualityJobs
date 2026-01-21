"""
Job notification system - detects new jobs and sends email notifications.
Sends to owner via Gmail and to subscribers via Resend.
"""

import json
import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass


JOBS_FILE = Path(__file__).parent / "jobs.json"
SEEN_JOBS_FILE = Path(__file__).parent / "seen_jobs.json"

EMAIL_ADDRESS = "danko.penko@gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

SUBSCRIBERS_FILE = Path(__file__).parent / "subscribers.json"


@dataclass
class NewJob:
    id: str
    title: str
    company: str
    url: str
    location: str


def load_jobs() -> list[dict]:
    """Load all jobs from jobs.json."""
    if not JOBS_FILE.exists():
        return []
    with open(JOBS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_seen_job_ids() -> set[str]:
    """Load IDs of jobs we've already notified about."""
    if not SEEN_JOBS_FILE.exists():
        return set()
    with open(SEEN_JOBS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return set(data.get("seen_ids", []))


def save_seen_job_ids(seen_ids: set[str]) -> None:
    """Save IDs of jobs we've notified about."""
    with open(SEEN_JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "seen_ids": list(seen_ids),
            "last_updated": datetime.now().isoformat()
        }, f, indent=2)


def detect_new_jobs() -> list[NewJob]:
    """Detect jobs that haven't been seen before."""
    all_jobs = load_jobs()
    seen_ids = load_seen_job_ids()

    new_jobs = []
    for job in all_jobs:
        job_id = str(job.get("id", ""))
        if job_id and job_id not in seen_ids:
            new_jobs.append(NewJob(
                id=job_id,
                title=job.get("title", "Unknown"),
                company=job.get("company", "Unknown"),
                url=job.get("url", ""),
                location=job.get("location", "Unknown")
            ))

    return new_jobs


def mark_jobs_as_seen(jobs: list[NewJob]) -> None:
    """Mark jobs as seen so we don't notify about them again."""
    seen_ids = load_seen_job_ids()
    for job in jobs:
        seen_ids.add(job.id)
    save_seen_job_ids(seen_ids)


def print_new_jobs(jobs: list[NewJob]) -> None:
    """Print new jobs to console."""
    if not jobs:
        print("No new jobs found.")
        return

    print(f"\n{'='*60}")
    print(f"  {len(jobs)} NEW JOB(S) FOUND!")
    print(f"{'='*60}\n")

    for i, job in enumerate(jobs, 1):
        print(f"{i}. {job.title}")
        print(f"   Company: {job.company}")
        print(f"   Location: {job.location}")
        print(f"   URL: {job.url}")
        print()


def send_email(jobs: list[NewJob], password: str, to_email: str = None, unsubscribe_url: str = None) -> bool:
    """Send email with new jobs to a single recipient."""
    if not jobs:
        return False

    recipient = to_email or EMAIL_ADDRESS
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Quality Jobs: {len(jobs)} new position(s) found!"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = recipient

    # Plain text version
    text = f"{len(jobs)} new job(s) found:\n\n"
    for job in jobs:
        text += f"- {job.title} at {job.company}\n  {job.url}\n\n"
    text += "\nView all jobs: https://dankopenko.github.io/QualityJobs/\n"
    if unsubscribe_url:
        text += f"\nUnsubscribe: {unsubscribe_url}\n"

    # HTML version
    unsubscribe_html = ""
    if unsubscribe_url:
        unsubscribe_html = f'<p style="color: #666; font-size: 12px;"><a href="{unsubscribe_url}">Unsubscribe</a></p>'

    html = f"""
    <html>
    <body>
    <h2>{len(jobs)} new job(s) found!</h2>
    <ul>
    {"".join(f'<li><a href="{job.url}"><b>{job.title}</b></a> at {job.company} ({job.location})</li>' for job in jobs)}
    </ul>
    <p><a href="https://dankopenko.github.io/QualityJobs/">View all jobs</a></p>
    {unsubscribe_html}
    </body>
    </html>
    """

    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Failed to send email to {recipient}: {e}")
        return False


def load_subscribers_from_file() -> list[dict]:
    """Load subscribers from local JSON file."""
    if not SUBSCRIBERS_FILE.exists():
        return []
    try:
        with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("subscribers", [])
    except Exception as e:
        print(f"Failed to load subscribers file: {e}")
        return []


def get_subscribers(worker_url: str, worker_secret: str) -> list[dict]:
    """Fetch subscribers from Cloudflare Worker."""
    try:
        response = requests.get(
            f"{worker_url}/subscribers",
            params={"key": worker_secret},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("subscribers", [])
    except Exception as e:
        print(f"Failed to get subscribers: {e}")
        return []


def sync_subscribers_to_file(worker_url: str, worker_secret: str) -> None:
    """Fetch subscribers from Worker and save to local file."""
    subscribers = get_subscribers(worker_url, worker_secret)
    if subscribers:
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "subscribers": subscribers,
                "synced_at": datetime.now().isoformat()
            }, f, indent=2)
        print(f"Synced {len(subscribers)} subscribers to {SUBSCRIBERS_FILE}")


def send_to_subscribers(jobs: list[NewJob], password: str, worker_url: str) -> None:
    """Send email notifications to all subscribers via Gmail."""
    if not jobs:
        return

    subscribers = load_subscribers_from_file()
    if not subscribers:
        print("No subscribers to notify")
        return

    print(f"Sending to {len(subscribers)} subscriber(s) via Gmail...")
    sent = 0
    failed = 0

    for subscriber in subscribers:
        email = subscriber.get("email")
        token = subscriber.get("token")

        if not email or not token:
            continue

        unsubscribe_url = f"{worker_url}/unsubscribe?token={token}"

        if send_email(jobs, password, to_email=email, unsubscribe_url=unsubscribe_url):
            sent += 1
            print(f"  Sent to {email}")
        else:
            failed += 1

    print(f"Subscriber emails: {sent} sent, {failed} failed")


def initialize_seen_jobs() -> None:
    """Mark all current jobs as seen (for initial setup)."""
    all_jobs = load_jobs()
    seen_ids = {str(job.get("id", "")) for job in all_jobs if job.get("id")}
    save_seen_job_ids(seen_ids)
    print(f"Initialized with {len(seen_ids)} existing jobs marked as seen.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--init":
        initialize_seen_jobs()
    elif len(sys.argv) > 1 and sys.argv[1] == "--sync":
        # Sync subscribers from Worker to local file
        worker_url = os.environ.get("WORKER_URL")
        worker_secret = os.environ.get("WORKER_SECRET")
        if worker_url and worker_secret:
            sync_subscribers_to_file(worker_url, worker_secret)
        else:
            print("WORKER_URL and WORKER_SECRET required for sync")
    else:
        new_jobs = detect_new_jobs()
        print_new_jobs(new_jobs)

        if new_jobs:
            password = os.environ.get("EMAIL_PASSWORD")
            worker_url = os.environ.get("WORKER_URL")

            if password:
                # Send email to owner
                if send_email(new_jobs, password):
                    print("Owner email sent successfully!")

                # Send to subscribers via Gmail
                if worker_url:
                    send_to_subscribers(new_jobs, password, worker_url)
                else:
                    print("(WORKER_URL not set, skipping subscriber emails)")
            else:
                print("(EMAIL_PASSWORD not set, skipping all emails)")

            mark_jobs_as_seen(new_jobs)
            print("(Jobs marked as seen for next run)")
