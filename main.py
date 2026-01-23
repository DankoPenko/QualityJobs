#!/usr/bin/env python3
"""
Job Scraper - Main entry point

Usage:
    python main.py
"""

import json
from datetime import datetime
from pathlib import Path
from scrapers import (
    GreenhouseScraper,
    SmartRecruitersScraper,
    AmazonScraper,
    ZalandoScraper,
    SAPScraper,
    SnapchatScraper,
)

ARCHIVE_FILE = "archived_jobs.json"

# ============================================================================
# COMPANY CONFIGURATIONS
# ============================================================================

# Companies using Greenhouse job boards
GREENHOUSE_COMPANIES = [
    # Existing
    {"name": "Bolt", "slug": "boltv2", "domain": "bolt.eu"},
    {"name": "N26", "slug": "n26", "domain": "n26.com"},
    {"name": "HelloFresh", "slug": "hellofresh", "domain": "hellofresh.com"},
    {"name": "Canonical", "slug": "canonical", "domain": "canonical.com"},
    {"name": "GitLab", "slug": "gitlab", "domain": "gitlab.com"},
    {"name": "Databricks", "slug": "databricks", "domain": "databricks.com"},
    {"name": "Grammarly", "slug": "grammarly", "domain": "grammarly.com"},
    {"name": "Grafana Labs", "slug": "grafanalabs", "domain": "grafana.com"},
    {"name": "Vercel", "slug": "vercel", "domain": "vercel.com"},
    {"name": "Cloudflare", "slug": "cloudflare", "domain": "cloudflare.com"},
    {"name": "Discord", "slug": "discord", "domain": "discord.com"},
    {"name": "Stripe", "slug": "stripe", "domain": "stripe.com"},
    {"name": "Coinbase", "slug": "coinbase", "domain": "coinbase.com"},
    {"name": "Dropbox", "slug": "dropbox", "domain": "dropbox.com"},
    {"name": "Reddit", "slug": "reddit", "domain": "reddit.com"},
    {"name": "Airbnb", "slug": "airbnb", "domain": "airbnb.com"},
    {"name": "Figma", "slug": "figma", "domain": "figma.com"},
    {"name": "Datadog", "slug": "datadog", "domain": "datadoghq.com"},
    {"name": "Elastic", "slug": "elastic", "domain": "elastic.co"},
    {"name": "Collibra", "slug": "collibra", "domain": "collibra.com"},
    # New from TrueUp hypergrowth list
    {"name": "xAI", "slug": "xai", "domain": "x.ai"},
    {"name": "Anthropic", "slug": "anthropic", "domain": "anthropic.com"},
    {"name": "Anduril", "slug": "andurilindustries", "domain": "anduril.com"},
    {"name": "Samsara", "slug": "samsara", "domain": "samsara.com"},
    {"name": "CoreWeave", "slug": "coreweave", "domain": "coreweave.com"},
    {"name": "Verkada", "slug": "verkada", "domain": "verkada.com"},
    {"name": "Rubrik", "slug": "rubrik", "domain": "rubrik.com"},
    {"name": "Applied Intuition", "slug": "appliedintuition", "domain": "appliedintuition.com"},
    {"name": "ClickHouse", "slug": "clickhouse", "domain": "clickhouse.com"},
    {"name": "Robinhood", "slug": "robinhood", "domain": "robinhood.com"},
    {"name": "Cribl", "slug": "cribl", "domain": "cribl.io"},
    {"name": "PsiQuantum", "slug": "psiquantum", "domain": "psiquantum.com"},
    {"name": "IonQ", "slug": "ionq", "domain": "ionq.com"},
    {"name": "Lovable", "slug": "lovable", "domain": "lovable.dev"},
    {"name": "Helsing", "slug": "helsing", "domain": "helsing.ai"},
    {"name": "Neuralink", "slug": "neuralink", "domain": "neuralink.com"},
    {"name": "Nubank", "slug": "nubank", "domain": "nubank.com.br"},
    {"name": "Chainguard", "slug": "chainguard", "domain": "chainguard.dev"},
    {"name": "Mercury", "slug": "mercury", "domain": "mercury.com"},
    {"name": "Wayve", "slug": "wayve", "domain": "wayve.ai"},
    {"name": "Figure", "slug": "figure", "domain": "figure.ai"},
    {"name": "Fireworks", "slug": "fireworksai", "domain": "fireworks.ai"},
    {"name": "Runway", "slug": "runwayml", "domain": "runwayml.com"},
    {"name": "ShopMy", "slug": "shopmy", "domain": "shopmy.us"},
    {"name": "Coalition", "slug": "coalition", "domain": "coalitioninc.com"},
    {"name": "Temporal", "slug": "temporal", "domain": "temporal.io"},
    # Healthcare/Biotech from TrueUp
    {"name": "Doctolib", "slug": "doctolib", "domain": "doctolib.com"},
    {"name": "Strive Health", "slug": "strivehealth", "domain": "strivehealth.com"},
    {"name": "Pomelo Care", "slug": "pomelocare", "domain": "pomelocare.com"},
    {"name": "Headway", "slug": "headway", "domain": "headway.co"},
    {"name": "Oura", "slug": "oura", "domain": "ouraring.com"},
    {"name": "Lila Sciences", "slug": "lilasciences", "domain": "lilasciences.com"},
    {"name": "Truveta", "slug": "truveta", "domain": "truveta.com"},
    {"name": "Freenome", "slug": "freenome", "domain": "freenome.com"},
    {"name": "Transcarent", "slug": "transcarent", "domain": "transcarent.com"},
    {"name": "Tebra", "slug": "tebra", "domain": "tebra.com"},
    {"name": "Thyme Care", "slug": "thymecare", "domain": "thymecare.com"},
    {"name": "Generate Biomedicines", "slug": "generatebiomedicines", "domain": "generatebiomedicines.com"},
    {"name": "Roivant Sciences", "slug": "roivantsciences", "domain": "roivant.com"},
    {"name": "Resilience", "slug": "resilience", "domain": "resilience.com"},
    {"name": "NewLimit", "slug": "newlimit", "domain": "newlimit.com"},
    {"name": "EvolutionaryScale", "slug": "evolutionaryscale", "domain": "evolutionaryscale.ai"},
    # Fintech from TrueUp
    {"name": "SoFi", "slug": "sofi", "domain": "sofi.com"},
    {"name": "Brex", "slug": "brex", "domain": "brex.com"},
    {"name": "C6 Bank", "slug": "c6bank", "domain": "c6bank.com.br"},
    {"name": "Monzo", "slug": "monzo", "domain": "monzo.com"},
    {"name": "PhonePe", "slug": "phonepe", "domain": "phonepe.com"},
    {"name": "Kalshi", "slug": "kalshi", "domain": "kalshi.com"},
    {"name": "Upgrade", "slug": "upgrade", "domain": "upgrade.com"},
    {"name": "Array", "slug": "array", "domain": "array.com"},
    # German companies
    {"name": "FlixBus", "slug": "flix", "domain": "flixbus.com"},
    {"name": "Raisin", "slug": "raisin", "domain": "raisin.com"},
    {"name": "SumUp", "slug": "sumup", "domain": "sumup.com"},
    {"name": "Free Now", "slug": "freenow", "domain": "free-now.com"},
    {"name": "Celonis", "slug": "celonis", "domain": "celonis.com"},
    {"name": "Contentful", "slug": "contentful", "domain": "contentful.com"},
    {"name": "GetYourGuide", "slug": "getyourguide", "domain": "getyourguide.com"},
    {"name": "Trivago", "slug": "trivago", "domain": "trivago.com"},
    {"name": "Ada Health", "slug": "adahealth", "domain": "ada.com"},
]

# Companies using SmartRecruiters job boards
SMARTRECRUITERS_COMPANIES = [
    {"name": "Delivery Hero", "slug": "DeliveryHero", "domain": "deliveryhero.com"},
    {"name": "Canva", "slug": "Canva", "domain": "canva.com"},
    {"name": "Together", "slug": "Together", "domain": "together.ai"},
    {"name": "ByteDance", "slug": "ByteDance", "domain": "bytedance.com"},
    {"name": "Devoted Health", "slug": "DevotedHealth", "domain": "devotedhealth.com"},
    {"name": "Glean", "slug": "Glean", "domain": "glean.com"},
    {"name": "Uber", "slug": "Uber", "domain": "uber.com"},
    {"name": "Xiaomi", "slug": "Xiaomi", "domain": "mi.com"},
    # Fintech from TrueUp
    {"name": "Binance", "slug": "Binance", "domain": "binance.com"},
    # German companies
    {"name": "Check24", "slug": "check24", "domain": "check24.de"},
    {"name": "AboutYou", "slug": "aboutyougmbh", "domain": "aboutyou.com"},
    {"name": "Sixt", "slug": "sixt", "domain": "sixt.com"},
    {"name": "AUTO1 Group", "slug": "auto1", "domain": "auto1-group.com"},
    {"name": "Omio", "slug": "omio", "domain": "omio.com"},
]


def load_existing_jobs(filepath: str) -> dict[str, dict]:
    """Load existing jobs and return a dict keyed by job ID."""
    path = Path(filepath)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        jobs = json.load(f)
    return {str(job.get("id", "")): job for job in jobs if job.get("id")}


def load_archived_jobs() -> list[dict]:
    """Load archived jobs from archive file."""
    path = Path(ARCHIVE_FILE)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_archived_jobs(jobs: list[dict]) -> None:
    """Save archived jobs to archive file."""
    with open(ARCHIVE_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)


def archive_stale_jobs(existing_jobs: dict[str, dict], current_job_ids: set[str]) -> int:
    """Move jobs that no longer appear in scrape results to archive."""
    stale_ids = set(existing_jobs.keys()) - current_job_ids
    if not stale_ids:
        return 0

    archived = load_archived_jobs()
    archived_ids = {str(job.get("id", "")) for job in archived}
    now = datetime.now().isoformat()

    for job_id in stale_ids:
        if job_id not in archived_ids:
            job = existing_jobs[job_id].copy()
            job["archived_at"] = now
            archived.append(job)

    # Sort by archived_at descending (most recently archived first)
    archived.sort(key=lambda x: x.get("archived_at", ""), reverse=True)
    save_archived_jobs(archived)

    return len(stale_ids)


def main():
    print("=" * 80)
    print("Job Scraper - Germany ML/AI Jobs")
    print("=" * 80)
    print()

    output_file = "jobs.json"

    # Load existing jobs to preserve scraped_at for known jobs
    existing_jobs = load_existing_jobs(output_file)
    print(f"Loaded {len(existing_jobs)} existing jobs from {output_file}")

    # Build scrapers list
    scrapers = []

    # Greenhouse-based companies
    for company in GREENHOUSE_COMPANIES:
        scrapers.append(GreenhouseScraper(
            company_name=company["name"],
            board_slug=company["slug"],
            domain=company["domain"],
            country_code="DEU",
        ))

    # SmartRecruiters-based companies
    for company in SMARTRECRUITERS_COMPANIES:
        scrapers.append(SmartRecruitersScraper(
            company_name=company["name"],
            company_slug=company["slug"],
            domain=company["domain"],
            country_code="DEU",
        ))

    # Custom scrapers
    scrapers.extend([
        AmazonScraper(country_code="DEU"),
        ZalandoScraper(country_code="DEU"),
        SAPScraper(country_code="DEU"),
        SnapchatScraper(country_code="DEU"),
    ])

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

    # Archive jobs that are no longer returned by scrapers
    current_job_ids = {str(job_dict.get("id", "")) for job_dict in jobs_data}
    archived_count = archive_stale_jobs(existing_jobs, current_job_ids)
    if archived_count > 0:
        print(f"Archived jobs: {archived_count}")

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
