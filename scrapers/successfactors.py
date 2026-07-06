"""Generic scraper for SAP SuccessFactors "Career Site Builder" career pages.

These sites (e.g. karriere.nordlb.de) serve a Google `<urlset>` sitemap of
`/{COMPANY}/job/{City-Title-...}/{id}/` URLs, and each detail page describes the
posting with schema.org **microdata** (itemprop/itemscope) rather than the
JSON-LD block Phenom tenants use. Everything else - the ML/DS keyword filter,
the Germany filter, the Job construction - is identical to Phenom, so this
subclasses PhenomScraper and only swaps in a microdata parser.
"""

import re
from typing import Optional
from urllib.parse import unquote
from datetime import datetime

from .phenom import PhenomScraper


class SuccessFactorsScraper(PhenomScraper):
    """
    Scraper for SuccessFactors Career Site Builder tenants.

    Usage:
        scraper = SuccessFactorsScraper(
            company_name="NORD/LB",
            host="karriere.nordlb.de",
            domain="nordlb.de",
        )
    """

    # Suffixes SuccessFactors appends to the <title> of a job-detail page.
    _TITLE_SUFFIXES = ("Stellendetails", "Job Details", "Jobdetails")

    @staticmethod
    def _slug_text(url: str) -> str:
        """SuccessFactors URLs are '/{COMPANY}/job/{City-Title-...}/{id}/', so the
        readable title slug is the *second-to-last* path segment (the last is the
        numeric id)."""
        parts = url.rstrip("/").split("/")
        slug = parts[-2] if len(parts) >= 2 else parts[-1]
        return unquote(slug).replace("-", " ")

    def _fetch_job_posting(self, url: str) -> Optional[dict]:
        """Fetch a detail page and shape its schema.org microdata into the same
        dict layout PhenomScraper's JSON-LD path expects."""
        try:
            body = self._make_request(url).text
        except Exception:
            return None

        block_start = body.find('itemtype="http://schema.org/JobPosting"')
        if block_start == -1:
            block_start = body.find('itemtype="https://schema.org/JobPosting"')
        if block_start == -1:
            return None
        block = body[block_start:]

        def meta(prop: str) -> Optional[str]:
            m = re.search(
                r'itemprop="%s"[^>]*content="([^"]*)"' % re.escape(prop), block
            )
            return m.group(1).strip() if m else None

        address = {
            "addressLocality": meta("addressLocality"),
            "addressRegion": meta("addressRegion"),
            "addressCountry": meta("addressCountry"),
        }

        job_id = url.rstrip("/").rsplit("/", 1)[-1]

        return {
            "@type": "JobPosting",
            "title": self._title_from_html(body, url),
            "datePosted": self._normalise_date(meta("datePosted")),
            "identifier": {"value": job_id},
            "jobLocation": {"address": address},
            "description": self._description_from_html(body),
        }

    def _title_from_html(self, body: str, url: str) -> str:
        m = re.search(r"<title>(.*?)</title>", body, re.DOTALL)
        if not m:
            return self._slug_text(url).strip()
        title = m.group(1).split("|", 1)[0].strip()
        for suffix in self._TITLE_SUFFIXES:
            if title.endswith(suffix):
                title = title[: -len(suffix)].strip()
        return title or self._slug_text(url).strip()

    @staticmethod
    def _description_from_html(body: str) -> Optional[str]:
        """Grab the itemprop='description' region. Nested markup makes an exact
        close-tag match unreliable, so take a generous slice (starting after the
        opening tag) and let BaseScraper._clean_html strip tags and truncate."""
        idx = body.find('itemprop="description"')
        if idx == -1:
            return None
        content_start = body.find(">", idx)
        if content_start == -1:
            return None
        return body[content_start + 1:content_start + 1 + 8000]

    @staticmethod
    def _normalise_date(raw: Optional[str]) -> Optional[str]:
        """SuccessFactors stamps dates like 'Fri Jul 03 02:00:00 UTC 2026'.
        Convert to ISO so the parent's date sort works; fall back to raw."""
        if not raw:
            return None
        try:
            return datetime.strptime(raw, "%a %b %d %H:%M:%S UTC %Y").isoformat()
        except ValueError:
            return raw

    def _build_job_jsonld(self, posting: dict, url: str, location_node: dict):
        # Parent already runs html.unescape + _clean_html on posting["description"].
        job = super()._build_job_jsonld(posting, url, location_node)
        job.source = f"SuccessFactors:{self.host}"
        return job
