"""SAP Jobs scraper - parses HTML from SuccessFactors job board."""

import re
from typing import Optional
from datetime import datetime
from html import unescape

from .base import BaseScraper
from models import Job


class SAPScraper(BaseScraper):
    """
    Scraper for SAP Jobs.

    SAP uses SuccessFactors job board with HTML rendering.
    """

    company_name = "SAP"
    base_url = "https://jobs.sap.com/search/"

    def fetch_jobs(self, query: str = "data science", max_results: Optional[int] = None) -> list[Job]:
        """
        Fetch ML/DS jobs from SAP careers page.

        Returns:
            List of Job objects from Germany in Software-Development Operations
        """
        print(f"  [{self.company_name}] Fetching jobs from SuccessFactors...")

        all_jobs: list[Job] = []
        offset = 0
        page_size = 25

        while True:
            params = {
                "q": "data science",
                "optionsFacetsDD_country": "DE",
                "optionsFacetsDD_department": "Software-Development Operations",
                "startrow": offset,
            }

            try:
                response = self._make_request(self.base_url, params=params)
                html = response.text
            except Exception as e:
                print(f"  [{self.company_name}] Error: {e}")
                break

            # Extract jobs from this page
            jobs = self._extract_jobs(html)

            if not jobs:
                break

            all_jobs.extend(jobs)
            print(f"  [{self.company_name}] Fetched {len(all_jobs)} jobs...")

            # Check if there are more pages
            if len(jobs) < page_size:
                break

            offset += page_size

            # Safety limit
            if offset >= 200:
                break

        print(f"  [{self.company_name}] Total jobs found: {len(all_jobs)}")

        if max_results:
            all_jobs = all_jobs[:max_results]

        return all_jobs

    def _extract_jobs(self, html: str) -> list[Job]:
        """Extract jobs from HTML page."""
        jobs = []

        # Find all job rows
        rows = re.findall(r'<tr[^>]*data-row[^>]*>(.*?)</tr>', html, re.DOTALL)

        for row in rows:
            title_match = re.search(r'class="jobTitle-link"[^>]*>([^<]+)</a>', row)
            link_match = re.search(r'href="(/job/[^"]+)"', row)
            loc_match = re.search(r'class="jobLocation"[^>]*>([^<]+)</span>', row)
            date_match = re.search(r'class="jobDate"[^>]*>([^<]+)</span>', row)

            if title_match and link_match:
                title = unescape(title_match.group(1).strip())
                link = link_match.group(1)
                location = unescape(loc_match.group(1).strip()) if loc_match else ""
                date = date_match.group(1).strip() if date_match else None

                # Extract city from location (format: "City, DE, PostalCode")
                city = location.split(",")[0].strip() if location else ""

                # Extract job ID from link
                job_id_match = re.search(r'/(\d+)/?$', link)
                job_id = job_id_match.group(1) if job_id_match else ""

                job = Job(
                    id=job_id,
                    title=title,
                    company=self.company_name,
                    url=f"https://jobs.sap.com{link}",
                    location=location,
                    city=city,
                    country="Germany",
                    posted_date=date,
                    updated_time=None,
                    source=self.__class__.__name__,
                )
                jobs.append(job)

        return jobs
