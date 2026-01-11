"""Zalando Jobs scraper - parses job listings from HTML."""

import re
from typing import Optional
from datetime import datetime

from .base import BaseScraper
from models import Job


class ZalandoScraper(BaseScraper):
    """
    Scraper for Zalando Jobs.

    Zalando uses React Server Components, so we parse job data directly from HTML.
    """

    company_name = "Zalando"
    base_url = "https://jobs.zalando.com/en/jobs"

    def fetch_jobs(self, query: str = "data science", max_results: Optional[int] = None) -> list[Job]:
        """
        Fetch ML/DS jobs from Zalando's careers page.

        Returns:
            List of Job objects from Germany
        """
        print(f"  [{self.company_name}] Fetching jobs from careers page...")

        # Fetch page with ML/DS category filters
        url = f"{self.base_url}?category=Applied+Science+%26+Research&category=Software+Engineering+-+Data"
        response = self._make_request(url)
        html = response.text

        # Extract job titles from h2 tags
        titles = re.findall(r'<h2 class="font-bold">(.*?)</h2>', html)

        # Extract job links (href to individual job pages)
        links = re.findall(r'href="(/en/jobs/\d+[^"]*)"', html)

        # Extract categories (shown below titles)
        categories = re.findall(r'<p class="text-primary-black-60 leading-8">(.*?)</p>', html)

        print(f"  [{self.company_name}] Found {len(titles)} jobs")

        all_jobs: list[Job] = []

        for i, title in enumerate(titles):
            # Clean HTML entities
            title = title.replace('&amp;', '&')

            # Get link if available
            link = links[i] if i < len(links) else None
            job_url = f"https://jobs.zalando.com{link}" if link else self.base_url

            # Extract job ID from link
            job_id = ""
            if link:
                id_match = re.search(r'/jobs/(\d+)', link)
                if id_match:
                    job_id = id_match.group(1)

            # Get category/department
            department = categories[i].replace('&amp;', '&') if i < len(categories) else None

            job = Job(
                id=job_id,
                title=title,
                company=self.company_name,
                url=job_url,
                location="Berlin, Germany",
                city="Berlin",
                country="Germany",
                posted_date=None,
                updated_time=None,
                source=self.__class__.__name__,
                department=department,
            )
            all_jobs.append(job)

        if max_results:
            all_jobs = all_jobs[:max_results]

        return all_jobs
