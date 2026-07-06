"""Scraper for Finanz Informatik (www.f-i.de).

F-I runs a bespoke Netgen/Ibexa careers site with no job sitemap, but every
job-detail page embeds a clean JSON-LD `JobPosting` block - exactly what
PhenomScraper's detail path already parses. So this subclasses PhenomScraper and
only overrides URL collection: the open positions are server-rendered as
`/karriere/offene-stellen/{city}/{slug}` links on the listing page.
"""

import re
from typing import Optional

from .phenom import PhenomScraper
from models import Job

LISTING_PATH = "/karriere/offene-stellen"
JOB_LINK_RE = re.compile(r'href="(/karriere/offene-stellen/[a-z0-9-]+/[a-z0-9-]+)"')


class FinanzInformatikScraper(PhenomScraper):
    """
    Usage:
        scraper = FinanzInformatikScraper()  # host/name/domain are fixed
    """

    def __init__(self, **kwargs):
        super().__init__(
            company_name="Finanz Informatik",
            host="www.f-i.de",
            domain="f-i.de",
            **kwargs,
        )

    def fetch_jobs(self, query: str = "machine learning", max_results: Optional[int] = None) -> list[Job]:
        print(f"  [{self.company_name}] Fetching jobs from careers listing...")
        try:
            body = self._make_request(f"{self.base_url}{LISTING_PATH}").text
        except Exception as e:
            print(f"  [{self.company_name}] Error fetching listing: {e}")
            return []

        paths = sorted(set(JOB_LINK_RE.findall(body)))
        job_urls = [f"{self.base_url}{p}" for p in paths]
        print(f"  [{self.company_name}] Listed jobs: {len(job_urls)}")

        jobs = self._scrape_job_url_list(job_urls)
        jobs.sort(key=lambda j: self._parse_date(j.posted_date), reverse=True)
        if max_results:
            jobs = jobs[:max_results]
        return jobs

    def _build_job_jsonld(self, posting: dict, url: str, location_node: dict) -> Job:
        job = super()._build_job_jsonld(posting, url, location_node)
        job.source = f"F-I:{self.host}"
        return job
