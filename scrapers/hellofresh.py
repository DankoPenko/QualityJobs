"""HelloFresh Jobs scraper - parses embedded DDO data from Phenom platform."""

import re
import json
from typing import Optional
from datetime import datetime

from .base import BaseScraper
from models import Job


class HelloFreshScraper(BaseScraper):
    """
    Scraper for HelloFresh Jobs.

    HelloFresh uses Phenom People platform with embedded DDO data.
    Only initial page load jobs are available without JavaScript.
    """

    company_name = "HelloFresh"
    # Filter by Data category directly in URL
    base_url = "https://careers.hellofresh.com/global/en/germany?category=Data"

    def fetch_jobs(self, query: str = "data science", max_results: Optional[int] = None) -> list[Job]:
        """
        Fetch Data category jobs from HelloFresh careers page.

        Returns:
            List of Job objects from Germany in Data category
        """
        print(f"  [{self.company_name}] Fetching Data category jobs...")

        try:
            response = self._make_request(self.base_url)
            html = response.text
        except Exception as e:
            print(f"  [{self.company_name}] Error fetching page: {e}")
            return []

        # Parse the phApp.ddo object
        jobs_data = self._parse_ddo(html)
        print(f"  [{self.company_name}] Data jobs found: {len(jobs_data)}")

        # All jobs from this URL are already Data category
        all_jobs: list[Job] = []
        for job_data in jobs_data:
            job = self._parse_job(job_data)
            all_jobs.append(job)

        # Sort by posted date (newest first)
        all_jobs.sort(key=lambda j: self._parse_date(j.posted_date), reverse=True)

        if max_results:
            all_jobs = all_jobs[:max_results]

        return all_jobs

    def _parse_ddo(self, html: str) -> list[dict]:
        """Parse the phApp.ddo JavaScript object from HTML."""
        ddo_start = html.find('phApp.ddo')
        if ddo_start < 0:
            return []

        obj_start = html.find('{', ddo_start)
        if obj_start < 0:
            return []

        # Find matching closing brace
        depth = 0
        end = obj_start
        for i, c in enumerate(html[obj_start:obj_start + 200000]):
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    end = obj_start + i + 1
                    break

        try:
            ddo = json.loads(html[obj_start:end])
            jobs = ddo.get('eagerLoadRefineSearch', {}).get('data', {}).get('jobs', [])
            return jobs
        except json.JSONDecodeError:
            return []

    def _parse_job(self, data: dict) -> Job:
        """Parse raw job data into a Job object."""
        city = data.get("city", "")
        state = data.get("state", "")
        country = data.get("country", "Germany")

        location = data.get("cityStateCountry", f"{city}, {state}, {country}")

        return Job(
            id=str(data.get("jobId", "")),
            title=data.get("title", ""),
            company=self.company_name,
            url=data.get("applyUrl", f"https://careers.hellofresh.com/global/en/job/{data.get('jobId', '')}"),
            location=location,
            city=city,
            country=country,
            posted_date=data.get("postedDate"),
            updated_time=data.get("dateCreated"),
            source=self.__class__.__name__,
            department=data.get("category"),
            description=data.get("descriptionTeaser"),
        )

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> datetime:
        """Parse date string for sorting."""
        if not date_str:
            return datetime(1900, 1, 1)
        try:
            # Phenom uses format like "January 6, 2025"
            return datetime.strptime(date_str, "%B %d, %Y")
        except ValueError:
            try:
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except ValueError:
                return datetime(1900, 1, 1)
