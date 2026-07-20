"""Generic Phenom People scraper - works with most *.phenompeople.com-backed career sites.

Two on-disk formats are seen in the wild, both served from /sitemap.xml:

  1. Google-for-Jobs **RSS feed** (e.g. jobs.bayer.com) - every posting is a
     <item> with title, link, full description, g:location, g:id.
  2. Google **sitemap-index** (e.g. careers.allianz.com) -> sub-sitemaps with
     every /job/{id}/{slug} URL, and each detail page embeds a JSON-LD
     JobPosting block with country, city, dates, full description.

The scraper auto-detects which format the host serves and dispatches.
"""

import html
import json
import re
import xml.etree.ElementTree as ET
from typing import Optional
from datetime import datetime

from .base import BaseScraper
from models import Job


class PhenomScraper(BaseScraper):
    """
    Generic scraper for companies running Phenom People career sites.

    Usage:
        scraper = PhenomScraper(
            company_name="Bayer",
            host="jobs.bayer.com",
            domain="bayer.com",
        )
    """

    GOOGLE_JOBS_NS = "{http://base.google.com/ns/1.0}"

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

    GERMANY_NAMES = ("germany", "deutschland")

    # Whether the sitemap's job URLs contain a readable title slug that can be
    # used to skip non-ML detail fetches. Subclasses whose URLs are opaque set
    # this False and pay the cost of fetching every posting.
    prefilter_by_slug: bool = True

    def __init__(self, company_name: str, host: str, domain: str = "",
                 job_url_match: str = "/job/", **kwargs):
        """
        Args:
            company_name: Display name (e.g. "Allianz", "Bayer")
            host: Hostname of the Phenom careers site (e.g. "careers.allianz.com")
            domain: Company domain for logo (e.g. "allianz.com")
            job_url_match: Substring that marks a job-detail URL in the sitemap
                (default "/job/"; some tenants use "/job-", e.g. Deloitte).
        """
        self.company_name = company_name
        self.host = host
        self.domain = domain
        self.job_url_match = job_url_match
        self.base_url = f"https://{host}"
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
        print(f"  [{self.company_name}] Fetching jobs from Phenom...")

        try:
            body = self._make_request(f"{self.base_url}/sitemap.xml").text
        except Exception as e:
            print(f"  [{self.company_name}] Error fetching sitemap.xml: {e}")
            return []

        head = body[:500]
        if "<rss" in head or "<channel>" in head:
            jobs = self._scrape_rss(body)
        elif "<sitemapindex" in head:
            jobs = self._scrape_sitemap_index(body)
        elif "<urlset" in head:
            jobs = self._scrape_urlset(body)
        else:
            print(f"  [{self.company_name}] Unknown sitemap format - skipping")
            return []

        jobs.sort(key=lambda j: self._parse_date(j.posted_date), reverse=True)
        if max_results:
            jobs = jobs[:max_results]
        return jobs

    # ----------------------------- RSS mode -----------------------------

    def _scrape_rss(self, body: str) -> list[Job]:
        """Bayer-style: Google for Jobs RSS with every posting inline."""
        root = ET.fromstring(body)
        items = root.findall(".//item")
        print(f"  [{self.company_name}] RSS feed items: {len(items)}")

        all_jobs: list[Job] = []
        germany_count = 0
        for item in items:
            location = item.findtext(f"{self.GOOGLE_JOBS_NS}location", "") or ""
            if not self._location_is_germany(location):
                continue
            germany_count += 1
            title = item.findtext("title", "") or ""
            if not self._is_ml_ds_title(title):
                continue
            all_jobs.append(self._build_job_rss(item, location))

        print(f"  [{self.company_name}] Germany jobs: {germany_count}, ML/DS jobs: {len(all_jobs)}")
        return all_jobs

    def _build_job_rss(self, item: ET.Element, location: str) -> Job:
        title = (item.findtext("title", "") or "").strip()
        link = (item.findtext("link", "") or "").strip()
        job_id = (item.findtext(f"{self.GOOGLE_JOBS_NS}id") or item.findtext("guid") or "").strip()
        department = (item.findtext(f"{self.GOOGLE_JOBS_NS}job_function") or "").strip() or None
        expiration = (item.findtext(f"{self.GOOGLE_JOBS_NS}expiration_date") or "").strip() or None
        description_raw = (item.findtext("description") or "").strip()
        description = self._clean_html(html.unescape(description_raw)) if description_raw else None

        # g:location is "City, State, CC" - first segment is the city.
        city = location.split(",")[0].strip() or None

        return Job(
            id=job_id or link,
            title=title,
            company=self.company_name,
            url=link,
            location=location,
            city=city,
            country="Germany",
            posted_date=None,  # RSS only carries expiration; leave posted blank
            updated_time=expiration,
            source=f"Phenom:{self.host}",
            domain=self.domain,
            department=department,
            description=description,
        )

    @staticmethod
    def _location_is_germany(location: str) -> bool:
        """Check Bayer-style location strings: 'Berlin, Berlin, DE' or 'Monheim, Nordrhein-Westfalen, DE'."""
        loc = location.lower()
        if any(name in loc for name in PhenomScraper.GERMANY_NAMES):
            return True
        last_segment = loc.rsplit(",", 1)[-1].strip()
        return last_segment in ("de", "ger")

    # --------------------------- Sitemap mode ---------------------------

    def _scrape_sitemap_index(self, body: str) -> list[Job]:
        """Allianz-style: <sitemapindex> -> sub-sitemaps -> /job/{id}/{slug} URLs."""
        sub_sitemaps = re.findall(r"<loc>([^<]+)</loc>", body)
        seen: set[str] = set()
        job_urls: list[str] = []
        for sm in sub_sitemaps:
            try:
                sub_body = self._make_request(sm).text
            except Exception:
                continue
            for url in self._sitemap_locs(sub_body):
                if self.job_url_match in url and url not in seen:
                    seen.add(url)
                    job_urls.append(url)
        return self._scrape_job_url_list(job_urls)

    def _scrape_urlset(self, body: str) -> list[Job]:
        """Single-sitemap <urlset> with job-detail URLs inline."""
        job_urls = [u for u in self._sitemap_locs(body) if self.job_url_match in u]
        return self._scrape_job_url_list(job_urls)

    @staticmethod
    def _sitemap_locs(body: str) -> list[str]:
        """Extract <loc> URLs, unescaping XML entities (&amp; in query strings)."""
        return [html.unescape(u) for u in re.findall(r"<loc>([^<]+)</loc>", body)]

    def _scrape_job_url_list(self, job_urls: list[str]) -> list[Job]:
        print(f"  [{self.company_name}] Total job URLs: {len(job_urls)}")
        if self.prefilter_by_slug:
            candidates = [u for u in job_urls if self._is_ml_ds_title(self._slug_text(u))]
        else:
            # Tenant's job URLs carry no readable title (e.g. Lufthansa's
            # ?ac=jobad&id=123), so every detail page has to be fetched and
            # filtered on its JSON-LD title instead.
            candidates = job_urls
        print(f"  [{self.company_name}] ML/DS candidates: {len(candidates)}")

        all_jobs: list[Job] = []
        for url in candidates:
            posting = self._fetch_job_posting(url)
            if posting is None:
                continue
            if not self.prefilter_by_slug and not self._is_ml_ds_title(posting.get("title", "")):
                continue
            germany_location = self._first_germany_location_jsonld(posting)
            if germany_location is None:
                continue
            all_jobs.append(self._build_job_jsonld(posting, url, germany_location))

        print(f"  [{self.company_name}] Germany ML/DS jobs: {len(all_jobs)}")
        return all_jobs

    @staticmethod
    def _slug_text(url: str) -> str:
        """Convert the job URL's title slug ('IT-Architect-Principal') back to readable text."""
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        return slug.replace("-", " ")

    def _fetch_job_posting(self, url: str) -> Optional[dict]:
        """Fetch a job detail page and return its JSON-LD JobPosting block."""
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
            # A block may be the posting itself, a list of nodes, or a Yoast
            # style {"@graph": [...]} wrapper (Mercedes-Benz).
            if isinstance(data, dict) and "@graph" in data:
                data = data["@graph"]
            if isinstance(data, list):
                data = next((d for d in data if isinstance(d, dict) and d.get("@type") == "JobPosting"), None)
            if isinstance(data, dict) and data.get("@type") == "JobPosting":
                return data
        return None

    @staticmethod
    def _first_germany_location_jsonld(posting: dict) -> Optional[dict]:
        """Return the first jobLocation whose addressCountry is Germany, or None.
        `jobLocation` can be a dict or a list (multi-location)."""
        raw = posting.get("jobLocation")
        locations = raw if isinstance(raw, list) else [raw] if raw else []
        for loc in locations:
            if not isinstance(loc, dict):
                continue
            address = loc.get("address") or {}
            country = (address.get("addressCountry") or "").strip().lower()
            # addressCountry may be a name ("Germany"/"Deutschland") or an ISO
            # code - alpha-2 "DE" (Deloitte, NORD/LB) or alpha-3 "DEU" (PwC).
            if country in PhenomScraper.GERMANY_NAMES or country in ("de", "deu"):
                return loc
        return None

    def _build_job_jsonld(self, posting: dict, url: str, location_node: dict) -> Job:
        # schema.org allows identifier to be a PropertyValue object or a bare
        # string (Munich Re uses the latter).
        identifier = posting.get("identifier") or {}
        if isinstance(identifier, dict):
            identifier = identifier.get("value")
        job_id = str(identifier or url.rsplit("/", 2)[-2])
        title = posting.get("title") or self._slug_text(url).strip()

        address = location_node.get("address", {})
        city = address.get("addressLocality") or None
        region = address.get("addressRegion") or ""
        location = ", ".join(p for p in (city, region, "Germany") if p)

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
            source=f"Phenom:{self.host}",
            domain=self.domain,
            department=None,
            description=description,
        )

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> datetime:
        if not date_str:
            return datetime(1900, 1, 1)
        try:
            parsed = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            return datetime(1900, 1, 1)
        # Strip tzinfo so all returned datetimes are naive (mix would crash sort).
        return parsed.replace(tzinfo=None) if parsed.tzinfo is not None else parsed
