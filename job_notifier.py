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

# Resend config (for subscriber notifications)
RESEND_FROM = "Quality Jobs <jobs@resend.dev>"  # Update with your verified domain


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


def send_email(jobs: list[NewJob], password: str) -> bool:
    """Send email with new jobs."""
    if not jobs:
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Quality Jobs: {len(jobs)} new position(s) found!"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_ADDRESS

    # Plain text version
    text = f"{len(jobs)} new job(s) found:\n\n"
    for job in jobs:
        text += f"- {job.title} at {job.company}\n  {job.url}\n\n"

    # HTML version
    html = f"""
    <html>
    <body>
    <h2>{len(jobs)} new job(s) found!</h2>
    <ul>
    {"".join(f'<li><a href="{job.url}"><b>{job.title}</b></a> at {job.company} ({job.location})</li>' for job in jobs)}
    </ul>
    <p><a href="https://dankopenko.github.io/QualityJobs/">View all jobs</a></p>
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
        print("Email sent successfully!")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


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


def create_subscriber_email_html(jobs: list[NewJob], unsubscribe_url: str) -> str:
    """Create HTML email content for subscribers."""
    job_items = ""
    for job in jobs[:20]:  # Limit to 20 jobs per email
        job_items += f"""
        <tr>
            <td style="padding: 16px; border-bottom: 1px solid #eee;">
                <a href="{job.url}" style="color: #0066cc; text-decoration: none; font-weight: 500;">
                    {job.title}
                </a>
                <div style="color: #666; font-size: 14px; margin-top: 4px;">
                    {job.company} - {job.location}
                </div>
            </td>
        </tr>
        """

    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background: #f5f5f5; padding: 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <tr>
                        <td style="padding: 30px 30px 20px; text-align: center; border-bottom: 1px solid #eee;">
                            <h1 style="margin: 0; color: #333; font-size: 24px;">Quality Jobs</h1>
                            <p style="margin: 8px 0 0; color: #666; font-size: 14px;">
                                {len(jobs)} new ML/DS position{"s" if len(jobs) != 1 else ""} in Germany
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <td>
                            <table width="100%" cellpadding="0" cellspacing="0">
                                {job_items}
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 20px 30px; text-align: center; background: #f9f9f9; border-radius: 0 0 8px 8px;">
                            <a href="https://dankopenko.github.io/QualityJobs/" style="color: #0066cc; text-decoration: none;">
                                View all jobs
                            </a>
                            <span style="color: #ccc; margin: 0 10px;">|</span>
                            <a href="{unsubscribe_url}" style="color: #999; text-decoration: none; font-size: 13px;">
                                Unsubscribe
                            </a>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""


def send_to_subscribers(jobs: list[NewJob], resend_api_key: str, worker_url: str, worker_secret: str) -> None:
    """Send email notifications to all subscribers via Resend."""
    if not jobs:
        return

    subscribers = get_subscribers(worker_url, worker_secret)
    if not subscribers:
        print("No subscribers to notify")
        return

    print(f"Sending to {len(subscribers)} subscriber(s)...")

    subject = f"{len(jobs)} new ML/DS job{'s' if len(jobs) != 1 else ''} in Germany"
    sent = 0
    failed = 0

    for subscriber in subscribers:
        email = subscriber.get("email")
        token = subscriber.get("token")

        if not email or not token:
            continue

        unsubscribe_url = f"{worker_url}/unsubscribe?token={token}"
        html_content = create_subscriber_email_html(jobs, unsubscribe_url)

        try:
            response = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {resend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": RESEND_FROM,
                    "to": [email],
                    "subject": subject,
                    "html": html_content,
                },
                timeout=30,
            )

            if response.status_code == 200:
                sent += 1
                print(f"  Sent to {email}")
            else:
                failed += 1
                print(f"  Failed to send to {email}: {response.text}")
        except Exception as e:
            failed += 1
            print(f"  Error sending to {email}: {e}")

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
    else:
        new_jobs = detect_new_jobs()
        print_new_jobs(new_jobs)

        if new_jobs:
            # Send email to owner via Gmail
            password = os.environ.get("EMAIL_PASSWORD")
            if password:
                send_email(new_jobs, password)
            else:
                print("(EMAIL_PASSWORD not set, skipping owner email)")

            # Send to subscribers via Resend
            resend_api_key = os.environ.get("RESEND_API_KEY")
            worker_url = os.environ.get("WORKER_URL")
            worker_secret = os.environ.get("WORKER_SECRET")

            if all([resend_api_key, worker_url, worker_secret]):
                send_to_subscribers(new_jobs, resend_api_key, worker_url, worker_secret)
            else:
                print("(Resend config not set, skipping subscriber emails)")

            mark_jobs_as_seen(new_jobs)
            print("(Jobs marked as seen for next run)")
