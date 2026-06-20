"""Revolut careers scraper.

Revolut runs its own (non third-party) recruitment system on a Next.js site at
https://www.revolut.com/careers/. The careers landing page server-side renders
*every* open position into the embedded ``__NEXT_DATA__`` JSON blob, so a single
request returns the full list (id, title, locations, team) - no pagination, no
headless browser needed.

Each matched job's full HTML description is fetched lazily from its detail page,
whose ``__NEXT_DATA__`` exposes a ``position`` object with a ``description`` field.
"""

import json
import re
from typing import Optional

from .base import BaseScraper
from models import Job


class RevolutScraper(BaseScraper):
    """Scraper for Revolut's self-hosted careers site."""

    # Keywords that mark an ML/DS role from the title alone (the "Data" team is
    # matched directly, so these mainly catch AI roles living under Engineering).
    ML_DS_KEYWORDS = [
        "machine learning", "data scien", "data engineer", "data analyst",
        "deep learning", "nlp", "computer vision", "neural", "llm",
        "genai", "gen ai", "research scientist", "applied scientist",
        "artificial intelligence", " ai ", "ai engineer", "applied ai",
        "reinforcement learning", "analytics engineer",
    ]

    # Teams whose roles are inherently ML/DS regardless of the title wording.
    ML_DS_TEAMS = {"data"}

    # Drop obvious false positives (e.g. legal "data protection" roles).
    EXCLUDE_KEYWORDS = [
        "data protection", "data privacy", "privacy counsel",
    ]

    def __init__(self, company_name: str = "Revolut", domain: str = "revolut.com", **kwargs):
        self.company_name = company_name
        self.domain = domain
        self.base_url = "https://www.revolut.com/careers/"
        super().__init__(**kwargs)

    def get_headers(self) -> dict:
        # Revolut's CDN rejects non-browser user agents, so look like a browser.
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
            "Accept-Encoding": "gzip, deflate",
        }

    @staticmethod
    def _next_data(html: str) -> dict:
        """Extract and parse the embedded Next.js ``__NEXT_DATA__`` JSON."""
        match = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            html,
            re.DOTALL,
        )
        if not match:
            raise ValueError("__NEXT_DATA__ blob not found in page")
        return json.loads(match.group(1))

    @staticmethod
    def _slug(title: str) -> str:
        """Replicate Revolut's URL slug (title lowercased, non-alphanumeric -> '-')."""
        return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")

    def _is_ml_ds_job(self, position: dict) -> bool:
        """Check if a position is ML/DS related based on team and title."""
        title = (position.get("text") or "").lower()
        team = (position.get("team") or "").lower()
        if any(kw in title for kw in self.EXCLUDE_KEYWORDS):
            return False
        if team in self.ML_DS_TEAMS:
            return True
        return any(kw in f"{title} {team}" for kw in self.ML_DS_KEYWORDS)

    def fetch_jobs(self, query: str = "data science", max_results: Optional[int] = None) -> list[Job]:
        """Fetch ML/DS jobs (all countries) from Revolut's careers site."""
        print(f"  [{self.company_name}] Fetching positions from careers site...")

        try:
            response = self._make_request(self.base_url)
            positions = self._next_data(response.text)["props"]["pageProps"]["positions"]
        except Exception as e:
            print(f"  [{self.company_name}] Error: {e}")
            return []

        print(f"  [{self.company_name}] Total positions: {len(positions)}")

        matched = [p for p in positions if self._is_ml_ds_job(p)]
        print(f"  [{self.company_name}] ML/DS jobs: {len(matched)}")

        if max_results:
            matched = matched[:max_results]

        return [self._parse_job(position) for position in matched]

    def _fetch_description(self, url: str) -> Optional[str]:
        """Fetch the full HTML description from a position's detail page."""
        try:
            response = self._make_request(url)
            position = self._next_data(response.text)["props"]["pageProps"]["position"]
            return self._clean_html(position.get("description", "")) or None
        except Exception:
            return None

    def _parse_job(self, position: dict) -> Job:
        """Build a Job from a position (across all of its locations)."""
        position_id = str(position.get("id", ""))
        title = position.get("text", "")
        url = f"https://www.revolut.com/careers/position/{self._slug(title)}-{position_id}/"

        locations = position.get("locations") or []
        office = next((l for l in locations if l.get("type") == "office"), None)
        primary = office or (locations[0] if locations else {})
        city = office.get("name") if office else None
        country = primary.get("country") or ""
        location = ", ".join(l.get("name", "") for l in locations)

        return Job(
            id=position_id,
            title=title,
            company=self.company_name,
            url=url,
            location=location,
            city=city,
            country=country,
            posted_date=None,
            updated_time=None,
            source="Revolut",
            domain=self.domain,
            department=position.get("team"),
            description=self._fetch_description(url),
        )
