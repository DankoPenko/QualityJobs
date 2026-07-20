"""Munich Re careers scraper (careers.munichre.com).

Not a Phenom tenant, but the same shape: a single <urlset> sitemap listing
job-detail URLs whose pages embed a JSON-LD JobPosting block, so it reuses
``PhenomScraper``.

Its URLs end with two numeric ids::

    /en/job/{city}/{title-slug}/{org-id}/{job-id}

which ``PhenomScraper._slug_text`` handles generically by skipping trailing
numeric segments, so no override is needed here.

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
