#!/usr/bin/env python3
"""
Job Scraper - Main entry point

Usage:
    python main.py
"""

import json
from pathlib import Path
from scrapers import AmazonScraper, DeliveryHeroScraper, BoltScraper, ZalandoScraper, HelloFreshScraper, N26Scraper, Auto1Scraper, SAPScraper


def load_existing_jobs(filepath: str) -> dict[str, dict]:
    """Load existing jobs and return a dict keyed by job ID."""
    path = Path(filepath)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        jobs = json.load(f)
    return {str(job.get("id", "")): job for job in jobs if job.get("id")}


def main():
    print("=" * 80)
    print("Job Scraper - Germany ML/AI Jobs")
    print("=" * 80)
    print()

    output_file = "jobs.json"

    # Load existing jobs to preserve scraped_at for known jobs
    existing_jobs = load_existing_jobs(output_file)
    print(f"Loaded {len(existing_jobs)} existing jobs from {output_file}")

    # Initialize scrapers
    scrapers = [
        AmazonScraper(country_code="DEU"),
        DeliveryHeroScraper(country_code="DEU"),
        BoltScraper(country_code="DEU"),
        ZalandoScraper(country_code="DEU"),
        HelloFreshScraper(country_code="DEU"),
        N26Scraper(country_code="DEU"),
        Auto1Scraper(country_code="DEU"),
        SAPScraper(country_code="DEU"),
    ]

    all_jobs = []

    # Run each scraper
    for scraper in scrapers:
        print(f"\n[{scraper.company_name}] Starting scrape...")
        print("-" * 40)

        try:
            jobs = scraper.fetch_jobs(query="machine learning")
            all_jobs.extend(jobs)
            print(f"[{scraper.company_name}] Found {len(jobs)} jobs")
        except Exception as e:
            print(f"[{scraper.company_name}] Error: {e}")

    print()
    print("=" * 80)
    print(f"TOTAL: {len(all_jobs)} jobs found across {len(scrapers)} companies")
    print("=" * 80)

    # Convert to dicts, preserving scraped_at for existing jobs
    jobs_data = []
    new_count = 0
    for job in all_jobs:
        job_dict = job.to_dict()
        job_id = str(job_dict.get("id", ""))

        if job_id in existing_jobs:
            # Preserve original scraped_at timestamp
            job_dict["scraped_at"] = existing_jobs[job_id].get("scraped_at", job_dict["scraped_at"])
        else:
            new_count += 1

        jobs_data.append(job_dict)

    print(f"New jobs: {new_count}")

    # Sort by scraped_at descending (newest first)
    jobs_data.sort(key=lambda x: x.get("scraped_at", ""), reverse=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(jobs_data, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to {output_file}")

    # Display jobs (with safe encoding for Windows console)
    print("\nJobs (sorted by date):")
    print("-" * 80)

    for i, job in enumerate(all_jobs, 1):
        # Replace non-ASCII chars for safe console output
        title = job.title.encode('ascii', 'replace').decode('ascii')
        location = job.location.encode('ascii', 'replace').decode('ascii')

        print(f"{i:3}. [{job.company}] {title}")
        print(f"     Location: {location}")
        print(f"     Posted: {job.posted_date or 'N/A'} | Updated: {job.updated_time or 'N/A'}")
        print(f"     URL: {job.url}")
        print()


if __name__ == "__main__":
    main()
