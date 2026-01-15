"""Generic SmartRecruiters Jobs scraper - works with any company using SmartRecruiters."""

from typing import Optional
from datetime import datetime

from .base import BaseScraper
from models import Job


class SmartRecruitersScraper(BaseScraper):
    """
    Generic scraper for companies using SmartRecruiters job boards.

    Usage:
        scraper = SmartRecruitersScraper(
            company_name="Delivery Hero",
            company_slug="DeliveryHero",
            domain="deliveryhero.com"
        )
    """

    # Germany cities to filter by
    GERMANY_CITIES = {"Berlin", "Munich", "Hamburg", "Frankfurt", "Cologne", "Stuttgart"}

    # Keywords for ML/DS job filtering
    ML_DS_KEYWORDS = [
        "machine learning", "data scien", "data engineer", "data analyst",
        "ml ", " ml", "ai ", " ai", "deep learning", "nlp",
        "computer vision", "analytics", "neural", "llm",
        "research scientist", "applied scientist"
    ]

    def __init__(self, company_name: str, company_slug: str, domain: str = "", **kwargs):
        """
        Initialize SmartRecruiters scraper for a specific company.

        Args:
            company_name: Display name of the company
            company_slug: SmartRecruiters company ID (e.g., 'DeliveryHero', 'AUTO1Group')
            domain: Company domain for logo (e.g., 'deliveryhero.com')
        """
        self.company_name = company_name
        self.company_slug = company_slug
        self.domain = domain
        self.base_url = f"https://api.smartrecruiters.com/v1/companies/{company_slug}/postings"
        super().__init__(**kwargs)

    def _is_ml_ds_job(self, job_data: dict) -> bool:
        """Check if job is ML/DS related based on title and department."""
        title = job_data.get("name", "").lower()
        department = job_data.get("department", {})
        dept_name = department.get("label", "").lower() if department else ""

        searchable = f"{title} {dept_name}"
        return any(kw in searchable for kw in self.ML_DS_KEYWORDS)

    def _is_germany_job(self, job_data: dict) -> bool:
        """Check if job is in Germany."""
        location = job_data.get("location", {})
        country = location.get("country", "")
        city = location.get("city", "")

        return "Germany" in country or city in self.GERMANY_CITIES

    def fetch_jobs(self, query: str = "data science", max_results: Optional[int] = None) -> list[Job]:
        """
        Fetch ML/DS jobs from SmartRecruiters API.

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
        filtered_jobs = []

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
                if self._is_germany_job(job_data):
                    germany_count += 1
                    if self._is_ml_ds_job(job_data):
                        filtered_jobs.append(job_data)

            total_found = data.get("totalFound", 0)
            print(f"  [{self.company_name}] Processed {min(offset + limit, total_found)}/{total_found} jobs")

            if offset + limit >= total_found:
                break

            offset += limit

        print(f"  [{self.company_name}] Germany jobs: {germany_count}, ML/DS jobs: {len(filtered_jobs)}")

        # Fetch descriptions for filtered jobs
        if filtered_jobs:
            print(f"  [{self.company_name}] Fetching descriptions for {len(filtered_jobs)} jobs...")
        for job_data in filtered_jobs:
            description = self._fetch_job_description(job_data.get("id", ""))
            job = self._parse_job(job_data, description)
            all_jobs.append(job)

        # Sort by posted date (newest first)
        all_jobs.sort(key=lambda j: self._parse_date(j.posted_date), reverse=True)

        if max_results:
            all_jobs = all_jobs[:max_results]

        return all_jobs

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
            url=f"https://careers.smartrecruiters.com/{self.company_slug}/{data.get('id', '')}",
            location=f"{location.get('city', '')}, {location.get('country', '')}",
            city=location.get("city"),
            country=location.get("country", "Germany"),
            posted_date=data.get("releasedDate"),
            updated_time=None,
            source=f"SmartRecruiters:{self.company_slug}",
            department=department.get("label") if department else None,
            description=description,
        )

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> datetime:
        """Parse SmartRecruiters date format (ISO 8601) for sorting."""
        if not date_str:
            return datetime(1900, 1, 1)
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            return datetime(1900, 1, 1)
