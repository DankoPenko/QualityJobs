"""
Job notification system - detects new jobs and prepares email notifications.
"""

import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass


JOBS_FILE = Path(__file__).parent / "jobs.json"
SEEN_JOBS_FILE = Path(__file__).parent / "seen_jobs.json"


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
            mark_jobs_as_seen(new_jobs)
            print("(Jobs marked as seen for next run)")
