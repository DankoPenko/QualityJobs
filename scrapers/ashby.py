"""Generic Ashby Jobs scraper - works with any company using an Ashby (jobs.ashbyhq.com) job board."""

from typing import Optional
from datetime import datetime

from .base import BaseScraper
from models import Job


class AshbyScraper(BaseScraper):
    """
    Generic scraper for companies using Ashby job boards (jobs.ashbyhq.com).

    Ashby exposes a public posting API that returns every listed job - including
    the full description - in a single request:
        GET https://api.ashbyhq.com/posting-api/job-board/{slug}

    Usage:
        scraper = AshbyScraper(
            company_name="DeepL",
            board_slug="DeepL",
            domain="deepl.com",
        )
    """

    GERMANY_TERMS = [
        "germany", "deutschland", "berlin", "munich", "münchen", "hamburg",
        "frankfurt", "köln", "cologne", "düsseldorf", "stuttgart", "heidelberg",
    ]

    # Keywords for ML/DS job filtering
    ML_DS_KEYWORDS = [
        "machine learning", "data scien", "data engineer", "data analyst",
        "ml ", " ml,", " ml ", "(ml)", "deep learning", "nlp",
        "computer vision", "neural", "llm", "genai", "gen ai",
        "research scientist", "applied scientist", "artificial intelligence",
        "ai research", "ai engineer", "reinforcement learning"
    ]

    # Keywords that indicate NOT an ML/DS job (to filter out false positives)
    EXCLUDE_KEYWORDS = [
        "site reliability", "sre ", "devops",
        "frontend", "front-end", "backend", "back-end", "fullstack",
        "network engineer", "security engineer", "platform engineer"
    ]

    def __init__(self, company_name: str, board_slug: str, domain: str = "", **kwargs):
        """
        Initialize Ashby scraper for a specific company.

        Args:
            company_name: Display name of the company
            board_slug: Ashby job board id (e.g., 'DeepL', 'AlephAlpha')
            domain: Company domain for logo (e.g., 'deepl.com')
        """
        self.company_name = company_name
        self.board_slug = board_slug
        self.domain = domain
        self.base_url = f"https://api.ashbyhq.com/posting-api/job-board/{board_slug}"
        super().__init__(**kwargs)

    def _is_ml_ds_job(self, job_data: dict) -> bool:
        """Check if job is ML/DS related based on title and department/team."""
        title = job_data.get("title", "").lower()
        dept = f"{job_data.get('department', '')} {job_data.get('team', '')}".lower()
        searchable = f"{title} {dept}"
        if any(kw in searchable for kw in self.EXCLUDE_KEYWORDS):
            return False
        return any(kw in searchable for kw in self.ML_DS_KEYWORDS)

    def _is_germany_job(self, job_data: dict) -> bool:
        """Check if a job is located in Germany."""
        country = (
            job_data.get("address", {})
            .get("postalAddress", {})
            .get("addressCountry", "")
        )
        if country.strip().lower() in ("germany", "deutschland"):
            return True
        # Fall back to the location string and any secondary locations.
        locations = [job_data.get("location", "")]
        for sec in job_data.get("secondaryLocations") or []:
            locations.append(sec if isinstance(sec, str) else sec.get("location", ""))
        text = " ".join(locations).lower()
        return any(term in text for term in self.GERMANY_TERMS)

    def fetch_jobs(self, query: str = "data science", max_results: Optional[int] = None) -> list[Job]:
        """
        Fetch ML/DS jobs in Germany from an Ashby job board.

        Returns:
            List of Job objects from Germany, sorted by published date (newest first)
        """
        print(f"  [{self.company_name}] Fetching jobs from Ashby...")

        try:
            response = self._make_request(self.base_url)
            jobs_data = response.json().get("jobs", [])
        except Exception as e:
            print(f"  [{self.company_name}] Error: {e}")
            return []

        print(f"  [{self.company_name}] Total jobs from API: {len(jobs_data)}")

        all_jobs: list[Job] = []
        germany_count = 0
        for job_data in jobs_data:
            if not job_data.get("isListed", True):
                continue
            if not self._is_germany_job(job_data):
                continue
            germany_count += 1
            if self._is_ml_ds_job(job_data):
                all_jobs.append(self._parse_job(job_data))

        print(f"  [{self.company_name}] Germany jobs: {germany_count}, ML/DS jobs: {len(all_jobs)}")

        all_jobs.sort(key=lambda j: self._parse_date(j.posted_date), reverse=True)
        if max_results:
            all_jobs = all_jobs[:max_results]
        return all_jobs

    def _parse_job(self, data: dict) -> Job:
        """Parse raw Ashby API data into a Job object."""
        postal = data.get("address", {}).get("postalAddress", {})
        city = postal.get("addressLocality") or data.get("location", "")
        location = data.get("location", "") or city
        description = self._clean_html(data.get("descriptionHtml", "")) or None

        return Job(
            id=str(data.get("id", "")),
            title=data.get("title", ""),
            company=self.company_name,
            url=data.get("jobUrl", "") or data.get("applyUrl", ""),
            location=location,
            city=city.strip() or None,
            country="Germany",
            posted_date=data.get("publishedAt"),
            updated_time=None,
            source=f"Ashby:{self.board_slug}",
            domain=self.domain,
            department=data.get("department"),
            description=description,
        )

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> datetime:
        """Parse Ashby date format (ISO 8601) for sorting."""
        if not date_str:
            return datetime(1900, 1, 1)
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            return datetime(1900, 1, 1)
