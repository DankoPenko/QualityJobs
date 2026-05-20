"""Generic Workday Jobs scraper - works with any company using a Workday (myworkdayjobs.com) career site."""

import json
from typing import Optional
from datetime import datetime

from .base import BaseScraper
from models import Job


class WorkdayScraper(BaseScraper):
    """
    Generic scraper for companies using Workday career sites (*.myworkdayjobs.com).

    Workday exposes a JSON "CXS" API behind every career site:
        POST https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
        GET  https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}{externalPath}

    Two strategies are used, picked automatically per tenant:
      1. If the tenant exposes a genuine Germany location facet, jobs are filtered
         to Germany server-side, then filtered to ML/DS roles by title.
      2. Otherwise the scraper falls back to keyword searches and confirms each
         result's country via the job detail endpoint.

    Usage:
        scraper = WorkdayScraper(
            company_name="NVIDIA",
            tenant="nvidia",
            wd="wd5",
            site="NVIDIAExternalCareerSite",
            domain="nvidia.com",
        )
    """

    MAX_PAGES = 40            # facet mode: 40 x 20 = 800 Germany postings per company
    MAX_PAGES_PER_TERM = 8    # keyword fallback: 8 x 20 = 160 results per search term
    SEARCH_TERMS = ["machine learning", "data scientist", "artificial intelligence"]
    GERMANY_NAMES = ("germany", "deutschland")

    # Keywords for ML/DS job filtering
    ML_DS_KEYWORDS = [
        "machine learning", "data scien", "data engineer", "data analyst",
        "ml ", " ml,", " ml ", "(ml)", "deep learning", "nlp",
        "computer vision", "neural", "llm", "genai", "gen ai",
        "research scientist", "applied scientist", "artificial intelligence",
        "ai research", "ai engineer", "reinforcement learning"
    ]

    # Keywords that indicate NOT an ML/DS job (to filter out false positives)
    EXCLUDE_KEYWORDS = [
        "site reliability", "sre ", "devops",
        "frontend", "front-end", "backend", "back-end", "fullstack",
        "network engineer", "security engineer", "platform engineer"
    ]

    def __init__(self, company_name: str, tenant: str, wd: str, site: str, domain: str = "", **kwargs):
        """
        Initialize Workday scraper for a specific company.

        Args:
            company_name: Display name of the company
            tenant: Workday tenant id (the first label of the host, e.g. 'nvidia')
            wd: Workday data-center subdomain (e.g. 'wd1', 'wd3', 'wd5')
            site: Career site path id (e.g. 'NVIDIAExternalCareerSite', 'LLY')
            domain: Company domain for logo (e.g. 'nvidia.com')
        """
        self.company_name = company_name
        self.tenant = tenant
        self.wd = wd
        self.site = site
        self.domain = domain
        self.host = f"https://{tenant}.{wd}.myworkdayjobs.com"
        self.base_url = f"{self.host}/wday/cxs/{tenant}/{site}"
        super().__init__(**kwargs)

    def get_headers(self) -> dict:
        """Workday's CXS API expects JSON requests."""
        headers = super().get_headers()
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"
        return headers

    def _is_ml_ds_job(self, title: str) -> bool:
        """Check if job is ML/DS related based on the posting title."""
        searchable = title.lower()
        if any(kw in searchable for kw in self.EXCLUDE_KEYWORDS):
            return False
        return any(kw in searchable for kw in self.ML_DS_KEYWORDS)

    def fetch_jobs(self, query: str = "data science", max_results: Optional[int] = None) -> list[Job]:
        """
        Fetch ML/DS jobs in Germany from a Workday career site.

        Returns:
            List of Job objects from Germany, sorted by posted date (newest first)
        """
        print(f"  [{self.company_name}] Fetching jobs from Workday...")

        try:
            facets = self._query({}, offset=0, limit=1).get("facets", [])
        except Exception as e:
            print(f"  [{self.company_name}] Error: {e}")
            return []

        germany = self._find_germany_facets(facets)

        try:
            if germany is not None:
                facet_param, germany_ids = germany
                postings = self._fetch_all_postings({facet_param: germany_ids}, self.MAX_PAGES)
                verify_country = False  # facet already guarantees Germany
            else:
                postings = self._search_by_keywords()
                verify_country = True
        except Exception as e:
            print(f"  [{self.company_name}] Error: {e}")
            return []

        print(f"  [{self.company_name}] Candidate postings: {len(postings)}")

        all_jobs: list[Job] = []
        for posting in postings:
            title = posting.get("title", "")
            if not self._is_ml_ds_job(title):
                continue
            path = posting.get("externalPath")
            if not path:
                continue
            detail = self._fetch_detail(path) or {}
            if verify_country and not self._is_germany_detail(detail, posting):
                continue
            all_jobs.append(self._parse_job(posting, detail, path))

        print(f"  [{self.company_name}] Germany ML/DS jobs: {len(all_jobs)}")

        all_jobs.sort(key=lambda j: self._parse_date(j.posted_date), reverse=True)
        if max_results:
            all_jobs = all_jobs[:max_results]
        return all_jobs

    def _query(self, applied_facets: dict, offset: int, limit: int, search_text: str = "") -> dict:
        """POST a single jobs query to the CXS API."""
        body = {"appliedFacets": applied_facets, "limit": limit,
                "offset": offset, "searchText": search_text}
        response = self.session.post(f"{self.base_url}/jobs", data=json.dumps(body))
        response.raise_for_status()
        return response.json()

    def _find_germany_facets(self, facets: list) -> Optional[tuple[str, list[str]]]:
        """
        Walk the tenant's facet tree to find a usable Germany location filter.

        Returns (facetParameter, [valueIds]) or None. Facet ids are tenant-specific.
        A country-level facet (e.g. 'locationCountry'/'locationHierarchy1') with an
        exact "Germany" value is preferred. Site-level facets ('locations') are only
        used for "<City>, Germany" style values - a bare "Germany" site is ignored
        because some tenants expose it as a near-empty virtual location.
        """
        country: dict[str, list[str]] = {}
        sites: dict[str, list[str]] = {}

        def walk(nodes: list, param: Optional[str]) -> None:
            for node in nodes:
                descriptor = (node.get("descriptor") or "").strip().lower()
                value_id = node.get("id")
                if value_id and param:
                    is_exact = descriptor in self.GERMANY_NAMES
                    has_germany = any(name in descriptor for name in self.GERMANY_NAMES)
                    if is_exact and param != "locations":
                        country.setdefault(param, []).append(value_id)
                    elif has_germany and not is_exact:
                        sites.setdefault(param, []).append(value_id)
                walk(node.get("values") or [], node.get("facetParameter") or param)

        for facet in facets:
            walk(facet.get("values") or [], facet.get("facetParameter"))

        if country:
            param = next(iter(country))
            return (param, country[param])
        if sites:
            param = max(sites, key=lambda p: len(sites[p]))
            return (param, sites[param])
        return None

    def _fetch_all_postings(self, applied_facets: dict, max_pages: int,
                            search_text: str = "") -> list[dict]:
        """Page through every posting matching the applied facets / search text."""
        postings: list[dict] = []
        offset = 0
        limit = 20
        total = None  # Workday only reports `total` reliably on the first page
        for _ in range(max_pages):
            data = self._query(applied_facets, offset, limit, search_text)
            page = data.get("jobPostings", [])
            if not page:
                break
            postings.extend(page)
            if total is None:
                total = data.get("total", 0)
            offset += limit
            if total and offset >= total:
                break
        return postings

    def _search_by_keywords(self) -> list[dict]:
        """Fallback: collect postings via keyword searches, deduped by externalPath."""
        candidates: dict[str, dict] = {}
        for term in self.SEARCH_TERMS:
            for posting in self._fetch_all_postings({}, self.MAX_PAGES_PER_TERM, term):
                path = posting.get("externalPath")
                if path and path not in candidates:
                    candidates[path] = posting
        return list(candidates.values())

    def _is_germany_detail(self, detail: dict, posting: dict) -> bool:
        """Check whether a job detail / posting refers to Germany."""
        country = (detail.get("country") or {}).get("descriptor", "").strip().lower()
        if country in self.GERMANY_NAMES:
            return True
        text = f"{detail.get('location', '')} {posting.get('locationsText', '')}".lower()
        return any(name in text for name in self.GERMANY_NAMES)

    def _fetch_detail(self, external_path: str) -> Optional[dict]:
        """Fetch the full job posting detail (description, location, dates)."""
        try:
            response = self.session.get(f"{self.base_url}{external_path}")
            response.raise_for_status()
            return response.json().get("jobPostingInfo", {})
        except Exception:
            return None

    def _parse_job(self, posting: dict, detail: dict, external_path: str) -> Job:
        """Parse Workday posting + detail data into a Job object."""
        location = detail.get("location") or posting.get("locationsText", "")
        city = location.split(",")[0].strip() if location else None
        description = self._clean_html(detail.get("jobDescription", "")) or None

        return Job(
            id=str(detail.get("jobReqId") or external_path),
            title=detail.get("title") or posting.get("title", ""),
            company=self.company_name,
            url=f"{self.host}/{self.site}{external_path}",
            location=location,
            city=city,
            country="Germany",
            posted_date=detail.get("startDate"),
            updated_time=posting.get("postedOn"),
            source=f"Workday:{self.tenant}",
            domain=self.domain,
            department=None,
            description=description,
        )

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> datetime:
        """Parse Workday date format for sorting."""
        if not date_str:
            return datetime(1900, 1, 1)
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            return datetime(1900, 1, 1)
