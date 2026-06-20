"""Generic Jobs2Web / SuccessFactors career-site scraper.

Many large employers run **Jobs2Web** (a SuccessFactors recruiting front-end)
with no public JSON API. Two server-friendly data sources exist, and tenants
differ in which one is usable:

1. **HTML search** — ``https://{host}/search?q={term}&startrow={n}`` returns
   server-rendered results with one ``<tr class="data-row">`` per posting. This
   works on classic tenants (e.g. adidas).
2. **RSS feed** — ``https://{host}/services/rss/job/?locale=en_US&keywords=({term})``
   returns the (latest) matching jobs as an RSS document, each ``<item>`` carrying
   the title (with a trailing ``(City, Region, CC)``), link, pubDate and the full
   job description inline. Tenants that migrated to the client-rendered
   "searchResultsUnify" template (e.g. BMW) no longer expose ``data-row`` in the
   initial HTML, so the RSS feed is the only requests-friendly source.

``mode="auto"`` (default) tries HTML first and falls back to RSS when HTML yields
nothing, so a single config handles either tenant generation. Adding a Jobs2Web
company is a one-line config (host + display name), mirroring ``WorkdayScraper``.

Usage::

    scraper = Jobs2WebScraper(
        company_name="adidas",
        host="jobs.adidas-group.com",
        domain="adidas.com",
        source="adidas",
    )
"""

import html
import re
from typing import Optional
from datetime import datetime
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

from .base import BaseScraper
from models import Job


class Jobs2WebScraper(BaseScraper):
    """Generic scraper for Jobs2Web / SuccessFactors career sites."""

    SEARCH_TERMS = ["machine learning", "data scientist", "artificial intelligence"]
    MAX_PAGES_PER_TERM = 5  # HTML pages are 25-50 rows; 5 pages covers ML/DS

    ML_DS_KEYWORDS = [
        "machine learning", "data scien", "data engineer", "data analyst",
        "ml ", " ml,", " ml ", "(ml)", "deep learning", "nlp",
        "computer vision", "neural", "llm", "genai", "gen ai",
        "research scientist", "applied scientist", "artificial intelligence",
        "ai research", "ai engineer", "reinforcement learning",
        # German equivalents these sites often use
        " ki ", " ki,", " ki-", "(ki)", "künstliche intelligenz",
    ]

    EXCLUDE_KEYWORDS = [
        "site reliability", "sre ", "devops",
        "frontend", "front-end", "backend", "back-end", "fullstack",
        "network engineer", "security engineer", "platform engineer",
    ]

    def __init__(self, company_name: str, host: str, domain: str = "",
                 source: Optional[str] = None, country_code_token: str = "DE",
                 country_name: str = "Germany", mode: str = "auto", **kwargs):
        """
        Args:
            company_name: Display name of the company.
            host: Jobs2Web host, e.g. ``jobs.adidas-group.com`` (no scheme).
            domain: Company domain for logos, e.g. ``adidas.com``.
            source: Value stored in ``Job.source`` (defaults to ``company_name``).
            country_code_token: ISO-2 country code that marks the target country
                in the location cell. Jobs2Web renders locations as
                ``City, Region, CC`` or ``City, Region, CC, ZIP``; the country is
                the last 2-letter uppercase token (``DE`` = Germany).
            country_name: Human-readable country stored on each Job.
            mode: ``"auto"`` (HTML, fall back to RSS), ``"html"`` or ``"rss"``.
        """
        self.company_name = company_name
        self.host = host.replace("https://", "").replace("http://", "").rstrip("/")
        self.base_url = f"https://{self.host}"
        self.domain = domain
        self.source = source or company_name
        self.country_code_token = country_code_token.upper()
        self.country_name = country_name
        self.mode = mode
        super().__init__(**kwargs)

    def get_headers(self) -> dict:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
        }

    # ------------------------------------------------------------------ filters
    def _is_ml_ds_job(self, title: str) -> bool:
        searchable = title.lower()
        if any(kw in searchable for kw in self.EXCLUDE_KEYWORDS):
            return False
        return any(kw in searchable for kw in self.ML_DS_KEYWORDS)

    def _in_target_country(self, location: str) -> bool:
        """True if the location's country code matches the target.

        The country code is the last 2-letter uppercase comma-separated token,
        skipping a trailing ZIP. This handles both ``City, BY, DE`` and
        ``City, BY, DE, 80809`` while rejecting US-state false positives like
        ``Rehoboth Beach, DE, US`` (where the final country token is ``US``).
        """
        for part in reversed([p.strip() for p in location.split(",")]):
            if len(part) == 2 and part.isalpha() and part.isupper():
                return part == self.country_code_token
        return False

    # -------------------------------------------------------------- entry point
    def fetch_jobs(self, query: str = "machine learning", max_results: Optional[int] = None) -> list[Job]:
        """Search the career site for ML/AI roles in the target country."""
        print(f"  [{self.company_name}] Fetching jobs from Jobs2Web ({self.host})...")

        candidates: dict[str, dict] = {}
        if self.mode in ("auto", "html"):
            self._collect_html(candidates)
            if not candidates and self.mode == "auto":
                print(f"  [{self.company_name}] HTML search empty - falling back to RSS feed")
                self._collect_rss(candidates)
        elif self.mode == "rss":
            self._collect_rss(candidates)

        print(f"  [{self.company_name}] Candidate postings: {len(candidates)}")

        all_jobs: list[Job] = []
        for posting in candidates.values():
            if not self._in_target_country(posting["location"]):
                continue
            if not self._is_ml_ds_job(posting["title"]):
                continue
            description = posting.get("description")
            if description is None and posting.get("path"):
                description = self._fetch_description(posting["path"])
            all_jobs.append(self._build_job(posting, description))

        print(f"  [{self.company_name}] {self.country_name} ML/DS jobs: {len(all_jobs)}")

        all_jobs.sort(key=lambda j: self._parse_date(j.posted_date), reverse=True)
        if max_results:
            all_jobs = all_jobs[:max_results]
        return all_jobs

    # --------------------------------------------------------------- HTML mode
    def _collect_html(self, candidates: dict[str, dict]) -> None:
        for term in self.SEARCH_TERMS:
            try:
                self._collect_html_term(term, candidates)
            except Exception as e:
                print(f"  [{self.company_name}] HTML error searching '{term}': {e}")

    def _collect_html_term(self, term: str, candidates: dict[str, dict]) -> None:
        """Page through one HTML search-term query.

        Pagination advances by the number of rows actually returned, so it is
        robust to differing page sizes across tenants (BMW 25, adidas 50).
        """
        startrow = 0
        for _ in range(self.MAX_PAGES_PER_TERM):
            response = self._make_request(f"{self.base_url}/search",
                                          params={"q": term, "startrow": startrow})
            postings = self._parse_search_page(response.text)
            if not postings:
                break
            for posting in postings:
                candidates.setdefault(posting["id"], posting)
            startrow += len(postings)

    def _parse_search_page(self, page_html: str) -> list[dict]:
        """Extract postings from one HTML search results page."""
        rows = re.findall(r'<tr\s+class="data-row".*?</tr>', page_html, re.DOTALL)
        postings: list[dict] = []
        for row in rows:
            link = re.search(r'<a\s+class="jobTitle-link"\s+href="([^"]+)"[^>]*>([^<]+)</a>', row)
            location = re.search(r'<td\s+class="colLocation[^"]*"[^>]*>\s*<span[^>]*>\s*([^<]+?)\s*</span>', row, re.DOTALL)
            date = re.search(r'<td\s+class="colDate[^"]*"[^>]*>\s*<span[^>]*>\s*([^<]+?)\s*</span>', row, re.DOTALL)
            if not link:
                continue
            path = html.unescape(link.group(1))
            job_id_match = re.search(r'/(\d+)/?(?:\?|$)', path)
            if not job_id_match:
                continue
            postings.append({
                "id": job_id_match.group(1),
                "path": path,
                "url": path if path.startswith("http") else f"{self.base_url}{path}",
                "title": html.unescape(link.group(2).strip()),
                "location": html.unescape(location.group(1).strip()) if location else "",
                "date": date.group(1).strip() if date else "",
                "description": None,
            })
        return postings

    def _fetch_description(self, path: str) -> Optional[str]:
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        try:
            response = self._make_request(url)
        except Exception:
            return None
        match = re.search(
            r'<div[^>]*class="[^"]*jobdescription[^"]*"[^>]*>(.*?)</div>\s*(?:<div|<footer|</section|</main)',
            response.text, re.DOTALL | re.IGNORECASE,
        )
        if not match:
            return None
        return self._clean_html(match.group(1)) or None

    # ---------------------------------------------------------------- RSS mode
    _RSS_LOC_RE = re.compile(r'^(.*)\s+\(([^()]*)\)\s*$')

    def _collect_rss(self, candidates: dict[str, dict]) -> None:
        for term in self.SEARCH_TERMS:
            try:
                response = self._make_request(
                    f"{self.base_url}/services/rss/job/",
                    params={"locale": "en_US", "keywords": f"({term})"},
                )
                root = ET.fromstring(response.content)
            except Exception as e:
                print(f"  [{self.company_name}] RSS error searching '{term}': {e}")
                continue
            for item in root.findall(".//item"):
                self._add_rss_item(item, candidates)

    def _add_rss_item(self, item: ET.Element, candidates: dict[str, dict]) -> None:
        raw_title = (item.findtext("title") or "").strip()
        m = self._RSS_LOC_RE.match(raw_title)
        if m:
            title, location = m.group(1).strip(), m.group(2).strip()
        else:
            title, location = raw_title, ""
        link = (item.findtext("link") or "").strip()
        id_match = re.search(r'/(\d+)/?(?:\?|$)', link)
        job_id = id_match.group(1) if id_match else (item.findtext("guid") or link)
        if not job_id or job_id in candidates:
            return
        candidates[job_id] = {
            "id": job_id,
            "path": "",
            "url": link,
            "title": title,
            "location": location,
            "date": (item.findtext("pubDate") or "").strip(),
            "description": self._clean_html(item.findtext("description") or "") or None,
        }

    # -------------------------------------------------------------- build / util
    def _build_job(self, posting: dict, description: Optional[str]) -> Job:
        location = posting["location"]
        # Location format: "Munich, BY, DE, 80809" - first segment is the city.
        city = location.split(",")[0].strip() if location else None
        url = posting.get("url") or (
            posting["path"] if posting.get("path", "").startswith("http")
            else f"{self.base_url}{posting.get('path', '')}"
        )
        return Job(
            id=posting["id"],
            title=posting["title"],
            company=self.company_name,
            url=url,
            location=location,
            city=city,
            country=self.country_name,
            posted_date=self._to_iso(posting["date"]),
            updated_time=posting["date"] or None,
            source=self.source,
            domain=self.domain,
            department=None,
            description=description,
        )

    @staticmethod
    def _to_iso(date_str: Optional[str]) -> Optional[str]:
        """Normalise the various Jobs2Web date formats to an ISO date string.

        HTML search renders ``Jun 12, 2026``; the RSS feed renders RFC-822
        (``Sat, 20 Jun 2026 02:01:00 GMT``).
        """
        if not date_str:
            return None
        date_str = date_str.strip()
        try:
            return datetime.strptime(date_str, "%b %d, %Y").date().isoformat()
        except ValueError:
            pass
        try:
            return parsedate_to_datetime(date_str).date().isoformat()
        except (TypeError, ValueError):
            pass
        try:
            return datetime.fromisoformat(date_str).date().isoformat()
        except ValueError:
            return None

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> datetime:
        if not date_str:
            return datetime(1900, 1, 1)
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            return datetime(1900, 1, 1)
