#!/usr/bin/env python3
"""
Job Scraper - Main entry point

Usage:
    python main.py
"""

import json
from scrapers import AmazonScraper, DeliveryHeroScraper, BoltScraper, ZalandoScraper, HelloFreshScraper, N26Scraper, Auto1Scraper, SAPScraper


def main():
    print("=" * 80)
    print("Job Scraper - Germany ML/AI Jobs")
    print("=" * 80)
    print()

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

    # Save to JSON first (before printing which may fail on Windows with Unicode)
    output_file = "jobs.json"
    jobs_data = [job.to_dict() for job in all_jobs]

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
