"""Munich Re careers scraper (careers.munichre.com).

Not a Phenom tenant, but the same shape: a single <urlset> sitemap listing
job-detail URLs whose pages embed a JSON-LD JobPosting block, so it reuses
``PhenomScraper``.

The one difference is the URL layout. Phenom puts the title slug in the last
path segment; Munich Re ends its URLs with two numeric ids::

    /en/job/{city}/{title-slug}/{org-id}/{job-id}

so the title has to be read from the third-from-last segment instead.

Note on robots.txt: careers.munichre.com disallows ``/search-jobs/`` for every
agent except IndeedJobBot. The sitemap and the ``/en/job/`` detail pages are not
disallowed, which is why this scraper goes through the sitemap and never touches
the search endpoint.
"""

from .phenom import PhenomScraper


class MunichReScraper(PhenomScraper):
    """Munich Re - sitemap + JSON-LD, with a mid-path title slug."""

    def __init__(self, **kwargs):
        kwargs.setdefault("company_name", "Munich Re")
        kwargs.setdefault("host", "careers.munichre.com")
        kwargs.setdefault("domain", "munichre.com")
        kwargs.setdefault("job_url_match", "/job/")
        super().__init__(**kwargs)

    def _slug_text(self, url: str) -> str:
        """Read the title from /en/job/{city}/{title}/{org}/{id}."""
        parts = [p for p in url.rstrip("/").split("/") if p]
        if len(parts) >= 3 and parts[-1].isdigit() and parts[-2].isdigit():
            return parts[-3].replace("-", " ")
        return super()._slug_text(url)
