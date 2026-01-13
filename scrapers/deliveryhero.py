"""Delivery Hero Jobs scraper using SmartRecruiters API."""

from typing import Optional
from datetime import datetime

from .base import BaseScraper
from models import Job


class DeliveryHeroScraper(BaseScraper):
    """
    Scraper for Delivery Hero Jobs.

    Uses SmartRecruiters API at api.smartrecruiters.com
    """

    company_name = "Delivery Hero"
    base_url = "https://api.smartrecruiters.com/v1/companies/DeliveryHero/postings"

    # Germany cities to filter by
    GERMANY_CITIES = {"Berlin", "Munich", "Hamburg", "Frankfurt", "Cologne", "Stuttgart"}

    # Keywords for ML/DS job filtering
    ML_DS_KEYWORDS = [
        "machine learning", "data scien", "data engineer", "data analyst",
        "ml ", " ml", "ai ", " ai", "deep learning", "nlp",
        "computer vision", "analytics", "neural", "llm",
        "research scientist", "applied scientist"
    ]

    def _is_ml_ds_job(self, job_data: dict) -> bool:
        """Check if job is ML/DS related based on title and department."""
        title = job_data.get("name", "").lower()
        department = job_data.get("department", {})
        dept_name = department.get("label", "").lower() if department else ""

        # Combine title and department for matching
        searchable = f"{title} {dept_name}"

        return any(kw in searchable for kw in self.ML_DS_KEYWORDS)

    def fetch_jobs(self, query: str = "data science", max_results: Optional[int] = None) -> list[Job]:
        """
        Fetch ML/DS jobs from Delivery Hero's SmartRecruiters API.

        Args:
            query: Search query (used for filtering results)
            max_results: Maximum number of jobs to fetch (None for all)

        Returns:
            List of Job objects from Germany, sorted by posted date (newest first)
        """
        all_jobs: list[Job] = []
        offset = 0
        limit = 100
        germany_count = 0

        print(f"  [{self.company_name}] Fetching all jobs...")

        while True:
            try:
                data = self._fetch_page(offset, limit)
            except Exception as e:
                print(f"  [{self.company_name}] Error: {e}")
                break

            content = data.get("content", [])

            if not content:
                break

            # Filter for Germany + ML/DS jobs
            for job_data in content:
                location = job_data.get("location", {})
                country = location.get("country", "")
                city = location.get("city", "")

                # Check if job is in Germany
                is_germany = (
                    "Germany" in country or
                    city in self.GERMANY_CITIES
                )

                if is_germany:
                    germany_count += 1
                    # Also check if it's ML/DS related
                    if self._is_ml_ds_job(job_data):
                        all_jobs.append(job_data)

            total_found = data.get("totalFound", 0)
            print(f"  [{self.company_name}] Processed {min(offset + limit, total_found)}/{total_found} jobs")

            if offset + limit >= total_found:
                break

            offset += limit

        print(f"  [{self.company_name}] Germany jobs: {germany_count}, ML/DS jobs: {len(all_jobs)}")

        # Fetch descriptions for filtered jobs
        print(f"  [{self.company_name}] Fetching descriptions for {len(all_jobs)} jobs...")
        parsed_jobs: list[Job] = []
        for job_data in all_jobs:
            description = self._fetch_job_description(job_data.get("id", ""))
            job = self._parse_job(job_data, description)
            parsed_jobs.append(job)

        # Sort by posted date (newest first)
        parsed_jobs.sort(key=lambda j: self._parse_date(j.posted_date), reverse=True)

        if max_results:
            parsed_jobs = parsed_jobs[:max_results]

        return parsed_jobs

    def _fetch_page(self, offset: int, limit: int) -> dict:
        """Fetch a single page of results from the API."""
        params = {
            "offset": offset,
            "limit": limit,
        }

        response = self._make_request(self.base_url, params=params)
        return response.json()

    def _fetch_job_description(self, job_id: str) -> Optional[str]:
        """Fetch full job description from the job detail API."""
        if not job_id:
            return None
        try:
            url = f"{self.base_url}/{job_id}"
            response = self._make_request(url)
            data = response.json()
            # Extract description from jobAd sections
            job_ad = data.get("jobAd", {})
            sections = job_ad.get("sections", {})
            job_desc = sections.get("jobDescription", {})
            description_html = job_desc.get("text", "")
            if description_html:
                return self._clean_html(description_html)
        except Exception:
            pass
        return None

    def _parse_job(self, data: dict, description: Optional[str] = None) -> Job:
        """Parse raw API data into a Job object."""
        location = data.get("location", {})
        department = data.get("department", {})

        return Job(
            id=data.get("id", ""),
            title=data.get("name", ""),
            company=self.company_name,
            url=f"https://careers.smartrecruiters.com/DeliveryHero/{data.get('id', '')}",
            location=f"{location.get('city', '')}, {location.get('country', '')}",
            city=location.get("city"),
            country=location.get("country", "Germany"),
            posted_date=data.get("releasedDate"),
            updated_time=None,  # SmartRecruiters doesn't provide this
            source=self.__class__.__name__,
            department=department.get("label") if department else None,
            description=description,
        )

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> datetime:
        """Parse SmartRecruiters date format (ISO 8601) for sorting."""
        if not date_str:
            return datetime(1900, 1, 1)
        try:
            # Format: 2025-01-08T10:30:00.000Z
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            return datetime(1900, 1, 1)
