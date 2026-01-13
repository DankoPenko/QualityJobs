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
            jobs_data = self._extract_jobs_data(html)

            if not jobs_data:
                break

            all_jobs.extend(jobs_data)
            print(f"  [{self.company_name}] Fetched {len(all_jobs)} jobs...")

            # Check if there are more pages
            if len(jobs_data) < page_size:
                break

            offset += page_size

            # Safety limit
            if offset >= 200:
                break

        print(f"  [{self.company_name}] Total jobs found: {len(all_jobs)}")

        # Fetch descriptions for each job
        print(f"  [{self.company_name}] Fetching descriptions for {len(all_jobs)} jobs...")
        final_jobs: list[Job] = []
        for job_data in all_jobs:
            description = self._fetch_job_description(job_data["url"])
            job = Job(
                id=job_data["id"],
                title=job_data["title"],
                company=self.company_name,
                url=job_data["url"],
                location=job_data["location"],
                city=job_data["city"],
                country="Germany",
                posted_date=job_data["posted_date"],
                updated_time=None,
                source=self.__class__.__name__,
                description=description,
            )
            final_jobs.append(job)
        all_jobs = final_jobs

        if max_results:
            all_jobs = all_jobs[:max_results]

        return all_jobs

    def _extract_jobs_data(self, html: str) -> list[dict]:
        """Extract job data from HTML page."""
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

                jobs.append({
                    "id": job_id,
                    "title": title,
                    "url": f"https://jobs.sap.com{link}",
                    "location": location,
                    "city": city,
                    "posted_date": date,
                })

        return jobs

    def _fetch_job_description(self, job_url: str) -> Optional[str]:
        """Fetch job description from individual job page."""
        if not job_url:
            return None
        try:
            response = self._make_request(job_url)
            html = response.text
            # SAP SuccessFactors pages have job content in joblayouttoken divs
            # Find the section starting from "What you'll do" or similar
            start_idx = -1
            for marker in ["What you'll do", "What you will do", "About the team", "Your responsibilities"]:
                idx = html.find(marker)
                if idx > 0:
                    start_idx = idx
                    break

            if start_idx > 0:
                # Extract from marker to end of job content section
                # Look backwards for the containing div
                section_start = html.rfind('<div class="joblayouttoken', max(0, start_idx - 500), start_idx)
                if section_start < 0:
                    section_start = start_idx - 100

                # Find a reasonable end point
                end_markers = ['<div class="applylink"', '<footer', '<div class="job-details"']
                section_end = len(html)
                for marker in end_markers:
                    idx = html.find(marker, start_idx)
                    if idx > 0 and idx < section_end:
                        section_end = idx

                content = html[section_start:section_end]
                return self._clean_html(content)
        except Exception:
            pass
        return None
