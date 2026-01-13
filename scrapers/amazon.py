"""Amazon Jobs scraper."""

from typing import Optional
from datetime import datetime

from .base import BaseScraper
from models import Job


class AmazonScraper(BaseScraper):
    """
    Scraper for Amazon Jobs.

    Uses Amazon's public JSON API at amazon.jobs/en/search.json
    Key parameter: normalized_country_code[]=DEU for Germany filtering
    """

    company_name = "Amazon"
    base_url = "https://www.amazon.jobs/en/search.json"

    def fetch_jobs(self, query: str = "machine learning", max_results: Optional[int] = None) -> list[Job]:
        """
        Fetch jobs from Amazon's career API.

        Args:
            query: Search query (e.g., "machine learning", "data scientist")
            max_results: Maximum number of jobs to fetch (None for all)

        Returns:
            List of Job objects, sorted by posted date (newest first)
        """
        all_jobs: list[Job] = []
        offset = 0
        limit = 100  # Max per request

        while True:
            print(f"  [{self.company_name}] Fetching jobs at offset {offset}...")

            try:
                data = self._fetch_page(query, offset, limit)
            except Exception as e:
                print(f"  [{self.company_name}] Error: {e}")
                break

            jobs_data = data.get("jobs", [])

            if not jobs_data:
                break

            for job_data in jobs_data:
                job = self._parse_job(job_data)
                all_jobs.append(job)

            print(f"  [{self.company_name}] Found {len(jobs_data)} jobs in this batch")

            # Check limits
            if max_results and len(all_jobs) >= max_results:
                all_jobs = all_jobs[:max_results]
                break

            total_hits = data.get("hits", 0)
            if offset + limit >= total_hits:
                print(f"  [{self.company_name}] Reached end (total: {total_hits})")
                break

            offset += limit

        # Sort by posted date (newest first)
        all_jobs.sort(key=lambda j: self._parse_date(j.posted_date), reverse=True)

        return all_jobs

    def _fetch_page(self, query: str, offset: int, limit: int) -> dict:
        """Fetch a single page of results from the API."""
        params = {
            "base_query": query,
            "normalized_country_code[]": self.country_code,
            "offset": offset,
            "result_limit": limit,
            "sort": "recent",
        }

        response = self._make_request(self.base_url, params=params)
        return response.json()

    def _parse_job(self, data: dict) -> Job:
        """Parse raw API data into a Job object."""
        job_id = data.get("id_icims", "")

        return Job(
            id=job_id,
            title=data.get("title", ""),
            company=self.company_name,
            url=f"https://www.amazon.jobs/en/jobs/{job_id}",
            location=data.get("location", ""),
            city=data.get("city"),
            country="Germany" if self.country_code == "DEU" else self.country_code,
            posted_date=data.get("posted_date"),
            updated_time=data.get("updated_time"),
            source=self.__class__.__name__,
            job_type=data.get("job_schedule_type"),
            description=data.get("description"),
        )

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> datetime:
        """Parse Amazon's date format for sorting."""
        if not date_str:
            return datetime(1900, 1, 1)
        try:
            return datetime.strptime(date_str, "%B %d, %Y")
        except ValueError:
            return datetime(1900, 1, 1)
