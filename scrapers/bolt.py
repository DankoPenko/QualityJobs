"""Bolt Jobs scraper using Greenhouse API."""

from typing import Optional
from datetime import datetime

from .base import BaseScraper
from models import Job


class BoltScraper(BaseScraper):
    """
    Scraper for Bolt Jobs (ride-hailing/delivery company).

    Uses Greenhouse API. Bolt's board ID is 'boltv2'.
    """

    company_name = "Bolt"
    base_url = "https://api.greenhouse.io/v1/boards/boltv2/jobs"

    # Keywords for ML/DS job filtering
    ML_DS_KEYWORDS = [
        "machine learning", "data scien", "data engineer", "data analyst",
        "ml ", " ml", "ai ", " ai", "deep learning", "nlp",
        "computer vision", "analytics", "neural", "llm",
        "research scientist", "applied scientist"
    ]

    def _is_ml_ds_job(self, job_data: dict) -> bool:
        """Check if job is ML/DS related based on title and department."""
        title = job_data.get("title", "").lower()

        # Check departments
        departments = job_data.get("departments", [])
        dept_names = " ".join(d.get("name", "").lower() for d in departments)

        # Combine title and department for matching
        searchable = f"{title} {dept_names}"

        return any(kw in searchable for kw in self.ML_DS_KEYWORDS)

    def fetch_jobs(self, query: str = "data science", max_results: Optional[int] = None) -> list[Job]:
        """
        Fetch ML/DS jobs from Bolt's Greenhouse API.

        Args:
            query: Search query (used for filtering results)
            max_results: Maximum number of jobs to fetch (None for all)

        Returns:
            List of Job objects from Germany, sorted by updated date (newest first)
        """
        print(f"  [{self.company_name}] Fetching jobs...")

        try:
            data = self._fetch_all_jobs()
        except Exception as e:
            print(f"  [{self.company_name}] Error: {e}")
            return []

        jobs_data = data.get("jobs", [])
        print(f"  [{self.company_name}] Total jobs from API: {len(jobs_data)}")

        # Filter for Germany + ML/DS jobs
        all_jobs: list[Job] = []
        germany_count = 0
        for job_data in jobs_data:
            location = job_data.get("location", {})
            loc_name = location.get("name", "") if isinstance(location, dict) else str(location)

            # Check if job is in Germany
            is_germany = (
                "Germany" in loc_name or
                "Berlin" in loc_name or
                "Munich" in loc_name or
                "Hamburg" in loc_name
            )

            if is_germany:
                germany_count += 1
                # Also check if it's ML/DS related
                if self._is_ml_ds_job(job_data):
                    job = self._parse_job(job_data)
                    all_jobs.append(job)

        print(f"  [{self.company_name}] Germany jobs: {germany_count}, ML/DS jobs: {len(all_jobs)}")

        # Sort by updated date (newest first)
        all_jobs.sort(key=lambda j: self._parse_date(j.updated_time), reverse=True)

        if max_results:
            all_jobs = all_jobs[:max_results]

        return all_jobs

    def _fetch_all_jobs(self) -> dict:
        """Fetch all jobs from the API (Greenhouse returns all at once)."""
        params = {"content": "true"}  # Include job content/description
        response = self._make_request(self.base_url, params=params)
        return response.json()

    def _parse_job(self, data: dict) -> Job:
        """Parse raw API data into a Job object."""
        location = data.get("location", {})
        loc_name = location.get("name", "") if isinstance(location, dict) else str(location)

        # Extract department
        departments = data.get("departments", [])
        department = departments[0].get("name") if departments else None

        # Parse location into city/country
        city = None
        country = "Germany"
        if loc_name:
            parts = loc_name.split(", ")
            if len(parts) >= 1:
                city = parts[0]

        return Job(
            id=str(data.get("id", "")),
            title=data.get("title", ""),
            company=self.company_name,
            url=data.get("absolute_url", ""),
            location=loc_name,
            city=city,
            country=country,
            posted_date=None,  # Greenhouse doesn't provide posting date in list
            updated_time=data.get("updated_at"),
            source=self.__class__.__name__,
            department=department,
        )

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> datetime:
        """Parse Greenhouse date format (ISO 8601) for sorting."""
        if not date_str:
            return datetime(1900, 1, 1)
        try:
            # Format: 2025-11-28T08:14:18-05:00
            return datetime.fromisoformat(date_str)
        except ValueError:
            return datetime(1900, 1, 1)
