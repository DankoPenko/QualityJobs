"""Generic Personio Jobs scraper - works with any company using a Personio (jobs.personio.de) job board."""

import re
import xml.etree.ElementTree as ET
from typing import Optional
from datetime import datetime

from .base import BaseScraper
from models import Job


class PersonioScraper(BaseScraper):
    """
    Generic scraper for companies using Personio job boards.

    Personio publishes a public XML feed at:
        https://{slug}.jobs.personio.de/xml

    The feed contains every published position with its full description, so
    a single GET request returns everything we need.

    Usage:
        scraper = PersonioScraper(
            company_name="Pitch",
            board_slug="pitch",
            domain="pitch.com",
        )
    """

    GERMANY_CITIES = {
        "Berlin", "Munich", "München", "Hamburg", "Frankfurt", "Cologne", "Köln",
        "Düsseldorf", "Stuttgart", "Leipzig", "Dresden", "Hannover", "Nuremberg",
        "Nürnberg", "Bremen", "Heidelberg", "Karlsruhe", "Mannheim", "Aachen",
        "Bonn", "Freiburg", "Wiesbaden", "Augsburg", "Kiel", "Münster",
    }
    GERMANY_TERMS = ("germany", "deutschland")

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
        Initialize Personio scraper for a specific company.

        Args:
            company_name: Display name of the company
            board_slug: Personio subdomain (e.g., 'pitch', 'personio')
            domain: Company domain for logo (e.g., 'pitch.com')
        """
        self.company_name = company_name
        self.board_slug = board_slug
        self.domain = domain
        self.base_url = f"https://{board_slug}.jobs.personio.de/xml"
        super().__init__(**kwargs)

    @staticmethod
    def _text(element: Optional[ET.Element]) -> str:
        return (element.text or "").strip() if element is not None else ""

    def _is_ml_ds_job(self, position: ET.Element) -> bool:
        """Check if job is ML/DS related based on title and department."""
        title = self._text(position.find("name")).lower()
        dept = self._text(position.find("department")).lower()
        searchable = f"{title} {dept}"
        if any(kw in searchable for kw in self.EXCLUDE_KEYWORDS):
            return False
        return any(kw in searchable for kw in self.ML_DS_KEYWORDS)

    def _is_germany_job(self, position: ET.Element) -> bool:
        """Check if a job is located in Germany. Personio's <office> is free-form text,
        commonly a city ("Berlin"), city+country ("Berlin, Germany"), or full address."""
        office = self._text(position.find("office")).lower()
        if not office:
            return False
        if any(term in office for term in self.GERMANY_TERMS):
            return True
        return any(city.lower() in office for city in self.GERMANY_CITIES)

    def fetch_jobs(self, query: str = "data science", max_results: Optional[int] = None) -> list[Job]:
        """
        Fetch ML/DS jobs in Germany from a Personio XML feed.

        Returns:
            List of Job objects from Germany, sorted by created date (newest first)
        """
        print(f"  [{self.company_name}] Fetching jobs from Personio...")

        try:
            response = self._make_request(self.base_url)
            # Personio sometimes serves an HTML marketing page for invalid slugs;
            # parse only if the response actually looks like the XML feed.
            if not response.text.lstrip().startswith("<?xml"):
                print(f"  [{self.company_name}] Slug returned non-XML response - skipping")
                return []
            root = ET.fromstring(response.text)
        except Exception as e:
            print(f"  [{self.company_name}] Error: {e}")
            return []

        positions = root.findall("position")
        print(f"  [{self.company_name}] Total jobs from feed: {len(positions)}")

        all_jobs: list[Job] = []
        germany_count = 0
        for position in positions:
            if not self._is_germany_job(position):
                continue
            germany_count += 1
            if self._is_ml_ds_job(position):
                all_jobs.append(self._parse_job(position))

        print(f"  [{self.company_name}] Germany jobs: {germany_count}, ML/DS jobs: {len(all_jobs)}")

        all_jobs.sort(key=lambda j: self._parse_date(j.posted_date), reverse=True)
        if max_results:
            all_jobs = all_jobs[:max_results]
        return all_jobs

    def _parse_job(self, position: ET.Element) -> Job:
        """Parse a single <position> element into a Job object."""
        job_id = self._text(position.find("id"))
        title = self._text(position.find("name"))
        city = self._text(position.find("office")) or None
        department = self._text(position.find("department")) or None
        created = self._text(position.find("createdAt")) or None

        # Concatenate every <jobDescription>/<value> section into one description.
        description_parts: list[str] = []
        descriptions = position.find("jobDescriptions")
        if descriptions is not None:
            for jd in descriptions.findall("jobDescription"):
                section_name = self._text(jd.find("name"))
                section_value = self._text(jd.find("value"))
                if section_value:
                    description_parts.append(f"{section_name}\n{section_value}" if section_name else section_value)
        description = self._clean_html("\n\n".join(description_parts)) if description_parts else None

        return Job(
            id=job_id,
            title=title,
            company=self.company_name,
            url=f"https://{self.board_slug}.jobs.personio.de/job/{job_id}",
            location=city or "Germany",
            city=city,
            country="Germany",
            posted_date=created,
            updated_time=None,
            source=f"Personio:{self.board_slug}",
            domain=self.domain,
            department=department,
            description=description,
        )

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> datetime:
        """Parse Personio createdAt timestamp (ISO 8601 with timezone)."""
        if not date_str:
            return datetime(1900, 1, 1)
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            return datetime(1900, 1, 1)
