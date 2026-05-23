"""Allianz Group jobs scraper - careers.allianz.com (Phenom People)."""

import html
import json
import re
from typing import Optional
from datetime import datetime

from .base import BaseScraper
from models import Job


class AllianzScraper(BaseScraper):
    """
    Scraper for Allianz's careers site at careers.allianz.com.

    The Vue 3 SPA loads jobs via XHR with rotating tokens, but Allianz also
    publishes a Google sitemap index at /sitemap.xml that lists every job URL
    and every job detail page embeds a JSON-LD JobPosting block with country,
    city, and the full description. The scraper:

      1. Walks the sitemap index, collecting every /job/{id}/{slug} URL.
      2. Filters URLs by the title slug against ML/AI keywords.
      3. Fetches each candidate's HTML and parses the JSON-LD JobPosting.
      4. Keeps only jobs whose addressCountry is Germany.
    """

    base_url = "https://careers.allianz.com"
    company_name = "Allianz"

    ML_DS_KEYWORDS = [
        "machine learning", "data scien", "data engineer", "data analyst",
        "ml ", " ml,", " ml ", "(ml)", "deep learning", "nlp",
        "computer vision", "neural", "llm", "genai", "gen ai",
        "research scientist", "applied scientist", "artificial intelligence",
        "ai research", "ai engineer", "reinforcement learning",
        # German equivalents
        " ki ", " ki,", " ki-", "(ki)", "künstliche intelligenz", "kuenstliche",
    ]

    EXCLUDE_KEYWORDS = [
        "site reliability", "sre ", "devops",
        "frontend", "front-end", "backend", "back-end", "fullstack",
        "network engineer", "security engineer", "platform engineer"
    ]

    def __init__(self, **kwargs):
        self.domain = "allianz.com"
        super().__init__(**kwargs)

    def get_headers(self) -> dict:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xml,*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def _is_ml_ds_title(self, title_text: str) -> bool:
        searchable = title_text.lower()
        if any(kw in searchable for kw in self.EXCLUDE_KEYWORDS):
            return False
        return any(kw in searchable for kw in self.ML_DS_KEYWORDS)

    def fetch_jobs(self, query: str = "machine learning", max_results: Optional[int] = None) -> list[Job]:
        print(f"  [{self.company_name}] Fetching jobs from Allianz...")

        try:
            job_urls = self._collect_job_urls()
        except Exception as e:
            print(f"  [{self.company_name}] Error walking sitemap: {e}")
            return []

        print(f"  [{self.company_name}] Total job URLs in sitemap: {len(job_urls)}")

        # Filter by title slug - cheap client-side filter to avoid fetching every detail page.
        candidates = [u for u in job_urls if self._is_ml_ds_title(self._slug_text(u))]
        print(f"  [{self.company_name}] ML/DS candidates: {len(candidates)}")

        all_jobs: list[Job] = []
        for url in candidates:
            posting = self._fetch_job_posting(url)
            if posting is None:
                continue
            germany_location = self._first_germany_location(posting)
            if germany_location is None:
                continue
            all_jobs.append(self._build_job(posting, url, germany_location))

        print(f"  [{self.company_name}] Germany ML/DS jobs: {len(all_jobs)}")

        all_jobs.sort(key=lambda j: self._parse_date(j.posted_date), reverse=True)
        if max_results:
            all_jobs = all_jobs[:max_results]
        return all_jobs

    def _collect_job_urls(self) -> list[str]:
        """Walk /sitemap.xml -> sub-sitemaps and return every /job/ URL."""
        index = self._make_request(f"{self.base_url}/sitemap.xml").text
        sub_sitemaps = re.findall(r"<loc>([^<]+)</loc>", index)
        job_urls: list[str] = []
        seen: set[str] = set()
        for sitemap_url in sub_sitemaps:
            try:
                body = self._make_request(sitemap_url).text
            except Exception:
                continue
            for url in re.findall(r"<loc>([^<]+/job/[^<]+)</loc>", body):
                if url not in seen:
                    seen.add(url)
                    job_urls.append(url)
        return job_urls

    @staticmethod
    def _slug_text(url: str) -> str:
        """Convert the job URL's title slug ('IT-Architect-Principal') back to readable text."""
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        return slug.replace("-", " ")

    def _fetch_job_posting(self, url: str) -> Optional[dict]:
        """Fetch a job detail page and parse its JSON-LD JobPosting block."""
        try:
            body = self._make_request(url).text
        except Exception:
            return None
        for match in re.finditer(
            r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
            body, re.DOTALL,
        ):
            payload = match.group(1).strip()
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if isinstance(data, list):
                data = next((d for d in data if isinstance(d, dict) and d.get("@type") == "JobPosting"), None)
            if isinstance(data, dict) and data.get("@type") == "JobPosting":
                return data
        return None

    @staticmethod
    def _first_germany_location(posting: dict) -> Optional[dict]:
        """Return the first jobLocation whose addressCountry is Germany, or None.
        `jobLocation` can be a dict (single location) or a list (multi-location)."""
        raw = posting.get("jobLocation")
        locations = raw if isinstance(raw, list) else [raw] if raw else []
        for loc in locations:
            if not isinstance(loc, dict):
                continue
            address = loc.get("address") or {}
            country = (address.get("addressCountry") or "").strip().lower()
            if country in ("germany", "deutschland"):
                return loc
        return None

    def _build_job(self, posting: dict, url: str, location_node: dict) -> Job:
        identifier = posting.get("identifier", {})
        job_id = str(identifier.get("value") or url.rsplit("/", 2)[-2])
        title = posting.get("title") or self._slug_text(url).strip()

        address = location_node.get("address", {})
        city = address.get("addressLocality") or None
        region = address.get("addressRegion") or ""
        location_parts = [p for p in (city, region, "Germany") if p]
        location = ", ".join(location_parts)

        # JSON-LD descriptions are HTML-escaped (e.g. "&lt;p&gt;") - decode then strip tags.
        description = posting.get("description") or ""
        if description:
            description = self._clean_html(html.unescape(description)) or None
        else:
            description = None

        return Job(
            id=job_id,
            title=title,
            company=self.company_name,
            url=url,
            location=location,
            city=city,
            country="Germany",
            posted_date=posting.get("datePosted") or None,
            updated_time=None,
            source="Allianz",
            domain=self.domain,
            department=None,
            description=description,
        )

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> datetime:
        if not date_str:
            return datetime(1900, 1, 1)
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            return datetime(1900, 1, 1)
