"""Base scraper class that all company scrapers inherit from."""

from abc import ABC, abstractmethod
from typing import Optional
import requests

from models import Job


class BaseScraper(ABC):
    """
    Abstract base class for all job scrapers.

    Each company scraper must implement:
    - company_name: The name of the company
    - fetch_jobs(): Method to fetch and return jobs

    Optionally override:
    - country_code: Default country to filter (default: "DEU" for Germany)
    - base_url: The API or website URL
    - headers: HTTP headers for requests
    """

    company_name: str = "Unknown"
    country_code: str = "DEU"
    base_url: str = ""

    def __init__(self, country_code: Optional[str] = None):
        """
        Initialize the scraper.

        Args:
            country_code: Override the default country code
        """
        if country_code:
            self.country_code = country_code

        self.session = requests.Session()
        self.session.headers.update(self.get_headers())

    def get_headers(self) -> dict:
        """
        Return HTTP headers for requests.
        Override in subclass if needed.
        """
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/html, */*",
            "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
            "Accept-Encoding": "gzip, deflate",
        }

    @abstractmethod
    def fetch_jobs(self, query: str, max_results: Optional[int] = None) -> list[Job]:
        """
        Fetch jobs from the company's career page.

        Args:
            query: Search query (e.g., "machine learning")
            max_results: Maximum number of jobs to fetch (None for all)

        Returns:
            List of Job objects
        """
        pass

    def _make_request(self, url: str, params: Optional[dict] = None) -> requests.Response:
        """
        Make an HTTP GET request with error handling.

        Args:
            url: The URL to request
            params: Query parameters

        Returns:
            Response object

        Raises:
            requests.RequestException: If the request fails
        """
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} company='{self.company_name}' country='{self.country_code}'>"
