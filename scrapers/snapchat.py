"""Snapchat Jobs scraper - parses careers.snap.com."""

import re
import json
from typing import Optional

from .base import BaseScraper
from models import Job


class SnapchatScraper(BaseScraper):
    """
    Scraper for Snapchat/Snap Inc Jobs.

    Parses embedded JSON from careers.snap.com
    """

    company_name = "Snapchat"
    base_url = "https://careers.snap.com/jobs"

    # Keywords for ML/DS job filtering
    ML_DS_KEYWORDS = [
        "machine learning", "data scien", "data engineer", "data analyst",
        "ml ", " ml", "ai ", " ai", "deep learning", "nlp",
        "computer vision", "analytics", "neural", "llm",
        "research scientist", "applied scientist", "research engineer"
    ]

    # Target locations: Germany, London, Vienna
    TARGET_LOCATIONS = [
        "germany", "berlin", "munich", "frankfurt", "hamburg",
        "london", "united kingdom", "uk",
        "vienna", "austria", "wien"
    ]

    # Location search terms for API
    LOCATION_SEARCHES = ["Germany", "London", "Austria"]

    def _is_ml_ds_job(self, job_data: dict) -> bool:
        """Check if job is ML/DS related based on title or description."""
        title = job_data.get("title", "").lower()
        # Also check description snippet if available
        desc = str(job_data.get("description", "")).lower()
        text = title + " " + desc
        return any(kw in text for kw in self.ML_DS_KEYWORDS)

    def _is_target_location(self, job_data: dict) -> bool:
        """Check if job is in one of our target locations."""
        location = job_data.get("primary_location", "").lower()
        offices = job_data.get("offices", [])
        for office in offices:
            loc = office.get("location", "").lower()
            if any(t in loc for t in self.TARGET_LOCATIONS):
                return True
        return any(t in location for t in self.TARGET_LOCATIONS)

    def fetch_jobs(self, query: str = "machine learning", max_results: Optional[int] = None) -> list[Job]:
        """
        Fetch ML/DS jobs from Snapchat careers page.

        Returns:
            List of Job objects from Germany, London, and Vienna
        """
        print(f"  [{self.company_name}] Fetching jobs from careers page...")

        all_jobs: list[Job] = []
        seen_ids = set()

        # Search each location
        for location in self.LOCATION_SEARCHES:
            params = {"location": location}

            try:
                response = self._make_request(self.base_url, params=params)
                html = response.text
            except Exception as e:
                print(f"  [{self.company_name}] Error fetching {location}: {e}")
                continue

            jobs_data = self._extract_jobs_from_html(html)

            for job_data in jobs_data:
                job_id = job_data.get("id", "")
                if job_id in seen_ids:
                    continue

                if self._is_target_location(job_data) and self._is_ml_ds_job(job_data):
                    job = self._parse_job(job_data)
                    all_jobs.append(job)
                    seen_ids.add(job_id)

        print(f"  [{self.company_name}] Total ML/DS jobs found: {len(all_jobs)}")

        if max_results:
            all_jobs = all_jobs[:max_results]

        return all_jobs

    def _extract_jobs_from_html(self, html: str) -> list[dict]:
        """Extract job data from embedded JSON in HTML."""
        jobs = []

        # Find start of JSON
        start_marker = "window.ASYNC_DATA_CONTROLLER_CACHE = "
        start_idx = html.find(start_marker)
        if start_idx == -1:
            return jobs

        json_start = start_idx + len(start_marker)

        # Find matching closing brace using bracket counting
        depth = 0
        json_end = json_start
        for i, char in enumerate(html[json_start:]):
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    json_end = json_start + i + 1
                    break

        try:
            cache_data = json.loads(html[json_start:json_end])
            # Find jobs in cache - nested under data.body[]._source
            for key, value in cache_data.items():
                if "jobs" in key.lower() and isinstance(value, dict):
                    inner = value.get("data", {})
                    body = inner.get("body", [])
                    for item in body:
                        source = item.get("_source", {})
                        if source:
                            jobs.append(source)
        except json.JSONDecodeError:
            pass

        return jobs

    def _parse_job(self, data: dict) -> Job:
        """Parse raw job data into a Job object."""
        location = data.get("primary_location", "")
        offices = data.get("offices", [])
        if offices and isinstance(offices[0], dict):
            office = offices[0]
            location = office.get("location", location)

        city = location.split(",")[0].strip() if location else ""

        return Job(
            id=str(data.get("id", "")),
            title=data.get("title", ""),
            company=self.company_name,
            url=data.get("absolute_url", ""),
            location=location,
            city=city,
            country="Germany",
            posted_date=None,
            updated_time=None,
            source=self.__class__.__name__,
        )
