"""BMW Group jobs scraper - jobs.bmwgroup.com (Jobs2Web / SuccessFactors HTML)."""

import html
import re
from typing import Optional
from datetime import datetime

from .base import BaseScraper
from models import Job


class BMWScraper(BaseScraper):
    """
    Scraper for BMW Group's careers site at jobs.bmwgroup.com.

    BMW runs Jobs2Web (a SuccessFactors recruiting front-end) without a
    public JSON API. Search results are server-rendered HTML at
        https://jobs.bmwgroup.com/search?q={term}&startrow={n}
    with one `<tr class="data-row">` per posting.

    The scraper runs a handful of ML/AI keyword searches, pages through each,
    filters to Germany via the ", DE," country code in the location string,
    and fetches each matching job's detail page for its description.
    """

    base_url = "https://jobs.bmwgroup.com"
    company_name = "BMW Group"

    SEARCH_TERMS = ["machine learning", "data scientist", "artificial intelligence"]
    MAX_PAGES_PER_TERM = 5  # 25 results per page; 5 pages = up to 125 per term

    ML_DS_KEYWORDS = [
        "machine learning", "data scien", "data engineer", "data analyst",
        "ml ", " ml,", " ml ", "(ml)", "deep learning", "nlp",
        "computer vision", "neural", "llm", "genai", "gen ai",
        "research scientist", "applied scientist", "artificial intelligence",
        "ai research", "ai engineer", "reinforcement learning",
        # German equivalents BMW often uses
        " ki ", " ki,", " ki-", "(ki)", "künstliche intelligenz",
    ]

    EXCLUDE_KEYWORDS = [
        "site reliability", "sre ", "devops",
        "frontend", "front-end", "backend", "back-end", "fullstack",
        "network engineer", "security engineer", "platform engineer"
    ]

    def __init__(self, **kwargs):
        self.domain = "bmwgroup.com"
        super().__init__(**kwargs)

    def get_headers(self) -> dict:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
        }

    def _is_ml_ds_job(self, title: str) -> bool:
        searchable = title.lower()
        if any(kw in searchable for kw in self.EXCLUDE_KEYWORDS):
            return False
        return any(kw in searchable for kw in self.ML_DS_KEYWORDS)

    def fetch_jobs(self, query: str = "machine learning", max_results: Optional[int] = None) -> list[Job]:
        """Search BMW's career site for ML/AI roles in Germany."""
        print(f"  [{self.company_name}] Fetching jobs from BMW...")

        # Collect candidate postings across all search terms, deduped by job id.
        candidates: dict[str, dict] = {}
        for term in self.SEARCH_TERMS:
            try:
                self._collect_term(term, candidates)
            except Exception as e:
                print(f"  [{self.company_name}] Error searching '{term}': {e}")

        print(f"  [{self.company_name}] Candidate postings: {len(candidates)}")

        all_jobs: list[Job] = []
        for posting in candidates.values():
            if ", DE," not in posting["location"]:
                continue
            if not self._is_ml_ds_job(posting["title"]):
                continue
            description = self._fetch_description(posting["path"])
            all_jobs.append(self._build_job(posting, description))

        print(f"  [{self.company_name}] Germany ML/DS jobs: {len(all_jobs)}")

        all_jobs.sort(key=lambda j: self._parse_date(j.posted_date), reverse=True)
        if max_results:
            all_jobs = all_jobs[:max_results]
        return all_jobs

    def _collect_term(self, term: str, candidates: dict[str, dict]) -> None:
        """Page through one search-term query, adding postings to `candidates`."""
        for page in range(self.MAX_PAGES_PER_TERM):
            startrow = page * 25
            url = f"{self.base_url}/search"
            response = self._make_request(url, params={"q": term, "startrow": startrow})
            postings = self._parse_search_page(response.text)
            if not postings:
                break
            for posting in postings:
                candidates.setdefault(posting["id"], posting)
            if len(postings) < 25:
                break  # last page

    def _parse_search_page(self, page_html: str) -> list[dict]:
        """Extract postings from one search results page."""
        rows = re.findall(r'<tr\s+class="data-row".*?</tr>', page_html, re.DOTALL)
        postings: list[dict] = []
        for row in rows:
            link = re.search(r'<a\s+class="jobTitle-link"\s+href="([^"]+)"[^>]*>([^<]+)</a>', row)
            location = re.search(r'<td\s+class="colLocation[^"]*"[^>]*>\s*<span[^>]*>\s*([^<]+?)\s*</span>', row, re.DOTALL)
            date = re.search(r'<td\s+class="colDate[^"]*"[^>]*>\s*<span[^>]*>\s*([^<]+?)\s*</span>', row, re.DOTALL)
            if not link:
                continue
            path = link.group(1)
            job_id_match = re.search(r'/(\d+)/?$', path)
            if not job_id_match:
                continue
            postings.append({
                "id": job_id_match.group(1),
                "path": html.unescape(path),
                "title": html.unescape(link.group(2).strip()),
                "location": html.unescape(location.group(1).strip()) if location else "",
                "date": date.group(1).strip() if date else "",
            })
        return postings

    def _fetch_description(self, path: str) -> Optional[str]:
        try:
            response = self._make_request(f"{self.base_url}{path}")
        except Exception:
            return None
        match = re.search(
            r'<div[^>]*class="[^"]*jobdescription[^"]*"[^>]*>(.*?)</div>\s*(?:<div|<footer|</section|</main)',
            response.text, re.DOTALL | re.IGNORECASE,
        )
        if not match:
            return None
        return self._clean_html(match.group(1)) or None

    def _build_job(self, posting: dict, description: Optional[str]) -> Job:
        location = posting["location"]
        # Location format: "Munich, BY, DE, 80809" - first segment is the city.
        city = location.split(",")[0].strip() if location else None
        posted_iso = None
        if posting["date"]:
            try:
                posted_iso = datetime.strptime(posting["date"], "%b %d, %Y").date().isoformat()
            except ValueError:
                pass
        return Job(
            id=posting["id"],
            title=posting["title"],
            company=self.company_name,
            url=f"{self.base_url}{posting['path']}",
            location=location,
            city=city,
            country="Germany",
            posted_date=posted_iso,
            updated_time=posting["date"] or None,
            source="BMW",
            domain=self.domain,
            department=None,
            description=description,
        )

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> datetime:
        if not date_str:
            return datetime(1900, 1, 1)
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            return datetime(1900, 1, 1)
