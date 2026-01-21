#!/usr/bin/env python3
"""
Test SmartRecruiters scraper for one or more companies.

Examples:
  python scripts/test_smartrecruiters.py --slug DeliveryHero --name "Delivery Hero"
  python scripts/test_smartrecruiters.py --from-results --limit 5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scrapers import SmartRecruitersScraper  # noqa: E402


def load_from_results(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Results file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("smartrecruiters", [])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SmartRecruiters scrapes for testing.")
    parser.add_argument("--slug", help="SmartRecruiters company slug (e.g., DeliveryHero)")
    parser.add_argument("--name", help="Company display name")
    parser.add_argument("--domain", default="", help="Company domain for logo")
    parser.add_argument("--from-results", action="store_true", help="Use platform_matches.json list")
    parser.add_argument("--results-path", default="platform_matches.json", help="Path to results JSON")
    parser.add_argument("--limit", type=int, default=None, help="Max companies to test")
    parser.add_argument("--max-jobs", type=int, default=10, help="Max jobs per company")
    parser.add_argument("--query", default="machine learning", help="Search query")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    companies = []
    if args.slug:
        companies.append({
            "name": args.name or args.slug,
            "slug": args.slug,
            "domain": args.domain,
        })
    elif args.from_results:
        results_path = Path(args.results_path)
        companies = load_from_results(results_path)
    else:
        raise SystemExit("Provide --slug or --from-results")

    if args.limit:
        companies = companies[: args.limit]

    all_results = []
    for company in companies:
        scraper = SmartRecruitersScraper(
            company_name=company["name"],
            company_slug=company["slug"],
            domain=company.get("domain", ""),
            country_code="DEU",
        )
        print(f"\n[{scraper.company_name}] Testing SmartRecruiters scrape...")
        jobs = scraper.fetch_jobs(query=args.query, max_results=args.max_jobs)
        print(f"[{scraper.company_name}] Jobs found: {len(jobs)}")
        all_results.append({
            "name": scraper.company_name,
            "slug": company["slug"],
            "jobs": [job.to_dict() for job in jobs],
        })

    output_path = Path("smartrecruiters_test_output.json")
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved results to {output_path}")


if __name__ == "__main__":
    main()
