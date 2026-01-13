"""AUTO1 Group Jobs scraper - uses SmartRecruiters API."""

from typing import Optional
from datetime import datetime

from .base import BaseScraper
from models import Job


class Auto1Scraper(BaseScraper):
    """
    Scraper for AUTO1 Group Jobs.

    AUTO1 uses SmartRecruiters with company name 'auto1'.
    Uses search query to pre-filter, then keyword matching for ML/DS roles.
    """

    company_name = "AUTO1 Group"
    base_url = "https://api.smartrecruiters.com/v1/companies/auto1/postings"

    # Keywords for ML/DS job filtering
    ML_DS_KEYWORDS = [
        "machine learning", "data scien", "data engineer", "data analyst",
        "ml ", " ml", "mlops", "ai ", " ai", "deep learning", "nlp",
        "computer vision", "analytics", "neural", "llm",
        "research scientist", "applied scientist", "business analyst"
    ]

    def _is_ml_ds_job(self, job_data: dict) -> bool:
        """Check if job is ML/DS related based on title."""
        title = job_data.get("name", "").lower()
        return any(kw in title for kw in self.ML_DS_KEYWORDS)

    def fetch_jobs(self, query: str = "data science", max_results: Optional[int] = None) -> list[Job]:
        """
        Fetch ML/DS jobs from AUTO1's SmartRecruiters board.

        Returns:
            List of Job objects from Germany, filtered for ML/DS roles
        """
        print(f"  [{self.company_name}] Fetching jobs from SmartRecruiters API...")

        all_jobs: list[Job] = []

        try:
            # Use search query to pre-filter
            params = {
                "q": "Data Science",
                "limit": 100,
            }
            response = self._make_request(self.base_url, params=params)
            data = response.json()
        except Exception as e:
            print(f"  [{self.company_name}] Error: {e}")
            return []

        jobs_data = data.get("content", [])
        total = data.get("totalFound", 0)
        print(f"  [{self.company_name}] Search results: {total} jobs")

        # Filter for Germany + ML/DS jobs
        germany_count = 0
        filtered_jobs = []
        for job_data in jobs_data:
            country = job_data.get("location", {}).get("country", "")

            if country == "de":
                germany_count += 1
                if self._is_ml_ds_job(job_data):
                    filtered_jobs.append(job_data)

        print(f"  [{self.company_name}] Germany jobs: {germany_count}, ML/DS jobs: {len(filtered_jobs)}")

        # Fetch descriptions for filtered jobs
        print(f"  [{self.company_name}] Fetching descriptions for {len(filtered_jobs)} jobs...")
        for job_data in filtered_jobs:
            description = self._fetch_job_description(job_data.get("id", ""))
            job = self._parse_job(job_data, description)
            all_jobs.append(job)

        # Sort by released date (newest first)
        all_jobs.sort(key=lambda j: self._parse_date(j.posted_date), reverse=True)

        if max_results:
            all_jobs = all_jobs[:max_results]

        return all_jobs

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
        """Parse raw job data into a Job object."""
        location = data.get("location", {})
        city = location.get("city", "")
        country = "Germany"

        return Job(
            id=str(data.get("id", "")),
            title=data.get("name", ""),
            company=self.company_name,
            url=f"https://www.auto1-group.com/jobs/{data.get('id', '')}",
            location=location.get("fullLocation", f"{city}, {country}"),
            city=city,
            country=country,
            posted_date=data.get("releasedDate"),
            updated_time=None,
            source=self.__class__.__name__,
            department=data.get("department", {}).get("label"),
            description=description,
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
