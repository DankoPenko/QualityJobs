"""N26 Jobs scraper - uses Greenhouse API."""

from typing import Optional
from datetime import datetime

from .base import BaseScraper
from models import Job


class N26Scraper(BaseScraper):
    """
    Scraper for N26 Jobs.

    N26 uses Greenhouse with board name 'n26'.
    """

    company_name = "N26"
    base_url = "https://api.greenhouse.io/v1/boards/n26/jobs"

    # German cities
    GERMANY_LOCATIONS = ["berlin", "munich", "frankfurt", "hamburg", "germany"]

    # Keywords for ML/DS job filtering
    ML_DS_KEYWORDS = [
        "machine learning", "data scien", "data engineer", "data analyst",
        "ml ", " ml", "ai ", " ai", "deep learning", "nlp",
        "computer vision", "analytics", "neural", "llm",
        "research scientist", "applied scientist"
    ]

    def _is_germany_job(self, job_data: dict) -> bool:
        """Check if job is located in Germany."""
        location = job_data.get("location", {}).get("name", "").lower()
        return any(loc in location for loc in self.GERMANY_LOCATIONS)

    def _is_ml_ds_job(self, job_data: dict) -> bool:
        """Check if job is ML/DS related based on title."""
        title = job_data.get("title", "").lower()

        # Exclude pure database/infrastructure roles
        if "database" in title and "data scien" not in title and "data eng" not in title:
            return False

        return any(kw in title for kw in self.ML_DS_KEYWORDS)

    def fetch_jobs(self, query: str = "data science", max_results: Optional[int] = None) -> list[Job]:
        """
        Fetch ML/DS jobs from N26's Greenhouse board.

        Returns:
            List of Job objects from Germany, filtered for ML/DS roles
        """
        print(f"  [{self.company_name}] Fetching jobs from Greenhouse API...")

        try:
            response = self._make_request(self.base_url)
            data = response.json()
        except Exception as e:
            print(f"  [{self.company_name}] Error: {e}")
            return []

        jobs_data = data.get("jobs", [])
        print(f"  [{self.company_name}] Total jobs from API: {len(jobs_data)}")

        # Filter for Germany + ML/DS jobs
        all_jobs: list[Job] = []
        germany_count = 0

        for job_data in jobs_data:
            if self._is_germany_job(job_data):
                germany_count += 1
                if self._is_ml_ds_job(job_data):
                    job = self._parse_job(job_data)
                    all_jobs.append(job)

        print(f"  [{self.company_name}] Germany jobs: {germany_count}, ML/DS jobs: {len(all_jobs)}")

        # Sort by updated date (newest first)
        all_jobs.sort(key=lambda j: self._parse_date(j.updated_time), reverse=True)

        if max_results:
            all_jobs = all_jobs[:max_results]

        return all_jobs

    def _parse_job(self, data: dict) -> Job:
        """Parse raw job data into a Job object."""
        location = data.get("location", {}).get("name", "")

        return Job(
            id=str(data.get("id", "")),
            title=data.get("title", ""),
            company=self.company_name,
            url=data.get("absolute_url", ""),
            location=location,
            city=location.split(",")[0].strip() if location else "",
            country="Germany",
            posted_date=data.get("first_published"),
            updated_time=data.get("updated_at"),
            source=self.__class__.__name__,
        )

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> datetime:
        """Parse ISO 8601 date format for sorting."""
        if not date_str:
            return datetime(1900, 1, 1)
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            return datetime(1900, 1, 1)
