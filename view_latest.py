#!/usr/bin/env python3
"""
View Latest Jobs - Shows 5 most recent jobs from each company.
"""

import json
from datetime import datetime
from collections import defaultdict


def parse_date(job: dict) -> datetime:
    """Parse job date for sorting (handles different date formats)."""
    # Try posted_date first
    posted = job.get("posted_date")
    if posted:
        # Amazon format: "December 23, 2025"
        try:
            return datetime.strptime(posted, "%B %d, %Y")
        except ValueError:
            pass
        # SmartRecruiters format: "2025-01-08T10:30:00.000Z"
        try:
            return datetime.fromisoformat(posted.replace("Z", "+00:00"))
        except ValueError:
            pass

    # Try updated_time for Bolt (ISO format)
    updated = job.get("updated_time")
    if updated:
        try:
            return datetime.fromisoformat(updated)
        except ValueError:
            pass

    return datetime(1900, 1, 1)


def main():
    # Load jobs
    with open("jobs.json", "r", encoding="utf-8") as f:
        jobs = json.load(f)

    # Group by company
    by_company = defaultdict(list)
    for job in jobs:
        by_company[job["company"]].append(job)

    # Sort each company's jobs by date (newest first)
    for company in by_company:
        by_company[company].sort(key=parse_date, reverse=True)

    print("=" * 80)
    print("5 LATEST JOBS FROM EACH COMPANY")
    print("=" * 80)

    for company in sorted(by_company.keys()):
        company_jobs = by_company[company]
        print(f"\n{'-' * 80}")
        print(f"  {company.upper()} ({len(company_jobs)} total jobs)")
        print(f"{'-' * 80}")

        for i, job in enumerate(company_jobs[:5], 1):
            title = job["title"]
            location = job.get("city") or job.get("location", "N/A")
            posted = job.get("posted_date") or job.get("updated_time") or "N/A"
            url = job["url"]

            # Format date nicely
            if posted and "T" in str(posted):
                try:
                    dt = datetime.fromisoformat(posted.replace("Z", "+00:00"))
                    posted = dt.strftime("%B %d, %Y")
                except:
                    pass

            print(f"\n  {i}. {title}")
            print(f"     Location: {location}")
            print(f"     Posted:   {posted}")
            print(f"     URL:      {url}")

    print(f"\n{'=' * 80}")
    print(f"Total: {len(jobs)} jobs across {len(by_company)} companies")
    print("=" * 80)


if __name__ == "__main__":
    main()
