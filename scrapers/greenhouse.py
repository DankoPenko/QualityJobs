"""Generic Greenhouse Jobs scraper - works with any company using Greenhouse."""

from typing import Optional
from datetime import datetime

from .base import BaseScraper
from models import Job


class GreenhouseScraper(BaseScraper):
    """
    Generic scraper for companies using Greenhouse job boards.

    Usage:
        scraper = GreenhouseScraper(
            company_name="Databricks",
            board_slug="databricks",
            domain="databricks.com"
        )
    """

    # Keywords for ML/DS job filtering
    ML_DS_KEYWORDS = [
        "machine learning", "data scien", "data engineer", "data analyst",
        "ml ", " ml", "ai ", " ai", "deep learning", "nlp",
        "computer vision", "analytics", "neural", "llm",
        "research scientist", "applied scientist"
    ]

    def __init__(self, company_name: str, board_slug: str, domain: str = "", **kwargs):
        """
        Initialize Greenhouse scraper for a specific company.

        Args:
            company_name: Display name of the company
            board_slug: Greenhouse board ID (e.g., 'databricks', 'gitlab')
            domain: Company domain for logo (e.g., 'databricks.com')
        """
        self.company_name = company_name
        self.board_slug = board_slug
        self.domain = domain
        self.base_url = f"https://boards-api.greenhouse.io/v1/boards/{board_slug}/jobs"
        super().__init__(**kwargs)

    def _is_ml_ds_job(self, job_data: dict) -> bool:
        """Check if job is ML/DS related based on title and department."""
        title = job_data.get("title", "").lower()

        # Check departments
        departments = job_data.get("departments", [])
        dept_names = " ".join(d.get("name", "").lower() for d in departments)

        # Combine title and department for matching
        searchable = f"{title} {dept_names}"

        return any(kw in searchable for kw in self.ML_DS_KEYWORDS)

    def _is_germany_job(self, location: str) -> bool:
        """Check if job location is in Germany or EU-remote eligible."""
        loc_lower = location.lower()
        return any(term in loc_lower for term in [
            "germany", "berlin", "munich", "hamburg", "frankfurt",
            "emea", "europe", "remote"
        ])

    def fetch_jobs(self, query: str = "data science", max_results: Optional[int] = None) -> list[Job]:
        """
        Fetch ML/DS jobs from Greenhouse API.

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

            if self._is_germany_job(loc_name):
                germany_count += 1
                if self._is_ml_ds_job(job_data):
                    job = self._parse_job(job_data)
                    all_jobs.append(job)

        print(f"  [{self.company_name}] Germany/EU jobs: {germany_count}, ML/DS jobs: {len(all_jobs)}")

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

        # Extract description from content field (HTML)
        content = data.get("content", "")
        description = self._clean_html(content) if content else None

        return Job(
            id=str(data.get("id", "")),
            title=data.get("title", ""),
            company=self.company_name,
            url=data.get("absolute_url", ""),
            location=loc_name,
            city=city,
            country=country,
            posted_date=None,
            updated_time=data.get("updated_at"),
            source=f"Greenhouse:{self.board_slug}",
            department=department,
            description=description,
        )

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> datetime:
        """Parse Greenhouse date format (ISO 8601) for sorting."""
        if not date_str:
            return datetime(1900, 1, 1)
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            return datetime(1900, 1, 1)
